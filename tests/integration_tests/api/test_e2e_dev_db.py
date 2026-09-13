"""End-to-end against the real dev database: full lifespan (bootstrap poll
of all five tables), then every endpoint over the real ASGI stack.

Assertions are on shape, invariants and internal consistency rather than
exact values, since dev data moves. Skipped automatically when dev
credentials aren't available, so this stays runnable in a bare checkout.
"""

import os
from datetime import datetime

import pytest
from dotenv import load_dotenv

load_dotenv(".env.dev", override=True)

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_READ_URL"),
    reason="dev DATABASE_READ_URL not configured",
)

SOLAR_COLS = {"density", "speed", "temperature", "bz", "bx", "by", "bt", "pressure"}
TABLES = ["solar", "dst", "dst_predictions", "kp", "ssn"]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as c:  # runs the real lifespan: initial_load + pollers
        yield c


def _times(rows):
    return [datetime.fromisoformat(r["time"]) for r in rows]


class TestStartup:
    def test_health_is_ok_after_bootstrap(self, client):
        assert client.get("/health").json()["status"] == "ok"

    def test_every_table_loaded_rows(self, client):
        tables = client.get("/health").json()["tables"]
        for name in TABLES:
            assert tables[name]["rows"] > 0, f"{name} loaded no rows"

    def test_every_table_has_a_watermark(self, client):
        tables = client.get("/health").json()["tables"]
        for name in TABLES:
            assert tables[name]["last_updated_at"] is not None


class TestEveryEndpointResponds:
    @pytest.mark.parametrize(
        "path,params",
        [
            ("/solar-wind/raw", {"interval": "24h"}),
            ("/solar-wind/raw", {"interval": "7d"}),
            ("/solar-wind/monthly", None),
            ("/solar-wind/latest", None),
            ("/dst", {"interval": "24h"}),
            ("/dst", {"interval": "7d"}),
            ("/dst", {"interval": "1mo"}),
            ("/dst/latest", None),
            ("/dst/next-prediction", None),
            ("/kp", {"interval": "24h"}),
            ("/kp", {"interval": "1mo"}),
            ("/kp/latest", None),
            ("/ssn/full-cycle", None),
            ("/health", None),
        ],
    )
    def test_returns_200_with_content(self, client, path, params):
        r = client.get(path, params=params)
        assert r.status_code == 200
        assert r.json() not in (None, [])


class TestSolarWind:
    def test_raw_24h_is_minute_resolution(self, client):
        times = _times(client.get("/solar-wind/raw", params={"interval": "24h"}).json())
        gaps = {(b - a).total_seconds() for a, b in zip(times, times[1:])}
        assert gaps <= {60.0}, f"unexpected spacing: {gaps}"

    def test_raw_24h_spans_at_most_24h(self, client):
        times = _times(client.get("/solar-wind/raw", params={"interval": "24h"}).json())
        assert (times[-1] - times[0]).total_seconds() <= 24 * 3600

    def test_7d_is_a_superset_of_24h(self, client):
        day = client.get("/solar-wind/raw", params={"interval": "24h"}).json()
        week = client.get("/solar-wind/raw", params={"interval": "7d"}).json()
        assert len(week) > len(day)
        assert {r["time"] for r in day} <= {r["time"] for r in week}

    def test_monthly_is_hour_aligned(self, client):
        for t in _times(client.get("/solar-wind/monthly").json()):
            assert (t.minute, t.second) == (0, 0)

    def test_monthly_spans_at_most_a_calendar_month(self, client):
        times = _times(client.get("/solar-wind/monthly").json())
        assert (times[-1] - times[0]).days <= 31

    def test_monthly_has_no_duplicate_buckets(self, client):
        times = _times(client.get("/solar-wind/monthly").json())
        assert len(times) == len(set(times))

    def test_latest_matches_tail_of_raw(self, client):
        latest = client.get("/solar-wind/latest").json()
        raw = client.get("/solar-wind/raw", params={"interval": "24h"}).json()
        assert latest["time"] == raw[-1]["time"]

    def test_column_filter_applies_to_all_three_endpoints(self, client):
        for path in ("/solar-wind/raw", "/solar-wind/monthly", "/solar-wind/latest"):
            r = client.get(path, params={"columns": ["speed", "bz"]})
            body = r.json()
            row = body[0] if isinstance(body, list) else body
            assert set(row) == {"time", "speed", "bz"}, path

    def test_values_are_numeric(self, client):
        row = client.get("/solar-wind/latest").json()
        for col in SOLAR_COLS:
            assert isinstance(row[col], (int, float))


class TestDst:
    def test_carries_observed_and_predicted(self, client):
        for row in client.get("/dst", params={"interval": "24h"}).json():
            assert set(row) == {"time", "dst", "dst_predictions"}

    def test_predictions_are_never_null(self, client):
        # predictions drive the join, so every row must have one
        for row in client.get("/dst", params={"interval": "7d"}).json():
            assert row["dst_predictions"] is not None

    def test_hourly_resolution(self, client):
        times = _times(client.get("/dst", params={"interval": "24h"}).json())
        gaps = {(b - a).total_seconds() for a, b in zip(times, times[1:])}
        assert gaps <= {3600.0}

    def test_intervals_are_nested(self, client):
        day = client.get("/dst", params={"interval": "24h"}).json()
        month = client.get("/dst", params={"interval": "1mo"}).json()
        assert {r["time"] for r in day} <= {r["time"] for r in month}

    def test_latest_observed_is_never_null(self, client):
        assert client.get("/dst/latest").json()["dst"] is not None

    def test_next_prediction_is_at_or_ahead_of_latest_observation(self, client):
        observed = datetime.fromisoformat(client.get("/dst/latest").json()["time"])
        predicted = datetime.fromisoformat(client.get("/dst/next-prediction").json()["time"])
        assert predicted >= observed


class TestKp:
    def test_three_hourly_resolution(self, client):
        times = _times(client.get("/kp", params={"interval": "7d"}).json())
        gaps = {(b - a).total_seconds() for a, b in zip(times, times[1:])}
        assert gaps <= {3 * 3600.0}

    def test_latest_matches_tail_of_range(self, client):
        latest = client.get("/kp/latest").json()
        rows = client.get("/kp", params={"interval": "24h"}).json()
        assert latest["time"] == rows[-1]["time"]

    def test_values_are_in_plausible_range(self, client):
        for row in client.get("/kp", params={"interval": "7d"}).json():
            assert 0 <= row["Kp"] <= 9


class TestSsn:
    def test_full_cycle_is_ascending_and_unique(self, client):
        times = _times(client.get("/ssn/full-cycle").json())
        assert times == sorted(times)
        assert len(times) == len(set(times))

    def test_backfilled_spotless_days_are_present(self, client):
        # Aug 2019 sits in the 2018-2021 stretch where NOAA omitted spotless
        # days entirely. The one-time backfill restored 29 of its 31 days as
        # zeros, so at least one day that month should now be present.
        months = {(t.year, t.month) for t in _times(client.get("/ssn/full-cycle").json())}
        assert (2019, 8) in months

    def test_backfilled_spotless_day_is_zero(self, client):
        # 2019-08-01 is one of the backfilled zeros, not a gap - without the
        # backfill it wouldn't be in the series at all.
        rows = client.get("/ssn/full-cycle").json()
        row = next(r for r in rows if r["time"].startswith("2019-08-01"))
        assert row["swpc_ssn"] == 0

    def test_permanent_gap_day_is_simply_absent(self, client):
        # 2019-06-29 is one of the 33 days LISIRD reports as non-zero -
        # deliberately not backfilled (would mean importing another
        # series' magnitudes), so it's a real, permanent gap: no row at
        # all for that day, rather than a zero standing in for it.
        rows = client.get("/ssn/full-cycle").json()
        assert not any(r["time"].startswith("2019-06-29") for r in rows)

    def test_almost_every_historical_month_has_a_row(self, client):
        # daily rows span the full retained history - confirmed against
        # dev: 145 distinct months are represented
        months = {(t.year, t.month) for t in _times(client.get("/ssn/full-cycle").json())}
        assert len(months) >= 140


class TestValidation:
    @pytest.mark.parametrize(
        "path,params",
        [
            ("/solar-wind/raw", {"interval": "1mo"}),
            ("/solar-wind/raw", {"interval": "nonsense"}),
            ("/dst", {"interval": "1y"}),
            ("/kp", {"interval": "1y"}),
        ],
    )
    def test_unsupported_interval_is_422(self, client, path, params):
        assert client.get(path, params=params).status_code == 422

    def test_unknown_column_is_400_with_the_name(self, client):
        r = client.get("/solar-wind/raw", params={"columns": ["speed", "wrong"]})
        assert r.status_code == 400
        assert "wrong" in r.json()["detail"]


class TestOrderingInvariants:
    @pytest.mark.parametrize(
        "path,params",
        [
            ("/solar-wind/raw", {"interval": "24h"}),
            ("/solar-wind/monthly", None),
            ("/dst", {"interval": "7d"}),
            ("/kp", {"interval": "7d"}),
            ("/ssn/full-cycle", None),
        ],
    )
    def test_rows_are_time_ascending(self, client, path, params):
        times = _times(client.get(path, params=params).json())
        assert times == sorted(times)


class TestRepeatedRequestsAreStable:
    def test_same_request_twice_gives_identical_bytes(self, client):
        # served from memory - two calls with no intervening poll must match
        first = client.get("/dst", params={"interval": "24h"}).content
        second = client.get("/dst", params={"interval": "24h"}).content
        assert first == second

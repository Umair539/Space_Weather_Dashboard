"""Every endpoint exercised through the real ASGI app with a hand-populated
store - no database, no polling. Covers routing, validation, slicing and
serialisation."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import api.main as main
from api.store import store

SOLAR_COLS = ["density", "speed", "temperature", "bz", "bx", "by", "bt", "pressure"]
NOW = datetime(2026, 6, 15, 12, 0)


async def _noop():
    return None


async def _noop_poll(table, interval):
    return None


async def _noop_refresh(*args, **kwargs):
    return None


@pytest.fixture
def client(monkeypatch):
    """App with polling stubbed out, store seeded with deterministic data."""
    monkeypatch.setattr(main, "initial_load", _noop)
    monkeypatch.setattr(main, "poll_table", _noop_poll)
    # The aurora nowcast comes straight from NOAA rather than the database,
    # so without these the suite would make real network calls on every
    # TestClient startup. Aurora endpoint behaviour is covered below by
    # seeding the cache directly instead.
    monkeypatch.setattr(main, "refresh_once", _noop_refresh)
    monkeypatch.setattr(main, "refresh_aurora", _noop_refresh)

    store.solar.records = tuple(
        {"time": NOW - timedelta(minutes=i), **{c: float(i) for c in SOLAR_COLS}}
        for i in range(3000, -1, -1)
    )
    store.kp.records = tuple(
        {"time": NOW - timedelta(hours=3 * i), "Kp": float(i)} for i in range(300, -1, -1)
    )
    store.dst.records = tuple(
        {"time": NOW - timedelta(hours=i), "dst": float(i)} for i in range(800, -1, -1)
    )
    store.dst_predictions.records = tuple(
        {"time": NOW - timedelta(hours=i), "dst_predictions": float(i)}
        for i in range(800, -1, -1)
    )
    store.ssn.records = tuple(
        {"time": datetime(2026, 6, 15) - timedelta(days=i), "swpc_ssn": float(i)}
        for i in range(500, -1, -1)
    )
    store.set_derived(
        "dst_merged",
        tuple(
            {"time": NOW - timedelta(hours=i), "dst_predictions": float(i),
             "dst": None if i == 0 else float(i)}
            for i in range(800, -1, -1)
        ),
    )
    store.set_derived(
        "solar_hourly",
        tuple(
            {"time": NOW.replace(minute=0) - timedelta(hours=i),
             **{c: float(i) for c in SOLAR_COLS}}
            for i in range(2000, -1, -1)
        ),
    )
    with TestClient(main.app) as c:
        yield c

    for name in ("solar", "kp", "dst", "dst_predictions", "ssn"):
        store.table(name).records = ()
    for name in ("dst_merged", "solar_hourly"):
        store.set_derived(name, ())


class TestSolarWindRaw:
    def test_default_interval_is_24h(self, client):
        rows = client.get("/solar-wind/raw").json()
        assert len(rows) == 24 * 60 + 1

    def test_7d_window(self, client):
        # only 3001 minutes are seeded, so a 7d ask returns everything held
        rows = client.get("/solar-wind/raw", params={"interval": "7d"}).json()
        assert len(rows) == 3001

    def test_returns_all_columns_by_default(self, client):
        row = client.get("/solar-wind/raw").json()[0]
        assert set(row) == {"time", *SOLAR_COLS}

    def test_column_subset(self, client):
        row = client.get(
            "/solar-wind/raw", params={"columns": ["speed", "bz"]}
        ).json()[0]
        assert set(row) == {"time", "speed", "bz"}

    def test_unknown_column_is_400(self, client):
        r = client.get("/solar-wind/raw", params={"columns": ["bogus"]})
        assert r.status_code == 400
        assert "bogus" in r.json()["detail"]

    def test_invalid_interval_is_422(self, client):
        assert client.get("/solar-wind/raw", params={"interval": "1y"}).status_code == 422

    def test_rows_are_time_ascending(self, client):
        times = [r["time"] for r in client.get("/solar-wind/raw").json()]
        assert times == sorted(times)


class TestSolarWindMonthly:
    def test_sliced_to_one_month_not_whole_cache(self, client):
        # 2001 hourly buckets are seeded; a calendar month from 15 Jun is
        # 31 days back to 15 May = 744 hours + 1
        rows = client.get("/solar-wind/monthly").json()
        assert len(rows) == 31 * 24 + 1

    def test_column_subset(self, client):
        row = client.get("/solar-wind/monthly", params={"columns": ["speed"]}).json()[0]
        assert set(row) == {"time", "speed"}

    def test_all_timestamps_are_hour_aligned(self, client):
        for row in client.get("/solar-wind/monthly").json():
            assert row["time"].endswith(":00:00")

    def test_unknown_column_is_400(self, client):
        assert client.get(
            "/solar-wind/monthly", params={"columns": ["nope"]}
        ).status_code == 400


class TestSolarWindLatest:
    def test_returns_single_object_not_list(self, client):
        body = client.get("/solar-wind/latest").json()
        assert isinstance(body, dict)

    def test_is_the_newest_row(self, client):
        latest = client.get("/solar-wind/latest").json()
        newest_in_range = client.get("/solar-wind/raw").json()[-1]
        assert latest["time"] == newest_in_range["time"]

    def test_column_subset(self, client):
        body = client.get("/solar-wind/latest", params={"columns": ["speed"]}).json()
        assert set(body) == {"time", "speed"}

    def test_empty_cache_returns_null(self, client):
        store.solar.records = ()
        assert client.get("/solar-wind/latest").json() is None


class TestDst:
    def test_default_interval_is_7d(self, client):
        rows = client.get("/dst").json()
        assert len(rows) == 7 * 24 + 1

    def test_1mo_interval(self, client):
        rows = client.get("/dst", params={"interval": "1mo"}).json()
        assert len(rows) == 31 * 24 + 1

    def test_has_both_observed_and_predicted(self, client):
        row = client.get("/dst").json()[0]
        assert set(row) == {"time", "dst", "dst_predictions"}

    def test_pending_prediction_serialises_as_null(self, client):
        # the newest row is seeded with dst=None - it must survive as JSON null
        rows = client.get("/dst").json()
        assert rows[-1]["dst"] is None
        assert rows[-1]["dst_predictions"] is not None

    def test_invalid_interval_is_422(self, client):
        assert client.get("/dst", params={"interval": "5y"}).status_code == 422


class TestDstLatestAndPrediction:
    def test_dst_latest_is_single_object(self, client):
        assert isinstance(client.get("/dst/latest").json(), dict)

    def test_dst_latest_matches_newest_dst_row(self, client):
        assert client.get("/dst/latest").json()["time"] == store.dst.records[-1]["time"].isoformat()

    def test_next_prediction_is_single_object(self, client):
        body = client.get("/dst/next-prediction").json()
        assert set(body) == {"time", "dst_predictions"}

    def test_both_return_null_when_empty(self, client):
        store.dst.records = ()
        store.dst_predictions.records = ()
        assert client.get("/dst/latest").json() is None
        assert client.get("/dst/next-prediction").json() is None


class TestKp:
    def test_default_interval_is_7d(self, client):
        rows = client.get("/kp").json()
        assert len(rows) == 7 * 8 + 1  # 3-hourly

    def test_shape(self, client):
        assert set(client.get("/kp").json()[0]) == {"time", "Kp"}

    def test_latest_is_newest_row(self, client):
        assert client.get("/kp/latest").json()["time"] == store.kp.records[-1]["time"].isoformat()

    def test_latest_empty_returns_null(self, client):
        store.kp.records = ()
        assert client.get("/kp/latest").json() is None


class TestSsn:
    def test_full_cycle_returns_every_raw_daily_row(self, client):
        # 501 rows seeded above - full-cycle reads store.ssn directly, no
        # aggregation, so nothing narrows or buckets it
        rows = client.get("/ssn/full-cycle").json()
        assert len(rows) == 501

    def test_full_cycle_is_not_interval_sliced(self, client):
        # it deliberately serves all retained history, not a rolling window
        assert len(client.get("/ssn/full-cycle").json()) == len(store.ssn.snapshot())


class TestHealth:
    def test_reports_every_table(self, client):
        body = client.get("/health").json()
        assert set(body["tables"]) == {"solar", "dst", "dst_predictions", "kp", "ssn"}

    def test_reports_row_counts(self, client):
        body = client.get("/health").json()
        assert body["tables"]["solar"]["rows"] == 3001

    def test_warming_up_until_every_table_has_polled(self, client):
        # nothing has a watermark in this fixture (polling is stubbed)
        assert client.get("/health").json()["status"] == "warming_up"

    def test_ok_once_all_tables_have_a_watermark(self, client):
        for name in ("solar", "dst", "dst_predictions", "kp", "ssn"):
            store.table(name).last_updated_at = datetime(2026, 6, 15)
        assert client.get("/health").json()["status"] == "ok"
        for name in ("solar", "dst", "dst_predictions", "kp", "ssn"):
            store.table(name).last_updated_at = None


class TestUnknownRoutes:
    def test_unknown_path_is_404(self, client):
        assert client.get("/does-not-exist").status_code == 404

    def test_last_synced_was_removed(self, client):
        # dropped deliberately - metadata.last_synced is rewritten every ETL
        # run whether or not data changed, so it isn't an honest signal
        assert client.get("/last-synced").status_code == 404


class TestAurora:
    """The aurora cache is HTTP-sourced, not part of `store`, so these seed
    api.aurora.cache directly rather than going through the store fixture."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        from api.aurora import cache

        cache._payload = None
        yield
        cache._payload = None

    def test_serves_the_cached_forecast(self, client):
        from api.aurora import cache

        cache.set(
            {
                "observation_time": "2026-08-14T19:41:00Z",
                "forecast_time": "2026-08-14T20:57:00Z",
                "max_probability": 61,
                "point_count": 2,
                "points": [[-10, 65, 61], [12, -70, 20]],
                "retrieved_at": "2026-08-14T20:00:00+00:00",
            }
        )

        body = client.get("/aurora").json()
        assert body["point_count"] == 2
        assert body["points"] == [[-10, 65, 61], [12, -70, 20]]
        assert body["max_probability"] == 61
        assert body["forecast_time"] == "2026-08-14T20:57:00Z"

    def test_503_when_no_forecast_has_ever_been_fetched(self, client):
        """An empty 200 would render as "no aurora anywhere", which is a
        real forecast - an outage has to be distinguishable from calm."""
        response = client.get("/aurora")
        assert response.status_code == 503
        assert "not available" in response.json()["detail"]

    def test_quiet_forecast_is_a_200_with_no_points(self, client):
        from api.aurora import cache

        cache.set({"point_count": 0, "points": [], "max_probability": 0})
        response = client.get("/aurora")
        assert response.status_code == 200
        assert response.json()["points"] == []

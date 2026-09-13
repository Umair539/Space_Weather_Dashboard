"""Poller wired to a fake DB. Covers the query the poller builds, the
short-circuit, delta merging, derived-view recompute, and failure handling -
without touching a real database."""

import asyncio
from datetime import datetime, timedelta

import pytest

import api.poller as poller
from api.store import Store


class FakeResult:
    def __init__(self, scalar=None, rows=None):
        self._scalar = scalar
        self._rows = rows or []

    def scalar(self):
        return self._scalar

    def mappings(self):
        return self

    def all(self):
        return self._rows


class FakeConn:
    """Returns queued results in order, recording every statement it saw."""

    def __init__(self, results, log):
        self._results = list(results)
        self._log = log

    def execute(self, statement, params=None):
        self._log.append((" ".join(str(statement).split()), params))
        return self._results.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeEngine:
    def __init__(self, per_connect_results, log):
        self._queue = list(per_connect_results)
        self._log = log

    def connect(self):
        return FakeConn(self._queue.pop(0), self._log)


@pytest.fixture
def store(monkeypatch):
    """Fresh store per test - the poller writes to a module-level singleton."""
    fresh = Store()
    monkeypatch.setattr(poller, "store", fresh)
    monkeypatch.setattr(poller, "_solar_hourly_buckets", {})
    return fresh


@pytest.fixture
def sql_log():
    return []


def _engine(monkeypatch, per_connect_results, log):
    # one shared instance - a new FakeEngine per get_engine() call would
    # reset the queue and silently replay the first connection's results
    engine = FakeEngine(per_connect_results, log)
    monkeypatch.setattr(poller, "get_engine", lambda: engine)


class TestPollOnceQueryShape:
    def test_bootstrap_has_no_updated_at_bound(self, store, sql_log, monkeypatch):
        _engine(monkeypatch, [[FakeResult(scalar="w1"), FakeResult(rows=[])]], sql_log)
        poller._poll_once("kp")

        select = sql_log[1][0]
        assert "updated_at > :since" not in select
        assert "MAX(time) FROM kp" in select

    def test_delta_adds_updated_at_bound_with_watermark(self, store, sql_log, monkeypatch):
        row = {"time": datetime(2026, 1, 1), "Kp": 1.0}
        _engine(
            monkeypatch,
            [
                [FakeResult(scalar="w1"), FakeResult(rows=[row])],
                [FakeResult(scalar="w2"), FakeResult(rows=[])],
            ],
            sql_log,
        )
        poller._poll_once("kp")
        poller._poll_once("kp")

        select, params = sql_log[3]
        assert "updated_at > :since" in select
        assert params == {"since": "w1"}

    def test_retention_bound_present_for_bounded_table(self, store, sql_log, monkeypatch):
        _engine(monkeypatch, [[FakeResult(scalar="w1"), FakeResult(rows=[])]], sql_log)
        poller._poll_once("solar")

        assert "INTERVAL '31 days'" in sql_log[1][0]

    def test_no_retention_bound_for_unbounded_table(self, store, sql_log, monkeypatch):
        _engine(monkeypatch, [[FakeResult(scalar="w1"), FakeResult(rows=[])]], sql_log)
        poller._poll_once("ssn")

        assert "INTERVAL" not in sql_log[1][0]

    def test_quoted_kp_column_is_selected(self, store, sql_log, monkeypatch):
        _engine(monkeypatch, [[FakeResult(scalar="w1"), FakeResult(rows=[])]], sql_log)
        poller._poll_once("kp")

        assert '"Kp"' in sql_log[1][0]


class TestPollOnceShortCircuit:
    def test_unchanged_watermark_skips_the_heavy_query(self, store, sql_log, monkeypatch):
        row = {"time": datetime(2026, 1, 1), "Kp": 1.0}
        _engine(
            monkeypatch,
            [
                [FakeResult(scalar="w1"), FakeResult(rows=[row])],
                [FakeResult(scalar="w1")],  # same watermark, only one query expected
            ],
            sql_log,
        )
        poller._poll_once("kp")
        changed = poller._poll_once("kp")

        assert changed == set()
        assert len(sql_log) == 3  # 2 from first poll, 1 (the MAX check) from second

    def test_null_watermark_on_empty_table_is_handled(self, store, sql_log, monkeypatch):
        _engine(monkeypatch, [[FakeResult(scalar=None)]], sql_log)
        assert poller._poll_once("kp") == set()


class TestPollOnceMerging:
    def test_rows_land_in_the_cache(self, store, sql_log, monkeypatch):
        rows = [
            {"time": datetime(2026, 1, 1), "Kp": 1.0},
            {"time": datetime(2026, 1, 2), "Kp": 2.0},
        ]
        _engine(monkeypatch, [[FakeResult(scalar="w1"), FakeResult(rows=rows)]], sql_log)
        changed = poller._poll_once("kp")

        assert changed == {datetime(2026, 1, 1), datetime(2026, 1, 2)}
        assert len(store.kp.snapshot()) == 2
        assert store.kp.last_updated_at == "w1"

    def test_row_mappings_are_converted_to_plain_dicts(self, store, sql_log, monkeypatch):
        rows = [{"time": datetime(2026, 1, 1), "Kp": 1.0}]
        _engine(monkeypatch, [[FakeResult(scalar="w1"), FakeResult(rows=rows)]], sql_log)
        poller._poll_once("kp")

        assert type(store.kp.snapshot()[0]) is dict


class TestDerivedRecompute:
    def test_solar_poll_publishes_hourly_buckets(self, store, sql_log, monkeypatch):
        hour = datetime(2026, 1, 1, 5)
        rows = [
            {
                "time": hour + timedelta(minutes=m),
                **{c: 1.0 for c in
                   ["density", "speed", "temperature", "bz", "bx", "by", "bt", "pressure"]},
            }
            for m in range(60)
        ]
        _engine(monkeypatch, [[FakeResult(scalar="w1"), FakeResult(rows=rows)]], sql_log)
        poller._poll_and_recompute("solar")

        hourly = store.get_derived("solar_hourly")
        assert len(hourly) == 1
        assert hourly[0]["time"] == hour

    def test_incomplete_hour_is_not_published(self, store, sql_log, monkeypatch):
        hour = datetime(2026, 1, 1, 5)
        rows = [
            {
                "time": hour + timedelta(minutes=m),
                **{c: 1.0 for c in
                   ["density", "speed", "temperature", "bz", "bx", "by", "bt", "pressure"]},
            }
            for m in range(30)
        ]
        _engine(monkeypatch, [[FakeResult(scalar="w1"), FakeResult(rows=rows)]], sql_log)
        poller._poll_and_recompute("solar")

        assert store.get_derived("solar_hourly") == ()

    def test_ssn_poll_lands_raw_daily_rows_with_no_aggregation(self, store, sql_log, monkeypatch):
        # /ssn/full-cycle reads store.ssn directly now - no derived bucket to
        # recompute, so a poll just needs to land every row it's given.
        rows = [{"time": datetime(2026, 2, d), "swpc_ssn": 10.0} for d in range(1, 6)]
        _engine(monkeypatch, [[FakeResult(scalar="w1"), FakeResult(rows=rows)]], sql_log)
        poller._poll_and_recompute("ssn")

        assert [r["time"] for r in store.ssn.snapshot()] == [r["time"] for r in rows]

    def test_dst_poll_rebuilds_merged_view(self, store, sql_log, monkeypatch):
        _engine(
            monkeypatch,
            [
                [FakeResult(scalar="w1"),
                 FakeResult(rows=[{"time": datetime(2026, 1, 1), "dst": 5.0}])],
                [FakeResult(scalar="w1"),
                 FakeResult(rows=[{"time": datetime(2026, 1, 1), "dst_predictions": 1.0},
                                  {"time": datetime(2026, 1, 1, 1), "dst_predictions": 2.0}])],
            ],
            sql_log,
        )
        poller._poll_and_recompute("dst")
        poller._poll_and_recompute("dst_predictions")

        merged = store.get_derived("dst_merged")
        assert len(merged) == 2
        assert merged[0]["dst"] == 5.0
        assert merged[1]["dst"] is None  # pending prediction

    def test_predictions_poll_alone_also_rebuilds_merged(self, store, sql_log, monkeypatch):
        # either side changing must refresh the join
        _engine(
            monkeypatch,
            [[FakeResult(scalar="w1"),
              FakeResult(rows=[{"time": datetime(2026, 1, 1), "dst_predictions": 1.0}])]],
            sql_log,
        )
        poller._poll_and_recompute("dst_predictions")

        assert len(store.get_derived("dst_merged")) == 1

    def test_only_the_affected_hour_is_recomputed(self, store, sql_log, monkeypatch):
        cols = ["density", "speed", "temperature", "bz", "bx", "by", "bt", "pressure"]
        h1, h2 = datetime(2026, 1, 1, 5), datetime(2026, 1, 1, 6)
        first = [
            {"time": h + timedelta(minutes=m), **{c: 1.0 for c in cols}}
            for h in (h1, h2)
            for m in range(60)
        ]
        # second poll touches only one minute inside h2
        second = [{"time": h2 + timedelta(minutes=30), **{c: 9.0 for c in cols}}]
        _engine(
            monkeypatch,
            [
                [FakeResult(scalar="w1"), FakeResult(rows=first)],
                [FakeResult(scalar="w2"), FakeResult(rows=second)],
            ],
            sql_log,
        )
        poller._poll_and_recompute("solar")
        before = {r["time"]: r for r in store.get_derived("solar_hourly")}
        poller._poll_and_recompute("solar")
        after = {r["time"]: r for r in store.get_derived("solar_hourly")}

        assert after[h1] is before[h1]  # untouched object, not merely equal
        assert after[h2] is not before[h2]
        assert after[h2]["bt"] != before[h2]["bt"]


class TestFailureHandling:
    def test_poll_failure_is_swallowed_not_raised(self, store, monkeypatch):
        def boom():
            raise RuntimeError("db down")

        monkeypatch.setattr(poller, "get_engine", boom)
        poller._poll_and_recompute("kp")  # must not raise

    def test_failure_leaves_cache_untouched(self, store, sql_log, monkeypatch):
        rows = [{"time": datetime(2026, 1, 1), "Kp": 1.0}]
        _engine(monkeypatch, [[FakeResult(scalar="w1"), FakeResult(rows=rows)]], sql_log)
        poller._poll_and_recompute("kp")

        monkeypatch.setattr(poller, "get_engine", lambda: (_ for _ in ()).throw(RuntimeError()))
        poller._poll_and_recompute("kp")

        assert len(store.kp.snapshot()) == 1
        assert store.kp.last_updated_at == "w1"


class TestInitialLoad:
    def test_polls_every_configured_table(self, store, monkeypatch):
        called = []
        monkeypatch.setattr(poller, "_poll_and_recompute", lambda t: called.append(t))
        asyncio.run(poller.initial_load())

        assert set(called) == set(poller.TABLE_COLUMNS)

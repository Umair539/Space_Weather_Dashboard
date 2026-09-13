import threading
from datetime import datetime, timedelta

from api.store import Store, TableCache


def _row(t, v):
    return {"time": t, "v": v}


class TestTableCacheMergeDelta:
    def test_starts_empty(self):
        cache = TableCache("x")
        assert cache.records == ()
        assert cache.last_updated_at is None

    def test_first_merge_populates_empty_cache(self):
        cache = TableCache("x")
        changed = cache.merge_delta([_row(datetime(2026, 1, 1), 1.0)], "t1")

        assert changed == {datetime(2026, 1, 1)}
        assert len(cache.records) == 1
        assert cache.last_updated_at == "t1"

    def test_new_timestamp_is_appended(self):
        cache = TableCache("x")
        cache.merge_delta([_row(datetime(2026, 1, 1), 1.0)], "t1")
        cache.merge_delta([_row(datetime(2026, 1, 2), 2.0)], "t2")

        assert len(cache.records) == 2
        assert cache.records[1]["v"] == 2.0

    def test_existing_timestamp_is_overwritten_not_duplicated(self):
        cache = TableCache("x")
        cache.merge_delta([_row(datetime(2026, 1, 1), 1.0)], "t1")
        cache.merge_delta([_row(datetime(2026, 1, 1), 99.0)], "t2")

        assert len(cache.records) == 1
        assert cache.records[0]["v"] == 99.0

    def test_result_is_sorted_by_time(self):
        cache = TableCache("x")
        cache.merge_delta([_row(datetime(2026, 1, 5), 1.0)], "t1")
        cache.merge_delta([_row(datetime(2026, 1, 1), 2.0)], "t2")

        times = [r["time"] for r in cache.records]
        assert times == sorted(times)

    def test_unsorted_delta_is_sorted_on_insert(self):
        cache = TableCache("x")
        cache.merge_delta(
            [_row(datetime(2026, 1, 3), 3.0), _row(datetime(2026, 1, 1), 1.0)], "t1"
        )
        times = [r["time"] for r in cache.records]
        assert times == sorted(times)

    def test_empty_delta_updates_watermark_but_not_data(self):
        cache = TableCache("x")
        cache.merge_delta([_row(datetime(2026, 1, 1), 1.0)], "t1")
        changed = cache.merge_delta([], "t2")

        assert changed == set()
        assert len(cache.records) == 1
        assert cache.last_updated_at == "t2"  # watermark still advances

    def test_retention_trims_old_rows(self):
        cache = TableCache("x")
        cache.merge_delta([_row(datetime(2026, 1, 1), 1.0)], "t1", retention_days=1)
        cache.merge_delta([_row(datetime(2026, 1, 10), 2.0)], "t2", retention_days=1)

        assert len(cache.records) == 1
        assert cache.records[0]["time"] == datetime(2026, 1, 10)

    def test_retention_keeps_row_exactly_on_boundary(self):
        cache = TableCache("x")
        cache.merge_delta(
            [_row(datetime(2026, 1, 9), 1.0), _row(datetime(2026, 1, 10), 2.0)],
            "t1",
            retention_days=1,
        )
        assert len(cache.records) == 2

    def test_no_retention_keeps_everything(self):
        cache = TableCache("x")
        cache.merge_delta([_row(datetime(2020, 1, 1), 1.0)], "t1", retention_days=None)
        cache.merge_delta([_row(datetime(2026, 1, 1), 2.0)], "t2", retention_days=None)

        assert len(cache.records) == 2  # 6 years apart, both kept

    def test_returned_changed_set_excludes_rows_trimmed_by_retention(self):
        cache = TableCache("x")
        changed = cache.merge_delta(
            [_row(datetime(2026, 1, 1), 1.0), _row(datetime(2026, 1, 10), 2.0)],
            "t1",
            retention_days=1,
        )
        # the Jan 1 row didn't survive the trim - the aggregator shouldn't be
        # told to recompute a bucket for data that's no longer cached
        assert changed == {datetime(2026, 1, 10)}

    def test_changed_set_reflects_only_the_delta_not_the_whole_cache(self):
        cache = TableCache("x")
        cache.merge_delta([_row(datetime(2026, 1, 1), 1.0)], "t1")
        changed = cache.merge_delta([_row(datetime(2026, 1, 2), 2.0)], "t2")

        assert changed == {datetime(2026, 1, 2)}  # not the Jan 1 row


class TestTableCacheSnapshot:
    def test_snapshot_is_stable_across_later_writes(self):
        cache = TableCache("x")
        cache.merge_delta([_row(datetime(2026, 1, 1), 1.0)], "t1")

        snap = cache.snapshot()
        cache.merge_delta([_row(datetime(2026, 1, 2), 2.0)], "t2")

        assert len(snap) == 1  # the earlier snapshot is untouched
        assert len(cache.snapshot()) == 2

    def test_snapshot_of_empty_cache(self):
        assert TableCache("x").snapshot() == ()

    def test_concurrent_snapshots_never_see_a_partial_write(self):
        # writers swap in a whole new tuple rather than mutating, so a reader
        # should only ever observe a complete generation - never a half-built one
        cache = TableCache("x")
        base = [_row(datetime(2026, 1, 1) + timedelta(days=i), float(i)) for i in range(50)]
        cache.merge_delta(base, "t0")

        seen_lengths = []
        stop = threading.Event()

        def reader():
            while not stop.is_set():
                seen_lengths.append(len(cache.snapshot()))

        def writer():
            for i in range(50, 150):
                cache.merge_delta(
                    [_row(datetime(2026, 1, 1) + timedelta(days=i), float(i))], f"t{i}"
                )

        r = threading.Thread(target=reader)
        w = threading.Thread(target=writer)
        r.start(), w.start()
        w.join()
        stop.set()
        r.join()

        # every observed length must be one the writer actually produced
        assert all(50 <= n <= 150 for n in seen_lengths)


class TestStore:
    def test_all_five_tables_exist_and_are_distinct(self):
        store = Store()
        names = ["solar", "dst", "dst_predictions", "kp", "ssn"]
        caches = [store.table(n) for n in names]
        assert len({id(c) for c in caches}) == 5
        assert [c.name for c in caches] == names

    def test_table_lookup_by_name(self):
        store = Store()
        assert store.table("solar") is store.solar
        assert store.table("kp") is store.kp

    def test_derived_views_start_empty(self):
        store = Store()
        for name in ("solar_hourly", "dst_merged"):
            assert store.get_derived(name) == ()

    def test_derived_get_set_roundtrip(self):
        store = Store()
        store.set_derived("dst_merged", ({"time": datetime(2026, 1, 1), "v": 1.0},))
        assert len(store.get_derived("dst_merged")) == 1

    def test_derived_views_are_independent(self):
        store = Store()
        store.set_derived("solar_hourly", ({"time": datetime(2026, 1, 1)},))
        assert store.get_derived("dst_merged") == ()

    def test_tables_are_independent(self):
        store = Store()
        store.solar.merge_delta([_row(datetime(2026, 1, 1), 1.0)], "t1")
        assert store.kp.snapshot() == ()

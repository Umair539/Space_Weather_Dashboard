from datetime import datetime, timedelta

from api.aggregates import (
    find,
    hour_of,
    merge_dst,
    months_back,
    prune_buckets,
    recompute_hours,
    select_columns,
    slice_interval,
)


def _rows(col, values, *timestamps):
    return tuple({"time": t, col: v} for t, v in zip(timestamps, values))


def _minute_rows(hour, count, **cols):
    return tuple(
        {"time": hour + timedelta(minutes=m), **{c: v for c, v in cols.items()}}
        for m in range(count)
    )


class TestMonthsBack:
    def test_simple_month(self):
        assert months_back(datetime(2026, 3, 15), 1) == datetime(2026, 2, 15)

    def test_crosses_year_boundary(self):
        assert months_back(datetime(2026, 1, 10), 1) == datetime(2025, 12, 10)

    def test_year_offset(self):
        assert months_back(datetime(2026, 8, 8), 12) == datetime(2025, 8, 8)

    def test_clamps_day_for_shorter_month(self):
        # 31 Mar minus 1 month -> Feb only has 28 days in 2026
        assert months_back(datetime(2026, 3, 31), 1) == datetime(2026, 2, 28)

    def test_clamps_to_feb_29_in_leap_year(self):
        assert months_back(datetime(2024, 3, 31), 1) == datetime(2024, 2, 29)

    def test_year_back_from_leap_day(self):
        # 29 Feb 2024 minus 12 months -> 2023 has no 29 Feb
        assert months_back(datetime(2024, 2, 29), 12) == datetime(2023, 2, 28)

    def test_preserves_time_of_day(self):
        assert months_back(datetime(2026, 3, 15, 13, 45), 1) == datetime(2026, 2, 15, 13, 45)


class TestHourOf:
    def test_hour_of_truncates_minutes_and_below(self):
        assert hour_of(datetime(2026, 1, 1, 14, 39, 22, 5)) == datetime(2026, 1, 1, 14, 0)


class TestFind:
    def test_finds_exact_match(self):
        rows = _rows("x", [1, 2, 3], datetime(2026, 1, 1), datetime(2026, 1, 2), datetime(2026, 1, 3))
        assert find(rows, datetime(2026, 1, 2))["x"] == 2

    def test_finds_first_and_last(self):
        rows = _rows("x", [1, 2, 3], datetime(2026, 1, 1), datetime(2026, 1, 2), datetime(2026, 1, 3))
        assert find(rows, datetime(2026, 1, 1))["x"] == 1
        assert find(rows, datetime(2026, 1, 3))["x"] == 3

    def test_missing_inside_range_returns_none(self):
        rows = _rows("x", [1, 3], datetime(2026, 1, 1), datetime(2026, 1, 3))
        assert find(rows, datetime(2026, 1, 2)) is None

    def test_beyond_either_end_returns_none(self):
        rows = _rows("x", [1], datetime(2026, 1, 2))
        assert find(rows, datetime(2026, 1, 1)) is None
        assert find(rows, datetime(2026, 1, 5)) is None

    def test_empty_returns_none(self):
        assert find((), datetime(2026, 1, 1)) is None


class TestSliceInterval:
    def test_keeps_rows_within_window_of_latest_timestamp(self):
        # anchored on the latest row (matching WHERE time >= MAX(time) - INTERVAL),
        # not "now" - so only rows within 24h of the Jan 5 row survive.
        rows = _rows(
            "x", [1, 2, 3], datetime(2026, 1, 1), datetime(2026, 1, 4, 12), datetime(2026, 1, 5)
        )
        assert [r["x"] for r in slice_interval(rows, "24h")] == [2, 3]

    def test_boundary_row_is_inclusive(self):
        rows = _rows("x", [1, 2], datetime(2026, 1, 4), datetime(2026, 1, 5))
        # exactly 24h before the newest row - should be kept
        assert [r["x"] for r in slice_interval(rows, "24h")] == [1, 2]

    def test_7d_window(self):
        rows = _rows(
            "x", [1, 2, 3], datetime(2025, 12, 30), datetime(2026, 1, 5), datetime(2026, 1, 8)
        )
        # 7d back from Jan 8 is Jan 1, so the Dec 30 row falls outside
        assert [r["x"] for r in slice_interval(rows, "7d")] == [2, 3]

    def test_month_is_calendar_aware_not_30_days(self):
        # Feb is 28 days - a naive 30-day window would wrongly include Jan 30
        rows = _rows(
            "x", [1, 2, 3], datetime(2026, 1, 30), datetime(2026, 2, 15), datetime(2026, 3, 1)
        )
        assert [r["x"] for r in slice_interval(rows, "1mo")] == [2, 3]

    def test_year_is_calendar_aware(self):
        rows = _rows(
            "x", [1, 2, 3], datetime(2024, 8, 1), datetime(2025, 9, 1), datetime(2026, 8, 8)
        )
        assert [r["x"] for r in slice_interval(rows, "1y")] == [2, 3]

    def test_all_rows_within_window_returns_everything(self):
        rows = _rows("x", [1, 2], datetime(2026, 1, 5, 1), datetime(2026, 1, 5, 2))
        assert len(slice_interval(rows, "24h")) == 2

    def test_empty_input(self):
        assert slice_interval((), "24h") == ()


class TestSelectColumns:
    def test_narrows_to_requested_columns_keeping_time(self):
        rows = ({"time": datetime(2026, 1, 1), "a": 1, "b": 2},)
        assert select_columns(rows, ["a"]) == ({"time": datetime(2026, 1, 1), "a": 1},)

    def test_preserves_requested_column_order(self):
        rows = ({"time": datetime(2026, 1, 1), "a": 1, "b": 2, "c": 3},)
        assert list(select_columns(rows, ["c", "a"])[0]) == ["time", "c", "a"]

    def test_empty_records(self):
        assert select_columns((), ["a"]) == ()


class TestRecomputeHours:
    def test_complete_hour_is_published(self):
        hour = datetime(2026, 1, 1, 0)
        buckets = {}
        recompute_hours(_minute_rows(hour, 60, bt=1.0), buckets, {hour}, ["bt"])
        assert buckets[hour] == {"time": hour, "bt": 1.0}

    def test_incomplete_hour_is_not_published(self):
        hour = datetime(2026, 1, 1, 0)
        buckets = {}
        recompute_hours(_minute_rows(hour, 59, bt=1.0), buckets, {hour}, ["bt"])
        assert hour not in buckets

    def test_mean_is_correct_and_rounded(self):
        hour = datetime(2026, 1, 1, 0)
        rows = tuple(
            {"time": hour + timedelta(minutes=m), "bt": float(m)} for m in range(60)
        )
        buckets = {}
        recompute_hours(rows, buckets, {hour}, ["bt"])
        assert buckets[hour]["bt"] == 29.5  # mean of 0..59

    def test_multiple_columns(self):
        hour = datetime(2026, 1, 1, 0)
        rows = _minute_rows(hour, 60, bt=2.0, speed=400.0)
        buckets = {}
        recompute_hours(rows, buckets, {hour}, ["bt", "speed"])
        assert buckets[hour] == {"time": hour, "bt": 2.0, "speed": 400.0}

    def test_hour_that_regresses_from_complete_is_removed(self):
        # a correction leaving a previously-complete hour with a hole - the
        # stale published bucket must not linger
        hour = datetime(2026, 1, 1, 0)
        buckets = {hour: {"time": hour, "bt": 1.0}}
        recompute_hours(_minute_rows(hour, 59, bt=1.0), buckets, {hour}, ["bt"])
        assert hour not in buckets

    def test_only_requested_hours_are_touched(self):
        h1, h2 = datetime(2026, 1, 1, 0), datetime(2026, 1, 1, 1)
        untouched = {"time": h1, "bt": 99.0}
        buckets = {h1: untouched}
        recompute_hours(_minute_rows(h2, 60, bt=2.0), buckets, {h2}, ["bt"])
        assert buckets[h1] is untouched  # same object, not just equal
        assert buckets[h2]["bt"] == 2.0

    def test_no_hours_requested_is_a_noop(self):
        buckets = {}
        recompute_hours(_minute_rows(datetime(2026, 1, 1), 60, bt=1.0), buckets, set(), ["bt"])
        assert buckets == {}


class TestPruneBuckets:
    def test_drops_buckets_older_than_cutoff(self):
        buckets = {datetime(2026, 1, 1): {"x": 1}, datetime(2026, 2, 1): {"x": 2}}
        prune_buckets(buckets, oldest=datetime(2026, 1, 15))
        assert list(buckets) == [datetime(2026, 2, 1)]

    def test_keeps_bucket_exactly_at_cutoff(self):
        buckets = {datetime(2026, 1, 15): {"x": 1}}
        prune_buckets(buckets, oldest=datetime(2026, 1, 15))
        assert list(buckets) == [datetime(2026, 1, 15)]

    def test_empty_buckets_is_a_noop(self):
        buckets = {}
        prune_buckets(buckets, oldest=datetime(2026, 1, 1))
        assert buckets == {}


class TestMergeDst:
    def test_matched_row_gets_real_dst_value(self):
        predictions = ({"time": datetime(2026, 1, 1), "dst_predictions": 1.1},)
        dst = ({"time": datetime(2026, 1, 1), "dst": 10.0},)
        assert merge_dst(predictions, dst)[0]["dst"] == 10.0

    def test_unmatched_pending_prediction_gets_none_not_dropped(self):
        # the scenario the cache-invalidation design was built around: the
        # newest prediction row has no matching dst yet
        predictions = (
            {"time": datetime(2026, 1, 1), "dst_predictions": 1.1},
            {"time": datetime(2026, 1, 1, 1), "dst_predictions": 2.2},
        )
        dst = ({"time": datetime(2026, 1, 1), "dst": 10.0},)
        merged = merge_dst(predictions, dst)
        assert len(merged) == 2  # preserved, not dropped
        assert merged[1]["dst"] is None

    def test_dst_value_of_zero_is_kept_not_treated_as_missing(self):
        predictions = ({"time": datetime(2026, 1, 1), "dst_predictions": 1.1},)
        dst = ({"time": datetime(2026, 1, 1), "dst": 0.0},)
        assert merge_dst(predictions, dst)[0]["dst"] == 0.0

    def test_predictions_drive_the_join(self):
        # a dst row with no matching prediction must not appear
        predictions = ({"time": datetime(2026, 1, 2), "dst_predictions": 2.2},)
        dst = (
            {"time": datetime(2026, 1, 1), "dst": 10.0},
            {"time": datetime(2026, 1, 2), "dst": 20.0},
        )
        merged = merge_dst(predictions, dst)
        assert len(merged) == 1
        assert merged[0]["time"] == datetime(2026, 1, 2)

    def test_output_is_time_sorted(self):
        predictions = (
            {"time": datetime(2026, 1, 3), "dst_predictions": 3.0},
            {"time": datetime(2026, 1, 1), "dst_predictions": 1.0},
        )
        merged = merge_dst(predictions, ())
        assert [r["time"] for r in merged] == sorted(r["time"] for r in merged)

    def test_empty_predictions_returns_empty(self):
        assert merge_dst((), ({"time": datetime(2026, 1, 1), "dst": 10.0},)) == ()

    def test_empty_dst_gives_all_none(self):
        predictions = ({"time": datetime(2026, 1, 1), "dst_predictions": 1.1},)
        assert merge_dst(predictions, ())[0]["dst"] is None

"""Config invariants. These aren't testing library behaviour - they're
guarding the couplings that are easy to break silently when adding a table
or changing a window."""

from api.db import POLL_INTERVALS, RETENTION_DAYS, TABLE_COLUMNS

# The widest interval any retention-bounded table serves is "1mo", and the
# longest calendar month is 31 days.
LONGEST_MONTH_DAYS = 31


class TestTableConfigConsistency:
    def test_all_three_configs_cover_the_same_tables(self):
        # adding a table to one dict and forgetting the others would either
        # crash the poller or silently never poll it
        assert set(TABLE_COLUMNS) == set(POLL_INTERVALS) == set(RETENTION_DAYS)

    def test_expected_tables_are_present(self):
        assert set(TABLE_COLUMNS) == {"solar", "dst", "dst_predictions", "kp", "ssn"}

    def test_every_table_has_at_least_one_column(self):
        for table, columns in TABLE_COLUMNS.items():
            assert columns, f"{table} has no columns configured"

    def test_time_is_not_listed_as_a_value_column(self):
        # the poller selects "time" separately; listing it here would produce
        # a duplicate column in the SELECT
        for table, columns in TABLE_COLUMNS.items():
            assert "time" not in columns, f"{table} lists time as a value column"

    def test_updated_at_is_not_listed_as_a_value_column(self):
        # likewise - the poller adds it, and it must not leak into responses
        for table, columns in TABLE_COLUMNS.items():
            assert "updated_at" not in columns, f"{table} lists updated_at"


class TestPollIntervals:
    def test_all_intervals_are_positive(self):
        for table, seconds in POLL_INTERVALS.items():
            assert seconds > 0, f"{table} has a non-positive poll interval"

    def test_solar_polls_at_least_as_often_as_slower_tables(self):
        # solar is minute-resolution; it should never be the laziest poller
        assert POLL_INTERVALS["solar"] <= min(
            POLL_INTERVALS[t] for t in POLL_INTERVALS if t != "solar"
        )

    def test_dst_and_predictions_share_a_cadence(self):
        # they feed one merged view - staggering them just adds skew between
        # the two halves of the join
        assert POLL_INTERVALS["dst"] == POLL_INTERVALS["dst_predictions"]


class TestRetention:
    def test_month_serving_tables_retain_at_least_a_full_month(self):
        # /dst, /kp and /solar-wind/monthly all serve a "1mo" window; less
        # retention than the longest month would silently truncate them
        for table in ("solar", "dst", "dst_predictions", "kp"):
            assert RETENTION_DAYS[table] >= LONGEST_MONTH_DAYS, (
                f"{table} retains {RETENTION_DAYS[table]}d, "
                f"less than the {LONGEST_MONTH_DAYS}d it may need to serve"
            )

    def test_ssn_is_unbounded_for_the_full_cycle_view(self):
        # /ssn/full-cycle covers all retained history, far more than a month
        assert RETENTION_DAYS["ssn"] is None


class TestQuotedColumns:
    def test_kp_column_is_quoted_for_its_mixed_case(self):
        # unquoted, Postgres would fold "Kp" to lowercase and error
        assert TABLE_COLUMNS["kp"] == ['"Kp"']

    def test_other_columns_are_unquoted_lowercase(self):
        for table, columns in TABLE_COLUMNS.items():
            if table == "kp":
                continue
            for column in columns:
                assert '"' not in column, f"{table}.{column} is needlessly quoted"
                assert column == column.lower(), f"{table}.{column} is not lowercase"

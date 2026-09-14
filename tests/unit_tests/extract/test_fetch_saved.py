from collections import Counter
from unittest.mock import patch

import pandas as pd

from src.extract.fetch_saved import (
    fetch_saved,
    _fetch_partitions,
    _fetch_full,
    _has_min_full_days,
    _download_partitions,
    MIN_FULL_DAYS,
)


class FakeStorage:
    """Stands in for the real storage client, keyed by object path. Also
    tracks how many times each key was fetched, so tests can assert on
    redundant downloads."""

    def __init__(self, objects):
        self.objects = objects
        self.calls = Counter()

    def download_json(self, key):
        self.calls[key] += 1
        return self.objects.get(key)


def _mag_days(*days, month="2026-09"):
    return [{"time_tag": f"{month}-{day:02d}T00:00:00"} for day in days]


class TestFetchSaved:
    def test_full_list_folder_returns_empty_when_filter_raw(self):
        assert fetch_saved("old_mag", filter_raw=True).empty

    @patch("src.extract.fetch_saved.get_storage_client")
    def test_full_list_folder_fetches_when_not_filter_raw(self, mock_client):
        storage = FakeStorage({"old_mag/lists.json": [["time_tag"], ["2026-09-01T00:00:00"]]})
        mock_client.return_value = storage
        df = fetch_saved("old_mag", filter_raw=False)
        assert len(df) == 1

    @patch("src.extract.fetch_saved.get_storage_client")
    def test_full_dicts_folder_ignores_filter_raw(self, mock_client):
        storage = FakeStorage({"ssn/dicts.json": [{"time_tag": "2026-09-01T00:00:00"}]})
        mock_client.return_value = storage
        df = fetch_saved("ssn", filter_raw=True)
        assert len(df) == 1

    def test_unrecognized_folder_returns_none(self):
        assert fetch_saved("not_a_real_folder") is None


class TestFetchFull:
    def test_returns_parsed_data(self):
        storage = FakeStorage({"ssn/dicts.json": [{"time_tag": "2026-09-01T00:00:00"}]})
        df = _fetch_full(storage, "ssn/dicts.json")
        assert len(df) == 1

    def test_missing_data_returns_empty_df(self):
        storage = FakeStorage({})
        df = _fetch_full(storage, "ssn/dicts.json")
        assert df.empty


class TestHasMinFullDays:
    def test_no_data_is_false(self):
        assert _has_min_full_days(None, MIN_FULL_DAYS) is False

    def test_empty_records_is_false(self):
        assert _has_min_full_days([], MIN_FULL_DAYS) is False

    def test_max_day_equal_to_min_is_false(self):
        # The latest day may still be partial, so day-of-month == min_days
        # is not yet min_days of *full* days.
        data = _mag_days(1, MIN_FULL_DAYS)
        assert _has_min_full_days(data, MIN_FULL_DAYS) is False

    def test_max_day_over_min_is_true(self):
        data = _mag_days(1, MIN_FULL_DAYS + 1)
        assert _has_min_full_days(data, MIN_FULL_DAYS) is True


class TestFetchPartitions:
    def test_no_metadata_returns_empty_df(self):
        storage = FakeStorage({})
        assert _fetch_partitions(storage, "mag", True).empty

    def test_metadata_without_partitions_key_returns_empty_df(self):
        storage = FakeStorage({"mag/metadata.json": {}})
        assert _fetch_partitions(storage, "mag", True).empty

    def test_empty_partitions_list_returns_empty_df(self):
        storage = FakeStorage({"mag/metadata.json": {"partitions": []}})
        assert _fetch_partitions(storage, "mag", True).empty

    def test_not_filter_raw_fetches_every_partition(self):
        storage = FakeStorage(
            {
                "mag/metadata.json": {"partitions": ["2026-07", "2026-08", "2026-09"]},
                "mag/dicts/2026-07.json": _mag_days(1, month="2026-07"),
                "mag/dicts/2026-08.json": _mag_days(1, month="2026-08"),
                "mag/dicts/2026-09.json": _mag_days(1, month="2026-09"),
            }
        )
        df = _fetch_partitions(storage, "mag", False)
        assert len(df) == 3
        assert storage.calls["mag/dicts/2026-07.json"] == 1

    def test_single_partition_short_circuits_min_days_check(self):
        # Only one partition exists, so the MIN_FULL_DAYS check is skipped
        # even though the partition itself is thin.
        storage = FakeStorage(
            {
                "mag/metadata.json": {"partitions": ["2026-09"]},
                "mag/dicts/2026-09.json": _mag_days(1, 2),
            }
        )
        df = _fetch_partitions(storage, "mag", True)
        assert len(df) == 2
        assert storage.calls["mag/dicts/2026-09.json"] == 1

    def test_last_partition_with_enough_full_days_skips_prior_month(self):
        storage = FakeStorage(
            {
                "mag/metadata.json": {"partitions": ["2026-08", "2026-09"]},
                "mag/dicts/2026-09.json": _mag_days(1, MIN_FULL_DAYS + 1),
                "mag/dicts/2026-08.json": _mag_days(1, month="2026-08"),
            }
        )
        df = _fetch_partitions(storage, "mag", True)
        assert len(df) == 2
        assert storage.calls["mag/dicts/2026-09.json"] == 1
        assert storage.calls["mag/dicts/2026-08.json"] == 0

    def test_thin_last_partition_reaches_back_one_month(self):
        storage = FakeStorage(
            {
                "mag/metadata.json": {"partitions": ["2026-08", "2026-09"]},
                "mag/dicts/2026-09.json": _mag_days(1, 3),
                "mag/dicts/2026-08.json": _mag_days(1, 30, month="2026-08"),
            }
        )
        df = _fetch_partitions(storage, "mag", True)
        assert len(df) == 4
        # Regression check for the redundant-download bug: the last month
        # is used to run the MIN_FULL_DAYS check *and* returned in the
        # result, so it must only be downloaded once.
        assert storage.calls["mag/dicts/2026-09.json"] == 1
        assert storage.calls["mag/dicts/2026-08.json"] == 1

    def test_thin_last_partition_with_no_prior_month_data_still_returns_it(self):
        storage = FakeStorage(
            {
                "mag/metadata.json": {"partitions": ["2026-08", "2026-09"]},
                "mag/dicts/2026-09.json": _mag_days(1, 3),
                # 2026-08 listed in metadata but its object is missing.
            }
        )
        df = _fetch_partitions(storage, "mag", True)
        assert len(df) == 2

    def test_missing_last_partition_data_returns_empty_df(self):
        storage = FakeStorage({"mag/metadata.json": {"partitions": ["2026-09"]}})
        df = _fetch_partitions(storage, "mag", True)
        assert df.empty


class TestDownloadPartitions:
    def test_no_months_returns_empty_df(self):
        storage = FakeStorage({})
        assert _download_partitions(storage, "mag", []).empty

    def test_fetches_each_month_once(self):
        storage = FakeStorage(
            {
                "mag/dicts/2026-08.json": _mag_days(1, month="2026-08"),
                "mag/dicts/2026-09.json": _mag_days(1, month="2026-09"),
            }
        )
        df = _download_partitions(storage, "mag", ["2026-08", "2026-09"])
        assert len(df) == 2
        assert storage.calls["mag/dicts/2026-08.json"] == 1
        assert storage.calls["mag/dicts/2026-09.json"] == 1

    def test_prefetched_month_is_not_downloaded_again(self):
        storage = FakeStorage({"mag/dicts/2026-08.json": _mag_days(1, month="2026-08")})
        prefetched = {"2026-09": _mag_days(1, month="2026-09")}
        df = _download_partitions(storage, "mag", ["2026-08", "2026-09"], prefetched=prefetched)
        assert len(df) == 2
        assert storage.calls["mag/dicts/2026-08.json"] == 1
        assert storage.calls["mag/dicts/2026-09.json"] == 0

    def test_all_months_prefetched_makes_no_calls(self):
        storage = FakeStorage({})
        prefetched = {
            "2026-08": _mag_days(1, month="2026-08"),
            "2026-09": _mag_days(1, month="2026-09"),
        }
        df = _download_partitions(storage, "mag", ["2026-08", "2026-09"], prefetched=prefetched)
        assert len(df) == 2
        assert sum(storage.calls.values()) == 0

    def test_missing_month_data_is_skipped_not_errored(self):
        storage = FakeStorage({"mag/dicts/2026-09.json": _mag_days(1, month="2026-09")})
        df = _download_partitions(storage, "mag", ["2026-08", "2026-09"])
        assert len(df) == 1

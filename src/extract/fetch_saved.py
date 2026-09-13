from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.utils.storage import get_storage_client
from src.utils.parser import parse_data
from src.utils.logging_utils import setup_logger

logger = setup_logger("fetch_saved", "extract_data.log")

PARTITIONED = {"mag", "plasma", "dst", "kp"}  # dicts/ partitions
FULL_DICTS = {"ssn", "smoothed_ssn"}  # single dicts.json
FULL_LISTS = {"old_mag", "old_plasma"}  # single lists.json


def fetch_saved(folder, filter_raw=True):
    storage = get_storage_client()

    if folder in FULL_LISTS:
        if filter_raw:
            return pd.DataFrame()
        return _fetch_full(storage, f"{folder}/lists.json")

    if folder in FULL_DICTS:
        return _fetch_full(storage, f"{folder}/dicts.json")

    if folder in PARTITIONED:
        return _fetch_partitions(storage, folder, filter_raw)


def _fetch_full(storage, file_path):
    logger.info(f"Fetching {file_path} from storage...")
    raw = storage.download_json(file_path)
    if not raw:
        logger.warning(f"No data found at {file_path}, returning empty DataFrame.")
        return pd.DataFrame()
    return pd.DataFrame(parse_data(raw))


MIN_FULL_DAYS = 8


def _fetch_partitions(storage, folder, filter_raw):
    logger.info(f"Fetching partitions for {folder} [filter_raw={filter_raw}]...")

    metadata = _get_metadata(storage, folder)
    if not metadata or "partitions" not in metadata:
        return pd.DataFrame()

    partitions = metadata["partitions"]
    if not partitions:
        return pd.DataFrame()

    if not filter_raw:
        logger.info(f"Fetching months: {partitions}")
        return _download_partitions(storage, folder, partitions)

    # filter_raw: pull the last partition first, and only reach back to the
    # month before it if the last one doesn't yet cover MIN_FULL_DAYS - e.g.
    # early in a new month, the current partition alone is too thin a window.
    last_month = partitions[-1]
    last_data = storage.download_json(f"{folder}/dicts/{last_month}.json")

    if _has_min_full_days(last_data, MIN_FULL_DAYS) or len(partitions) < 2:
        months = [last_month]
    else:
        months = [partitions[-2], last_month]
        logger.info(
            f"{folder}: {last_month} has fewer than {MIN_FULL_DAYS} full days, "
            f"also fetching {partitions[-2]}"
        )

    if months == [last_month]:
        # Already downloaded above - avoid fetching it again.
        if not last_data:
            logger.warning(
                f"No partition data found for {folder}, returning empty DataFrame."
            )
            return pd.DataFrame()
        return pd.DataFrame(parse_data(last_data))

    logger.info(f"Fetching months: {months}")

    return _download_partitions(storage, folder, months)


def _has_min_full_days(data, min_days):
    """Proxy check: assumes the partition starts on day 1 with no gaps, so the
    day-of-month of its latest record is a stand-in for days elapsed. The
    latest day itself may still be partial, so it needs day-of-month > min_days
    (not >=) to count as min_days full days."""
    if not data:
        return False
    records = parse_data(data)
    if not records:
        return False
    max_day = max(int(record["time_tag"][8:10]) for record in records)
    return max_day > min_days


def _get_metadata(storage, folder):
    metadata = storage.download_json(f"{folder}/metadata.json")
    if not metadata:
        logger.error(f"No metadata found for {folder}.")
    return metadata


def _download_partitions(storage, folder, months):
    if not months:
        return pd.DataFrame()

    # Each month is its own object in storage - independent downloads, so
    # fetch them concurrently instead of one at a time. This is what made
    # mag/plasma (5 months each) the slowest part of extraction.
    with ThreadPoolExecutor(max_workers=len(months)) as executor:
        results = executor.map(
            lambda month: storage.download_json(f"{folder}/dicts/{month}.json"), months
        )

    records = []
    for data in results:
        if data:
            records.extend(data)

    if not records:
        logger.warning(
            f"No partition data found for {folder}, returning empty DataFrame."
        )
        return pd.DataFrame()

    return pd.DataFrame(parse_data(records))

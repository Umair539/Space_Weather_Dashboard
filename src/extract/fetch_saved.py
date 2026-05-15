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


def _fetch_partitions(storage, folder, filter_raw):
    logger.info(f"Fetching partitions for {folder} [filter_raw={filter_raw}]...")

    metadata = _get_metadata(storage, folder)
    if not metadata or "partitions" not in metadata:
        return pd.DataFrame()

    if filter_raw:
        months = metadata["partitions"][-2:]
    else:
        months = metadata["partitions"]

    return _download_partitions(storage, folder, months)


def _get_metadata(storage, folder):
    metadata = storage.download_json(f"{folder}/metadata.json")
    if not metadata:
        logger.error(f"No metadata found for {folder}.")
    return metadata


def _download_partitions(storage, folder, months):
    records = []
    for month in months:
        data = storage.download_json(f"{folder}/dicts/{month}.json")
        if data:
            records.extend(data)

    if not records:
        logger.warning(
            f"No partition data found for {folder}, returning empty DataFrame."
        )
        return pd.DataFrame()

    return pd.DataFrame(parse_data(records))

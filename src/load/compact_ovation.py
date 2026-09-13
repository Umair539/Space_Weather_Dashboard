from datetime import datetime, timedelta, timezone

import pyarrow as pa

from src.load.load_ovation import (
    PARQUET_CONTENT_TYPE,
    _PARTITION_SCHEMA,
    _read_parquet,
    _write_parquet,
)
from src.utils.logging_utils import setup_logger
from src.utils.storage import get_ovation_storage_client, get_storage_client

logger = setup_logger("compact_ovation", "load_data.log")


def _day_prefix(folder_path, year, month, day):
    return f"{folder_path}/{year}/{month}/{day}/"


def _day_key(folder_path, year, month, day):
    return f"{folder_path}/{year}/{month}/{day}.parquet"


def _update_metadata(storage, folder_path, partition_label):
    existing_metadata = storage.download_json(f"{folder_path}/metadata.json") or {}
    existing_partitions = set(existing_metadata.get("partitions", []))
    existing_partitions.add(partition_label)
    storage.upload_json(
        f"{folder_path}/metadata.json",
        {"partitions": sorted(existing_partitions)},
    )


def compact_day(folder_path, year, month, day, source_storage=None, dest_storage=None):
    """Merge one day's per-run OVATION files (written every ~3 minutes by
    load_ovation.py, in S3 - see load_ovation.py for why) into a single
    `{folder_path}/YYYY/MM/DD.parquet` in R2 (see get_ovation_storage_client
    for why the compacted output lands there instead).

    The S3 run-files are deliberately left in place after merging - they're
    the only raw copy of each snapshot, cost is trivial at this data volume,
    and deleting them here would mean a bug in this merge could destroy data
    with no way to recover or re-run it. If they ever need cleaning up,
    that's a separate concern (e.g. an S3 lifecycle rule), not something
    this function does.

    Idempotent by design: merges in whatever compacted day file already
    exists too, keyed by observation_time, so re-running this - whether
    because run-files are still there from a previous compaction or a
    retry after a partial failure - just re-merges the same data harmlessly
    rather than losing or duplicating it.
    """
    source_storage = source_storage or get_storage_client()
    dest_storage = dest_storage or get_ovation_storage_client()

    prefix = _day_prefix(folder_path, year, month, day)
    run_keys = source_storage.list_keys(prefix)

    if not run_keys:
        logger.info(f"ovation compact {year}-{month}-{day}: no run files, nothing to do")
        return 0

    rows = {}

    day_key = _day_key(folder_path, year, month, day)
    existing_day = dest_storage.download_bytes(day_key)
    sources = ([existing_day] if existing_day is not None else []) + [
        source_storage.download_bytes(key) for key in run_keys
    ]
    for blob in sources:
        table = _read_parquet(blob)
        for obs, fc, vals in zip(
            table.column("observation_time").to_pylist(),
            table.column("forecast_time").to_pylist(),
            table.column("values").to_pylist(),
        ):
            rows[obs] = (fc, vals)

    sorted_times = sorted(rows)
    combined = pa.table(
        {
            "observation_time": sorted_times,
            "forecast_time": [rows[t][0] for t in sorted_times],
            "values": [rows[t][1] for t in sorted_times],
        },
        schema=_PARTITION_SCHEMA,
    )
    dest_storage.upload_bytes(day_key, _write_parquet(combined), PARQUET_CONTENT_TYPE)
    _update_metadata(dest_storage, folder_path, f"{year}-{month}-{day}")

    logger.info(
        f"ovation compact {year}-{month}-{day}: merged {len(run_keys)} run "
        f"files into {combined.num_rows} rows (run files left in place in S3)"
    )
    return combined.num_rows


def compact_yesterday(folder_path="ovation", source_storage=None, dest_storage=None):
    """Default target for the daily scheduled job - the day that just
    ended (UTC), once it's no longer being written to."""
    target = datetime.now(timezone.utc).date() - timedelta(days=1)
    return compact_day(
        folder_path,
        f"{target.year:04d}",
        f"{target.month:02d}",
        f"{target.day:02d}",
        source_storage=source_storage,
        dest_storage=dest_storage,
    )

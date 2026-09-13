import io

import pyarrow as pa
import pyarrow.parquet as pq

from src.utils.logging_utils import setup_logger
from src.utils.storage import get_storage_client

logger = setup_logger("load_ovation", "load_data.log")

PARQUET_CONTENT_TYPE = "application/vnd.apache.parquet"

# OVATION's 360x181 grid is the same fixed set of (lon, lat) points on every
# fetch, in this exact deterministic order (verified against a live fetch) -
# only the probability at each point changes. So there's no need to fetch
# or store the coordinates anywhere: they're generated here and each row
# keeps just the probability values, in this same grid order.
_EXPECTED_LONS = [lon for lon in range(360) for _ in range(-90, 91)]
_EXPECTED_LATS = [lat for _ in range(360) for lat in range(-90, 91)]

_PARTITION_SCHEMA = pa.schema(
    [
        ("observation_time", pa.string()),
        ("forecast_time", pa.string()),
        ("values", pa.list_(pa.int16())),
    ]
)


def _write_parquet(table):
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="zstd")
    return buf.getvalue()


def _read_parquet(data):
    return pq.read_table(io.BytesIO(data))


def _grid_matches(lons, lats):
    """True if `lons`/`lats` match OVATION's known fixed grid order. A pure
    in-memory comparison (~0.4ms for the full 65,160 points) - cheap enough
    to run on every invocation rather than caching or verifying against a
    stored reference, so it also catches drift immediately rather than only
    at the next cold start."""
    return lons == _EXPECTED_LONS and lats == _EXPECTED_LATS


def _run_file_key(folder_path, observation_time):
    year, month, day = observation_time[:10].split("-")
    safe_time = observation_time.replace(":", "-")
    return f"{folder_path}/{year}/{month}/{day}/{safe_time}.parquet"


def load_ovation(folder_path, data):
    """Archive one OVATION snapshot as its own small file at
    `{folder_path}/YYYY/MM/DD/<observation_time>.parquet`.

    Written via get_storage_client() (S3 in prod, same bucket/IAM role as
    mag/plasma/dst/kp) rather than forced R2 - nothing outside the daily
    compaction job ever reads these per-run files, so there's no repeated
    external-read cost to avoid here. R2 is reserved for the *compacted*
    output (see compact_ovation.py), which is what actually gets read
    repeatedly from outside the ETL.

    Deliberately NOT a read-merge-rewrite of a growing day file - at this
    Lambda's ~3-minute schedule (480 runs/day) that pattern would mean
    re-uploading the entire day's data on every single run, growing to
    several MB and multiple seconds by the last run of the day. Instead
    each run is a single independent small write (no download at all), and
    the daily compaction job consolidates a finished day's files into one
    `{folder_path}/YYYY/MM/DD.parquet` in R2.
    """
    if not data:
        return

    coords = data.get("coordinates")
    observation_time = data.get("Observation Time")
    forecast_time = data.get("Forecast Time")
    if not coords or not observation_time:
        logger.warning("ovation: missing coordinates or observation time, skipping")
        return

    storage = get_storage_client()
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    values = [c[2] for c in coords]

    if not _grid_matches(lons, lats):
        logger.error(
            "ovation: NOAA's grid point order no longer matches the expected "
            "fixed grid, skipping this snapshot rather than misalign it"
        )
        return

    table = pa.table(
        {
            "observation_time": [observation_time],
            "forecast_time": [forecast_time],
            "values": [values],
        },
        schema=_PARTITION_SCHEMA,
    )
    key = _run_file_key(folder_path, observation_time)
    storage.upload_bytes(key, _write_parquet(table), PARQUET_CONTENT_TYPE)

    return table

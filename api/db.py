import os

from sqlalchemy import create_engine

_engine = None


def get_engine():
    """Read-only role, same pooler-compatibility flag as the write-side
    engine in src/load/load_data_into_db.py. Created lazily so importing
    this module doesn't require DATABASE_READ_URL to be set yet - main.py
    loads the right .env.{env} before the first poll runs."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            os.environ["DATABASE_READ_URL"], connect_args={"prepare_threshold": None}
        )
    return _engine


# Per-table poll interval in seconds - staggered by how fast each source
# actually changes (solar is minute-resolution; ssn is daily).
POLL_INTERVALS = {
    "solar": 30,
    "dst": 60,
    "dst_predictions": 60,
    "kp": 120,
    "ssn": 300,
}

# table -> columns to select. "Kp" needs quoting for its mixed case, same as
# src/load/load_data_into_db.py's _SPEC (the resulting DataFrame column is
# unquoted "Kp"). time/updated_at are added by the poller.
TABLE_COLUMNS = {
    "solar": ["density", "speed", "temperature", "bz", "bx", "by", "bt", "pressure"],
    "dst": ["dst"],
    "dst_predictions": ["dst_predictions"],
    "kp": ['"Kp"'],
    "ssn": ["swpc_ssn"],
}

# Rolling in-memory retention per table, in days. Bounds the bootstrap
# fetch, every delta fetch, and the in-memory trim - so a full-refresh ETL
# run (upsert_hours=1000000) can't pull a year of history into memory.
#
# 31 = the longest calendar month, which is exactly what "1mo" (the widest
# interval these tables serve) can span. Everything - this trim, the
# bootstrap query, and slice_interval - anchors on the newest row rather
# than NOW(), so a stalled pipeline keeps a full month rather than the
# window eroding.
#
# None = unbounded: ssn is only ~4,383 rows for 12yr and /ssn/full-cycle
# needs all of it.
RETENTION_DAYS = {
    "solar": 31,
    "dst": 31,
    "dst_predictions": 31,
    "kp": 31,
    "ssn": None,
}

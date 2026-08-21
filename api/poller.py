import asyncio
import logging

from sqlalchemy import text

from api.aggregates import hour_of, merge_dst, prune_buckets, recompute_hours
from api.db import RETENTION_DAYS, TABLE_COLUMNS, get_engine
from api.store import store

logger = logging.getLogger("api.poller")

# Working state for the bucketed aggregate: {bucket_start: row}. Only the
# poller touches this, and only one task polls solar, so it needs no lock -
# what gets published to the store is an immutable tuple.
_solar_hourly_buckets: dict = {}


def _poll_once(table: str) -> set:
    """Cheap MAX(updated_at) check; only if that's advanced, fetch the rows
    that changed and merge them in. Returns the set of changed times.

    The first call for a table (last_updated_at is None) has no
    "updated_at >" bound, so it naturally becomes the bootstrap full load -
    same code path, no separate init function.
    """
    cache = store.table(table)
    retention_days = RETENTION_DAYS.get(table)
    cols_sql = ", ".join(TABLE_COLUMNS[table])

    conditions, params = [], {}
    if retention_days:
        # Anchored on the newest row, not NOW() - same anchor as
        # slice_interval, the in-memory trim, and the frontend's existing
        # WHERE time >= (SELECT MAX(time) ...) queries. With a NOW() anchor
        # a stalled pipeline would silently shrink the usable window.
        conditions.append(
            f"time >= (SELECT MAX(time) FROM {table}) - INTERVAL '{retention_days} days'"
        )
    if cache.last_updated_at is not None:
        conditions.append("updated_at > :since")
        params["since"] = cache.last_updated_at
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_engine().connect() as conn:
        max_updated = conn.execute(text(f"SELECT MAX(updated_at) FROM {table}")).scalar()
        if max_updated is None or max_updated == cache.last_updated_at:
            return set()

        rows = conn.execute(
            text(f"SELECT time, {cols_sql} FROM {table} {where} ORDER BY time ASC"), params
        ).mappings().all()

    return cache.merge_delta([dict(row) for row in rows], max_updated, retention_days)


def _recompute_derived(table: str, changed_times: set) -> None:
    """Rebuild only what the changed rows actually affect."""
    if table == "solar":
        records = store.solar.snapshot()
        recompute_hours(
            records, _solar_hourly_buckets, {hour_of(t) for t in changed_times},
            TABLE_COLUMNS["solar"],
        )
        prune_buckets(_solar_hourly_buckets, hour_of(records[0]["time"]))
        store.set_derived(
            "solar_hourly", tuple(_solar_hourly_buckets[k] for k in sorted(_solar_hourly_buckets))
        )

    elif table in ("dst", "dst_predictions"):
        # Cheap enough to rebuild whole (~745 rows) - no bucketing needed.
        store.set_derived(
            "dst_merged", merge_dst(store.dst_predictions.snapshot(), store.dst.snapshot())
        )


def _poll_and_recompute(table: str) -> None:
    try:
        changed = _poll_once(table)
        if changed:
            _recompute_derived(table, changed)
    except Exception:
        # never let one failed poll kill the loop
        logger.exception(f"poll failed for {table}")


async def poll_table(table: str, interval_s: float) -> None:
    while True:
        await asyncio.to_thread(_poll_and_recompute, table)
        await asyncio.sleep(interval_s)


async def initial_load() -> None:
    """One poll cycle for every table, awaited before the app serves
    traffic, so no request ever hits an empty cache."""
    for table in TABLE_COLUMNS:
        await asyncio.to_thread(_poll_and_recompute, table)

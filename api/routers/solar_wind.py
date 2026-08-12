from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from api.aggregates import select_columns, slice_interval
from api.db import TABLE_COLUMNS
from api.store import store

router = APIRouter(prefix="/solar-wind", tags=["solar-wind"])

ALL_COLUMNS = TABLE_COLUMNS["solar"]


# Validated against db.TABLE_COLUMNS so the column list has a single source
# of truth - adding a column to the solar table doesn't need a second edit
# here. Unknown names 400 rather than silently returning rows with no data
# in them.
def _columns(requested: list[str] | None) -> list[str]:
    if not requested:
        return ALL_COLUMNS
    unknown = sorted(set(requested) - set(ALL_COLUMNS))
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown columns: {unknown}")
    return requested


# app/views/solar_wind.py "Last 24 Hours"/"Last Week" - raw minute rows.
@router.get("/raw")
def get_solar_wind_raw(
    interval: Literal["24h", "7d"] = "24h",
    columns: list[str] | None = Query(default=None),
):
    records = slice_interval(store.solar.snapshot(), interval)
    return select_columns(records, _columns(columns))


# app/views/solar_wind.py "Last Month" - hourly means, served pre-aggregated
# from the cache instead of recomputed per request.
#
# Sliced to a month explicitly rather than just returning whatever the
# cache happens to hold - the endpoint's window is a contract, it shouldn't
# drift if RETENTION_DAYS is ever changed.
@router.get("/monthly")
def get_solar_wind_monthly(columns: list[str] | None = Query(default=None)):
    records = slice_interval(store.get_derived("solar_hourly"), "1mo")
    return select_columns(records, _columns(columns))


# Newest solar wind row. One row of one table - speed/bz/etc are columns of
# the same record, so `columns` narrows it rather than there being a
# separate endpoint per measurement.
@router.get("/latest")
def get_solar_wind_latest(columns: list[str] | None = Query(default=None)):
    records = store.solar.snapshot()
    if not records:
        return None
    return select_columns(records[-1:], _columns(columns))[0]

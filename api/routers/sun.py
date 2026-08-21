from typing import Literal

from fastapi import APIRouter

from api.aggregates import slice_interval
from api.store import store

router = APIRouter(prefix="/ssn", tags=["ssn"])


@router.get("/raw")
def get_ssn_raw(interval: Literal["1mo", "1y"] = "1mo"):
    """app/views/sun.py "Last Month"/"Last Year" - raw daily rows."""
    return slice_interval(store.ssn.snapshot(), interval)


@router.get("/full-cycle")
def get_ssn_full_cycle():
    """"Last Full Cycle" - every retained daily row, unaggregated.

    A full solar cycle is ~4,383 daily points, which is fewer points than
    a single week of 1-minute solar wind - itself served and charted raw.
    Monthly-averaging something already smaller than a chart we render at
    full resolution elsewhere bought nothing but a coarser plot."""
    return store.ssn.snapshot()

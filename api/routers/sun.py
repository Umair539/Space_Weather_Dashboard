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
    """app/views/sun.py "Last Full Cycle" - monthly means over all retained
    history. Only complete months are published, so the in-progress month
    doesn't appear as an artificially low partial average."""
    return store.get_derived("ssn_monthly")

from typing import Literal

from fastapi import APIRouter

from api.aggregates import slice_interval
from api.store import store

router = APIRouter(tags=["geomag"])


@router.get("/dst")
def get_dst(interval: Literal["24h", "7d", "1mo"] = "7d"):
    """Observed dst + predictions, LEFT JOIN with predictions driving (see
    merge_dst). A null "dst" on the newest row(s) is expected - that's a
    prediction with no observed value yet."""
    return slice_interval(store.get_derived("dst_merged"), interval)


@router.get("/dst/latest")
def get_dst_latest():
    """Newest observed dst, straight from the dst table. The dst table
    itself never contains nulls (verified against dev/prod) - nulls only
    appear in the joined /dst view, where a prediction has no matching
    observation yet."""
    records = store.dst.snapshot()
    return records[-1] if records else None


@router.get("/dst/next-prediction")
def get_dst_next_prediction():
    """Newest prediction row - the forward-looking value the home page
    shows as "Predicted: X nT"."""
    records = store.dst_predictions.snapshot()
    return records[-1] if records else None


@router.get("/kp")
def get_kp(interval: Literal["24h", "7d", "1mo"] = "7d"):
    return slice_interval(store.kp.snapshot(), interval)


@router.get("/kp/latest")
def get_kp_latest():
    records = store.kp.snapshot()
    return records[-1] if records else None

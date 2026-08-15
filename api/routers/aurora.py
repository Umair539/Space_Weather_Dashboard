from fastapi import APIRouter, HTTPException

from api.aurora import cache

router = APIRouter(prefix="/aurora", tags=["aurora"])


@router.get("")
def get_aurora():
    """Current OVATION aurora nowcast as [lon, lat, probability] triples.

    Longitudes are already normalised to -180..180 and points below the
    display floor dropped, so this is ready to plot as-is.
    """
    payload = cache.get()
    if payload is None:
        # Only reachable if the very first fetch failed and no refresh has
        # succeeded since - there is no stale copy to fall back on, and an
        # empty 200 would render as "no aurora anywhere on Earth", which is
        # a real forecast rather than an outage.
        raise HTTPException(
            status_code=503,
            detail="Aurora forecast is not available yet - the upstream NOAA fetch has not succeeded.",
        )
    return payload

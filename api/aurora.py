"""OVATION aurora forecast, fetched from NOAA and held in memory.

Unlike every other dataset here, this one never goes through Postgres: the
ETL pipeline doesn't ingest it and there's no history to keep - OVATION is
a single "right now" nowcast that NOAA replaces wholesale every few
minutes. So this module is the poller and the store in one, sitting
alongside api/poller.py rather than inside it, which only knows how to read
tables via `updated_at` watermarks.

The raw payload is a 360x181 degree grid, 65,160 points, ~920KB of JSON.
Serving that per visitor would be the single heaviest response the API has
by an order of magnitude, so it's filtered to the points that actually draw
anything before being published (see MIN_PROBABILITY).
"""

import asyncio
import logging
import threading
from datetime import datetime, timezone

import requests

logger = logging.getLogger("api.aurora")

OVATION_URL = "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"

# NOAA regenerates the forecast every ~5 minutes and sets Cache-Control:
# max-age=60. Polling on the same 5-minute cadence keeps the served copy at
# most one cycle behind without hammering a public endpoint.
REFRESH_SECONDS = 300

REQUEST_TIMEOUT = 30

# Aurora values are a percentage chance of visible aurora overhead. Points
# below this are the vast dim background covering most of both hemispheres:
# ~2/3 of the grid is exactly 0, and what remains under 2% is not visible on
# a globe at any zoom. Dropping them is what turns ~920KB into ~150KB. It is
# a display floor, not a data correction - the raw feed is unmodified for
# anyone who wants it.
MIN_PROBABILITY = 2

# The OVATION grid carries a thin band of low nonzero values along the
# equator (latitudes -2..0, typically 1-5%) with nothing at all between
# roughly 12 and 28 degrees either side of it. Aurora cannot occur there:
# the oval sits over the magnetic poles, and even the Carrington event, the
# most extreme storm on record, only pushed it to about 20 degrees magnetic
# latitude. Rendered on a globe the band draws as a false equatorial ring,
# so it's cut here. The 20 degree cutoff is well outside any real aurora
# while sitting far above the artifact.
MIN_ABS_LATITUDE = 20


class AuroraCache:
    """Last successfully fetched forecast. One writer (the refresh task),
    many readers (requests), so the same immutable-swap discipline as
    api/store.py: build the new payload, swap the reference under the lock,
    never mutate what readers may already hold.
    """

    def __init__(self):
        self._payload: dict | None = None
        self._lock = threading.Lock()

    def get(self) -> dict | None:
        with self._lock:
            return self._payload

    def set(self, payload: dict) -> None:
        with self._lock:
            self._payload = payload


cache = AuroraCache()


def parse_ovation(raw: dict) -> dict:
    """Turn NOAA's payload into the compact shape the globe consumes.

    Coordinates arrive as [longitude, latitude, probability] with longitude
    on NOAA's 0-360 convention. The frontend (and every mapping library)
    wants -180..180, so it's converted here rather than in the browser -
    doing it server-side means it happens once per refresh instead of once
    per visitor, and keeps the wire format immediately usable.
    """
    points = [
        # Rounded to whole percent: the source grid is integer-valued
        # already, and floats would only add bytes.
        [lon if lon <= 180 else lon - 360, lat, value]
        for lon, lat, value in raw.get("coordinates", ())
        if value >= MIN_PROBABILITY and abs(lat) >= MIN_ABS_LATITUDE
    ]

    return {
        "observation_time": raw.get("Observation Time"),
        "forecast_time": raw.get("Forecast Time"),
        # Saves the frontend a pass over 20k points just to scale its colour
        # ramp, and means an all-quiet forecast can't be rendered as though
        # its dim maximum were a strong one.
        "max_probability": max((p[2] for p in points), default=0),
        "point_count": len(points),
        "points": points,
    }


def fetch_ovation() -> dict:
    """Blocking fetch + parse. Called in a worker thread."""
    response = requests.get(OVATION_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return parse_ovation(response.json())


async def refresh_once() -> bool:
    """One fetch/publish cycle. Returns whether the cache was updated.

    Failures are logged and swallowed rather than raised: a refresh that
    fails leaves the previous forecast in place, which is the right
    behaviour for a nowcast that's replaced every few minutes anyway. The
    endpoint reports how old what it's serving is, so a stall is visible to
    clients instead of silently pretending to be current.
    """
    try:
        payload = await asyncio.to_thread(fetch_ovation)
    except Exception:
        logger.exception("aurora: OVATION refresh failed, serving previous forecast")
        return False

    payload["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    cache.set(payload)
    logger.info(
        "aurora: refreshed, %d points above %d%%, peak %d%%",
        payload["point_count"],
        MIN_PROBABILITY,
        payload["max_probability"],
    )
    return True


async def refresh_aurora(interval_seconds: float = REFRESH_SECONDS) -> None:
    """Background refresh loop, started by the app lifespan."""
    while True:
        await asyncio.sleep(interval_seconds)
        await refresh_once()

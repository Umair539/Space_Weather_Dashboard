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
# below this are the vast dim background covering most of both hemispheres.
# Dropping non-auroral values keeps payload bandwidth low while preserving
# spatial continuity where the oval actually forms.
MIN_PROBABILITY = 0


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
    on NOAA's 0-360 convention. Converted to -180..180 here so the wire format
    is immediately usable by standard mapping projections.
    """
    raw_coords = raw.get("coordinates", ())

    # Filter out empty background points below display threshold without slicing
    # latitude gaps across the grid equator.
    points = [
        [lon if lon <= 180 else lon - 360, lat, value]
        for lon, lat, value in raw_coords
        if value >= MIN_PROBABILITY
    ]

    return {
        "observation_time": raw.get("Observation Time"),
        "forecast_time": raw.get("Forecast Time"),
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
    """One fetch/publish cycle. Returns whether the cache was updated."""
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

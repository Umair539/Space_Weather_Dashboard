import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.aurora import refresh_aurora, refresh_once
from api.db import POLL_INTERVALS
from api.poller import initial_load, poll_table
from api.rate_limit import RateLimitMiddleware
from api.resource_monitor import log_resource_usage
from api.routers import aurora, geomag, meta, solar_wind, sun

logging.basicConfig(level=logging.INFO)

# How often to log process CPU/RAM usage. Render's own resource dashboard
# is paywalled, so this is the free substitute - visible straight in the
# log stream. Configurable since the "right" cadence trades off log volume
# against how fine-grained the visibility needs to be.
RESOURCE_LOG_INTERVAL_SECONDS = float(os.environ.get("RESOURCE_LOG_INTERVAL_SECONDS", "60"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initial_load()
    # Awaited rather than left to the loop's first tick, so /aurora serves a
    # forecast from the first request instead of 503ing for five minutes.
    # It can't block startup on NOAA being up: refresh_once swallows its own
    # failures, and the endpoint reports the outage on its own.
    await refresh_once()

    tasks = [
        asyncio.create_task(poll_table(table, interval))
        for table, interval in POLL_INTERVALS.items()
    ]
    tasks.append(asyncio.create_task(refresh_aurora()))
    tasks.append(asyncio.create_task(log_resource_usage(RESOURCE_LOG_INTERVAL_SECONDS)))
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="Space Weather API", lifespan=lifespan)

# No data or DB risk from unrestricted traffic - every endpoint is GET,
# unauthenticated, public NOAA-derived data, and the in-memory cache
# already decouples request volume from database load entirely. What this
# actually bounds is Render compute/bandwidth cost and request queueing
# (the container runs one worker deliberately, so a flood of concurrent
# requests can genuinely slow things down for real visitors).
app.add_middleware(RateLimitMiddleware)

# The React frontend will call this straight from the browser, so without
# CORS headers those requests fail regardless of the API being fine. The
# default is "*" because every origin is unknown until that frontend is
# deployed (and preview deploys change origin per build).
#
# "*" is safe specifically because allow_credentials stays False: nothing
# here is authenticated, there are no cookies or session state, and every
# response is public NOAA-derived data that's already free to fetch. A
# permissive origin list has nothing to leak. If credentials were ever
# added, the browser would reject "*" anyway and this would need to become
# an explicit list - hence the env override.
#
# Streamlit doesn't go through this path at all: its server makes the HTTP
# calls in Python and renders the result, so the browser never sees a
# cross-origin request.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",")],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(solar_wind.router)
app.include_router(geomag.router)
app.include_router(sun.router)
app.include_router(aurora.router)
app.include_router(meta.router)


def launch():
    import argparse

    import uvicorn
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["dev", "prod"], default="dev")
    parser.add_argument("--port", type=int, default=8000)
    # Localhost-only by default; --expose binds all interfaces so other
    # devices on the same network (e.g. a phone testing the frontend) can
    # reach it at this machine's LAN IP.
    parser.add_argument("--expose", action="store_true")
    args = parser.parse_args()

    # Before uvicorn starts, so the engine (created lazily on first poll)
    # sees DATABASE_READ_URL. Deployed containers set env vars directly and
    # run `uvicorn api.main:app`, skipping this path entirely.
    load_dotenv(f".env.{args.env}", override=True)
    host = "0.0.0.0" if args.expose else "127.0.0.1"
    uvicorn.run(app, host=host, port=args.port)


if __name__ == "__main__":
    launch()

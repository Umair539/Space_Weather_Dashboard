import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.db import POLL_INTERVALS
from api.poller import initial_load, poll_table
from api.routers import geomag, meta, solar_wind, sun

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initial_load()
    tasks = [
        asyncio.create_task(poll_table(table, interval))
        for table, interval in POLL_INTERVALS.items()
    ]
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="Space Weather API", lifespan=lifespan)
app.include_router(solar_wind.router)
app.include_router(geomag.router)
app.include_router(sun.router)
app.include_router(meta.router)


def launch():
    import argparse

    import uvicorn
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["dev", "prod"], default="dev")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Before uvicorn starts, so the engine (created lazily on first poll)
    # sees DATABASE_READ_URL. Deployed containers set env vars directly and
    # run `uvicorn api.main:app`, skipping this path entirely.
    load_dotenv(f".env.{args.env}", override=True)
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    launch()

import asyncio
import logging

import psutil

logger = logging.getLogger("api.resource_monitor")

# Same process psutil.Process() targets throughout a run, so cpu_percent()
# gets real deltas between calls instead of the meaningless "since process
# start" figure a fresh Process() would report each time.
_proc = psutil.Process()


def _log_once() -> None:
    proc_cpu = _proc.cpu_percent(interval=None)
    proc_rss_mb = _proc.memory_info().rss / 1024**2
    sys_cpu = psutil.cpu_percent(interval=None)
    sys_mem = psutil.virtual_memory().percent
    logger.info(
        "resource usage: proc_cpu=%.1f%% proc_rss=%.1fMB sys_cpu=%.1f%% sys_mem=%.1f%%",
        proc_cpu,
        proc_rss_mb,
        sys_cpu,
        sys_mem,
    )


async def log_resource_usage(interval_s: float) -> None:
    """Periodically logs process/system CPU and memory usage.

    Render's own resource dashboard is paywalled, so this gives free
    visibility into CPU/RAM through the log stream instead. The container
    runs a single uvicorn worker (see docker/api/Dockerfile), so the
    process-level numbers are the ones that matter here.
    """
    while True:
        try:
            await asyncio.to_thread(_log_once)
        except Exception:
            # never let one failed sample kill the loop
            logger.exception("resource usage logging failed")
        await asyncio.sleep(interval_s)

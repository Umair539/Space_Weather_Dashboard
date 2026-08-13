"""Per-IP rate limiting, hand-rolled against `limits` (the counting engine
the `slowapi` package itself wraps) rather than using slowapi directly.

slowapi was tried first and dropped: its middleware finds "which endpoint
is this request for" by walking app.routes and matching each entry's
.matches() against the request - but this FastAPI version wraps routes
registered via include_router in an internal _IncludedRouter type that
slowapi's matching code doesn't recognise. Confirmed directly (not
assumed): calling slowapi's own _find_route_handler against this app's
real routes returned None for every single endpoint. slowapi treats "no
handler found" as "exempt this route" - silently, no error - so the limit
was never actually being enforced on anything.

Plain ASGI middleware sidesteps the whole problem: it runs on every
request unconditionally, with no route-tree introspection involved, so
this failure mode can't recur here.
"""

import os

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# 60/minute: generous enough that real browsing never brushes it. Home
# alone fires 5 concurrent requests on mount (before settling to ~2.5/min
# steady state from its 120s poll), and that burst repeats on every
# reload/navigation and doubles under React StrictMode's dev double-mount -
# 20/minute left too little headroom above that legitimate traffic. This
# still bounds what a script hammering the API can cost in Render compute/
# bandwidth - not because anything sensitive is at risk, every response
# here is public data, but because the container runs one worker
# deliberately (so the in-memory cache stays one consistent copy), and a
# flood of concurrent requests can genuinely queue up and slow things down
# for real visitors.
_RATE = parse("60/minute")
_limiter = MovingWindowRateLimiter(MemoryStorage())

# Render's own health check hits this far more often than any real visitor
# would - a 429 here risks Render marking a perfectly healthy service down.
_EXEMPT_PATHS = {"/health"}


def client_ip(request: Request) -> str:
    """Cloudflare sits in front of Render (confirmed via CF-RAY and
    x-render-origin-server on every response), so the raw TCP peer address
    FastAPI sees is Cloudflare's edge, not the visitor - every visitor
    would collapse into one "IP" and a per-IP limit would silently become
    a whole-site limit instead. CF-Connecting-IP is the header Cloudflare
    sets to the real client address on every proxied request.
    X-Forwarded-For covers any hop that isn't Cloudflare (or local testing
    without it); the raw peer address is the last-resort fallback for a
    direct connection with neither header set.
    """
    if cf_ip := request.headers.get("CF-Connecting-IP"):
        return cf_ip
    if forwarded := request.headers.get("X-Forwarded-For"):
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Checked per-request rather than once at middleware construction:
        # api.main.app is a module-level singleton built at import time, so
        # a test suite that imports it before setting this env var couldn't
        # otherwise turn it off. tests/conftest.py sets this to "false" for
        # the whole run - the component/integration tests fire well over 20
        # requests at a single shared TestClient "IP" across one module,
        # which has nothing to do with what those tests are actually
        # checking (schema, ordering, validation).
        if os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "false":
            return await call_next(request)

        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        if not _limiter.hit(_RATE, client_ip(request)):
            return JSONResponse(
                {"detail": "Rate limit exceeded: 60 per 1 minute"}, status_code=429
            )

        return await call_next(request)

import os

# The api/ rate limiter is per-process global state, and every component/
# integration test that hits api.main.app shares one TestClient "IP" - a
# single test module easily fires well past the real 60/minute limit,
# which has nothing to do with what those tests actually check (schema,
# ordering, validation, not rate limiting itself). Set once, for the whole
# suite, before any test imports api.main (which builds the FastAPI app -
# and with it, the rate limit middleware - at import time).
os.environ["RATE_LIMIT_ENABLED"] = "false"

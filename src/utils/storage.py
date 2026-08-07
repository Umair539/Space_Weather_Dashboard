import os
import threading
from src.utils.s3 import S3Client
from src.utils.r2 import R2Client

# Constructed once and reused across calls/threads instead of a fresh client
# (and fresh connection pool/TLS setup) per call. boto3 clients are
# thread-safe, so sharing one is safe now that fetch_saved/load_raw_* run
# concurrently on a thread pool. Double-checked locking since the first
# concurrent batch of calls can race on construction otherwise.
_client = None
_lock = threading.Lock()


def get_storage_client():
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                if os.environ.get("ENV", "dev") == "prod":
                    _client = S3Client()
                else:
                    _client = R2Client()
    return _client

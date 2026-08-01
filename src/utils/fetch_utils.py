import logging
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.logging_utils import setup_logger
from src.utils.validator import validate_schema

# Configure the logger
logger = setup_logger(__name__, "extract_data.log", level=logging.DEBUG)


def _make_session():
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


_session = _make_session()


def _put_metric(metric_name, source):
    if os.environ.get("ENV", "dev") != "prod":
        return
    try:
        # Instantiate inside function to avoid NoRegionError on import in dev
        import boto3

        cw = boto3.client("cloudwatch", region_name="eu-west-2")
        cw.put_metric_data(
            Namespace="SpaceWeather",
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Dimensions": [{"Name": "Source", "Value": source}],
                    "Value": 1,
                    "Unit": "Count",
                }
            ],
        )
    except Exception:
        logger.warning(f"Failed to emit CloudWatch {metric_name} metric")


def put_fetch_metric(name):
    _put_metric("SuccessfulFetch", name)


def put_fetch_failure_metric(name):
    _put_metric("FailedFetch", name)


def get_response(url, **kwargs):
    return _session.get(url, timeout=10, **kwargs)


def _fetch_with_retries(label, fetch_fn, name, attempts):
    # Validating here (not just catching exceptions) matters because a WAF
    # challenge response can come back as a 200 with an empty body - a
    # non-raising HTTP call alone isn't proof of a good fetch.
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            data = fetch_fn()
            validate_schema(name, data)
            return data
        except Exception as e:
            last_exc = e
            logger.warning(f"{label}: attempt {attempt}/{attempts} failed: {e}")
    raise last_exc


def fetch_with_fallback(name, primary, fallback, attempts=3):
    """Try `primary` up to `attempts` times, then `fallback` up to `attempts`
    times. Only once both are exhausted is it a real failure - emits a
    CloudWatch FailedFetch metric and re-raises for the caller to handle."""
    try:
        return _fetch_with_retries(f"{name} (primary)", primary, name, attempts)
    except Exception as primary_exc:
        logger.warning(
            f"{name}: primary exhausted {attempts} attempts, falling back: {primary_exc}"
        )

    try:
        return _fetch_with_retries(f"{name} (fallback)", fallback, name, attempts)
    except Exception as fallback_exc:
        logger.warning(
            f"{name}: fallback also exhausted {attempts} attempts: {fallback_exc}"
        )
        put_fetch_failure_metric(name)
        raise

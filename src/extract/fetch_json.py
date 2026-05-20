import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.validator import validate_schema
from src.utils.logging_utils import setup_logger

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


def fetch_json(url, name):
    response = get_response(url)
    json_data = extract_json(response)
    validate_schema(name, json_data)
    logger.info(f"Successfully retrieved data from {url}")
    return json_data


def get_response(url):
    return _session.get(url, timeout=10)


def extract_json(response):
    return response.json()

import json

import boto3
from botocore import UNSIGNED
from botocore.config import Config

from src.utils.fetch_utils import get_response, fetch_with_fallback

# Public AWS Open Data bucket mirroring NOAA SWPC products - no credentials needed.
BUCKET = "noaa-swpc-pds"
REGION = "us-east-1"

NOAA_MAG_URL = "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"
NOAA_PLASMA_URL = "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"
MAG_S3_KEY = "json/rtsw/rtsw_mag_1m.json"
PLASMA_S3_KEY = "json/rtsw/rtsw_wind_1m.json"

_s3 = boto3.client("s3", region_name=REGION, config=Config(signature_version=UNSIGNED))


def fetch_rtsw_json(key, bucket=BUCKET):
    obj = _s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read())


def _fetch_mag_noaa():
    return get_response(NOAA_MAG_URL).json()


def _fetch_mag_s3():
    return fetch_rtsw_json(MAG_S3_KEY)


def _fetch_plasma_noaa():
    return get_response(NOAA_PLASMA_URL).json()


def _fetch_plasma_s3():
    return fetch_rtsw_json(PLASMA_S3_KEY)


def fetch_mag():
    return fetch_with_fallback("mag", _fetch_mag_noaa, _fetch_mag_s3)


def fetch_plasma():
    return fetch_with_fallback("plasma", _fetch_plasma_noaa, _fetch_plasma_s3)

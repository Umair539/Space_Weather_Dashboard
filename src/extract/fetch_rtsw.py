import json

import boto3
from botocore import UNSIGNED
from botocore.config import Config

# Public AWS Open Data bucket mirroring NOAA SWPC products - no credentials needed.
BUCKET = "noaa-swpc-pds"
REGION = "us-east-1"

MAG_KEY = "json/rtsw/rtsw_mag_1m.json"
PLASMA_KEY = "json/rtsw/rtsw_wind_1m.json"

_s3 = boto3.client("s3", region_name=REGION, config=Config(signature_version=UNSIGNED))


def fetch_rtsw_json(key, bucket=BUCKET):
    obj = _s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read())


def fetch_mag():
    return fetch_rtsw_json(MAG_KEY)


def fetch_plasma():
    return fetch_rtsw_json(PLASMA_KEY)

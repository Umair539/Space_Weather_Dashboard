import gzip
import boto3
import orjson
import os
from botocore.config import Config

# See r2.py - shared across thread pools, so raise the pool size beyond the
# default of 10.
_CONFIG = Config(max_pool_connections=50)


class S3Client:
    def __init__(self):
        self.bucket = os.getenv("S3_BUCKET")
        self.client = boto3.client(
            "s3",
            region_name="eu-west-2",
            config=_CONFIG,
        )

    def download_json(self, key):
        # Stored as key + ".gz" (orjson + gzip). All previously-plain objects
        # were backfilled to this format in a one-time migration, so there's
        # no legacy plain-JSON fallback to handle here.
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=f"{key}.gz")
            return orjson.loads(gzip.decompress(response["Body"].read()))
        except self.client.exceptions.NoSuchKey:
            return None

    def upload_json(self, key, data):
        # Only ever write the new gzip format going forward - the plain
        # key is left as whatever it already was (untouched if it exists,
        # never created if it doesn't).
        self.client.put_object(
            Bucket=self.bucket,
            Key=f"{key}.gz",
            Body=gzip.compress(orjson.dumps(data)),
            ContentType="application/json",
            ContentEncoding="gzip",
        )

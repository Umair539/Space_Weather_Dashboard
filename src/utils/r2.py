import gzip
import boto3
import orjson
import os
from botocore.config import Config

# This client is now shared across the extract/load thread pools, which can
# have several dozen requests in flight at once. Default max_pool_connections
# is 10 - raise it so sharing doesn't serialize that concurrency.
_CONFIG = Config(max_pool_connections=50)


class R2Client:
    def __init__(self):
        self.bucket = os.getenv("R2_BUCKET")
        self.client = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            region_name="auto",
            config=_CONFIG,
        )

    def download_json(self, key):
        # See s3.py - same reasoning, no legacy plain-JSON fallback needed.
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=f"{key}.gz")
            return orjson.loads(gzip.decompress(response["Body"].read()))
        except self.client.exceptions.NoSuchKey:
            return None

    def upload_json(self, key, data):
        self.client.put_object(
            Bucket=self.bucket,
            Key=f"{key}.gz",
            Body=gzip.compress(orjson.dumps(data)),
            ContentType="application/json",
            ContentEncoding="gzip",
        )

    def download_bytes(self, key):
        # Unlike download_json, no gzip suffix/compression - Parquet is
        # already a compressed binary format, so callers pass the key as-is.
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except self.client.exceptions.NoSuchKey:
            return None

    def upload_bytes(self, key, data, content_type="application/octet-stream"):
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def list_keys(self, prefix):
        keys = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return keys

    def delete_objects(self, keys):
        # delete_objects caps at 1000 keys per call.
        for i in range(0, len(keys), 1000):
            batch = keys[i : i + 1000]
            self.client.delete_objects(
                Bucket=self.bucket,
                Delete={"Objects": [{"Key": k} for k in batch]},
            )

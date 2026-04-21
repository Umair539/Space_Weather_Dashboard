import json
import boto3
import os


class S3Client:
    def __init__(self):
        self.bucket = os.getenv("S3_BUCKET")
        self.client = boto3.client(
            "s3",
            region_name="eu-west-2",
        )

    def download_json(self, key):
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return json.loads(response["Body"].read())
        except self.client.exceptions.NoSuchKey:
            return None

    def upload_json(self, key, data):
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(data, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

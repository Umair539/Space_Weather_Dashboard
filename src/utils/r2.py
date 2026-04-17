import json
import boto3
import os


class R2Client:
    def __init__(self):
        self.bucket = os.getenv("R2_BUCKET")
        self.client = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            region_name="auto",
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

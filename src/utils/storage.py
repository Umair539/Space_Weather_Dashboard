import os
from src.utils.s3 import S3Client
from src.utils.r2 import R2Client


def get_storage_client():
    if os.environ.get("ENV", "dev") == "prod":
        return S3Client()
    return R2Client()

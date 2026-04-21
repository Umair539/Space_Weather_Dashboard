import pandas as pd
from src.utils.s3 import S3Client
from src.utils.parser import parse_data
from src.utils.logging_utils import setup_logger

logger = setup_logger("fetch_saved_data", "transform_data.log")


def fetch_saved_data(file_path, raw=None):
    if raw is None:
        logger.info(f"Fetching {file_path} from S3...")
        s3 = S3Client()
        raw = s3.download_json(file_path)
    else:
        logger.info(f"Using updated data for {file_path}, skipping S3.")
    if not raw:
        logger.warning(f"No data found for {file_path}, returning empty DataFrame.")
        return pd.DataFrame()
    return pd.DataFrame(parse_data(raw))

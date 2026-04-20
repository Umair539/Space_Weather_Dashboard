import pandas as pd
from src.utils.r2 import R2Client
from src.utils.parser import parse_data


def fetch_saved_data(file_path, raw=None):
    if raw is None:
        r2 = R2Client()
        raw = r2.download_json(file_path)
    if not raw:
        return pd.DataFrame()
    return pd.DataFrame(parse_data(raw))

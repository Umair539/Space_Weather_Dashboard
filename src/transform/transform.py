from src.transform.process_solar_wind import process_solar_wind
from src.transform.process_dst import process_dst
from src.transform.process_kp import process_kp
from src.utils.logging_utils import setup_logger
import pandas as pd
import json

# from src.transform.aggregate_solar_wind import aggregate_solar_wind
logger = setup_logger("transform_data", "transform_data.log")


def transform_data():
    try:
        logger.info("Loading raw data...")

        with open("data/raw/mag.json") as f:
            mag_raw = json.load(f)
        with open("data/raw/plasma.json") as f:
            plasma_raw = json.load(f)
        with open("data/raw/dst.json") as f:
            dst_raw = json.load(f)
        with open("data/raw/kp.json") as f:
            kp_raw = json.load(f)

        logger.info("Raw data loaded. Converting to DataFrames...")

        mag = pd.DataFrame(mag_raw[1:], columns=mag_raw[0])
        plasma = pd.DataFrame(plasma_raw[1:], columns=plasma_raw[0])
        dst = pd.DataFrame(dst_raw[1:], columns=dst_raw[0])
        kp = pd.DataFrame(kp_raw[1:], columns=kp_raw[0])

        logger.info("Starting data transformation process...")

        logger.info("Transforming solar wind data...")
        solar = process_solar_wind(mag, plasma)
        logger.info("Solar wind data transformation complete.")

        # logger.info("Aggregating solar wind data...")
        # solar_agg = aggregate_solar_wind(solar)
        # logger.info("Solar wind data aggregation complete.")

        logger.info("Transforming dst data...")
        dst = process_dst(dst)
        logger.info("Dst data transformation complete.")

        logger.info("Transforming kp data...")
        kp = process_kp(kp)
        logger.info("Kp data transformation complete.")

        logger.info("Data transformations completed.")

        return (solar, dst, kp)  # solar_agg
    except Exception as e:
        logger.error(f"Data transformation failed: {str(e)}")
        raise

from src.transform.process_solar_wind import process_solar_wind
from src.transform.process_dst import process_dst
from src.transform.process_kp import process_kp
from src.transform.process_ssn import process_ssn
from src.transform.process_smoothed_ssn import process_smoothed_ssn
from src.transform.prepare_model_input import prepare_model_input
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
        with open("data/raw/ssn.json") as f:
            ssn_raw = json.load(f)
        with open("data/raw/smoothed_ssn.json") as f:
            smoothed_ssn_raw = json.load(f)

        logger.info("Raw data loaded. Converting to DataFrames...")

        mag = pd.DataFrame(mag_raw[1:], columns=mag_raw[0])
        plasma = pd.DataFrame(plasma_raw[1:], columns=plasma_raw[0])
        dst = pd.DataFrame(dst_raw)
        kp = pd.DataFrame(kp_raw)
        ssn = pd.DataFrame(ssn_raw)
        smoothed_ssn = pd.DataFrame(smoothed_ssn_raw)

        logger.info("Starting data transformation process...")

        logger.info("Transforming solar wind data...")
        solar = process_solar_wind(mag, plasma)
        logger.info("Solar wind data transformation complete.")

        logger.info("Transforming dst data...")
        dst = process_dst(dst)
        logger.info("Dst data transformation complete.")

        logger.info("Transforming kp data...")
        kp = process_kp(kp)
        logger.info("Kp data transformation complete.")

        logger.info("Transforming sunspot data...")
        ssn = process_ssn(ssn)
        logger.info("Sunspot data transformation complete.")

        logger.info("Transforming smoothed sunspot data...")
        smoothed_ssn = process_smoothed_ssn(smoothed_ssn)
        logger.info("Smoothed sunspot data transformation complete.")

        # model inference
        model_input = prepare_model_input(solar, smoothed_ssn)

        #

        logger.info("Data transformations completed.")

        return (solar, dst, kp, ssn, smoothed_ssn)
    except Exception as e:
        logger.error(f"Data transformation failed: {str(e)}")
        raise

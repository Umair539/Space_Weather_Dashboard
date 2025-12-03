import pandas as pd
from src.extract.extract_data_from_json import extract_data_from_json
from src.utils.logging_utils import setup_logger

logger = setup_logger("extract_data", "extract_data.log")

mag_url = "https://services.swpc.noaa.gov/products/solar-wind/mag-7-day.json"
plasma_url = """"
        https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json
    """
dst_url = "https://services.swpc.noaa.gov/products/kyoto-dst.json"
kp_url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"


def extract_data():
    try:
        logger.info("Starting data extraction process")

        mag = extract_data_from_json(mag_url)
        plasma = extract_data_from_json(plasma_url)
        dst = extract_data_from_json(dst_url)
        kp = extract_data_from_json(kp_url)

        logger.info("Completed data extraction process")

        return (mag, plasma, dst, kp)

    except Exception as e:
        logger.error(f"Data extraction from json failed: {str(e)}.")
        logger.info("Retrieving raw data from previous successful extraction.")

        try:
            plasma = pd.read_csv("data/raw/plasma.csv")
            mag = pd.read_csv("data/raw/mag.csv")
            kp = pd.read_csv("data/raw/kp.csv")
            dst = pd.read_csv("data/raw/dst.csv")

            return (mag, plasma, dst, kp)

        except FileNotFoundError:
            logger.error("No local files available")

        except Exception as e:
            logger.error(
                f"An unexpected error occured when retrieving local files: {e}"
            )

from src.extract.fetch_json import fetch_json
from src.utils.logging_utils import setup_logger

logger = setup_logger("extract_data", "extract_data.log")

base_url = "https://services.swpc.noaa.gov/products/"

mag_url = base_url + "solar-wind/mag-7-day.json"
plasma_url = base_url + "solar-wind/plasma-7-day.json"
dst_url = base_url + "kyoto-dst.json"
kp_url = base_url + "noaa-planetary-k-index.json"


def extract_data():
    try:
        logger.info("Starting data extraction process")

        mag = fetch_json(mag_url)
        plasma = fetch_json(plasma_url)
        dst = fetch_json(dst_url)
        kp = fetch_json(kp_url)

        logger.info("Completed data extraction process")

        return (mag, plasma, dst, kp)

    except Exception as e:
        logger.error(f"Failed to retrieve NOAA JSON data: {str(e)}.")
        logger.info(
            "Transformation will be done on raw JSON data from previous successful extraction."
        )

from src.extract.fetch_json import fetch_json
from src.utils.logging_utils import setup_logger

logger = setup_logger("extract_data", "extract_data.log")

base_url = "https://services.swpc.noaa.gov/"

mag_url = base_url + "products/solar-wind/mag-7-day.json"
plasma_url = base_url + "products/solar-wind/plasma-7-day.json"

# mag_url = base_url + "json/rtsw/rtsw_mag_1m.json"
# plasma_url = base_url + "json/rtsw/rtsw_wind_1m.json"

dst_url = base_url + "products/kyoto-dst.json"
kp_url = base_url + "products/noaa-planetary-k-index.json"

ssn_url = base_url + "json/solar-cycle/swpc_observed_ssn.json"
smoothed_ssn_url = base_url + "json/solar-cycle/predicted-solar-cycle.json"


def extract_data():
    try:
        logger.info("Starting data extraction process")

        mag = fetch_json(mag_url)
        plasma = fetch_json(plasma_url)
        dst = fetch_json(dst_url)
        kp = fetch_json(kp_url)
        ssn = fetch_json(ssn_url)
        smoothed_ssn = fetch_json(smoothed_ssn_url)

        logger.info("Completed data extraction process")

        return (mag, plasma, dst, kp, ssn, smoothed_ssn)

    except Exception as e:
        logger.error(f"Failed to retrieve NOAA JSON data: {str(e)}.")
        logger.info(
            "Transformation will be done on raw JSON data from previous successful extraction."
        )

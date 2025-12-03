from src.transform.process_solar_wind import process_solar_wind
from src.transform.aggregate_solar_wind import aggregate_solar_wind
from src.transform.process_dst import process_dst
from src.transform.process_kp import process_kp
from src.utils.logging_utils import setup_logger

logger = setup_logger("transform_data", "transform_data.log")


def transform_data(extracted_data):
    try:
        mag, plasma, dst, kp = extracted_data

        logger.info("Starting data transformation process...")

        logger.info("Transforming solar wind data...")
        solar = process_solar_wind(mag, plasma)
        logger.info("Solar wind data transformation complete.")

        logger.info("Aggregating solar wind data...")
        solar_agg = aggregate_solar_wind(solar)
        logger.info("Solar wind data aggregation complete.")

        logger.info("Transforming dst data...")
        dst = process_dst(dst)
        logger.info("Dst data transformation complete.")

        logger.info("Transforming kp data...")
        kp = process_kp(kp)
        logger.info("Kp data transformation complete.")

        logger.info("Data transformations completed.")

        return (solar, solar_agg, dst, kp)
    except Exception as e:
        logger.error(f"Data transformation failed: {str(e)}")

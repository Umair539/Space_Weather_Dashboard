from src.transform.fetch_saved_data import fetch_saved_data
from src.transform.process_solar_wind import process_solar_wind
from src.transform.process_dst import process_dst
from src.transform.process_kp import process_kp
from src.transform.process_ssn import process_ssn
from src.transform.process_smoothed_ssn import process_smoothed_ssn
from src.transform.prepare_model_inputs import prepare_model_inputs
from src.transform.model_inference import model_inference
from src.utils.logging_utils import setup_logger

logger = setup_logger("transform_data", "transform_data.log")


def transform_data():
    try:
        logger.info("Fetching saved data...")

        mag = fetch_saved_data("data/raw/mag/")
        plasma = fetch_saved_data("data/raw/plasma/")
        dst = fetch_saved_data("data/raw/dst/")
        kp = fetch_saved_data("data/raw/kp/")
        ssn = fetch_saved_data("data/raw/ssn/")
        smoothed_ssn = fetch_saved_data("data/raw/smoothed_ssn/")

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
        logger.info("Preparing data for model inference...")
        model_inputs = prepare_model_inputs(solar, smoothed_ssn)
        logger.info("Completed preparing data for model inference.")

        logger.info("Performing model inference...")
        dst = model_inference(model_inputs, dst)
        logger.info("Model inference complete.")

        logger.info("Data transformations completed.")

        return (solar, dst, kp, ssn)
    except Exception as e:
        logger.error(f"Data transformation failed: {str(e)}")
        raise

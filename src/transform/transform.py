from src.utils.fetch_saved_data import fetch_saved_data
from src.transform.process_rtsw import process_rtsw
from src.transform.process_dst import process_dst
from src.transform.process_kp import process_kp
from src.transform.process_ssn import process_ssn
from src.transform.process_smoothed_ssn import process_smoothed_ssn
from src.transform.prepare_model_inputs import prepare_model_inputs
from src.transform.model_inference import model_inference
from src.utils.logging_utils import setup_logger

logger = setup_logger("transform_data", "transform_data.log")


def transform_data(updated_data=None):
    try:
        old_mag, old_plasma, mag, plasma, dst, kp, ssn, smoothed_ssn = (
            updated_data if updated_data else (None,) * 8
        )

        old_mag = fetch_saved_data("mag/lists.json", old_mag)
        old_plasma = fetch_saved_data("plasma/lists.json", old_plasma)
        mag = fetch_saved_data("mag/dicts.json", mag)
        plasma = fetch_saved_data("plasma/dicts.json", plasma)
        dst = fetch_saved_data("dst/dicts.json", dst)
        kp = fetch_saved_data("kp/dicts.json", kp)
        ssn = fetch_saved_data("ssn/dicts.json", ssn)
        smoothed_ssn = fetch_saved_data("smoothed_ssn/dicts.json", smoothed_ssn)

        logger.info("Starting data transformation process...")

        logger.info("Transforming solar wind data...")
        solar = process_rtsw(mag, plasma, old_mag, old_plasma)
        del mag, plasma, old_mag, old_plasma
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
        del smoothed_ssn
        logger.info("Completed preparing data for model inference.")

        logger.info("Performing model inference...")
        dst_predictions = model_inference(model_inputs)
        del model_inputs
        logger.info("Model inference complete.")

        logger.info("Data transformations completed.")

        return (solar, dst, kp, ssn, dst_predictions)
    except Exception as e:
        logger.error(f"Data transformation failed: {str(e)}")
        raise

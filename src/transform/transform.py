from src.transform.process_rtsw import process_rtsw
from src.transform.process_dst import process_dst
from src.transform.process_kp import process_kp
from src.transform.process_ssn import process_ssn
from src.transform.process_smoothed_ssn import process_smoothed_ssn
from src.transform.prepare_model_inputs import prepare_model_inputs
from src.transform.model_inference import model_inference
from src.utils.logging_utils import setup_logger

logger = setup_logger("transform_data", "transform_data.log")


def transform_data(saved_data):
    try:
        old_mag = saved_data.get("old_mag")
        old_plasma = saved_data.get("old_plasma")
        mag = saved_data.get("mag")
        plasma = saved_data.get("plasma")
        dst = saved_data.get("dst")
        kp = saved_data.get("kp")
        ssn = saved_data.get("ssn")
        smoothed_ssn = saved_data.get("smoothed_ssn")

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

        logger.info("Data transformations complete.")

        return (solar, dst, kp, ssn, dst_predictions)

    except Exception as e:
        logger.error(f"Data transformation failed: {str(e)}")
        raise

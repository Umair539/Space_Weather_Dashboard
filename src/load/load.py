from src.utils.logging_utils import setup_logger
from src.load.load_raw_json import load_raw_json
from src.load.load_data_into_db import load_data_into_db
from src.load.load_raw_rtsw import load_raw_rtsw

logger = setup_logger("load_data", "load_data.log")


def load_raw_data(extracted_data):
    try:
        old_mag, old_plasma, mag, plasma, dst, kp, ssn, smoothed_ssn = extracted_data
    except Exception as e:
        logger.error(f"Failed to unpack extracted data: {e}")
        return ()
    logger.info("Loading raw data...")

    results = {}
    for name, folder_path, loader, data in [
        ("old_mag", "mag", load_raw_json, old_mag),
        ("old_plasma", "plasma", load_raw_json, old_plasma),
        ("mag", "mag", load_raw_rtsw, mag),
        ("plasma", "plasma", load_raw_rtsw, plasma),
        ("dst", "dst", load_raw_json, dst),
        ("kp", "kp", load_raw_json, kp),
        ("ssn", "ssn", load_raw_json, ssn),
        ("smoothed_ssn", "smoothed_ssn", load_raw_json, smoothed_ssn),
    ]:
        try:
            results[name] = loader(folder_path, data)
        except Exception as e:
            logger.error(f"Failed to load {folder_path}: {e}")
            results[name] = None

    logger.info("Raw data loading complete.")
    return (
        results["old_mag"], results["old_plasma"],
        results["mag"], results["plasma"],
        results["dst"], results["kp"],
        results["ssn"], results["smoothed_ssn"],
    )


def load_transformed_data(transformed_data):
    try:
        logger.info("Saving transformed data to Supabase SQL database...")
        load_data_into_db(transformed_data)
        logger.info("Supabase SQL database updated successfully.")

    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")
        raise

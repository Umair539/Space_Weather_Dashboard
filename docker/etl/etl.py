import logging

from src.extract.extract import extract_live_data, extract_saved_data
from src.load.load import load_raw_data, load_transformed_data
from src.load.compact_ovation import compact_yesterday
from src.transform.transform import transform_data

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    # Two schedules share this one function: the usual ~3-minute EventBridge
    # rule invokes it with no action (runs the ETL below as normal), and a
    # separate once-daily rule invokes it with {"action": "compact_ovation"}
    # in its target Input to run the OVATION day-file compaction instead -
    # see compact_ovation.py for why that has to be a lower-frequency job of
    # its own rather than something the 3-minute pipeline does inline.
    if event and event.get("action") == "compact_ovation":
        return _handle_compact_ovation()

    return _handle_etl()


def _handle_compact_ovation():
    try:
        logger.info("Starting OVATION compaction")
        rows = compact_yesterday()
        logger.info(f"OVATION compaction complete ({rows} rows).")
    except Exception as e:
        logger.error(f"OVATION compaction failed: {e}")
        raise


def _handle_etl():
    try:
        logger.info("Starting ETL pipeline")

        logger.info("Beginning live data extraction phase...")
        live_data = extract_live_data()
        logger.info("Live data extraction complete.")

        logger.info("Beginning raw data load phase...")
        load_raw_data(live_data)
        logger.info("Raw data load complete.")

        logger.info("Beginning saved data extraction phase...")
        saved_data = extract_saved_data(filter_raw=True)
        logger.info("Saved data extraction complete.")

        logger.info("Beginning transformation phase...")
        transformed_data = transform_data(saved_data)
        logger.info("Transformation complete.")

        logger.info("Beginning transformed data load phase...")
        load_transformed_data(transformed_data)
        logger.info("Transformed data load complete.")

        logger.info("ETL pipeline successful.")

    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}")
        raise

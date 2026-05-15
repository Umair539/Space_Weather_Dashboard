import argparse
from dotenv import load_dotenv

from src.extract.extract import extract_live_data, extract_saved_data
from src.load.load import load_raw_data, load_transformed_data
from src.transform.transform import transform_data
from src.utils.logging_utils import setup_logger


def run_etl_pipeline():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env",
        choices=["dev", "prod"],
        required=False,
        help="Target environment",
        default="dev",
    )
    parser.add_argument(
        "--upsert-hours",
        type=int,
        required=False,
        help="Hours of data to upsert (default: 168 = 1 week)",
        default=24 * 7,
    )
    parser.add_argument(
        "--filter-raw",
        action="store_true",
        required=False,
        default=False,
        help="Filter saved data to last 2 months",
    )
    args = parser.parse_args()
    load_dotenv(f".env.{args.env}", override=True)

    logger = setup_logger("etl_pipeline", "etl_pipeline.log")

    try:
        logger.info(
            f"Starting ETL pipeline [env={args.env}, filter_raw={args.filter_raw}]"
        )

        logger.info("Beginning live data extraction phase...")
        live_data = extract_live_data()
        logger.info("Live data extraction complete.")

        logger.info("Beginning raw data load phase...")
        load_raw_data(live_data)
        logger.info("Raw data load complete.")

        logger.info("Beginning saved data extraction phase...")
        saved_data = extract_saved_data(filter_raw=args.filter_raw)
        logger.info("Saved data extraction complete.")

        logger.info("Beginning transformation phase...")
        transformed_data = transform_data(saved_data)
        logger.info("Transformation complete.")

        logger.info("Beginning transformed data load phase...")
        load_transformed_data(transformed_data, upsert_hours=args.upsert_hours)
        logger.info("Transformed data load complete.")

        logger.info("ETL pipeline successful.")

    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}")
        raise

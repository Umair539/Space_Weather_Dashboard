import argparse

from dotenv import load_dotenv

from src.load.compact_ovation import compact_day, compact_yesterday
from src.utils.logging_utils import setup_logger


def run_compact_ovation():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env",
        choices=["dev", "prod"],
        default="prod",
        help="Target environment (ovation always lives in R2 regardless, "
        "but this still selects which .env file/bucket to load)",
    )
    parser.add_argument(
        "--date",
        required=False,
        default=None,
        help="Day to compact, YYYY-MM-DD. Default: yesterday (UTC) - the "
        "usual daily job target, since that day is no longer being written "
        "to by the live pipeline.",
    )
    args = parser.parse_args()
    load_dotenv(f".env.{args.env}", override=True)

    logger = setup_logger("compact_ovation", "etl_pipeline.log")

    if args.date:
        year, month, day = args.date.split("-")
        logger.info(f"Compacting ovation/{year}/{month}/{day}...")
        rows = compact_day("ovation", year, month, day)
    else:
        logger.info("Compacting yesterday's ovation data...")
        rows = compact_yesterday()

    logger.info(f"Ovation compaction complete ({rows} rows).")


if __name__ == "__main__":
    run_compact_ovation()

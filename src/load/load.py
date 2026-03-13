from src.utils.logging_utils import setup_logger
import json
from sqlalchemy import create_engine

logger = setup_logger("load_data", "load_data.log")


def load_raw_data(extracted_data):
    try:
        mag, plasma, dst, kp = extracted_data

        logger.info("Saving raw data...")

        with open("data/raw/mag.json", "w") as f:
            json.dump(mag, f, indent=2)

        with open("data/raw/plasma.json", "w") as f:
            json.dump(plasma, f, indent=2)

        with open("data/raw/dst.json", "w") as f:
            json.dump(dst, f, indent=2)

        with open("data/raw/kp.json", "w") as f:
            json.dump(kp, f, indent=2)

        logger.info("Raw data saved.")

    except Exception as e:
        logger.error(f"Failed to load raw data: {str(e)}")


def load_transformed_data(transformed_data):
    try:
        solar, solar_agg, dst, kp = transformed_data

        db_path = "data/transformed/noaa_data.db"

        engine = create_engine(f"sqlite:///{db_path}")

        logger.info(f"Saving transformed data to {db_path}...")

        # Saving as tables
        solar.to_sql("solar", engine, if_exists="replace", index=True)
        solar_agg.to_sql("solar_agg", engine, if_exists="replace", index=True)
        dst.to_sql("dst", engine, if_exists="replace", index=True)
        kp.to_sql("kp", engine, if_exists="replace", index=True)

        logger.info("SQL database updated in data/transformed/.")

    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")

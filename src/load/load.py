from src.utils.logging_utils import setup_logger
import json
from sqlalchemy import create_engine
from sqlalchemy import text

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
        solar, dst, kp = transformed_data  # solar_agg,

        db_path = "data/transformed/noaa_data.db"

        engine = create_engine(f"sqlite:///{db_path}")

        logger.info(f"Saving transformed data to {db_path}...")

        # Saving as temp tables then switching
        # prevent errors reading whilst table updating
        # clear out any old temp indexes/tables first
        with engine.begin() as conn:
            for name in ["solar", "dst", "kp"]:
                conn.execute(text(f"DROP INDEX IF EXISTS ix_{name}_temp_time"))
                conn.execute(text(f"DROP TABLE IF EXISTS {name}_temp"))

        solar.to_sql("solar_temp", engine, if_exists="replace", index=True)
        dst.to_sql("dst_temp", engine, if_exists="replace", index=True)
        # solar_agg.to_sql("solar_agg_temp", engine, if_exists="replace", index=True)
        kp.to_sql("kp_temp", engine, if_exists="replace", index=True)

        with engine.begin() as conn:
            for name in ["solar", "dst", "kp"]:  # solar_agg
                conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
                conn.execute(text(f"ALTER TABLE {name}_temp RENAME TO {name}"))

        logger.info("SQL database updated in data/transformed/.")

    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")
        raise

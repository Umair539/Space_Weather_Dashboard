from src.utils.logging_utils import setup_logger
from src.load.load_raw_json_dicts import load_raw_json_dicts
from src.load.load_raw_json_lists import load_raw_json_lists
from sqlalchemy import create_engine
from sqlalchemy import text
from dotenv import load_dotenv
import os

logger = setup_logger("load_data", "load_data.log")

load_dotenv()
neon_db_url = os.environ.get("DATABASE_URL")


def load_raw_data(extracted_data):
    try:
        mag, plasma, dst, kp, ssn, smoothed_ssn = extracted_data

        logger.info("Loading raw data...")

        load_raw_json_lists("data/raw/mag.json", mag)
        load_raw_json_lists("data/raw/plasma.json", plasma)
        load_raw_json_dicts("data/raw/dst.json", dst)
        load_raw_json_dicts("data/raw/kp.json", kp)
        load_raw_json_dicts("data/raw/ssn.json", ssn)
        load_raw_json_dicts("data/raw/smoothed_ssn.json", smoothed_ssn)

        logger.info("Loaded raw data.")

    except Exception as e:
        logger.error(f"Failed to load raw data: {str(e)}")


def load_transformed_data(transformed_data):
    try:
        solar, dst, kp, ssn = transformed_data

        engine = create_engine(neon_db_url)

        logger.info("Saving transformed data to Neon SQL database...")

        # Saving as temp tables then switching to
        # prevent errors reading whilst table updating
        # clear out any old temp indexes/tables first
        with engine.begin() as conn:
            # 1. Clean up old temp tables
            for name in ["solar", "dst", "kp", "ssn"]:
                conn.execute(text(f"DROP INDEX IF EXISTS ix_{name}_temp_time"))
                conn.execute(text(f"DROP TABLE IF EXISTS {name}_temp CASCADE"))

            # 2. Upload new data to temp tables
            solar.to_sql("solar_temp", conn, if_exists="replace", index=True)
            dst.to_sql("dst_temp", conn, if_exists="replace", index=True)
            kp.to_sql("kp_temp", conn, if_exists="replace", index=True)
            ssn.to_sql("ssn_temp", conn, if_exists="replace", index=True)

            # 3. Swap tables
            for name in ["solar", "dst", "kp", "ssn"]:
                conn.execute(text(f"DROP TABLE IF EXISTS {name} CASCADE"))
                conn.execute(text(f"ALTER TABLE {name}_temp RENAME TO {name}"))

            # 4. Metadata table for time last updated
            conn.execute(
                text("CREATE TABLE IF NOT EXISTS metadata (last_updated TIMESTAMP);")
            )
            conn.execute(text("TRUNCATE TABLE metadata;"))
            conn.execute(text("INSERT INTO metadata (last_updated) VALUES (NOW());"))

        logger.info("Neon SQL database updated Sucessfully.")

    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")
        raise

from src.utils.logging_utils import setup_logger
import json
import os
from sqlalchemy import create_engine
from sqlalchemy import text
from dotenv import load_dotenv

logger = setup_logger("load_data", "load_data.log")

load_dotenv()
neon_db_url = os.environ.get("DATABASE_URL")


def append_json_file(filepath, new_data):
    # Append only new records to existing JSON file based on time_tag
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Dst and Kp json data suddenly in new dictionary format
    # convert back to lists of lists as existing
    if isinstance(new_data[0], dict):
        headers = list(new_data[0].keys())

        new_rows = []
        for item in new_data:
            vals = list(item.values())
            vals[0] = vals[0].replace("T", " ")
            new_rows.append(vals)
    else:
        headers = new_data[0]
        new_rows = new_data[1:]

    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                existing = json.load(f)

            existing_timestamps = {row[0] for row in existing[1:]}
            new_rows = [row for row in new_rows if row[0] not in existing_timestamps]

            data_to_save = existing + new_rows
        else:
            data_to_save = [headers] + new_rows

        with open(filepath, "w") as f:
            json.dump(data_to_save, f, indent=2)

    except Exception as e:
        logger.error(f"Failed to append raw {filepath[9:-5]} data: {str(e)}")


def load_raw_data(extracted_data):
    try:
        mag, plasma, dst, kp = extracted_data

        logger.info("Appending raw data...")

        append_json_file("data/raw/mag.json", mag)
        logger.info("Appended raw mag data...")

        append_json_file("data/raw/plasma.json", plasma)
        logger.info("Appended raw plasma data...")

        append_json_file("data/raw/dst.json", dst)
        logger.info("Appended raw dst data...")

        append_json_file("data/raw/kp.json", kp)
        logger.info("Appended raw kp data...")

        logger.info("Raw data appended.")

    except Exception as e:
        logger.error(f"Failed to load raw data: {str(e)}")


def load_transformed_data(transformed_data):
    try:
        solar, dst, kp = transformed_data

        engine = create_engine(neon_db_url)

        logger.info("Saving transformed data to Neon SQL database...")

        # Saving as temp tables then switching
        # prevent errors reading whilst table updating
        # clear out any old temp indexes/tables first
        with engine.begin() as conn:
            # 1. Clean up old temp tables
            for name in ["solar", "dst", "kp"]:
                conn.execute(text(f"DROP INDEX IF EXISTS ix_{name}_temp_time"))
                conn.execute(text(f"DROP TABLE IF EXISTS {name}_temp CASCADE"))

            # 2. Upload new data to temp tables
            solar.to_sql("solar_temp", conn, if_exists="replace", index=True)
            dst.to_sql("dst_temp", conn, if_exists="replace", index=True)
            kp.to_sql("kp_temp", conn, if_exists="replace", index=True)

            # 3. Swap tables
            for name in ["solar", "dst", "kp"]:
                conn.execute(text(f"DROP TABLE IF EXISTS {name} CASCADE"))
                conn.execute(text(f"ALTER TABLE {name}_temp RENAME TO {name}"))

        logger.info("Neon SQL database updated Sucessfully.")

    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")
        raise

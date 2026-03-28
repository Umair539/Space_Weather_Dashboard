from src.utils.logging_utils import setup_logger
import json
import os
from sqlalchemy import create_engine
from sqlalchemy import text

logger = setup_logger("load_data", "load_data.log")


def append_json_file(filepath, new_data):
    """Append only new records to existing JSON file based on time_tag."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    headers = new_data[0]
    new_rows = new_data[1:]

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


def load_raw_data(extracted_data):
    try:
        mag, plasma, dst, kp = extracted_data

        logger.info("Appending raw data...")

        append_json_file("data/raw/mag.json", mag)
        append_json_file("data/raw/plasma.json", plasma)
        append_json_file("data/raw/dst.json", dst)
        append_json_file("data/raw/kp.json", kp)

        logger.info("Raw data appended.")

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

from src.utils.logging_utils import setup_logger
from src.load.load_raw_json import load_raw_json
from sqlalchemy import create_engine
from sqlalchemy import text
from dotenv import load_dotenv
import os
from datetime import timedelta

logger = setup_logger("load_data", "load_data.log")

load_dotenv()
neon_db_url = os.environ.get("DATABASE_URL")


def load_raw_data(extracted_data):
    try:
        mag, plasma, dst, kp, ssn, smoothed_ssn = extracted_data

        logger.info("Loading raw data...")

        load_raw_json("data/raw/mag/", mag)
        load_raw_json("data/raw/plasma/", plasma)
        load_raw_json("data/raw/dst/", dst)
        load_raw_json("data/raw/kp/", kp)
        load_raw_json("data/raw/ssn/", ssn)
        load_raw_json("data/raw/smoothed_ssn/", smoothed_ssn)

        logger.info("Loaded raw data.")

    except Exception as e:
        logger.error(f"Failed to load raw data: {str(e)}")


def load_transformed_data(transformed_data):
    try:
        solar, dst, kp, ssn = transformed_data

        engine = create_engine(neon_db_url)

        logger.info("Saving transformed data to Neon SQL database...")

        with engine.begin() as conn:

            # Trim old data
            conn.execute(
                text("DELETE FROM solar WHERE time < NOW() - INTERVAL '30 days'")
            )
            conn.execute(
                text("DELETE FROM dst WHERE time < NOW() - INTERVAL '30 days'")
            )
            conn.execute(text("DELETE FROM kp WHERE time < NOW() - INTERVAL '30 days'"))
            conn.execute(
                text("DELETE FROM ssn WHERE time < NOW() - INTERVAL '13 months'")
            )

            # For solar table, insert new rows and replace previous 24 hours
            lookback = solar.index[-1] - timedelta(hours=24)
            solar_upsert = solar[solar.index >= lookback]

            conn.execute(
                text(
                    """
                    INSERT INTO solar (time, density, speed, temperature, bz, bx, by, bt, pressure)
                    VALUES (:time, :density, :speed, :temperature, :bz, :bx, :by, :bt, :pressure)
                    ON CONFLICT (time) DO UPDATE SET
                        density = EXCLUDED.density,
                        speed = EXCLUDED.speed,
                        temperature = EXCLUDED.temperature,
                        bz = EXCLUDED.bz,
                        bx = EXCLUDED.bx,
                        by = EXCLUDED.by,
                        bt = EXCLUDED.bt,
                        pressure = EXCLUDED.pressure
                """
                ),
                solar_upsert.reset_index().to_dict(orient="records"),
            )

            # For dst, kp and ssn tables, only insert new rows
            for df, table in [(dst, "dst"), (kp, "kp"), (ssn, "ssn")]:
                latest_db = conn.execute(
                    text(f"SELECT MAX(time) FROM {table}")
                ).scalar()
                if latest_db is None or df.index[-1] > latest_db:
                    new_rows = df if latest_db is None else df[df.index > latest_db]
                    new_rows.reset_index().to_sql(
                        table, conn, if_exists="append", index=False
                    )

            # Metadata
            conn.execute(
                text(
                    """
                    DELETE FROM metadata;
                    INSERT INTO metadata (last_synced) VALUES (NOW());
                """
                )
            )

        logger.info("Neon SQL database updated successfully.")

    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")
        raise

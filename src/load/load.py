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
        solar, dst, kp, ssn, dst_predictions = transformed_data

        engine = create_engine(neon_db_url)

        logger.info("Saving transformed data to Neon SQL database...")

        with engine.begin() as conn:

            # Trim old data
            conn.execute(
                text("DELETE FROM solar WHERE time < NOW() - INTERVAL '31 days'")
            )
            conn.execute(
                text("DELETE FROM dst WHERE time < NOW() - INTERVAL '31 days'")
            )
            conn.execute(text("DELETE FROM kp WHERE time < NOW() - INTERVAL '31 days'"))
            conn.execute(
                text("DELETE FROM ssn WHERE time < NOW() - INTERVAL '13 years'")
            )
            conn.execute(
                text(
                    "DELETE FROM dst_predictions WHERE time < NOW() - INTERVAL '31 days'"
                )
            )

            # For solar dst, and dst_predictions table, insert new rows and replace previous 24 hours
            # This is because solar wind and dst values get updated by NOAA, and the model uses the solar wind values as input
            upsert_hours = 72
            lookback = solar.index[-1] - timedelta(hours=upsert_hours)
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

            lookback = dst.index[-1] - timedelta(hours=upsert_hours)
            dst_upsert = dst[dst.index >= lookback]

            conn.execute(
                text(
                    """
                    INSERT INTO dst (time, dst)
                    VALUES (:time, :dst)
                    ON CONFLICT (time) DO UPDATE SET
                        dst = EXCLUDED.dst
                """
                ),
                dst_upsert.reset_index().to_dict(orient="records"),
            )

            lookback = dst_predictions.index[-1] - timedelta(hours=upsert_hours)
            dst_predictions_upsert = dst_predictions[dst_predictions.index >= lookback]

            conn.execute(
                text(
                    """
                    INSERT INTO dst_predictions (time, dst_predictions)
                    VALUES (:time, :dst_predictions)
                    ON CONFLICT (time) DO UPDATE SET
                        dst_predictions = EXCLUDED.dst_predictions
                """
                ),
                dst_predictions_upsert.reset_index().to_dict(orient="records"),
            )

            lookback = kp.index[-1] - timedelta(hours=upsert_hours)
            kp_upsert = kp[kp.index >= lookback]

            conn.execute(
                text(
                    """
                    INSERT INTO kp (time, "Kp")
                    VALUES (:time, :Kp)
                    ON CONFLICT (time) DO UPDATE SET
                        "Kp" = EXCLUDED."Kp"
                """
                ),
                kp_upsert.reset_index().to_dict(orient="records"),
            )

            lookback = ssn.index[-1] - timedelta(hours=upsert_hours)
            ssn_upsert = ssn[ssn.index >= lookback]

            conn.execute(
                text(
                    """
                    INSERT INTO ssn (time, swpc_ssn)
                    VALUES (:time, :swpc_ssn)
                    ON CONFLICT (time) DO UPDATE SET
                        swpc_ssn = EXCLUDED.swpc_ssn
                """
                ),
                ssn_upsert.reset_index().to_dict(orient="records"),
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

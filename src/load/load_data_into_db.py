from sqlalchemy import create_engine
from sqlalchemy import text
from dotenv import load_dotenv
import os
from datetime import timedelta

load_dotenv()
neon_db_url = os.environ.get("DATABASE_URL")


def load_data_into_db(transformed_data):
    solar, dst, kp, ssn, dst_predictions = transformed_data

    engine = create_engine(neon_db_url)

    with engine.begin() as conn:

        # Trim old data
        conn.execute(text("DELETE FROM solar WHERE time < NOW() - INTERVAL '31 days'"))
        conn.execute(text("DELETE FROM dst WHERE time < NOW() - INTERVAL '31 days'"))
        conn.execute(text("DELETE FROM kp WHERE time < NOW() - INTERVAL '31 days'"))
        conn.execute(text("DELETE FROM ssn WHERE time < NOW() - INTERVAL '13 months'"))
        conn.execute(
            text("DELETE FROM dst_predictions WHERE time < NOW() - INTERVAL '31 days'")
        )

        # For solar, dst and dst_predictions tables, insert new rows and replace previous 24 hours
        # This is because solar wind and dst values get updated by NOAA, and the model uses the solar wind values as input
        upsert_hours = 24
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

        # For kp and ssn tables, only insert new rows
        for df, table, value_col in [(kp, "kp", "Kp"), (ssn, "ssn", "swpc_ssn")]:
            latest_db = conn.execute(text(f"SELECT MAX(time) FROM {table}")).scalar()
            if latest_db is None or df.index[-1] > latest_db:
                new_rows = df if latest_db is None else df[df.index > latest_db]
                conn.execute(
                    text(
                        f"INSERT INTO {table} (time, {value_col}) VALUES (:time, :{value_col}) ON CONFLICT (time) DO NOTHING"
                    ),
                    new_rows.reset_index().to_dict(orient="records"),
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

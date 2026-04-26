from sqlalchemy import create_engine
from sqlalchemy import text
import os
from datetime import timedelta


def load_data_into_db(transformed_data, upsert_hours=24 * 7):
    solar, dst, kp, ssn, dst_predictions = transformed_data

    neon_db_url = os.environ.get("DATABASE_URL")
    engine = create_engine(neon_db_url, connect_args={"prepare_threshold": None})

    with engine.begin() as conn:

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

        # Trim old data relative to the last timestamp in each table
        conn.execute(
            text(
                "DELETE FROM solar WHERE time < (SELECT MAX(time) FROM solar) - INTERVAL '31 days'"
            )
        )
        conn.execute(
            text(
                "DELETE FROM dst WHERE time < (SELECT MAX(time) FROM dst) - INTERVAL '31 days'"
            )
        )
        conn.execute(
            text(
                "DELETE FROM kp WHERE time < (SELECT MAX(time) FROM kp) - INTERVAL '31 days'"
            )
        )
        conn.execute(
            text(
                "DELETE FROM ssn WHERE time < (SELECT MAX(time) FROM ssn) - INTERVAL '13 years'"
            )
        )
        conn.execute(
            text(
                "DELETE FROM dst_predictions WHERE time < (SELECT MAX(time) FROM dst_predictions) - INTERVAL '31 days'"
            )
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

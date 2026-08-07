from sqlalchemy import create_engine
from sqlalchemy import text
import os
from datetime import timedelta

# table -> (columns [(bind_name, sql_column), ...], retention interval)
# sql_column differs from bind_name only for "Kp", which needs quoting for
# its mixed case.
_SPEC = {
    "solar": (
        [(c, c) for c in ["density", "speed", "temperature", "bz", "bx", "by", "bt", "pressure"]],
        "1 year",
    ),
    "dst": ([("dst", "dst")], "1 year"),
    "dst_predictions": ([("dst_predictions", "dst_predictions")], "1 year"),
    "kp": ([("Kp", '"Kp"')], "1 year"),
    "ssn": ([("swpc_ssn", "swpc_ssn")], "12 years"),
}

# Used only when upsert_hours isn't explicitly passed in - solar's source
# only provides a 24h window normally, the rest need a week to catch
# corrections. An explicit upsert_hours (e.g. a full backfill/migration)
# overrides this for every table, including solar.
_DEFAULT_LOOKBACK_HOURS = {
    "solar": 24,
    "dst": 24 * 7,
    "dst_predictions": 24 * 7,
    "kp": 24 * 7,
    "ssn": 24 * 7,
}


def load_data_into_db(transformed_data, upsert_hours=None):
    solar, dst, kp, ssn, dst_predictions = transformed_data
    dataframes = {"solar": solar, "dst": dst, "kp": kp, "ssn": ssn, "dst_predictions": dst_predictions}

    db_url = os.environ.get("DATABASE_URL")
    engine = create_engine(db_url, connect_args={"prepare_threshold": None})

    with engine.begin() as conn:
        for table, (columns, _) in _SPEC.items():
            df = dataframes[table]
            hours = upsert_hours if upsert_hours is not None else _DEFAULT_LOOKBACK_HOURS[table]
            lookback = df.index[-1] - timedelta(hours=hours)
            upsert_df = df[df.index >= lookback]

            columns_sql = ", ".join(sql_col for _, sql_col in columns)
            values_sql = ", ".join(f":{bind}" for bind, _ in columns)
            set_sql = ", ".join(f"{sql_col} = EXCLUDED.{sql_col}" for _, sql_col in columns)
            # Only touch updated_at (and actually write the row) when the
            # data genuinely changed - an unconditional update would make
            # updated_at meaningless for cache-invalidation purposes, since
            # it'd bump on every upsert regardless of real change.
            diff_sql = " OR ".join(
                f"{table}.{sql_col} IS DISTINCT FROM EXCLUDED.{sql_col}" for _, sql_col in columns
            )

            conn.execute(
                text(f"""
                    INSERT INTO {table} (time, {columns_sql}, updated_at)
                    VALUES (:time, {values_sql}, NOW())
                    ON CONFLICT (time) DO UPDATE SET
                        {set_sql},
                        updated_at = NOW()
                    WHERE {diff_sql}
                """),
                upsert_df.reset_index().to_dict(orient="records"),
            )

        # Trim old data relative to the last timestamp in each table, plus the
        # metadata refresh, all sent as one multi-statement round trip. None
        # of these take bind parameters, so psycopg can send them together
        # via the simple query protocol instead of one round trip each.
        trims = "\n".join(
            f"DELETE FROM {table} WHERE time < (SELECT MAX(time) FROM {table}) - INTERVAL '{retention}';"
            for table, (_, retention) in _SPEC.items()
        )
        conn.execute(
            text(f"""
                {trims}
                DELETE FROM metadata;
                INSERT INTO metadata (last_synced) VALUES (NOW());
            """)
        )

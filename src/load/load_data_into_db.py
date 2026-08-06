from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy import MetaData, Table, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
import os
from datetime import timedelta

# Reflected once per warm container and reused across invocations, so repeated
# Lambda calls don't re-query information_schema for table structure every run.
_metadata = MetaData()


def _get_table(engine, name):
    table = _metadata.tables.get(name)
    if table is None:
        table = Table(name, _metadata, autoload_with=engine)
    return table


def _diff_upsert(conn, table, index_col, df):
    """Batched upsert that only writes rows that are new or actually changed.

    Uses SQLAlchemy's insertmanyvalues to batch the INSERT into a handful of
    multi-row statements, and ON CONFLICT ... WHERE ... IS DISTINCT FROM to
    make Postgres skip the write entirely for unchanged rows.
    """
    records = df.reset_index().to_dict(orient="records")
    if not records:
        return

    update_cols = [c.name for c in table.columns if c.name != index_col]

    # No .values() here - passing records as execute() params (not baked into
    # the statement) is what lets SQLAlchemy's insertmanyvalues page the batch
    # itself, instead of compiling every row into one giant multi-VALUES
    # statement that can blow past Postgres's 65535 bind-parameter limit.
    stmt = pg_insert(table)
    stmt = stmt.on_conflict_do_update(
        index_elements=[index_col],
        set_={col: stmt.excluded[col] for col in update_cols},
        where=or_(*[table.c[col].is_distinct_from(stmt.excluded[col]) for col in update_cols]),
    )
    conn.execute(stmt, records)


def load_data_into_db(transformed_data, upsert_hours=24 * 7):
    solar, dst, kp, ssn, dst_predictions = transformed_data

    db_url = os.environ.get("DATABASE_URL")
    engine = create_engine(db_url, connect_args={"prepare_threshold": None})

    with engine.begin() as conn:
        solar_table = _get_table(engine, "solar")
        dst_table = _get_table(engine, "dst")
        dst_predictions_table = _get_table(engine, "dst_predictions")
        kp_table = _get_table(engine, "kp")
        ssn_table = _get_table(engine, "ssn")

        lookback = solar.index[-1] - timedelta(hours=upsert_hours)
        solar_upsert = solar[solar.index >= lookback]
        _diff_upsert(conn, solar_table, "time", solar_upsert)

        lookback = dst.index[-1] - timedelta(hours=upsert_hours)
        dst_upsert = dst[dst.index >= lookback]
        _diff_upsert(conn, dst_table, "time", dst_upsert)

        lookback = dst_predictions.index[-1] - timedelta(hours=upsert_hours)
        dst_predictions_upsert = dst_predictions[dst_predictions.index >= lookback]
        _diff_upsert(conn, dst_predictions_table, "time", dst_predictions_upsert)

        lookback = kp.index[-1] - timedelta(hours=upsert_hours)
        kp_upsert = kp[kp.index >= lookback]
        _diff_upsert(conn, kp_table, "time", kp_upsert)

        lookback = ssn.index[-1] - timedelta(hours=upsert_hours)
        ssn_upsert = ssn[ssn.index >= lookback]
        _diff_upsert(conn, ssn_table, "time", ssn_upsert)

        # Trim old data relative to the last timestamp in each table
        conn.execute(
            text(
                "DELETE FROM solar WHERE time < (SELECT MAX(time) FROM solar) - INTERVAL '1 year'"
            )
        )
        conn.execute(
            text(
                "DELETE FROM dst WHERE time < (SELECT MAX(time) FROM dst) - INTERVAL '1 year'"
            )
        )
        conn.execute(
            text(
                "DELETE FROM kp WHERE time < (SELECT MAX(time) FROM kp) - INTERVAL '1 year'"
            )
        )
        conn.execute(
            text(
                "DELETE FROM ssn WHERE time < (SELECT MAX(time) FROM ssn) - INTERVAL '12 years'"
            )
        )
        conn.execute(
            text(
                "DELETE FROM dst_predictions WHERE time < (SELECT MAX(time) FROM dst_predictions) - INTERVAL '1 year'"
            )
        )

        # Metadata
        conn.execute(text("""
                DELETE FROM metadata;
                INSERT INTO metadata (last_synced) VALUES (NOW());
            """))

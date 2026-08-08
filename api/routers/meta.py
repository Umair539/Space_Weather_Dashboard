from fastapi import APIRouter

from api.db import TABLE_COLUMNS
from api.store import store

router = APIRouter(tags=["meta"])


@router.get("/health")
def health():
    """Per-table row counts and true last-changed timestamps. last_updated_at
    only moves when data genuinely changed (the ETL's upsert bumps
    updated_at only on IS DISTINCT FROM), so it's an honest freshness
    signal, unlike metadata.last_synced which is rewritten every run."""
    tables = {
        name: {
            "rows": len(store.table(name).snapshot()),
            "last_updated_at": store.table(name).last_updated_at,
        }
        for name in TABLE_COLUMNS
    }
    warm = all(t["last_updated_at"] is not None for t in tables.values())
    return {"status": "ok" if warm else "warming_up", "tables": tables}

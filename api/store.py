import threading
from datetime import timedelta


class TableCache:
    """One table's rows, held as an immutable time-sorted tuple of dicts,
    each row including its "time".

    Writers build a new tuple and swap it in under the lock; readers take
    the reference and use it lock-free, since nothing is ever mutated in
    place. That keeps reads O(1) with no copying.
    """

    def __init__(self, name: str):
        self.name = name
        self.records: tuple[dict, ...] = ()
        self.last_updated_at = None
        self.lock = threading.Lock()

    def snapshot(self) -> tuple[dict, ...]:
        with self.lock:
            return self.records

    def merge_delta(self, delta: list[dict], new_max_updated_at, retention_days=None) -> set:
        """Upsert delta rows (each with "time") and trim to retention.

        Returns the set of times that changed and are still cached - the
        aggregates use it to recompute only the affected buckets rather
        than the whole series.
        """
        with self.lock:
            if not delta:
                self.last_updated_at = new_max_updated_at
                return set()

            # dict keyed by time gives upsert semantics for free: existing
            # timestamps are overwritten, new ones added.
            merged = {row["time"]: row for row in self.records}
            merged.update({row["time"]: row for row in delta})

            if retention_days is not None:
                cutoff = max(merged) - timedelta(days=retention_days)
                merged = {t: row for t, row in merged.items() if t >= cutoff}

            self.records = tuple(merged[t] for t in sorted(merged))
            self.last_updated_at = new_max_updated_at
            return {row["time"] for row in delta} & merged.keys()


class Store:
    """Published, immutable views. Raw tables plus the derived series the
    endpoints serve. Only the poller writes; every write swaps in a new
    tuple rather than mutating."""

    def __init__(self):
        self.solar = TableCache("solar")
        self.dst = TableCache("dst")
        self.dst_predictions = TableCache("dst_predictions")
        self.kp = TableCache("kp")
        self.ssn = TableCache("ssn")

        self._derived: dict[str, tuple[dict, ...]] = {
            "solar_hourly": (),
            "dst_merged": (),
        }
        self._derived_lock = threading.Lock()

    def table(self, name: str) -> TableCache:
        return getattr(self, name)

    def get_derived(self, name: str) -> tuple[dict, ...]:
        with self._derived_lock:
            return self._derived[name]

    def set_derived(self, name: str, records: tuple[dict, ...]) -> None:
        with self._derived_lock:
            self._derived[name] = records


# Module-level singleton - written by poller.py, read by the routers.
store = Store()

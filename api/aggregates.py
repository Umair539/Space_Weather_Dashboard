"""Pure functions over plain lists/dicts of rows - no DB, no shared state,
no pandas. Each row is a dict with a "time" key plus its value columns.

Aggregates are recomputed per affected bucket rather than over the whole
series: a poll delta usually touches one or two buckets, so there's no
reason to rebuild hundreds.
"""

import calendar
from bisect import bisect_left
from datetime import datetime, timedelta

_FIXED_INTERVALS = {"24h": timedelta(hours=24), "7d": timedelta(days=7)}
_MONTH_INTERVALS = {"1mo": 1, "1y": 12}


def months_back(when: datetime, months: int) -> datetime:
    """Calendar-aware, matching Postgres INTERVAL '1 month' / '1 year'
    rather than approximating as 30/365 days. Clamps the day when the
    target month is shorter (31 Mar -> 28 Feb)."""
    shifted = when.month - 1 - months
    year = when.year + shifted // 12
    month = shifted % 12 + 1
    day = min(when.day, calendar.monthrange(year, month)[1])
    return when.replace(year=year, month=month, day=day)


def hour_of(when: datetime) -> datetime:
    return when.replace(minute=0, second=0, microsecond=0)


def month_of(when: datetime) -> datetime:
    return when.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def find(records: tuple[dict, ...], when: datetime) -> dict | None:
    """Binary search by time. Used instead of building a {time: row} index,
    which for the solar table would mean an extra ~44k-entry dict."""
    i = bisect_left(records, when, key=lambda row: row["time"])
    if i < len(records) and records[i]["time"] == when:
        return records[i]
    return None


def slice_interval(records: tuple[dict, ...], interval: str) -> tuple[dict, ...]:
    """Window anchored on the newest row, matching the frontend's existing
    WHERE time >= (SELECT MAX(time) FROM ...) - INTERVAL pattern (not "now",
    so a stalled pipeline still returns a full window)."""
    if not records:
        return records
    newest = records[-1]["time"]
    if interval in _FIXED_INTERVALS:
        cutoff = newest - _FIXED_INTERVALS[interval]
    else:
        cutoff = months_back(newest, _MONTH_INTERVALS[interval])
    return records[bisect_left(records, cutoff, key=lambda row: row["time"]):]


def select_columns(records: tuple[dict, ...], columns: list[str]) -> tuple[dict, ...]:
    return tuple({"time": row["time"], **{c: row[c] for c in columns}} for row in records)


def recompute_hours(records, buckets, hours, columns) -> None:
    """Hourly means for the given hours only, in place on `buckets`.

    A bucket is kept only when all 60 minutes are present, matching the
    HAVING COUNT(*) = 60 in app/views/solar_wind.py - so an in-progress
    hour simply isn't published until it completes.
    """
    for hour in hours:
        minutes = [find(records, hour + timedelta(minutes=m)) for m in range(60)]
        if any(row is None for row in minutes):
            buckets.pop(hour, None)
            continue
        buckets[hour] = {
            "time": hour,
            **{c: round(sum(row[c] for row in minutes) / 60, 2) for c in columns},
        }


def recompute_months(records, buckets, months) -> None:
    """Monthly means for the given months only, in place on `buckets`.

    Only the current/latest month requires full completeness - averaging a
    handful of its early days would swing wildly as more arrive (the same
    problem the SSN backfill investigation started from). Past months are
    averaged over whatever days are actually present: their gaps are
    permanent (NOAA never published some solar-minimum days, and the
    confirmed-zero backfill only fills what LISIRD could verify as
    spotless), so gating them forever would hide real data for no benefit -
    unlike the current month, they will never "complete".
    """
    if not records:
        return
    latest_month = month_of(records[-1]["time"])

    for month in months:
        days_in_month = calendar.monthrange(month.year, month.month)[1]
        days = [find(records, month.replace(day=d)) for d in range(1, days_in_month + 1)]
        present = [row for row in days if row is not None]

        if not present or (month == latest_month and len(present) < days_in_month):
            buckets.pop(month, None)
            continue

        total = sum(row["swpc_ssn"] for row in present)
        buckets[month] = {"time": month, "swpc_ssn": round(total / len(present), 2)}


def prune_buckets(buckets: dict, oldest: datetime) -> None:
    """Drop buckets whose source rows have aged out of the retention window."""
    for key in [k for k in buckets if k < oldest]:
        del buckets[key]


def merge_dst(prediction_records, dst_records) -> tuple[dict, ...]:
    """LEFT JOIN with predictions driving, matching app/views/home.py.

    "dst" is None where there's no matching observation - the expected case
    for the newest row(s), since predictions are computed for
    sequence-end + 1 hour (src/transform/model_inference.py) and so run
    ahead of observed dst. Left as None rather than filled: filling would
    fabricate an observation that never happened.

    Sorted on the way out. Callers currently pass TableCache snapshots,
    which are already sorted, but the result feeds slice_interval's binary
    search - and bisect over unsorted rows returns a silently wrong window
    rather than failing, so the guarantee is worth the microseconds.
    """
    merged = []
    for prediction in prediction_records:
        observed = find(dst_records, prediction["time"])
        merged.append(
            {
                "time": prediction["time"],
                "dst_predictions": prediction["dst_predictions"],
                "dst": observed["dst"] if observed else None,
            }
        )
    return tuple(sorted(merged, key=lambda row: row["time"]))

from src.extract.fetch_rtsw import fetch_rtsw_json

# Not wired into extract.py's LIVE_FETCHERS: this changes on a monthly/yearly
# cadence at most and the existing stored forecast already runs into the
# 2030s, so a live refresh isn't needed for now.
SMOOTHED_SSN_S3_KEY = "json/solar-cycle/sunspots-smoothed.json"


def fetch_smoothed_ssn():
    return [
        {"time-tag": row["time-tag"], "predicted_ssn": row["smoothed_ssn"]}
        for row in fetch_rtsw_json(SMOOTHED_SSN_S3_KEY)
    ]

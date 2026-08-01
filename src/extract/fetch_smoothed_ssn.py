from src.extract.fetch_rtsw import fetch_rtsw_json
from src.utils.fetch_utils import get_response, fetch_with_fallback

NOAA_SMOOTHED_SSN_URL = (
    "https://services.swpc.noaa.gov/json/solar-cycle/predicted-solar-cycle.json"
)
# Not json/solar-cycle/sunspots-smoothed.json - that key is the *historical*
# smoothed series back to 1749, which carries a -1.0 sentinel for any recent
# month it can't smooth yet (smoothing needs future data on both sides), so
# it reads as no forecast at all for exactly the months this dataset needs.
# solar-cycle-25-predicted.json is the actual forward-looking forecast mirror,
# using time_tag/smoothed_ssn field names instead of NOAA's time-tag/predicted_ssn.
SMOOTHED_SSN_S3_KEY = "json/solar-cycle/solar-cycle-25-predicted.json"


def _fetch_smoothed_ssn_noaa():
    return get_response(NOAA_SMOOTHED_SSN_URL).json()


def _fetch_smoothed_ssn_s3():
    return [
        {"time-tag": row["time_tag"], "predicted_ssn": row["smoothed_ssn"]}
        for row in fetch_rtsw_json(SMOOTHED_SSN_S3_KEY)
    ]


def fetch_smoothed_ssn():
    return fetch_with_fallback(
        "smoothed_ssn", _fetch_smoothed_ssn_noaa, _fetch_smoothed_ssn_s3
    )

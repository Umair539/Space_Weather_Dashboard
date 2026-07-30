from datetime import datetime, timedelta, timezone

from src.utils.fetch_utils import get_response

# LISIRD mirrors SILSO's official daily international sunspot number.
# SILSO finalizes daily values on roughly a month's delay, so the window
# needs to reach well past "today" to pick up newly finalized days.
LISIRD_SSN_URL = "https://lasp.colorado.edu/lisird/latis/dap/international_sunspot_number.json"
LOOKBACK_DAYS = 60


def fetch_ssn():
    start = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    url = f"{LISIRD_SSN_URL}?time%3E={start.strftime('%Y-%m-%d')}"
    response = get_response(url)
    samples = response.json()["international_sunspot_number"]["samples"]
    return [
        {
            "Obsdate": sample["time"].replace(" ", "-") + "T00:00:00",
            "swpc_ssn": sample["ssn"],
        }
        for sample in samples
    ]

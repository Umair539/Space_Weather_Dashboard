from datetime import datetime, timedelta, timezone

from src.utils.fetch_utils import get_response

GFZ_KP_URL = "https://kp.gfz.de/app/json/"
LOOKBACK_DAYS = 7


def fetch_kp():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=LOOKBACK_DAYS)
    params = {
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "index": "Kp",
    }
    response = get_response(GFZ_KP_URL, params=params)
    payload = response.json()
    return [
        {"time_tag": time_tag.rstrip("Z"), "Kp": kp}
        for time_tag, kp in zip(payload["datetime"], payload["Kp"])
    ]

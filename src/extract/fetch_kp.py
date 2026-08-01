from datetime import datetime, timedelta, timezone

from src.utils.fetch_utils import get_response, fetch_with_fallback

NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
GFZ_KP_URL = "https://kp.gfz.de/app/json/"
LOOKBACK_DAYS = 7


def _fetch_kp_noaa():
    return get_response(NOAA_KP_URL).json()


def _fetch_kp_gfz():
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


def fetch_kp():
    return fetch_with_fallback("kp", _fetch_kp_noaa, _fetch_kp_gfz)

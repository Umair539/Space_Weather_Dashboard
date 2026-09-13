from src.utils.fetch_utils import get_response

# Same nowcast NOAA endpoint api/aurora.py polls live - fetched here as well
# so the ETL can archive a periodic snapshot to object storage.
OVATION_URL = "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"


def fetch_ovation():
    """Raw OVATION payload: {"Observation Time", "Forecast Time", "coordinates"},
    coordinates being [lon, lat, probability] triples on NOAA's 0-360 grid.

    No fallback source exists for this product, so unlike the other
    fetch_*.py modules there's no fetch_with_fallback - just the shared
    retrying session. The payload is a dict rather than a list of
    rows/records, so it also can't go through validate_schema; the shape
    check happens in load_ovation.py against the stored coordinate grid.
    """
    data = get_response(OVATION_URL).json()
    if not data.get("coordinates"):
        raise ValueError("ovation: empty or missing coordinates in response")
    return data

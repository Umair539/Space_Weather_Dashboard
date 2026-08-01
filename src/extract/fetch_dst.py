from datetime import datetime, timezone

from src.utils.fetch_utils import get_response, fetch_with_fallback

NOAA_DST_URL = "https://services.swpc.noaa.gov/products/kyoto-dst.json"
DST_URL_TEMPLATE = (
    "https://wdc.kugi.kyoto-u.ac.jp/dst_realtime/presentmonth/dst{yy:02d}{mm:02d}.for.request"
)

# Each data line is a 16-char header followed by 26 fixed-width 4-char fields:
# field 0 is a base-value placeholder, fields 1-24 are hourly Dst (UT hour 0-23),
# field 25 is a daily-mean summary. Missing hours are filled with the sentinel "9999".
HEADER_LEN = 16
FIELD_WIDTH = 4
FIELD_COUNT = 26
MISSING = "9999"


def _fetch_dst_noaa():
    return get_response(NOAA_DST_URL).json()


def _fetch_dst_kyoto():
    now = datetime.now(timezone.utc)
    url = DST_URL_TEMPLATE.format(yy=now.year % 100, mm=now.month)
    response = get_response(url)
    return _parse_dst(response.text)


def fetch_dst():
    return fetch_with_fallback("dst", _fetch_dst_noaa, _fetch_dst_kyoto)


def _parse_dst(text):
    records = []
    for line in text.splitlines():
        if not line.startswith("DST") or len(line) < HEADER_LEN + FIELD_COUNT * FIELD_WIDTH:
            continue

        year = 2000 + int(line[3:5])
        month = int(line[5:7])
        day = int(line[8:10])

        fields = [
            line[HEADER_LEN + i * FIELD_WIDTH : HEADER_LEN + (i + 1) * FIELD_WIDTH]
            for i in range(FIELD_COUNT)
        ]
        hourly_values = fields[1:25]

        for hour, raw in enumerate(hourly_values):
            value = raw.strip()
            if value == MISSING or value == "":
                continue
            records.append(
                {
                    "time_tag": f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:00:00",
                    "dst": float(value),
                }
            )
    return records

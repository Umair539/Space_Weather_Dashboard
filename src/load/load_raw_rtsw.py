from src.utils.r2 import R2Client

PLASMA_KEEP_COLS = {
    "time_tag",
    "active",
    "source",
    "proton_speed",
    "proton_temperature",
    "proton_density",
}

MAG_KEEP_COLS = {
    "time_tag",
    "active",
    "source",
    "bt",
    "bx_gsm",
    "by_gsm",
    "bz_gsm",
}


def load_raw_rtsw(folder_path, data):

    if data is None:
        return

    r2 = R2Client()
    key = f"{folder_path}/dicts.json"

    keep_cols = MAG_KEEP_COLS if folder_path == "mag" else PLASMA_KEEP_COLS

    existing = r2.download_json(key)
    existing_filtered = (
        [{k: v for k, v in row.items() if k in keep_cols} for row in existing]
        if existing
        else []
    )

    filtered_data = [{k: v for k, v in row.items() if k in keep_cols} for row in data]

    existing_dict = (
        {(row["time_tag"], row["source"]): row for row in existing_filtered}
        if existing_filtered
        else {}
    )

    existing_dict.update(
        {(row["time_tag"], row["source"]): row for row in filtered_data}
    )

    updated_data = list(existing_dict.values())
    r2.upload_json(key, updated_data)

    return updated_data

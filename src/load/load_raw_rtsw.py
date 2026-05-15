from src.utils.storage import get_storage_client

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

    storage = get_storage_client()
    keep_cols = MAG_KEEP_COLS if folder_path == "mag" else PLASMA_KEEP_COLS

    filtered_data = [{k: v for k, v in row.items() if k in keep_cols} for row in data]

    # Group incoming records by month
    by_month = {}
    for record in filtered_data:
        month = str(record["time_tag"])[:7]  # "YYYY-MM"
        if month not in by_month:
            by_month[month] = {}
        by_month[month][(record["time_tag"], record["source"])] = record

    # Merge each month's records into its partition
    for month, new_records in by_month.items():
        partition_key = f"{folder_path}/dicts/{month}.json"

        existing = storage.download_json(partition_key)
        existing_dict = (
            {(r["time_tag"], r["source"]): r for r in existing} if existing else {}
        )

        existing_dict.update(new_records)

        partition_data = sorted(
            existing_dict.values(), key=lambda r: (r["time_tag"], r["source"])
        )
        storage.upload_json(partition_key, partition_data)

    # Write metadata with max timestamp from incoming data
    max_timestamp = max(str(r["time_tag"]) for r in filtered_data)
    storage.upload_json(f"{folder_path}/metadata.json", {"last_updated": max_timestamp})

    return filtered_data

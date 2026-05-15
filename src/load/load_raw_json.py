from src.utils.parser import detect_format
from src.utils.storage import get_storage_client

PARTITIONED_FOLDERS = {"dst", "kp"}


def load_raw_json(folder_path, data):

    if data is None:
        return

    fmt = detect_format(data)
    storage = get_storage_client()

    if fmt == "list_of_lists":
        key = f"{folder_path}/lists.json"
        return load_raw_json_lists(storage, key, data)

    elif fmt == "list_of_dicts":
        if folder_path in PARTITIONED_FOLDERS:
            return load_raw_json_dicts(storage, folder_path, data)
        else:
            return load_raw_json_dicts_single(storage, folder_path, data)

    else:
        raise ValueError(f"Unsupported format: {fmt}")


def load_raw_json_lists(storage, key, new_data):
    headers = new_data[0]
    new_rows = new_data[1:]

    existing = storage.download_json(key)
    existing_dict = {row[0]: row for row in existing[1:]} if existing else {}

    existing_dict.update({row[0]: row for row in new_rows})

    updated_data = [headers] + list(existing_dict.values())
    storage.upload_json(key, updated_data)
    return updated_data


def load_raw_json_dicts(storage, folder_path, new_data):
    time_key = next(iter(new_data[0]))

    # Group incoming records by month
    by_month = {}
    for record in new_data:
        month = str(record[time_key])[:7]  # "YYYY-MM"
        if month not in by_month:
            by_month[month] = {}
        by_month[month][record[time_key]] = record

    # Merge each month's records into its partition
    for month, new_records in by_month.items():
        partition_key = f"{folder_path}/dicts/{month}.json"

        existing = storage.download_json(partition_key)
        existing_dict = {r[time_key]: r for r in existing} if existing else {}

        existing_dict.update(new_records)

        partition_data = sorted(existing_dict.values(), key=lambda r: r[time_key])
        storage.upload_json(partition_key, partition_data)

    # Update metadata
    existing_metadata = storage.download_json(f"{folder_path}/metadata.json") or {}
    existing_partitions = set(existing_metadata.get("partitions", []))
    existing_partitions.update(by_month.keys())

    storage.upload_json(
        f"{folder_path}/metadata.json",
        {
            "partitions": sorted(existing_partitions),
        },
    )

    return new_data


def load_raw_json_dicts_single(storage, folder_path, new_data):
    time_key = next(iter(new_data[0]))
    key = f"{folder_path}/dicts.json"

    existing = storage.download_json(key)
    existing_dict = {r[time_key]: r for r in existing} if existing else {}

    existing_dict.update({r[time_key]: r for r in new_data})

    updated_data = list(existing_dict.values())
    storage.upload_json(key, updated_data)
    return updated_data

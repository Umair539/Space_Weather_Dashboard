import os
import json
from src.utils.parser import detect_format


def load_raw_json(folder_path, data):
    fmt = detect_format(data)

    os.makedirs(folder_path, exist_ok=True)

    if fmt == "list_of_lists":
        filepath = os.path.join(folder_path, "lists.json")
        load_raw_json_lists(filepath, data)

    elif fmt == "list_of_dicts":
        filepath = os.path.join(folder_path, "dicts.json")
        load_raw_json_dicts(filepath, data)

    else:
        raise ValueError(f"Unsupported format: {fmt}")


def load_raw_json_lists(filepath, new_data):
    # Append only new records to existing JSON file based on time_tag
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    headers = new_data[0]
    new_rows = new_data[1:]

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            existing = json.load(f)

        existing_timestamps = {row[0] for row in existing[1:]}
        new_rows = [row for row in new_rows if row[0] not in existing_timestamps]

        data_to_save = existing + new_rows
    else:
        data_to_save = [headers] + new_rows

    with open(filepath, "w") as f:
        json.dump(data_to_save, f, indent=2)


def load_raw_json_dicts(filepath, new_data):
    # Append only new records to existing JSON file based on time_tag
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    id_key = next(iter(new_data[0]))

    existing_timestamps = {row[id_key] for row in existing_data}
    new_records = [row for row in new_data if row[id_key] not in existing_timestamps]

    updated_data = existing_data + new_records

    with open(filepath, "w") as f:
        json.dump(updated_data, f, indent=2)

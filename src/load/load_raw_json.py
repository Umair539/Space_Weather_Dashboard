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


# Instead of appending new data,
# replace saved data with newly fetched for any overlapping data
# this is to replace any data that has been updated by NOAA


def load_raw_json_lists(filepath, new_data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    headers = new_data[0]
    new_rows = new_data[1:]

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            existing = json.load(f)
        existing_dict = {row[0]: row for row in existing[1:]}
    else:
        existing_dict = {}

    existing_dict.update({row[0]: row for row in new_rows})

    data_to_save = [headers] + list(existing_dict.values())

    with open(filepath, "w") as f:
        json.dump(data_to_save, f, indent=2)


def load_raw_json_dicts(filepath, new_data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    id_key = next(iter(new_data[0]))

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            existing_data = json.load(f)
        existing_dict = {row[id_key]: row for row in existing_data}
    else:
        existing_dict = {}

    existing_dict.update({row[id_key]: row for row in new_data})

    data_to_save = list(existing_dict.values())

    with open(filepath, "w") as f:
        json.dump(data_to_save, f, indent=2)

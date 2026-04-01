import os
import json


def load_raw_indices(filepath, new_data):
    # Append only new records to existing JSON file (list of dicts) based on time_tag.
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    if not new_data:
        return existing_data

    id_key = next(iter(new_data[0]))

    existing_timestamps = {row[id_key] for row in existing_data}
    new_records = [row for row in new_data if row[id_key] not in existing_timestamps]

    updated_data = existing_data + new_records

    with open(filepath, "w") as f:
        json.dump(updated_data, f, indent=2)

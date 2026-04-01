import os
import json


def load_raw_solar(filepath, new_data):
    """Append only new records to existing JSON file based on time_tag."""
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

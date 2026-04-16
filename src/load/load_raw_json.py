from src.utils.parser import detect_format
from src.utils.r2 import R2Client


def load_raw_json(folder_path, data):

    if data is None:
        return

    fmt = detect_format(data)
    r2 = R2Client()

    if fmt == "list_of_lists":
        key = f"{folder_path}/lists.json"
        load_raw_json_lists(r2, key, data)

    elif fmt == "list_of_dicts":
        key = f"{folder_path}/dicts.json"
        load_raw_json_dicts(r2, key, data)

    else:
        raise ValueError(f"Unsupported format: {fmt}")


# Instead of appending new data,
# replace saved data with newly fetched for any overlapping data
# this is to replace any data that has been updated by NOAA


def load_raw_json_lists(r2, key, new_data):
    headers = new_data[0]
    new_rows = new_data[1:]

    existing = r2.download_json(key)
    existing_dict = {row[0]: row for row in existing[1:]} if existing else {}

    existing_dict.update({row[0]: row for row in new_rows})

    r2.upload_json(key, [headers] + list(existing_dict.values()))


def load_raw_json_dicts(r2, key, new_data):
    id_key = next(iter(new_data[0]))

    existing = r2.download_json(key)
    existing_dict = {row[id_key]: row for row in existing} if existing else {}

    existing_dict.update({row[id_key]: row for row in new_data})

    r2.upload_json(key, list(existing_dict.values()))

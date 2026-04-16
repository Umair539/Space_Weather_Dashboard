from src.utils.r2 import R2Client


def load_raw_rtsw(folder_path, data):

    if data is None:
        return

    r2 = R2Client()
    key = f"{folder_path}/dicts.json"

    existing = r2.download_json(key)
    existing_dict = (
        {(row["time_tag"], row["source"]): row for row in existing} if existing else {}
    )

    existing_dict.update({(row["time_tag"], row["source"]): row for row in data})

    r2.upload_json(key, list(existing_dict.values()))

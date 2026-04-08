def parse_data(data):
    fmt = detect_format(data)

    if fmt == "list_of_lists":
        return parse_list_of_lists(data)
    elif fmt == "list_of_dicts":
        return parse_list_of_dicts(data)


def detect_format(data):
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], list):
            return "list_of_lists"
        elif isinstance(data[0], dict):
            return "list_of_dicts"
    raise ValueError("Unknown format")


def parse_list_of_lists(data):
    headers = data[0]
    rows = data[1:]
    return [dict(zip(headers, row)) for row in rows]


def parse_list_of_dicts(data):
    return data

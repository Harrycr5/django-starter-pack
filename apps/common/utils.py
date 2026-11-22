DATE_INPUT_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d")


def normalize_uppercase(value):
    return value.strip().upper() if isinstance(value, str) else value

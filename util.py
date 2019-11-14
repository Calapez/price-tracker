def parse_int_or_null(val):
    try:
        return int(val)
    except TypeError:
        return None

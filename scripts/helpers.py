def chunk_dict(d: dict, size: int) -> list[dict]:
    """Break a dict into a list of dicts of length `size`."""
    items = list(d.items())
    return [dict(items[i:i+size]) for i in range(0, len(items), size)]

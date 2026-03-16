"""API request/response schemas."""


def to_camel(name: str) -> str:
    """Convert a snake_case name to camelCase (shared alias generator)."""
    parts = name.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])

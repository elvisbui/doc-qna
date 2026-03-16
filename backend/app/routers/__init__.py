"""Shared router utilities."""

ERROR_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "error": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "message": {"type": "string"},
                "detail": {},
            },
        }
    },
}

ERROR_RESPONSE_BODY: dict = {
    "content": {
        "application/json": {
            "schema": ERROR_RESPONSE_SCHEMA,
        }
    }
}

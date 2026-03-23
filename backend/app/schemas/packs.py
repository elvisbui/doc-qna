"""API request/response schemas for knowledge pack endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas import to_camel


class PackDetail(BaseModel):
    """Summary of a single knowledge pack."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    name: str
    version: str
    description: str
    doc_count: int
    installed: bool
    installed_version: str | None = None
    suggested_queries: list[str] = []


class PackListResponse(BaseModel):
    """Response for GET /api/packs."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    packs: list[PackDetail]

"""API request/response schemas for plugin endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas import to_camel


class PluginDetail(BaseModel):
    """Summary of a single plugin."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    name: str
    description: str
    version: str
    enabled: bool
    hooks: list[str]
    config_schema: list[dict[str, Any]] = []


class PluginListResponse(BaseModel):
    """Response for GET /api/plugins."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    plugins: list[PluginDetail]


class PluginToggleRequest(BaseModel):
    """Body for POST /api/plugins/{plugin_name}/toggle."""

    enabled: bool


class PluginToggleResponse(BaseModel):
    """Response for POST /api/plugins/{plugin_name}/toggle."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    name: str
    enabled: bool


class PluginConfigResponse(BaseModel):
    """Response for GET /api/plugins/{plugin_name}/config."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    name: str
    config: dict[str, Any]
    config_schema: list[dict[str, Any]]


class PluginConfigUpdateRequest(BaseModel):
    """Body for PUT /api/plugins/{plugin_name}/config."""

    config: dict[str, Any]


class PluginConfigUpdateResponse(BaseModel):
    """Response for PUT /api/plugins/{plugin_name}/config."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    name: str
    config: dict[str, Any]

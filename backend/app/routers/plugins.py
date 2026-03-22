"""Plugins router — GET /api/plugins, POST /api/plugins/{plugin_name}/toggle, config endpoints."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.plugins import (
    PluginConfigResponse,
    PluginConfigUpdateRequest,
    PluginConfigUpdateResponse,
    PluginDetail,
    PluginListResponse,
    PluginToggleRequest,
    PluginToggleResponse,
)

if TYPE_CHECKING:
    from app.plugins.loader import PluginInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


def _plugin_detail(info: PluginInfo) -> PluginDetail:
    """Build a PluginDetail response model from a PluginInfo dataclass.

    Args:
        info: The internal plugin metadata dataclass.

    Returns:
        A ``PluginDetail`` Pydantic model suitable for API responses.
    """
    return PluginDetail(
        name=info.name,
        description=info.description,
        version=info.version,
        enabled=info.enabled,
        hooks=list(info.hooks),
        config_schema=list(info.config_schema),
    )


@router.get(
    "",
    response_model=PluginListResponse,
    summary="List all discovered plugins",
)
async def list_plugins(request: Request) -> PluginListResponse:
    """Return every registered plugin with its current status.

    Args:
        request: The current FastAPI request, used to access the plugin
            registry on ``app.state``.

    Returns:
        A ``PluginListResponse`` containing details for all discovered plugins.
    """
    registry = request.app.state.plugin_registry
    details = [_plugin_detail(info) for info in registry.plugins.values()]
    return PluginListResponse(plugins=details)


@router.post(
    "/{plugin_name}/toggle",
    response_model=PluginToggleResponse,
    summary="Enable or disable a plugin",
)
async def toggle_plugin(
    plugin_name: str,
    body: PluginToggleRequest,
    request: Request,
) -> PluginToggleResponse:
    """Toggle the enabled state of a plugin.

    Updates both the registry and the live plugin pipeline instance so the
    change takes effect immediately without a restart.

    Args:
        plugin_name: The unique name of the plugin to toggle.
        body: Request body containing the desired ``enabled`` state.
        request: The current FastAPI request, used to access ``app.state``.

    Returns:
        A ``PluginToggleResponse`` confirming the plugin name and new state.

    Raises:
        HTTPException: If the plugin name is not found (404 Not Found).
    """
    registry = request.app.state.plugin_registry
    try:
        registry.toggle(plugin_name, body.enabled)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_name}' not found",
        ) from None

    # Sync the enabled state to the live PluginBase instances in the pipeline.
    pipeline = getattr(request.app.state, "plugin_pipeline", None)
    if pipeline is not None:
        for plugin in pipeline.plugins:
            if plugin.name == plugin_name:
                plugin.enabled = body.enabled
                break

    return PluginToggleResponse(name=plugin_name, enabled=body.enabled)


@router.get(
    "/{plugin_name}/config",
    response_model=PluginConfigResponse,
    summary="Get per-plugin configuration",
)
async def get_plugin_config(
    plugin_name: str,
    request: Request,
) -> PluginConfigResponse:
    """Return the current configuration and schema for a plugin.

    Args:
        plugin_name: The unique name of the plugin.
        request: The current FastAPI request, used to access ``app.state``.

    Returns:
        A ``PluginConfigResponse`` with the plugin's current config values
        and its config schema.

    Raises:
        HTTPException: If the plugin name is not found (404 Not Found).
    """
    registry = request.app.state.plugin_registry
    try:
        data = registry.get_config(plugin_name)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_name}' not found",
        ) from None
    return PluginConfigResponse(
        name=plugin_name,
        config=data["config"],
        config_schema=data["config_schema"],
    )


@router.put(
    "/{plugin_name}/config",
    response_model=PluginConfigUpdateResponse,
    summary="Update per-plugin configuration",
)
async def update_plugin_config(
    plugin_name: str,
    body: PluginConfigUpdateRequest,
    request: Request,
) -> PluginConfigUpdateResponse:
    """Update configuration values for a plugin.

    Persists the new config in the registry and syncs it to the live
    plugin instance in the pipeline.

    Args:
        plugin_name: The unique name of the plugin to configure.
        body: Request body containing a ``config`` dict of key-value pairs.
        request: The current FastAPI request, used to access ``app.state``.

    Returns:
        A ``PluginConfigUpdateResponse`` with the plugin name and the
        full updated config dict.

    Raises:
        HTTPException: If the plugin name is not found (404 Not Found).
    """
    registry = request.app.state.plugin_registry
    try:
        updated = registry.update_config(plugin_name, body.config)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_name}' not found",
        ) from None

    # Sync config to the live plugin instance in the pipeline
    pipeline = getattr(request.app.state, "plugin_pipeline", None)
    if pipeline is not None:
        for plugin in pipeline.plugins:
            if plugin.name == plugin_name:
                plugin.config = updated
                break

    return PluginConfigUpdateResponse(name=plugin_name, config=updated)

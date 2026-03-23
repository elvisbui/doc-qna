"""Pydantic models for knowledge pack metadata."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class PackManifest(BaseModel):
    """Manifest describing a knowledge pack's contents and metadata."""

    name: str = Field(..., description="Short identifier for the pack (e.g. 'python-docs')")
    version: str = Field(..., description="Semantic version string (e.g. '1.0.0')")
    description: str = Field(default="", description="Human-readable description of the pack")
    author: str = Field(default="", description="Author or organisation name")
    license: str = Field(default="", description="SPDX license identifier")
    documents: list[str] = Field(
        default_factory=list,
        description="Relative paths to documents inside the pack archive",
    )
    doc_count: int = Field(default=0, description="Number of documents in the pack")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the pack was created",
    )


class SuggestedQueries(BaseModel):
    """Optional starter questions shipped with a knowledge pack."""

    queries: list[str] = Field(default_factory=list)

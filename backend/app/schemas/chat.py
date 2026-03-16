"""API request/response schemas for chat endpoints."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import to_camel


class HistoryMessage(BaseModel):
    """A single message in the conversation history."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"role": "user", "content": "What is machine learning?"},
                {"role": "assistant", "content": "Machine learning is a subset of AI..."},
            ]
        }
    )

    role: str = Field(..., pattern=r"^(user|assistant)$", description="Message role")
    content: str = Field(..., min_length=1, description="Message content")


class ChatRequest(BaseModel):
    """Incoming chat query from the user."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "query": "What is machine learning?",
                },
                {
                    "query": "Explain the architecture described in chapter 3",
                    "history": [
                        {"role": "user", "content": "What is this document about?"},
                        {
                            "role": "assistant",
                            "content": "This document covers software architecture...",
                        },
                    ],
                    "documentIds": ["b5f7d3a0-1234-4abc-9def-0123456789ab"],
                },
            ]
        },
    )

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's natural-language question",
    )
    history: list[HistoryMessage] = Field(
        default_factory=list,
        description="Previous conversation messages for multi-turn context",
    )
    document_ids: list[str] | None = Field(
        default=None,
        description="Optional list of document IDs to scope the search to",
    )

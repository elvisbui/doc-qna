"""Chat router — streaming SSE responses for document Q&A.

Thin HTTP layer: validation and response formatting only.
Business logic lives in services/generation.py.
"""

import json
import logging
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.routers import ERROR_RESPONSE_SCHEMA
from app.schemas.chat import ChatRequest
from app.services.generation import generate_answer_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post(
    "/chat",
    summary="Ask a question about your documents",
    description=(
        "Send a natural-language query and receive a streaming SSE response. "
        "The stream emits answer tokens, source citations, and a done signal. "
        "Optionally scope the search to specific documents via document_ids."
    ),
    responses={
        422: {
            "description": "Request validation failed",
            "content": {"application/json": {"schema": ERROR_RESPONSE_SCHEMA}},
        },
        502: {
            "description": "LLM or embedding provider error",
            "content": {"application/json": {"schema": ERROR_RESPONSE_SCHEMA}},
        },
    },
)
async def chat(
    request: ChatRequest,
    http_request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> StreamingResponse:
    """Send a query and receive a streaming SSE response with citations.

    Accepts a JSON body with a ``query`` field and streams back
    Server-Sent Events containing answer tokens, citations, and a
    done signal.
    """

    async def _event_generator():
        """Yield SSE events from the answer generation stream.

        Delegates to ``generate_answer_stream``, forwarding each SSE event
        to the client. Extracts citation relevance scores for metrics
        recording. On error, emits an ``event: error`` SSE and logs the
        exception. Metrics are always recorded in the ``finally`` block.

        Yields:
            Formatted SSE event strings (tokens, citations, done, or error).
        """
        start = time.perf_counter()
        error_occurred = False
        error_message: str | None = None
        relevance_scores: list[float] = []
        num_chunks = 0

        try:
            collection = getattr(http_request.app.state, "chroma_collection", None)
            embedder = getattr(http_request.app.state, "embedder", None)
            embedding_cache = getattr(http_request.app.state, "embedding_cache", None)
            llm_provider = getattr(http_request.app.state, "llm_provider", None)
            plugin_pipeline = getattr(http_request.app.state, "plugin_pipeline", None)
            user_id = resolve_user_id(http_request, settings)
            history = [{"role": m.role, "content": m.content} for m in request.history]
            async for event in generate_answer_stream(
                request.query,
                settings,
                collection=collection,
                history=history,
                document_ids=request.document_ids,
                embedder=embedder,
                embedding_cache=embedding_cache,
                user_id=user_id,
                llm_provider=llm_provider,
                plugin_pipeline=plugin_pipeline,
            ):
                # Try to extract citation data from SSE events for metrics
                if event.startswith("event: citations\n"):
                    try:
                        data_line = event.split("data: ", 1)[1].split("\n")[0]
                        citations_data = json.loads(data_line)
                        if isinstance(citations_data, list):
                            for c in citations_data:
                                score = c.get("relevance_score") or c.get("relevanceScore")
                                if score is not None:
                                    relevance_scores.append(float(score))
                            num_chunks = len(citations_data)
                    except Exception:
                        pass
                yield event
        except Exception:
            error_occurred = True
            error_message = "Unexpected error during chat streaming"
            logger.exception(error_message)
            yield "event: error\ndata: An internal error occurred. Please try again.\n\n"
        finally:
            # Record metrics — wrapped so failures never break chat
            try:
                from app.services.metrics import record_metric

                latency_ms = (time.perf_counter() - start) * 1000
                avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
                await record_metric(
                    query_text=request.query,
                    latency_ms=latency_ms,
                    avg_relevance_score=avg_relevance,
                    num_chunks_retrieved=num_chunks,
                    error=error_occurred,
                    error_message=error_message,
                )
            except Exception:
                logger.debug("Failed to record chat metric", exc_info=True)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

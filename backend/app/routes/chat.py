"""Chat route — SSE streaming endpoint for the Oracle pipeline."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.database import ReportRow, get_session_factory
from app.graph.builder import build_oracle_graph
from app.graph.models import ThoughtEvent

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    query: str
    stream: bool = True


# ---------------------------------------------------------------------------
# SSE streaming endpoint
# ---------------------------------------------------------------------------


@router.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Accept a research query, run the LangGraph pipeline, and stream
    thought-trace events + the final report back via SSE.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty")

    settings = get_settings()
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    graph = build_oracle_graph()
    report_id = str(uuid.uuid4())

    async def event_generator():
        """Run the graph and yield SSE events."""
        initial_state = {
            "query": request.query,
            "refined_query": "",
            "search_results": [],
            "scraped_docs": [],
            "cloned_repos": [],
            "cleaned_chunks": [],
            "reasoning_output": "",
            "evaluation_score": 0.0,
            "final_report": "",
            "retry_count": 0,
            "active_node": "",
            "quality_warning": False,
            "thought_trace": [],
        }

        # Send initial event
        yield {
            "event": "thought",
            "data": json.dumps({
                "node": "system",
                "message": f"Starting research: \"{request.query}\"",
                "status": "running",
                "timestamp": datetime.utcnow().isoformat(),
            }),
        }

        all_thoughts: list[dict] = []
        final_state = initial_state

        try:
            # Stream through graph nodes
            # LangGraph's stream mode gives us state updates per node
            for event in graph.stream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    # Extract and forward thought events
                    new_thoughts = node_output.get("thought_trace", [])
                    for thought in new_thoughts:
                        thought_data = (
                            thought.model_dump()
                            if isinstance(thought, ThoughtEvent)
                            else thought
                        )
                        # Convert datetime to string
                        if "timestamp" in thought_data and hasattr(
                            thought_data["timestamp"], "isoformat"
                        ):
                            thought_data["timestamp"] = thought_data[
                                "timestamp"
                            ].isoformat()
                        all_thoughts.append(thought_data)

                        yield {
                            "event": "thought",
                            "data": json.dumps(thought_data),
                        }

                    # If this node produced a final report, stream it
                    if "final_report" in node_output and node_output["final_report"]:
                        # Stream the report in chunks for progressive rendering
                        report = node_output["final_report"]
                        chunk_size = 200
                        for i in range(0, len(report), chunk_size):
                            yield {
                                "event": "report",
                                "data": json.dumps({
                                    "content": report[i : i + chunk_size],
                                    "done": i + chunk_size >= len(report),
                                }),
                            }

                    # Track final state values
                    for key in node_output:
                        if key != "thought_trace":
                            final_state[key] = node_output[key]

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "message": f"Pipeline error: {str(e)}",
                    "node": final_state.get("active_node", "unknown"),
                }),
            }

        # ── Persist report to SQLite ──────────────────────────────────
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                row = ReportRow(
                    id=report_id,
                    query=request.query,
                    report=final_state.get("final_report", ""),
                    evaluation_score=final_state.get("evaluation_score", 0.0),
                    retry_count=final_state.get("retry_count", 0),
                )
                row.thought_trace = all_thoughts
                session.add(row)
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to persist report: {e}")

        # ── Final done event ──────────────────────────────────────────
        yield {
            "event": "done",
            "data": json.dumps({
                "report_id": report_id,
                "evaluation_score": final_state.get("evaluation_score", 0.0),
                "retry_count": final_state.get("retry_count", 0),
                "quality_warning": final_state.get("quality_warning", False),
            }),
        }

    return EventSourceResponse(event_generator())

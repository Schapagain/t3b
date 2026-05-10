"""
T3B: Talk to the Board
FastAPI backend
"""

from dotenv import load_dotenv

load_dotenv()

from collections.abc import AsyncIterable
from models import ChatRequest, ChatResponse, ToolEventResponse
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from fastapi.middleware.cors import CORSMiddleware
from ingest import re_index_db, get_last_synced_at
import json
from agent import run_agent

app = FastAPI(title="T3B API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


sessions: dict[str, list[dict]] = {}
pending_msgs: dict[str, dict] = {}
pending_tool_calls_used: dict[str, list[str]] = {}


@app.post("/chat/stream", response_class=EventSourceResponse)
async def chat(body: ChatRequest) -> AsyncIterable[ChatResponse | ToolEventResponse]:
    """
    Streaming chat endpoint that runs the agent loop and yields SSE events.

    Manages per-session message history and approval state. On approval,
    restores the pending assistant message so the agent can resume without
    an extra LLM call. On rejection, clears pending state so the agent
    re-runs from history with the denial included.

    Args:
        body: Chat request with session_id, optional message, and
            optional approved_tool name.

    Yields:
        SSE-encoded ChatResponse or ToolEventResponse dicts.
    """
    history = sessions.setdefault(body.session_id, [])

    if body.message:
        history.append({"role": "user", "content": body.message})
        print(
            f"New chat request for session id:{body.session_id}\nWe have history:\n{history}\n\nmsg:\n{body.message}"
        )
    approved_tools = []
    if body.approved_tool:
        approved_tools.append(body.approved_tool)

    if body.approved_tool:
        pending_msg = pending_msgs.pop(body.session_id, None)
        prior_tool_calls = pending_tool_calls_used.pop(body.session_id, None)
    else:
        pending_msgs.pop(body.session_id, None)
        pending_tool_calls_used.pop(body.session_id, None)
        pending_msg = None
        prior_tool_calls = None

    async for response in run_agent(
        history,
        approved_tools,
        pending_msg,
        prior_tool_calls,
    ):
        if response["type"] == "final_response":
            agent_response = response["content"]["message"]
            tool_calls_used = response["content"]["tool_calls_used"]
            cards = response["content"]["cards"]
            updated_history = response["content"]["history"]

            updated_history.append({"role": "assistant", "content": agent_response})
            sessions[body.session_id] = updated_history
            display_history = [
                m for m in updated_history if m["role"] in ("user", "assistant")
            ]
            yield {
                "agent_response": agent_response,
                "tool_calls_used": tool_calls_used,
                "history": display_history,
                "cards": cards,
            }
        elif response["type"] == "tool_called":
            tool_name = response["content"]["name"]
            yield {"tool_event": {"name": tool_name, "status": "started"}}
        elif response["type"] == "tool_finished":
            tool_name = response["content"]["name"]
            yield {"tool_event": {"name": tool_name, "status": "finished"}}
        elif response["type"] == "tool_skipped":
            tool_name = response["content"]["name"]
            yield {"tool_event": {"name": tool_name, "status": "skipped"}}
        elif response["type"] == "tool_failed":
            tool_name = response["content"]["name"]
            yield {"tool_event": {"name": tool_name, "status": "failed"}}
        elif response["type"] == "tool_approval_required":
            pending_msgs[body.session_id] = response["pending_msg"]
            pending_tool_calls_used[body.session_id] = response["tool_calls_used"]
            yield {"tool_event": {**response["content"], "status": "approval_required"}}


@app.post("/ingest/sync")
def ingest_sync():
    """
    Trigger a full re-index of Trello cards into ChromaDB.

    Returns:
        Dict with cards_ingested count.
    """
    response = re_index_db()
    return {"cards_ingested": response.get("cards_ingested", 0)}


@app.get("/ingest/last_synced_at")
def ingest_last_synced_at():
    """
    Return the timestamp of the most recent Trello sync.

    Returns:
        Dict with last_synced_at as a datetime or None if never synced.
    """
    last_synced_at = get_last_synced_at()
    return {"last_synced_at": last_synced_at}

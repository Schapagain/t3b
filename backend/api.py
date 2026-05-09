"""
T3B: Talk to the Board
FastAPI backend
"""

from dotenv import load_dotenv

load_dotenv()

from collections.abc import AsyncIterable, Iterable
from models import ChatRequest, ChatResponse, ToolEventResponse
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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


@app.post("/chat/stream", response_class=EventSourceResponse)
async def chat(body: ChatRequest) -> AsyncIterable[ChatResponse | ToolEventResponse]:
    history = sessions.setdefault(body.session_id, [])
    history.append({"role": "user", "content": body.message})
    print(
        f"New chat request for session id:{body.session_id}\nWe have history:\n{history}"
    )
    async for response in run_agent(history):
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
            yield {"tool_event": {"tool_called": tool_name}}
        elif response["type"] == "tool_finished":
            tool_name = response["content"]["name"]
            yield {"tool_event": {"tool_finished": tool_name}}
        elif response["type"] == "tool_skipped":
            tool_name = response["content"]["name"]
            yield {"tool_event": {"tool_skipped": tool_name}}
        elif response["type"] == "tool_failed":
            tool_name = response["content"]["name"]
            yield {"tool_event": {"tool_failed": tool_name}}


@app.post("/ingest/sync")
def ingest_sync():
    response = re_index_db()
    return {"cards_ingested": response.get("cards_ingested", 0)}


@app.get("/ingest/last_synced_at")
def ingest_last_synced_at():
    last_synced_at = get_last_synced_at()
    return {"last_synced_at": last_synced_at}

"""
T3B: Talk to the Board
FastAPI backend
"""

from dotenv import load_dotenv

load_dotenv()

from models import ChatMessage, ChatRequest
from fastapi import FastAPI
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


sessions: dict[str, list[ChatMessage]] = {}


@app.post("/chat")
def chat(body: ChatRequest):
    history = sessions.setdefault(body.session_id, [])
    history.append(ChatMessage(role="user", content=body.message))
    print(
        f"New chat request for session id:{body.session_id}\nWe have history:\n{history}"
    )
    agent_response, tool_calls_used, cards = run_agent(history)

    history.append(ChatMessage(role="assistant", content=agent_response))
    return {
        "agent_response": agent_response,
        "tool_calls_used": tool_calls_used,
        "history": history,
        "cards": cards,
    }


@app.post("/ingest/sync")
def ingest_sync():
    response = re_index_db()
    return {"cards_ingested": response.get("cards_ingested", 0)}


@app.get("/ingest/last_synced_at")
def ingest_last_synced_at():
    last_synced_at = get_last_synced_at()
    return {"last_synced_at": last_synced_at}

"""
T3B: Talk to the Board
FastAPI backend — minimal scaffold
"""

from dotenv import load_dotenv

load_dotenv()

from models import ChatMessage, ChatRequest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ingest import re_index_db
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

    agent_response, tool_calls_used = run_agent(history)

    history.append(ChatMessage(role="assistant", content=agent_response))
    return {"agent_response": agent_response, "tool_calls_used": tool_calls_used}


@app.post("/ingest/sync")
def ingest_sync():
    response = re_index_db()
    return {"cards_ingested": response.get("cards_ingested", 0)}

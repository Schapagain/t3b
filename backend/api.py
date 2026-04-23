"""
T3B: Talk to the Board
FastAPI backend — minimal scaffold
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="T3B API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class SyncRequest(BaseModel):
    board_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(body: ChatRequest):
    return {
        "answer": f"Echo: {body.message}",
        "tool_calls_used": [],
    }


@app.post("/ingest/sync")
def ingest_sync(body: SyncRequest):
    return {"cards_ingested": 0, "board_id": body.board_id}

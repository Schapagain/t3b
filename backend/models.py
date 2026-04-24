from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class Card(BaseModel):
    id: str
    name: str
    due: str | None
    desc: str
    url: str
    status: str
    assignee: str | None

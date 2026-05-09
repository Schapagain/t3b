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
    desc: str
    due: float | None
    url: str
    status: str
    assignee: str | None
    assignee_first_name: str | None
    assignee_last_name: str | None


class ChatResponse(BaseModel):
    agent_response: str | None
    tool_calls_used: list[str] | None
    history: list[dict]
    cards: list[Card]


class ToolEventResponse(BaseModel):
    tool_event: dict

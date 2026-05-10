# T3B — Talk to the Board

T3B is a chat assistant that lets engineering teams query and update their Trello boards through natural language. Instead of manually filtering cards or switching between tools, users can ask questions like "what is Alice working on?" or "does anyone have a scheduling conflict this sprint?" and get a direct answer grounded in live board data.

This is the final project for **CSC 7644: Applied LLM Development**.

---

## Features

- **Natural language search** — query cards by assignee, status, due date, or semantic similarity
- **Hybrid retrieval** — combines ChromaDB vector search with BM25 keyword matching for better coverage
- **Scheduling conflict detection** — checks whether card due dates fall within an assignee's OOO events from Google Calendar
- **Card updates** — move cards, reassign, or change due dates directly from the chat interface
- **Human-in-the-loop approval** — all writes require explicit confirmation before going through
- **Real-time streaming** — tool call progress is streamed to the UI as it happens via Server-Sent Events, rather than waiting for the full response

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI gpt-4o-mini |
| Embeddings | OpenAI text-embedding-3-small |
| Vector store | ChromaDB (persistent, local) |
| Keyword search | BM25 (rank-bm25) |
| Backend | FastAPI + uvicorn |
| Frontend | React + Vite + shadcn/ui + Tailwind CSS |
| External APIs | Trello REST API, Google Calendar (iCal) |

### Architecture

The backend exposes a streaming SSE endpoint at `POST /chat/stream`. Each user message is passed to an async agent loop that selects and executes tools (search, update, conflict check) and yields typed events back to the frontend as they happen. When an update is requested, the loop pauses and sends an approval prompt to the UI before writing anything to Trello.

Cards are ingested from Trello, embedded, and stored in ChromaDB. At query time, metadata filters narrow the candidate set first, then BM25 and vector similarity are fused to rank results.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Trello account with a board, API key, and token
- An OpenAI API key
- A Google Calendar public iCal URL (optional — required only for scheduling conflict detection)

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd t3b
```

### 2. Install dependencies

```bash
make install
```

This runs `pip install -r backend/requirements.txt` and `npm install` in the frontend.

### 3. Configure environment variables

Create a `.env` file in `backend/`:

```bash
cp backend/.env.example backend/.env
```

Then fill in the values:

```
OPENAI_API_KEY=...
TRELLO_API_KEY=...
TRELLO_TOKEN=...
TRELLO_BOARD_ID=...
CHROMA_DB_PATH=./db/chromadb
GOOGLE_CALENDAR_URL=...   # public iCal URL, optional
```

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `TRELLO_API_KEY` | Trello developer API key |
| `TRELLO_TOKEN` | Trello user token |
| `TRELLO_BOARD_ID` | ID of the Trello board to connect |
| `CHROMA_DB_PATH` | Local path where ChromaDB stores its data |
| `GOOGLE_CALENDAR_URL` | Public iCal feed URL for OOO event detection |

To get Trello credentials, visit [https://trello.com/power-ups/admin](https://trello.com/power-ups/admin). The board ID is the short alphanumeric string in your board's URL.

---

## Running the Application

Start the backend and frontend in separate terminals:

```bash
make backend    # starts FastAPI on http://localhost:8000
make frontend   # starts Vite dev server on http://localhost:5173
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

On first run, click **Sync Trello** in the top right to fetch and index your board's cards. After that, you can start chatting.

---

## Seeding a Demo Board

A seed script is included to populate a Trello board with realistic demo cards:

```bash
python seed_board.py
```

This wipes all existing cards and re-seeds the board with a predefined set of cards across Backlog, Triage, In Progress, In Review, and Done lists. The script reads credentials from `backend/.env`.

---

## Evaluation

A retrieval eval script is included:

```bash
cd t3b && python eval_retrieval.py
```

This runs 10 queries (5 metadata-only, 5 semantic) against the live ChromaDB collection and reports Recall@5. The backend must have been synced at least once before running this.

---

## Repository Structure

```
t3b/
├── backend/
│   ├── api.py               # FastAPI app and SSE chat endpoint
│   ├── agent.py             # Async agent loop and tool orchestration
│   ├── tools.py             # Tool definitions, schemas, and executors
│   ├── ingest.py            # Trello ingestion, embedding, and vector search
│   ├── trello.py            # Trello REST API client
│   ├── calendar_events.py   # Google Calendar iCal parsing
│   ├── services.py          # Cached OpenAI and ChromaDB client factories
│   ├── models.py            # Pydantic models
│   ├── utils.py             # Date conversion helpers
│   ├── constants.py         # Model names, thresholds, TTLs
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx                      # Main app and stream handling
│       ├── components/
│       │   ├── message-bubble.jsx       # Chat and tool event bubbles
│       │   ├── trello-card.jsx          # Card display component
│       │   └── chat-input.jsx
│       ├── hooks/
│       │   └── useSync.js               # Trello sync hook
│       └── lib/
│           └── utils.js                 # Card change detection helpers
├── eval_retrieval.py        # Recall@5 evaluation script
├── seed_board.py            # Demo board seeding script
└── Makefile                 # Shortcuts for install, backend, frontend
```

---

## Attributions

- [FastAPI SSE documentation](https://fastapi.tiangolo.com/) — reference for `EventSourceResponse` and streaming endpoint patterns
- [ChromaDB documentation](https://docs.trychroma.com/) — collection setup and metadata filtering
- [Trello REST API documentation](https://developer.atlassian.com/cloud/trello/rest/) — card and board endpoints
- [rank-bm25](https://github.com/dorianbrown/rank_bm25) — BM25 implementation used for keyword search fusion
- [shadcn/ui](https://ui.shadcn.com/) — React component library used for the frontend

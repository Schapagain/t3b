#!/usr/bin/env python3
"""
eval_retrieval.py — Recall evaluation for T3B's search_cards tool.

Calls exec_search_cards with the same args the agent would pass and checks
whether at least one expected card appears in the result set.

Usage: python eval_retrieval.py
Reads TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID, OPENAI_API_KEY from .env
"""

import os
import sys

sys.path.insert(0, "backend")

os.environ["CHROMA_DB_PATH"] = "backend/db/chromadb"

from dotenv import load_dotenv

load_dotenv("backend/.env")

from tools import exec_search_cards

# ---------------------------------------------------------------------------
# Test cases
# Each case has:
#   description  — what the user would actually ask
#   args         — what the agent would pass to exec_search_cards
#   expected     — list of substrings; a hit if ANY appears in any result name
# ---------------------------------------------------------------------------
CASES = [
    # --- Metadata-only queries -------------------------------------------
    {
        "description": "What is Alice currently working on?",
        "args": {
            "assignee": "alice",
            "status": "In Progress",
            "due_before": None,
            "due_after": None,
            "query": None,
        },
        "expected": ["calorie tracking"],
    },
    {
        "description": "Which cards are currently in review?",
        "args": {
            "assignee": None,
            "status": "In Review",
            "due_before": None,
            "due_after": None,
            "query": None,
        },
        "expected": ["social feed", "heart rate zone", "unit tests"],
    },
    {
        "description": "What is Dave assigned to?",
        "args": {
            "assignee": "dave",
            "status": None,
            "due_before": None,
            "due_after": None,
            "query": None,
        },
        "expected": ["push notification", "unit tests", "streak"],
    },
    {
        "description": "What backlog items are coming up?",
        "args": {
            "assignee": None,
            "status": "Backlog",
            "due_before": None,
            "due_after": None,
            "query": None,
        },
        "expected": ["dark mode", "leaderboard", "milestone"],
    },
    {
        "description": "What is Bob working on right now?",
        "args": {
            "assignee": "bob",
            "status": "In Progress",
            "due_before": None,
            "due_after": None,
            "query": None,
        },
        "expected": ["weekly summary"],
    },
    # --- Semantic queries ------------------------------------------------
    # These go through vector search (top_k=2) — expected to be harder.
    {
        "description": "Have we had any issues with push alerts before?",
        "args": {
            "assignee": None,
            "status": None,
            "due_before": None,
            "due_after": None,
            "query": "push notification issues alerts",
        },
        "expected": ["push notification", "completion notification"],
    },
    {
        "description": "Is anyone working on syncing with wearables or health platforms?",
        "args": {
            "assignee": None,
            "status": None,
            "due_before": None,
            "due_after": None,
            "query": "wearable device health platform sync",
        },
        "expected": ["healthkit", "garmin"],
    },
    {
        "description": "Are there any cards related to location or map tracking?",
        "args": {
            "assignee": None,
            "status": None,
            "due_before": None,
            "due_after": None,
            "query": "location map route tracking",
        },
        "expected": ["gps route"],
    },
    # --- Mixed queries ---------------------------------------------------
    {
        "description": "Is there any overlap between calorie-related cards?",
        "args": {
            "assignee": None,
            "status": None,
            "due_before": None,
            "due_after": None,
            "query": "calorie burn tracking workout",
        },
        "expected": ["calorie tracking", "track calories burned"],
    },
    {
        "description": "What auth or login related work has been done?",
        "args": {
            "assignee": None,
            "status": "Done",
            "due_before": None,
            "due_after": None,
            "query": "authentication login",
        },
        "expected": ["authentication", "auth"],
    },
]


def run():
    # Sanity check: env vars and collection state
    from services import get_collection
    from constants import COLLECTION_NAME

    print("=== ENV CHECK ===")
    print(f"  CHROMA_DB_PATH  : {os.getenv('CHROMA_DB_PATH')}")
    print(f"  OPENAI_API_KEY  : {'set' if os.getenv('OPENAI_API_KEY') else 'MISSING'}")
    col = get_collection(COLLECTION_NAME)
    count = col.count()
    print(f"  Collection '{COLLECTION_NAME}' has {count} document(s)")
    if count > 0:
        sample = col.get(limit=3, include=["metadatas"])
        for m in sample.get("metadatas", []):
            print(
                f"    sample: {m.get('name')} | assignee: {m.get('assignee')} | status: {m.get('status')}"
            )
    print()

    hits = 0
    misses = []

    for i, case in enumerate(CASES, 1):
        print(f"[{i:02d}] {case['description']}")
        print(f"     args: {case['args']}")
        try:
            result = exec_search_cards(case["args"])
            cards = result.get("cards", [])
            returned_names = [c.get("name", "").lower() for c in cards]
            print(f"     returned {len(cards)} card(s):")
            for c in cards:
                print(
                    f"       - '{c.get('name')}' | assignee: {c.get('assignee')} | status: {c.get('status')}"
                )

            hit = any(
                exp.lower() in name
                for exp in case["expected"]
                for name in returned_names
            )

            if hit:
                hits += 1
                print(f"     -> HIT (expected one of: {case['expected']})")
            else:
                misses.append(case["description"])
                print(f"     -> MISS (expected one of: {case['expected']})")

        except Exception as e:
            import traceback

            misses.append(case["description"])
            print(f"     -> ERROR: {e}")
            traceback.print_exc()
        print()

    total = len(CASES)
    recall = hits / total
    print(f"\n{'='*60}")
    print(f"Recall: {hits}/{total} = {recall:.2f}")
    if misses:
        print(f"\nMisses:")
        for m in misses:
            print(f"  - {m}")


if __name__ == "__main__":
    run()

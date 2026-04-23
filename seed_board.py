#!/usr/bin/env python3
"""
seed_board.py — Resets the Pulse demo Trello board for T3B.
Usage: python seed_board.py
Reads TRELLO_API_KEY, TRELLO_TOKEN, and TRELLO_BOARD_ID from the project root .env.

Wipes all cards, then re-seeds with real member assignments.
Lists and the board itself are left untouched.
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

API_KEY = os.getenv("TRELLO_API_KEY")
TOKEN = os.getenv("TRELLO_TOKEN")
BOARD_ID = os.getenv("TRELLO_BOARD_ID")

if not API_KEY or not TOKEN or not BOARD_ID:
    sys.exit(
        "Error: TRELLO_API_KEY, TRELLO_TOKEN, and TRELLO_BOARD_ID must be set in .env"
    )

BASE = "https://api.trello.com/1"
AUTH = {"key": API_KEY, "token": TOKEN}
LIST_ORDER = ["Backlog", "Triage", "In Progress", "In Review", "Done"]


def get(path, **params):
    r = requests.get(f"{BASE}{path}", params={**AUTH, **params})
    r.raise_for_status()
    return r.json()


def post(path, **params):
    r = requests.post(f"{BASE}{path}", params={**AUTH, **params})
    r.raise_for_status()
    return r.json()


def delete(path):
    r = requests.delete(f"{BASE}{path}", params=AUTH)
    r.raise_for_status()


# --- Fetch lists ---
raw_lists = get(f"/boards/{BOARD_ID}/lists", filter="open")
lists = {lst["name"]: lst["id"] for lst in raw_lists}

missing = [name for name in LIST_ORDER if name not in lists]
if missing:
    sys.exit(f"Error: missing lists on board: {missing}")

MEMBERS = {
    "Alice": "69e986ecc623ce670e297aaa",
    "Bob": "69e9871cca2af2a751456efa",
    "Carol": "69e9878ae6b74e6d3573f22c",
    "Dave": "69e987afc24a09ce7dfcce3b",
}

# --- Wipe existing cards ---
cards = get(f"/boards/{BOARD_ID}/cards")
for card in cards:
    delete(f"/cards/{card['id']}")
print(f"Deleted {len(cards)} existing cards")

# --- Seed cards ---
CARDS = [
    # Done
    ("Done", "Set up project repository", "Alice", None),
    ("Done", "Design onboarding screens", "Bob", None),
    ("Done", "Create user authentication flow", "Alice", None),
    ("Done", "Set up database schema for users and workouts", "Alice", None),
    (
        "In Review",
        "Add social feed for following friends",
        "Bob",
        "2026-04-24T23:59:00.000Z",
    ),
    (
        "In Review",
        "Implement heart rate zone calculations",
        "Alice",
        "2026-04-25T23:59:00.000Z",
    ),
    (
        "In Review",
        "Write unit tests for workout logging API",
        "Dave",
        "2026-04-24T23:59:00.000Z",
    ),
    (
        "In Progress",
        "Add calorie tracking to workout logs",
        "Alice",
        "2026-04-28T23:59:00.000Z",
    ),
    (
        "In Progress",
        "Fix push notification delay after workout ends",
        "Dave",
        "2026-04-28T23:59:00.000Z",
    ),
    (
        "In Progress",
        "Add GPS route tracking to outdoor runs",
        "Carol",
        "2026-04-29T23:59:00.000Z",
    ),
    (
        "In Progress",
        "Build weekly summary dashboard",
        "Bob",
        "2026-04-28T23:59:00.000Z",
    ),
    (
        "In Progress",
        "Integrate Apple HealthKit sync",
        "Carol",
        "2026-04-30T23:59:00.000Z",
    ),
    ("Backlog", "Track calories burned during workouts", "Bob", None),
    ("Backlog", "Workout completion notifications not triggering", "Carol", None),
    ("Backlog", "Add dark mode support", "Bob", "2026-04-28T23:59:00.000Z"),
    (
        "Backlog",
        "Implement personal bests leaderboard",
        "Alice",
        "2026-04-28T23:59:00.000Z",
    ),
    (
        "Backlog",
        "Update goal milestone thresholds",
        "Alice",
        "2026-04-28T23:59:00.000Z",
    ),
    ("Backlog", "Add rest day recommendations based on fatigue", "Alice", None),
    ("Backlog", "Support Garmin device integration", "Carol", None),
    ("Backlog", "Add profile photo upload", "Bob", None),
    ("Backlog", "Implement workout streak tracking", "Dave", None),
    ("Backlog", "Add export to CSV for workout history", "Dave", None),
    ("Backlog", "Build admin dashboard for user analytics", "Alice", None),
]

print(f"Creating {len(CARDS)} cards...")
for list_name, title, assignee, due in CARDS:
    params = {
        "name": title,
        "idList": lists[list_name],
        "idMembers": MEMBERS[assignee],
    }
    if due:
        params["due"] = due
    post("/cards", **params)
    print(f"  [{list_name}] {title} → {assignee}")

board_url = f"https://trello.com/b/{BOARD_ID}"
print(f"\nBoard ready: {board_url}")

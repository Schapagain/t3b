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
# (list, title, assignee, due, description)
CARDS = [
    (
        "Done",
        "Set up project repository",
        "Alice",
        None,
        "Initialize GitHub repo, configure CI pipeline, and set up branch protection rules. Includes linting and test scaffolding.",
    ),
    (
        "Done",
        "Design onboarding screens",
        "Bob",
        None,
        "Design and prototype the onboarding flow covering account creation, goal setting, and fitness level selection. Figma mockups approved.",
    ),
    (
        "Done",
        "Create user authentication flow",
        "Alice",
        None,
        "Implement JWT-based login and registration. Includes password hashing, token refresh, and session expiry handling.",
    ),
    (
        "Done",
        "Set up database schema for users and workouts",
        "Alice",
        None,
        "Design and migrate Postgres schema for users, workout sessions, exercises, and sets. Includes indexing on user_id and created_at.",
    ),
    (
        "In Review",
        "Add social feed for following friends",
        "Bob",
        "2026-04-24T23:59:00.000Z",
        "Build a social activity feed showing recent workouts from followed users. Includes follow/unfollow API and pagination. Currently in code review.",
    ),
    (
        "In Review",
        "Implement heart rate zone calculations",
        "Alice",
        "2026-04-25T23:59:00.000Z",
        "Calculate heart rate zones (rest, fat burn, cardio, peak) from user's max HR and real-time BPM data. Includes zone history chart.",
    ),
    (
        "In Review",
        "Write unit tests for workout logging API",
        "Dave",
        "2026-04-24T23:59:00.000Z",
        "Add test coverage for all workout logging endpoints including edge cases for concurrent sessions and invalid exercise data.",
    ),
    (
        "In Progress",
        "Add calorie tracking to workout logs",
        "Alice",
        "2026-04-28T23:59:00.000Z",
        "Calculate estimated calories burned per workout using MET values, user weight, and duration. Display running total on the workout screen.",
    ),
    (
        "In Progress",
        "Fix push notification delay after workout ends",
        "Dave",
        "2026-04-28T23:59:00.000Z",
        "Push notifications are firing 3-5 minutes late after workout completion. Suspected issue with background task queue on iOS. Needs investigation and fix.",
    ),
    (
        "In Progress",
        "Add GPS route tracking to outdoor runs",
        "Carol",
        "2026-04-29T23:59:00.000Z",
        "Integrate device GPS to record route coordinates during outdoor runs. Display route on map post-workout with elevation profile and split pacing.",
    ),
    (
        "In Progress",
        "Build weekly summary dashboard",
        "Bob",
        "2026-04-28T23:59:00.000Z",
        "Weekly dashboard showing total workout time, calories burned, distance covered, and streak. Includes comparison to previous week.",
    ),
    (
        "In Progress",
        "Integrate Apple HealthKit sync",
        "Carol",
        "2026-04-30T23:59:00.000Z",
        "Bi-directional sync with Apple HealthKit for steps, active calories, and workout sessions. Requires HealthKit entitlement and user permission flow.",
    ),
    (
        "Backlog",
        "Track calories burned during workouts",
        "Bob",
        None,
        "Users want to see how many calories they burn during each session. Should factor in exercise type, intensity, and body weight.",
    ),
    (
        "Backlog",
        "Workout completion notifications not triggering",
        "Carol",
        None,
        "Several users reporting they don't receive a push notification when their workout session ends. May be related to app backgrounding behavior.",
    ),
    (
        "Backlog",
        "Add dark mode support",
        "Bob",
        "2026-04-28T23:59:00.000Z",
        "Implement system-aware dark mode across all screens. Should respect the device's appearance setting and allow manual override in app settings.",
    ),
    (
        "Backlog",
        "Implement personal bests leaderboard",
        "Alice",
        "2026-04-28T23:59:00.000Z",
        "Track and display personal records for key metrics like fastest 5K, max bench press, and longest workout. Notify user when a new PR is set.",
    ),
    (
        "Backlog",
        "Update goal milestone thresholds",
        "Alice",
        "2026-04-28T23:59:00.000Z",
        "Current milestone thresholds are too easy for advanced users. Allow configurable milestones per fitness level and add stretch goals.",
    ),
    (
        "Backlog",
        "Add rest day recommendations based on fatigue",
        "Alice",
        None,
        "Analyze recent workout load and heart rate variability to recommend rest days. Should integrate with the weekly plan and send a proactive notification.",
    ),
    (
        "Backlog",
        "Support Garmin device integration",
        "Carol",
        None,
        "Allow users to connect Garmin wearables to sync heart rate, steps, sleep, and workout data via Garmin Connect API.",
    ),
    (
        "Backlog",
        "Add profile photo upload",
        "Bob",
        None,
        "Allow users to upload and crop a profile photo. Store in S3 with CDN delivery. Display in social feed and leaderboard.",
    ),
    (
        "Backlog",
        "Implement workout streak tracking",
        "Dave",
        None,
        "Track consecutive days with at least one logged workout. Display current and longest streak on the profile screen. Send streak-at-risk notification after 20 hours of inactivity.",
    ),
    (
        "Backlog",
        "Add export to CSV for workout history",
        "Dave",
        None,
        "Allow users to export their full workout history as a CSV file. Should include date, exercise, sets, reps, weight, duration, and calories.",
    ),
    (
        "Backlog",
        "Build admin dashboard for user analytics",
        "Alice",
        None,
        "Internal dashboard for the team to monitor DAU, retention, top exercises, and error rates. Should be role-gated and not accessible to regular users.",
    ),
]

print(f"Creating {len(CARDS)} cards...")
for list_name, title, assignee, due, desc in CARDS:
    params = {
        "name": title,
        "idList": lists[list_name],
        "idMembers": MEMBERS[assignee],
        "desc": desc,
    }
    if due:
        params["due"] = due
    post("/cards", **params)
    print(f"  [{list_name}] {title} → {assignee}")

board_url = f"https://trello.com/b/{BOARD_ID}"
print(f"\nBoard ready: {board_url}")

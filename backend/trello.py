import os
import requests
from models import Card

TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
TRELLO_BOARD_ID = os.getenv("TRELLO_BOARD_ID")

BASE_URL = "https://api.trello.com/1"
AUTH = {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}


def get_lists() -> dict[str, str]:
    r = requests.get(
        f"{BASE_URL}/boards/{TRELLO_BOARD_ID}/lists",
        params={**AUTH, "fields": "id,name"},
    )
    r.raise_for_status()
    return {lst["id"]: lst["name"] for lst in r.json()}


def get_members() -> dict[str, str]:
    r = requests.get(
        f"{BASE_URL}/boards/{TRELLO_BOARD_ID}/members",
        params={**AUTH, "fields": "id,fullName"},
    )
    r.raise_for_status()
    return {m["id"]: m["fullName"] for m in r.json()}


def get_all_cards() -> list[Card]:
    list_mapping = get_lists()
    member_mapping = get_members()
    r = requests.get(
        f"{BASE_URL}/boards/{TRELLO_BOARD_ID}/cards",
        params={**AUTH, "fields": "id,name,desc,idList,idMembers,due,url"},
    )
    r.raise_for_status()
    cards = []
    for raw in r.json():
        member_id = raw["idMembers"][0] if raw["idMembers"] else None
        cards.append(
            Card(
                id=raw["id"],
                name=raw["name"],
                due=raw["due"],
                desc=raw["desc"],
                url=raw["url"],
                status=list_mapping.get(raw["idList"], "Unknown"),
                assignee=member_mapping.get(member_id) if member_id else None,
            )
        )
    return cards

import os
import requests
from datetime import datetime, timezone
from models import Card
from utils import iso_to_timestamp

TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
TRELLO_BOARD_ID = os.getenv("TRELLO_BOARD_ID")

BASE_URL = "https://api.trello.com/1"
AUTH = {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}


def get_lists() -> dict[str, str]:
    """
    Fetch all lists on the configured Trello board.

    Returns:
        Dictionary mapping list ID to list name.
    """
    r = requests.get(
        f"{BASE_URL}/boards/{TRELLO_BOARD_ID}/lists",
        params={**AUTH, "fields": "id,name"},
    )
    r.raise_for_status()
    return {lst["id"]: lst["name"] for lst in r.json()}


def get_members() -> dict[str, str]:
    """
    Fetch all members of the configured Trello board.

    Returns:
        Dictionary mapping member ID to full name.
    """
    r = requests.get(
        f"{BASE_URL}/boards/{TRELLO_BOARD_ID}/members",
        params={**AUTH, "fields": "id,fullName"},
    )
    r.raise_for_status()
    return {m["id"]: m["fullName"] for m in r.json()}


def get_all_cards() -> list[Card]:
    """
    Fetch all cards from the configured Trello board and return them as Card models.

    Returns:
        List of Card instances with metadata resolved from board lists and members.
    """
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
        assignee = member_mapping.get(member_id) if member_id else None
        cards.append(
            Card(
                id=raw["id"],
                name=raw["name"],
                due=iso_to_timestamp(raw["due"]),
                desc=raw["desc"],
                url=raw["url"],
                status=list_mapping.get(raw["idList"], "Unknown"),
                assignee=assignee,
                assignee_first_name=assignee.split()[0] if assignee else None,
                assignee_last_name=assignee.split()[-1] if assignee else None,
            )
        )
    return cards


def update_card(card: Card) -> Card:
    """
    Push updates for a card to Trello via the REST API.

    Args:
        card: Card instance with updated fields. Only non-None fields
            (status, assignee, due) are included in the payload.

    Returns:
        The same Card instance passed in, unchanged.

    Raises:
        ValueError: If the card's status or assignee does not match a known
            list name or board member.
        requests.HTTPError: If the Trello API returns a non-2xx response.
    """
    list_mapping = {name: id for id, name in get_lists().items()}
    member_mapping = {name.lower(): id for id, name in get_members().items()}

    payload = {}
    if card.status:
        if card.status not in list_mapping:
            raise ValueError(f"Unknown status: {card.status!r}")
        payload["idList"] = list_mapping[card.status]
    if card.assignee:
        assignee_lower = card.assignee.lower()
        if assignee_lower not in member_mapping:
            raise ValueError(f"Unknown assignee: {card.assignee!r}")
        payload["idMembers"] = [member_mapping[assignee_lower]]
    if card.due is not None:
        payload["due"] = datetime.fromtimestamp(card.due, tz=timezone.utc).isoformat()

    r = requests.put(
        f"{BASE_URL}/cards/{card.id}",
        params={**AUTH},
        headers={"Accept": "application/json"},
        json=payload,
    )
    r.raise_for_status()
    return card

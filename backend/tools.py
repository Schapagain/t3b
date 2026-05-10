from typing import Any
from ingest import re_index_db, get_last_synced_at, vector_search, upsert_cards
from models import Card
from services import get_collection
from utils import iso_to_timestamp, timestamp_to_date
from jsonschema import validate, ValidationError
from datetime import timedelta, datetime, timezone
from constants import COLLECTION_NAME, TRELLO_SYNC_TTL
from calendar_events import get_named_events
from trello import update_card


def exec_trello_sync(args: dict[str, Any]) -> dict[str, Any]:
    """
    Sync trello cards with ChromaDB

    Args:
        args: Empty dictionary as no parameters are needed.

    Returns:
        Dictionary with key 'result' with sync status message
    """
    last_synced_at = get_last_synced_at()
    if last_synced_at and datetime.now() - last_synced_at < TRELLO_SYNC_TTL:
        return {
            "result": f"Cards were recently fetched at {last_synced_at}. "
            "They do not need to be synced at the moment. Other operations can continue.",
            "skipped": True,
        }

    result = re_index_db()
    return {
        "result": f"Synced {result['cards_ingested']} cards into the database at {result['synced_at']}."
    }


def build_chroma_where(args: dict[str, Any]) -> dict:
    filters = []
    if args.get("assignee"):
        filters.append(
            {
                "$or": [
                    {"assignee": {"$eq": args["assignee"].lower()}},
                    {"assignee_first_name": {"$eq": args["assignee"].lower()}},
                    {"assignee_last_name": {"$eq": args["assignee"].lower()}},
                ]
            }
        )
    if args.get("status"):
        filters.append({"status": {"$eq": args["status"]}})
    if args.get("due_before"):
        filters.append({"due": {"$lte": iso_to_timestamp(args["due_before"])}})
    if args.get("due_after"):
        filters.append({"due": {"$gte": iso_to_timestamp(args["due_after"])}})
    if args.get("due_within"):
        window_filters = [
            {
                "$and": [
                    {"due": {"$gte": iso_to_timestamp(str(w["start"]))}},
                    {"due": {"$lt": iso_to_timestamp(str(w["end"]))}},
                ]
            }
            for w in args["due_within"]
        ]
        filters.append(
            {"$or": window_filters} if len(window_filters) > 1 else window_filters[0]
        )

    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


def exec_search_cards(args: dict[str, Any]) -> dict[str, Any]:
    """
    Search cards within ChromaDB

    Args:
        args: Dictionary with assignee, status, due_before, due_after
            and query keys. keys are optional and populated
            as required by the search.

    Returns:
        Dictionary with key 'result' for summary of the search, and
        key 'cards' for any cards that were found
    """
    collection = get_collection(COLLECTION_NAME)
    result = collection.get(
        where=build_chroma_where(args),
        include=["documents", "metadatas"],
    )
    cards = result.get("metadatas", [])

    if args["query"]:
        semantic_results = vector_search(args["query"], 2, cards)
        cards = [res[3] for res in semantic_results]

    summary = "\n".join(
        f"-  {card['name']} | id: {card['id']} | assignee: {card.get('assignee')} | due: {timestamp_to_date(card.get('due'))} | status: {card.get('status')}"
        for card in cards
    )
    return {
        "result": f"Found {len(cards)} matching cards (only show relevant data to the user - not everything):\n{summary}",
        "cards": cards,
    }


def exec_clock_now(args: dict[str, Any]) -> dict[str, Any]:
    """
    Get the current UTC time.

    Args:
        args: Empty dictionary as no params are needed.

    Returns:
        Dictionary with current UTC datetime.
    """
    now = datetime.now(timezone.utc)
    return {
        "result": f"Current ISO time: {now.isoformat()}. Formatted time: {now.strftime("%Y-%m-%d %H:%M:%S UTC")}"
    }


def exec_update_card(args: dict[str, Any]) -> dict[str, Any]:
    """
    Update card status, assignee or due date in Trello
    and upsert ChromaDB with updated information

    Args:
        args: Dictionary with card_id, assignee and status.
          Only card_id and one of assignee or status is required
          as needed for the update.

    Returns:
        Dictionary with key 'result' for update status, and
        key 'cards' with a list of one card if it was
        successfully updated
    """

    card_id = args["card_id"]
    assignee_name = args["assignee"]
    status = args["status"]
    due = args["due"]

    collection = get_collection(COLLECTION_NAME)
    result = collection.get(
        where={"id": {"$eq": card_id}},
        include=["metadatas"],
    )

    cards = result.get("metadatas", [])

    if not cards:
        raise ValueError(f"Card with id {card_id!r} not found")

    card_data = cards[0]
    assignee_update_msg = None
    status_update_msg = None
    due_update_msg = None
    if assignee_name is not None:
        card_data["assignee"] = assignee_name
        assignee_update_msg = f"new assignee: {assignee_name}"

    if status is not None:
        card_data["status"] = status
        status_update_msg = f"new status: {status}"

    if due is not None:
        card_data["due"] = iso_to_timestamp(due)
        due_update_msg = f"new due: {due}"

    card = Card(
        id=card_data["id"],
        name=card_data["name"],
        desc=card_data.get("desc", ""),
        due=card_data["due"] or None,
        url=card_data["url"],
        status=card_data["status"],
        assignee=card_data.get("assignee") or None,
        assignee_first_name=card_data.get("assignee_first_name") or None,
        assignee_last_name=card_data.get("assignee_last_name") or None,
    )

    updated_card = update_card(card)
    upsert_cards([card])

    return {
        "result": f"Card updated successfully. {assignee_update_msg} {status_update_msg} {due_update_msg}",
        "cards": [card_data],
    }


def exec_check_schedule_conflicts(args: dict[str, Any]) -> dict[str, Any]:
    """
    Check whether due dates for an assignee fall within their vacation window(s)

    Args:
        args: Dictionary with assignee, status, due_before, due_after.
            Only assignee is required. The rest are optional and populated
            as required to narrow down the cards of interest.

    Returns:
        Dictionary with key 'result' for summary of the conflict check, and
        key 'cards' for any cards' whose due dates conflict
        with vacation window(s)
    """

    assignee = args["assignee"]
    if not assignee:
        raise ValidationError("Assignee is required to check schedule conflicts")

    assignee_first_name = assignee.split()[0] if " " in assignee else assignee
    all_ooo_events = get_named_events(assignee_first_name + " OOO")

    # No OOO events found in the calendar, so nothing can conflict
    if not all_ooo_events:
        return {
            "result": "No OOO events found for this assignee. No conflicts exist.",
        }

    collection = get_collection(COLLECTION_NAME)
    result = collection.get(
        where=build_chroma_where({**args, "due_within": all_ooo_events}),
        include=["documents", "metadatas"],
    )
    cards = result.get("metadatas", [])

    summary = "\n".join(
        f"- {card['name']} | assignee: {card.get('assignee')} | due: {timestamp_to_date(card.get('due'))} | status: {card.get('status')}"
        for card in cards
    )
    return {
        "result": f"Found {len(cards)} conflicting cards (only show relevant data to the user - not everything):\n{summary}",
        "cards": cards,
    }


def validate_tool_args(tool_name: str, args: dict[str, Any]) -> None:
    """
    Validate tool arguments against the tool's JSON Schema.

    Args:
        tool_name: Name of the tool.
        args: Arguments to validate.

    Raises:
        ValidationError: If arguments don't match the schema.
        KeyError: If tool name is not recognized.
    """
    if tool_name not in TOOL_SCHEMAS:
        raise KeyError(f"Unknown tool: {tool_name}")

    schema = TOOL_SCHEMAS[tool_name]
    validate(instance=args, schema=schema)


def execute_tool(
    tool_name: str, args: dict[str, Any]
) -> list[dict[str, Any], list[Any]]:
    """
    Validate and execute a tool.

    Args:
        tool_name: Name of the tool to execute.
        args: Arguments for the tool.

    Returns:
        Tool execution result as a dictionary.

    Raises:
        ValidationError: If arguments are invalid.
        KeyError: If tool is not recognized.
    """
    # Validate arguments before execution
    validate_tool_args(tool_name, args)

    print(f"Executing tool: {tool_name} with args: {args}")
    # Get and execute the tool
    if tool_name not in TOOL_EXECUTORS:
        raise KeyError(f"No executor found for tool: {tool_name}")

    executor = TOOL_EXECUTORS[tool_name]
    return executor(args)


def tool_requires_approval(tool_name: str) -> bool:
    return tool_name == "update_card"


TOOL_CLOCK_NOW = {
    "type": "function",
    "function": {
        "name": "clock_now",
        "description": "Get the current date and time in UTC. Use this tool to get the current timestamp."
        "ALWAYS use this tool before performing any date operations, "
        "but do not use if explicity date/time calculation is not needed",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
}

TOOL_TRELLO_SYNC = {
    "type": "function",
    "function": {
        "name": "trello_sync",
        "description": "Fetch all cards from Trello to re-index ChromaDB.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
}

TOOL_CHECK_SCHEDULE_CONFLICTS = {
    "type": "function",
    "function": {
        "name": "check_schedule_conflicts",
        "description": (
            "Check whether any Trello cards are due on dates when an assignee has "
            "OOO calendar events. Name of the assignee is required. Other parameters can be"
            "provided as necessary if there is a need to narrow the time window or card statuses"
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "assignee": {
                    "type": "string",
                    "description": "Name of the assignee."
                    "Can either be first/last name or the full name",
                },
                "status": {
                    "type": ["string", "null"],
                    "description": "Card status by which to filter.",
                    "enum": [
                        "Triage",
                        "In Progress",
                        "In Review",
                        None,
                    ],
                },
                "due_before": {
                    "type": ["string", "null"],
                    "description": "Return cards that are due before this date,"
                    "in ISO 8601 format.",
                },
                "due_after": {
                    "type": ["string", "null"],
                    "description": "Return cards that are due after this date,"
                    "in ISO 8601 format.",
                },
            },
            "required": ["assignee", "status", "due_before", "due_after"],
            "additionalProperties": False,
        },
    },
}

TOOL_SEARCH_CARDS = {
    "type": "function",
    "function": {
        "name": "search_cards",
        "description": "Search the database for matching cards using"
        "metadata fields: assignee, due, status. Only include"
        "the filters that are relevant to the user query. The metadata fields "
        "are first applied with an AND operator, and then "
        "the string query is used for vector/bm25 search.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "assignee": {
                    "type": ["string", "null"],
                    "description": "Name of the assignee."
                    "Can either be first/last name or the full name",
                },
                "status": {
                    "type": ["string", "null"],
                    "description": "Card status by which to filter.",
                    "enum": [
                        "Backlog",
                        "Triage",
                        "In Progress",
                        "In Review",
                        "Done",
                        None,
                    ],
                },
                "due_before": {
                    "type": ["string", "null"],
                    "description": "Return cards that are due before this date,"
                    "in ISO 8601 format.",
                },
                "due_after": {
                    "type": ["string", "null"],
                    "description": "Return cards that are due after this date,"
                    "in ISO 8601 format.",
                },
                "query": {
                    "type": ["string", "null"],
                    "description": "Semantic search query to find cards by similarity",
                },
            },
            "required": ["assignee", "status", "due_before", "due_after", "query"],
            "additionalProperties": False,
        },
    },
}

TOOL_UPDATE_CARD = {
    "type": "function",
    "function": {
        "name": "update_card",
        "description": "Update a card. Only include fields that you want to change. "
        "DO NOT include fields that would stay the same after the update, except for the id",
        "parameters": {
            "type": "object",
            "properties": {
                "card_id": {
                    "type": "string",
                    "description": "The card ID to update. This must be the exact id "
                    "from a prior tool call and never inferred or invented",
                },
                "due": {
                    "type": ["string", "null"],
                    "description": "New due date in ISO 8601 format (e.g. 2026-04-28T23:59:00.000Z)",
                },
                "status": {
                    "type": ["string", "null"],
                    "description": "New status of the card (Trello list)",
                    "enum": [
                        "Backlog",
                        "Triage",
                        "In Progress",
                        "In Review",
                        "Done",
                        None,
                    ],
                },
                "assignee": {
                    "type": ["string", "null"],
                    "description": "Full name of the new assignee.",
                },
            },
            "required": ["card_id", "due", "status", "assignee"],
        },
    },
}


# Map tool names to their executors
TOOL_EXECUTORS = {
    "trello_sync": exec_trello_sync,
    "search_cards": exec_search_cards,
    "clock_now": exec_clock_now,
    "update_card": exec_update_card,
    "check_schedule_conflicts": exec_check_schedule_conflicts,
}

# Map tool names to their parameter schemas (for validation)
TOOL_SCHEMAS = {
    "trello_sync": TOOL_TRELLO_SYNC["function"]["parameters"],
    "search_cards": TOOL_SEARCH_CARDS["function"]["parameters"],
    "clock_now": TOOL_CLOCK_NOW["function"]["parameters"],
    "check_schedule_conflicts": TOOL_CHECK_SCHEDULE_CONFLICTS["function"]["parameters"],
    "update_card": TOOL_UPDATE_CARD["function"]["parameters"],
}

TOOLS = [
    TOOL_TRELLO_SYNC,
    TOOL_SEARCH_CARDS,
    TOOL_CLOCK_NOW,
    TOOL_CHECK_SCHEDULE_CONFLICTS,
    TOOL_UPDATE_CARD,
]

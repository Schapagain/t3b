from typing import Any
from ingest import re_index_db, get_last_synced_at, vector_search
from services import get_collection
from utils import iso_to_timestamp, timestamp_to_date
from jsonschema import validate, ValidationError
from datetime import timedelta, datetime, timezone
from constants import COLLECTION_NAME, TRELLO_SYNC_TTL
from calendar_events import get_named_events


def exec_trello_sync(args: dict[str, Any]) -> dict[str, Any]:
    """
    Sync trello cards with ChromaDB

    Args:
        args: Empty dictionary as no parameters are needed.

    Returns:
        Text with number of cards synced successfully
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
        List of cards matched by the given metadata filters or query
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
        f"- {card['name']} | assignee: {card.get('assignee')} | due: {timestamp_to_date(card.get('due'))} | status: {card.get('status')}"
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


# def exec_update_card(args: dict[str, Any]) -> dict[str, Any]:
#     """
#     Update card in Trello, and trigger a re-index of
#     ChromaDB if title or description was updated

#     Args:
#         args: Dictionary with name, description, assignee,
#         status, and due. Keys are optional and populated
#             as required for an updated.

#     Returns:
#         List of fields that were updated.
#     """
#     collection = get_collection(COLLECTION_NAME)
#     result = collection.get(
#         where=build_chroma_where(args),
#         include=["documents", "metadatas"],
#     )
#     cards = result.get("metadatas", [])

#     if args["query"]:
#         semantic_results = vector_search(args["query"], 2, cards)
#         cards = [res[3] for res in semantic_results]

#     summary = "\n".join(
#         f"- {card['name']} | assignee: {card.get('assignee')} | due: {timestamp_to_date(card.get('due'))} | status: {card.get('status')}"
#         for card in cards
#     )
#     return {
#         "result": f"Found {len(cards)} matching cards:\n{summary}",
#         "cards": cards,
#     }


def exec_check_schedule_conflicts(args: dict[str, Any]) -> dict[str, Any]:
    """
    Check whether due dates for an assignee fall within their vacation window(s)

    Args:
        args: Dictionary with assignee, status, due_before, due_after.
            Only assignee is required. The rest are optional and populated
            as required to narrow down the cards of interest.

    Returns:
        List of cards whose due dates conflict with vacation window(s)
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

# TOOL_TRELLO_UPDATE_CARD = {
#     "type": "function",
#     "function": {
#         "name": "trello_update_card",
#         "description": "Update a Trello card's fields. Only include fields you want to change.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "card_id": {
#                     "type": "string",
#                     "description": "The Trello card ID to update",
#                 },
#                 "name": {
#                     "type": ["string", "null"],
#                     "description": "New title for the card",
#                 },
#                 "desc": {
#                     "type": ["string", "null"],
#                     "description": "New description for the card",
#                 },
#                 "due": {
#                     "type": ["string", "null"],
#                     "description": "New due date in ISO 8601 format (e.g. 2026-04-28T23:59:00.000Z)",
#                 },
#                 "status": {
#                     "type": ["string", "null"],
#                     "description": "Current status of the card (Trello list)",
#                     "enum": [
#                         "Backlog",
#                         "Triage",
#                         "In Progress",
#                         "In Review",
#                         "Done",
#                         None,
#                     ],
#                 },
#                 "assignee": {
#                     "type": ["string", "null"],
#                     "description": "Full name of the new assignee."
#                     "Full name of the assignee",
#                 },
#             },
#             "required": ["card_id", "name", "desc", "due", "status"],
#         },
#     },
# }


# Map tool names to their executors
TOOL_EXECUTORS = {
    "trello_sync": exec_trello_sync,
    "search_cards": exec_search_cards,
    "clock_now": exec_clock_now,
    # "update_card": exec_update_card,
    "check_schedule_conflicts": exec_check_schedule_conflicts,
}

# Map tool names to their parameter schemas (for validation)
TOOL_SCHEMAS = {
    "trello_sync": TOOL_TRELLO_SYNC["function"]["parameters"],
    "search_cards": TOOL_SEARCH_CARDS["function"]["parameters"],
    "clock_now": TOOL_CLOCK_NOW["function"]["parameters"],
    "check_schedule_conflicts": TOOL_CHECK_SCHEDULE_CONFLICTS["function"]["parameters"],
}

TOOLS = [
    TOOL_TRELLO_SYNC,
    TOOL_SEARCH_CARDS,
    TOOL_CLOCK_NOW,
    TOOL_CHECK_SCHEDULE_CONFLICTS,
]

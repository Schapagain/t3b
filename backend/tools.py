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
        "name": "check_scheduling_conflicts",
        "description": (
            "Check whether any Trello cards are due on dates when an assignee has "
            "OOO calendar events. Accepts a list of date windows to check so "
            "non-contiguous periods (e.g. Tuesday and Thursday of next week) can "
            "be evaluated in a single call."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "assignee": {
                    "type": ["string", "null"],
                    "description": "Name of the assignee to check. Can be first, last, or full name. Null to check all assignees.",
                },
                "windows": {
                    "type": "array",
                    "description": "List of date windows to check for conflicts. Use multiple windows for non-contiguous periods.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {
                                "type": "string",
                                "description": "Start of the window in ISO 8601 format (inclusive).",
                            },
                            "end": {
                                "type": "string",
                                "description": "End of the window in ISO 8601 format (inclusive).",
                            },
                        },
                        "required": ["start", "end"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["assignee", "windows"],
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
#                 "name": {"type": "string", "description": "New title for the card"},
#                 "desc": {
#                     "type": "string",
#                     "description": "New description for the card",
#                 },
#                 "due": {
#                     "type": "string",
#                     "description": "New due date in ISO 8601 format (e.g. 2026-04-28T23:59:00.000Z)",
#                 },
#             },
#             "required": ["card_id"],
#         },
#     },
# }

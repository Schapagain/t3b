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

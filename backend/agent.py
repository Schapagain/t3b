import json
from services import get_openai_client, get_collection
from ingest import re_index_db, get_last_synced_at, vector_search
from utils import iso_to_timestamp, timestamp_to_date
from tools import TOOL_TRELLO_SYNC, TOOL_SEARCH_CARDS, TOOL_CLOCK_NOW
from models import ChatMessage, Card
from jsonschema import validate, ValidationError
from typing import Any
from datetime import timedelta, datetime, timezone
from constants import (
    TRELLO_SYNC_TTL,
    MAX_AGENT_ITERATIONS,
    OPENAI_CHAT_MODEL,
    COLLECTION_NAME,
)


TOOLS = [TOOL_TRELLO_SYNC, TOOL_SEARCH_CARDS, TOOL_CLOCK_NOW]


def build_system_prompt() -> str:
    last_synced = get_last_synced_at()
    return f"""You are T3B, an assistant that helps engineering teams manage their Trello boards.
You can search for cards, detect duplicates, identify scheduling conflicts, and update cards. 
IMPORTANT - Do not reveal raw tool results to the user. 
Cards were last synced on: {last_synced.isoformat() if last_synced else "never"}
Here are the tools available to you:
- clock_now: Use this tool to get the current timestamp. ALWAYS use this tool before performing any date operations, 
but do not use if explicity date/time calculation is not needed
- trello_sync: Use this tool only if the user explicitly asks for their cards to be synced, 
or if the cards were synced more than 30 minutes ago. Do not attempt to use this tool if re-sync is not needed.
- search_cards: Use this tool to search for cards matching filter criteria or against a semantic query. 

Response Instructions:
- Always be concise and specific in your responses
- NEVER respond to queries not relevant to your role as T3B (very important)
- Your responses MUST be in plain text and should not include any raw objects like jsons and arrays, or any markdown syntax
- Do not use any dates in other tools without first calling clock_now at least once during a session
"""


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
        "result": f"Found {len(cards)} matching cards:\n{summary}",
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


# Map tool names to their executors
TOOL_EXECUTORS = {
    "trello_sync": exec_trello_sync,
    "search_cards": exec_search_cards,
    "clock_now": exec_clock_now,
}

# Map tool names to their parameter schemas (for validation)
TOOL_SCHEMAS = {
    "trello_sync": TOOL_TRELLO_SYNC["function"]["parameters"],
    "search_cards": TOOL_SEARCH_CARDS["function"]["parameters"],
    "clock_now": TOOL_CLOCK_NOW["function"]["parameters"],
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
    # Validate arguments before execution (DO NOT REMOVE)
    validate_tool_args(tool_name, args)

    print(f"Executing tool: {tool_name} with args: {args}")
    # Get and execute the tool
    if tool_name not in TOOL_EXECUTORS:
        raise KeyError(f"No executor found for tool: {tool_name}")

    executor = TOOL_EXECUTORS[tool_name]
    return executor(args)


def run_agent(message_history: list[ChatMessage]) -> tuple[str, list[str]]:
    client = get_openai_client()
    messages = [{"role": "system", "content": build_system_prompt()}]

    messages += [m.model_dump() for m in message_history]

    tool_calls_used = []
    cards_found = []
    found_card_ids = set()

    for _ in range(MAX_AGENT_ITERATIONS):
        response = client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            tools=TOOLS,
            messages=messages,
        )
        msg = response.choices[0].message

        print(f"OPENAI MSG:\n{msg}")

        if not msg.tool_calls:
            return msg.content, tool_calls_used, cards_found

        messages.append(msg)
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)

            try:
                result = execute_tool(name, args)

                if not result.get("skipped", False) and not name in tool_calls_used:
                    tool_calls_used.append(name)
                cards_from_tool = result.get("cards", [])
                cards_found.extend(cards_from_tool)
                found_card_ids.update(map(lambda card: card["id"], cards_found))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result.get("result", "")),
                    }
                )
                print(
                    "Tool executed:\n",
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result.get("result", "")),
                    },
                )
            except ValidationError as e:
                print(f"[Error] Validation failed: {e.message}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(
                            {"error": f"Validation failed: {e.message}"}
                        ),
                    }
                )
            except KeyError as e:
                print(f"[Error] Tool not recognized: {str(e)}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(
                            {"error": f"Tool not recognized: {str(e)}"}
                        ),
                    }
                )
            except Exception as e:
                print(f"[Error] Tool execution failed: {e}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({"error": str(e)}),
                    }
                )

    messages.append(
        {
            "role": "system",
            "content": "Max tool iterations have been reached, and you may not use any tools anymore unless the user sends futher instructions."
            "Create a response for the user with whatever information you were able to gather up to this point, and let the user know what was incomplete.",
        }
    )
    response = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        tools=TOOLS,
        messages=messages,
    )
    msg = response.choices[0].message
    return msg.content, tool_calls_used, cards_found

import json
from services import get_openai_client
from ingest import re_index_db
from tools import TOOL_TRELLO_SYNC
from models import ChatMessage
from jsonschema import validate, ValidationError
from typing import Any

MODEL = "gpt-4o-mini"
TOOLS = [TOOL_TRELLO_SYNC]
SYSTEM_PROMPT = """You are T3B, an assistant that helps engineering teams manage their Trello boards.
You can search for cards, detect duplicates, identify scheduling conflicts, and update cards.
When the user asks to refresh or sync the board, use the trello_sync tool.
Always be concise and specific in your responses."""


def exec_trello_sync(args: dict[str, Any]) -> dict[str, Any]:
    """
    Sync trello cards with ChromaDB

    Args:
        args: Empty dictionary as no parameters are needed.

    Returns:
        Text with number of cards synced successfully
    """
    result = re_index_db()
    return f"Synced {result['cards_ingested']} cards into the database."


# Map tool names to their executors
TOOL_EXECUTORS = {
    "trello_sync": exec_trello_sync,
}

# Map tool names to their parameter schemas (for validation)
TOOL_SCHEMAS = {
    "trello_sync": TOOL_TRELLO_SYNC["function"]["parameters"],
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


def execute_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
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
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [m.model_dump() for m in message_history]

    tool_calls_used = []

    while True:
        response = client.chat.completions.create(
            model=MODEL,
            tools=TOOLS,
            messages=messages,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content, tool_calls_used

        messages.append(msg)
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            tool_calls_used.append(name)
            result = execute_tool(name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

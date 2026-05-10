import json
from services import get_async_openai_client, get_collection
from ingest import get_last_synced_at
from tools import TOOLS, execute_tool, tool_requires_approval
from models import Card
from constants import COLLECTION_NAME
from jsonschema import ValidationError
from typing import Any, AsyncGenerator

from constants import (
    MAX_AGENT_ITERATIONS,
    OPENAI_CHAT_MODEL,
)


def build_system_prompt() -> str:
    """
    Build the system prompt for the agent, including the last sync time.

    Returns:
        System prompt string with tool descriptions and response instructions.
    """
    last_synced = get_last_synced_at()
    return f"""You are T3B, an assistant that helps engineering teams manage their Trello boards.
You can search for cards, detect duplicates, identify scheduling conflicts, and update cards. 
IMPORTANT - Do not reveal raw tool results to the user and ALWAYS use plain text to respond - not markdown, json, HTML, etc.
Cards were last synced on: {last_synced.isoformat() if last_synced else "never"}
Here are the tools available to you:
- clock_now: Use this tool to get the current timestamp. ALWAYS use this tool before performing any date operations, 
but do not use if explicity date/time calculation is not needed
- trello_sync: Use this tool only if the user explicitly asks for their cards to be synced, 
or if the cards were synced more than 30 minutes ago. Do not attempt to use this tool if re-sync is not needed.
- search_cards: Use this tool to search for cards matching filter criteria or against a semantic query. 
- update_card: Use this tool to update card status, assignee, due date in Trello.
IMPORTANT: You MUST call search_cards first to obtain the card's exact ID before calling update_card. Never invent or infer a card ID.

If the user rejects a tool call, ask the user what their intent is before calling any more tools.

Response Instructions:
- Always be concise and specific in your responses
- NEVER respond to queries not relevant to your role as T3B (very important)
- Your responses MUST be in plain text and should not include any raw objects like jsons and arrays, or any markdown syntax
- Do not use any dates in other tools without first calling clock_now at least once during a session
"""


def _lookup_card(card_id: str) -> dict | None:
    """
    Look up a card's metadata from ChromaDB by its Trello card ID.

    Args:
        card_id: The Trello card ID to look up.

    Returns:
        Card metadata dict if found, None otherwise.
    """
    result = get_collection(COLLECTION_NAME).get(
        where={"id": {"$eq": card_id}}, include=["metadatas"]
    )
    cards = result.get("metadatas", [])
    return cards[0] if cards else None


def _tc_fields(tc) -> tuple[str, str, dict]:
    """
    Extract (id, name, args) from a tool call regardless of its representation.

    Handles both OpenAI SDK objects (from live completions) and plain dicts
    (from deserialized pending messages restored across the approval pause).

    Args:
        tc: A tool call object or dict.

    Returns:
        Tuple of (tool_call_id, function_name, parsed_arguments_dict).
    """
    if isinstance(tc, dict):
        return tc["id"], tc["function"]["name"], json.loads(tc["function"]["arguments"])
    return tc.id, tc.function.name, json.loads(tc.function.arguments)


async def run_agent(
    message_history: list[dict],
    approved_tools: list[str],
    pending_msg: dict | None = None,
    prior_tool_calls_used: list[str] | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Run the agentic tool-calling loop and yield typed events as work happens.

    Yields events of type: tool_called, tool_finished, tool_skipped,
    tool_failed, tool_approval_required, and final_response. If pending_msg
    is provided, the first LLM call is skipped and execution resumes directly
    from the saved tool calls (used after human approval of update_card).

    Args:
        message_history: Full conversation history excluding the system prompt.
        approved_tools: Tool names that have been approved for execution in
            this request.
        pending_msg: Saved assistant message dict from a paused approval flow.
            When provided, the loop resumes from its tool calls without an
            extra LLM call.
        prior_tool_calls_used: Tool names already used before the approval
            pause, carried forward so the final response includes them.

    Yields:
        Dicts with a 'type' key and a 'content' key (plus extra keys for
        tool_approval_required).
    """
    client = get_async_openai_client()
    messages = [{"role": "system", "content": build_system_prompt()}]

    messages += message_history

    tool_calls_used = list(prior_tool_calls_used) if prior_tool_calls_used else []
    cards_by_id = {}

    for _ in range(MAX_AGENT_ITERATIONS):
        if pending_msg:
            msg_dict = pending_msg
            pending_msg = None
            tool_calls = msg_dict["tool_calls"]
            messages.append(msg_dict)
        else:
            response = await client.chat.completions.create(
                model=OPENAI_CHAT_MODEL,
                tools=TOOLS,
                messages=messages,
            )
            msg = response.choices[0].message
            print(f"OPENAI MSG:\n{msg}")

            if not msg.tool_calls:
                yield {
                    "type": "final_response",
                    "content": {
                        "message": msg.content,
                        "tool_calls_used": tool_calls_used,
                        "cards": list(cards_by_id.values()),
                        "history": messages[1:],
                    },
                }
                return

            messages.append(msg.model_dump(exclude_none=True))
            tool_calls = msg.tool_calls

        for tc in tool_calls:
            tc_id, name, args = _tc_fields(tc)

            if tool_requires_approval(name) and name not in approved_tools:
                print(
                    f'TOOL APPROVAL REQUIRED:\n\nTool name:{name}\n\ncard: {cards_by_id.get(args["card_id"])}'
                )
                yield (
                    {
                        "type": "tool_approval_required",
                        "content": {
                            "name": name,
                            "args": args,
                            "card": cards_by_id.get(args["card_id"])
                            or _lookup_card(args["card_id"]),
                        },
                        "pending_msg": messages[-1],
                        "tool_calls_used": tool_calls_used,
                    }
                )
                return

            yield ({"type": "tool_called", "content": {"name": name}})

            try:
                result = execute_tool(name, args)

                # Only allow approval to last for one execution
                if name in approved_tools:
                    approved_tools.remove(name)

                if result.get("skipped", False):
                    yield ({"type": "tool_skipped", "content": {"name": name}})
                if not result.get("skipped", False) and not name in tool_calls_used:
                    tool_calls_used.append(name)
                yield ({"type": "tool_finished", "content": {"name": name}})
                cards_from_tool = result.get("cards", [])
                cards_by_id.update({card["id"]: card for card in cards_from_tool})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": json.dumps(result.get("result", "")),
                    }
                )
                print(
                    "Tool executed:\n",
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": json.dumps(result.get("result", "")),
                    },
                )
            except ValidationError as e:
                print(f"[Error] Validation failed: {e.message}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
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
                        "tool_call_id": tc_id,
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
                        "tool_call_id": tc_id,
                        "content": json.dumps({"error": str(e)}),
                    }
                )
                yield {"type": "tool_failed", "content": {"name": name}}

    messages.append(
        {
            "role": "system",
            "content": "Max tool iterations have been reached, and you may not use any tools anymore unless the user sends further instructions."
            "Create a response for the user with whatever information you were able to gather up to this point, and let the user know what was incomplete.",
        }
    )
    response = await client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        tools=TOOLS,
        messages=messages,
    )
    msg = response.choices[0].message
    yield {
        "type": "final_response",
        "content": {
            "message": msg.content,
            "tool_calls_used": tool_calls_used,
            "cards": list(cards_by_id.values()),
            "history": messages[1:],
        },
    }
    return

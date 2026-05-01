import json
from services import get_openai_client
from ingest import get_last_synced_at
from tools import TOOLS, execute_tool
from models import ChatMessage, Card
from jsonschema import ValidationError
from typing import Any

from constants import (
    MAX_AGENT_ITERATIONS,
    OPENAI_CHAT_MODEL,
)


def build_system_prompt() -> str:
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

Response Instructions:
- Always be concise and specific in your responses
- NEVER respond to queries not relevant to your role as T3B (very important)
- Your responses MUST be in plain text and should not include any raw objects like jsons and arrays, or any markdown syntax
- Do not use any dates in other tools without first calling clock_now at least once during a session
"""


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
                cards_found.extend(
                    filter(
                        lambda card: card["id"] not in found_card_ids, cards_from_tool
                    )
                )
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

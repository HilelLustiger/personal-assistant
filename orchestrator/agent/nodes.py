"""LangGraph node functions: call_model, call_tools."""

import json
import os

import litellm
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from tools import ALL_TOOLS

from agent.state import ConversationState

_MODEL = os.environ.get("GROQ_MODEL", "groq/llama-3.3-70b-versatile")
_SYSTEM_PROMPT = (
    "You are a personal assistant that helps manage tasks, habits,"
    " goals, and reminders."
    " Use the provided tools to fulfil the user's requests."
    " After any tool call, summarise the result in a friendly, concise message"
    " — never return raw JSON."
    " Always respond in Hebrew, regardless of the language the user writes in."
)
_TOOLS_SCHEMA = [convert_to_openai_tool(t) for t in ALL_TOOLS]
_TOOL_MAP = {t.name: t for t in ALL_TOOLS}


def _to_litellm_messages(messages: list) -> list[dict]:
    result = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for message in messages:
        if message.type == "human":
            result.append({"role": "user", "content": message.content})
        elif message.type == "ai":
            entry: dict = {"role": "assistant", "content": message.content or ""}
            if message.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["args"]),
                        },
                    }
                    for tc in message.tool_calls
                ]
            result.append(entry)
        elif message.type == "tool":
            result.append(
                {
                    "role": "tool",
                    "content": str(message.content),
                    "tool_call_id": message.tool_call_id,
                }
            )
    return result


async def call_model(state: ConversationState) -> dict:
    messages = _to_litellm_messages(state["messages"])
    response = await litellm.acompletion(
        model=_MODEL,
        messages=messages,
        tools=_TOOLS_SCHEMA,
        tool_choice="auto",
    )
    raw = response.choices[0].message
    tool_calls = []
    if raw.tool_calls:
        tool_calls = [
            {
                "name": tc.function.name,
                "args": json.loads(tc.function.arguments),
                "id": tc.id,
                "type": "tool_call",
            }
            for tc in raw.tool_calls
        ]
    return {"messages": [AIMessage(content=raw.content or "", tool_calls=tool_calls)]}


async def call_tools(state: ConversationState) -> dict:
    last_message = state["messages"][-1]
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool = _TOOL_MAP.get(tool_call["name"])
        if tool is None:
            content = f"Unknown tool: {tool_call['name']}"
        else:
            try:
                result = await tool.ainvoke(tool_call["args"])
                content = json.dumps(result) if not isinstance(result, str) else result
            except Exception as exc:
                content = f"Error calling {tool_call['name']}: {exc}"
        tool_messages.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))
    return {"messages": tool_messages}

"""T07 — LangGraph agent: graph + state persistence."""

import json
import os

os.environ.setdefault("TASKS_SERVICE_URL", "http://tasks-service:8001")
os.environ.setdefault("GROQ_API_KEY", "test-key")

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from agent.graph import build_graph
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from tools.tasks_tool import TASKS_SERVICE_URL

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_tool_call_response(
    tool_name: str, tool_args: dict, call_id: str = "call_001"
):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(tool_args)

    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_text_response(text: str):
    msg = MagicMock()
    msg.content = text
    msg.tool_calls = None

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


BASE = TASKS_SERVICE_URL


# ── AC: 'add task: buy milk' → POST /tasks ────────────────────────────────────


@pytest.mark.asyncio
async def test_create_task_calls_tasks_service():
    task_response = {
        "id": "aaaa-aaaa-aaaa-aaaa",
        "title": "buy milk",
        "due_datetime": None,
        "goal_id": None,
        "completed_at": None,
        "created_at": "2026-06-25T10:00:00",
    }
    llm_side_effects = [
        _make_tool_call_response("create_task", {"title": "buy milk"}),
        _make_text_response("Done! I've added 'buy milk' to your task list."),
    ]

    graph = build_graph()
    config = _make_config("test-create-task")

    with patch(
        "agent.nodes.litellm.acompletion", AsyncMock(side_effect=llm_side_effects)
    ):
        with respx.mock(base_url=BASE) as mock:
            route = mock.post("/tasks").mock(
                return_value=httpx.Response(201, json=task_response)
            )

            result = await graph.ainvoke(
                {"messages": [HumanMessage("add task: buy milk")]},
                config,
            )

            assert route.called
            body = json.loads(mock.calls[0].request.content)
            assert body["title"] == "buy milk"

    assert isinstance(result["messages"][-1].content, str)
    assert result["messages"][-1].content != ""


# ── AC: 'show my open tasks' → GET /tasks?completed=false ────────────────────


@pytest.mark.asyncio
async def test_list_open_tasks_sends_correct_query():
    tasks_response = [
        {
            "id": "bbbb-bbbb-bbbb-bbbb",
            "title": "buy milk",
            "due_datetime": None,
            "goal_id": None,
            "completed_at": None,
            "created_at": "2026-06-25T10:00:00",
        }
    ]
    llm_side_effects = [
        _make_tool_call_response("list_tasks", {"completed": False}),
        _make_text_response("You have 1 open task: buy milk."),
    ]

    graph = build_graph()
    config = _make_config("test-list-tasks")

    with patch(
        "agent.nodes.litellm.acompletion", AsyncMock(side_effect=llm_side_effects)
    ):
        with respx.mock(base_url=BASE) as mock:
            route = mock.get("/tasks").mock(
                return_value=httpx.Response(200, json=tasks_response)
            )

            result = await graph.ainvoke(
                {"messages": [HumanMessage("show my open tasks")]},
                config,
            )

            assert route.called
            params = dict(mock.calls[0].request.url.params)
            assert params.get("completed") == "false"

    assert "You have 1 open task" in result["messages"][-1].content


# ── AC: two sequential messages share state via checkpointer ─────────────────


@pytest.mark.asyncio
async def test_sequential_messages_share_state():
    """Second message can see the history from the first message."""
    tasks_response = [
        {
            "id": "cccc-cccc-cccc-cccc",
            "title": "call doctor",
            "due_datetime": None,
            "goal_id": None,
            "completed_at": None,
            "created_at": "2026-06-25T10:00:00",
        }
    ]
    first_turn_effects = [
        _make_tool_call_response("list_tasks", {"completed": False}),
        _make_text_response("You have 1 open task: call doctor."),
    ]
    second_turn_effects = [
        _make_text_response(
            "Yes, I remember — I listed your tasks just now. call doctor is still open."
        ),
    ]

    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = _make_config("test-sequential")

    with patch(
        "agent.nodes.litellm.acompletion", AsyncMock(side_effect=first_turn_effects)
    ):
        with respx.mock(base_url=BASE) as mock:
            mock.get("/tasks").mock(
                return_value=httpx.Response(200, json=tasks_response)
            )
            await graph.ainvoke(
                {"messages": [HumanMessage("show my open tasks")]},
                config,
            )

    with patch(
        "agent.nodes.litellm.acompletion", AsyncMock(side_effect=second_turn_effects)
    ) as mock_llm:
        result = await graph.ainvoke(
            {"messages": [HumanMessage("do you remember what you said?")]},
            config,
        )

    call_args = mock_llm.call_args
    messages_sent = call_args.kwargs.get("messages") or call_args.args[0]
    roles = [m["role"] for m in messages_sent]
    assert "assistant" in roles, "prior AI turn should be in message history"
    assert result["messages"][-1].content != ""


# ── AC: agent returns formatted reply string, not raw JSON ───────────────────


@pytest.mark.asyncio
async def test_reply_is_human_readable_string():
    task_response = {
        "id": "dddd-dddd-dddd-dddd",
        "title": "dentist appointment",
        "due_datetime": None,
        "goal_id": None,
        "completed_at": None,
        "created_at": "2026-06-25T10:00:00",
    }
    llm_side_effects = [
        _make_tool_call_response("create_task", {"title": "dentist appointment"}),
        _make_text_response("Added! 'Dentist appointment' is now on your task list."),
    ]

    graph = build_graph()
    config = _make_config("test-reply-format")

    with patch(
        "agent.nodes.litellm.acompletion", AsyncMock(side_effect=llm_side_effects)
    ):
        with respx.mock(base_url=BASE) as mock:
            mock.post("/tasks").mock(
                return_value=httpx.Response(201, json=task_response)
            )
            result = await graph.ainvoke(
                {"messages": [HumanMessage("add dentist appointment")]},
                config,
            )

    reply = result["messages"][-1].content
    assert isinstance(reply, str)
    try:
        json.loads(reply)
        is_json = True
    except (json.JSONDecodeError, TypeError):
        is_json = False
    assert not is_json, f"reply should not be raw JSON, got: {reply!r}"


# ── AC: complete_task routes to correct endpoint ──────────────────────────────


@pytest.mark.asyncio
async def test_complete_task_routes_to_correct_endpoint():
    task_id = "eeee-eeee-eeee-eeee"
    task_response = {
        "id": task_id,
        "title": "buy milk",
        "due_datetime": None,
        "goal_id": None,
        "completed_at": "2026-06-25T12:00:00",
        "created_at": "2026-06-25T10:00:00",
    }
    llm_side_effects = [
        _make_tool_call_response("complete_task", {"task_id": task_id}),
        _make_text_response("Great job! I've marked 'buy milk' as complete."),
    ]

    graph = build_graph()
    config = _make_config("test-complete-task")

    with patch(
        "agent.nodes.litellm.acompletion", AsyncMock(side_effect=llm_side_effects)
    ):
        with respx.mock(base_url=BASE) as mock:
            route = mock.post(f"/tasks/{task_id}/complete").mock(
                return_value=httpx.Response(200, json=task_response)
            )

            result = await graph.ainvoke(
                {"messages": [HumanMessage(f"complete task {task_id}")]},
                config,
            )

            assert route.called

    content = result["messages"][-1].content
    assert "complete" in content.lower() or "great" in content.lower()


# ── AC: create_reminder tool works ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_reminder_calls_correct_endpoint():
    reminder_response = {
        "id": "ffff-ffff-ffff-ffff",
        "title": "call dentist",
        "trigger_datetime": "2026-06-30T09:00:00",
        "fired_at": None,
        "created_at": "2026-06-25T10:00:00",
    }
    llm_side_effects = [
        _make_tool_call_response(
            "create_reminder",
            {"title": "call dentist", "trigger_datetime": "2026-06-30T09:00:00"},
        ),
        _make_text_response(
            "Reminder set! I'll remind you to call the dentist on June 30th."
        ),
    ]

    graph = build_graph()
    config = _make_config("test-create-reminder")

    with patch(
        "agent.nodes.litellm.acompletion", AsyncMock(side_effect=llm_side_effects)
    ):
        with respx.mock(base_url=BASE) as mock:
            route = mock.post("/reminders").mock(
                return_value=httpx.Response(201, json=reminder_response)
            )

            result = await graph.ainvoke(
                {
                    "messages": [
                        HumanMessage("remind me to call the dentist on June 30")
                    ]
                },
                config,
            )

            assert route.called

    assert isinstance(result["messages"][-1].content, str)

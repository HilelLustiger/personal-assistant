"""T06 — LangGraph tool definitions wrapping tasks-service REST API."""
import json
import os

os.environ.setdefault("TASKS_SERVICE_URL", "http://tasks-service:8001")

import httpx
import pytest
import respx
from langchain_core.tools import BaseTool

from tools.tasks_tool import (
    TASKS_SERVICE_URL,
    complete_task,
    create_goal,
    create_habit,
    create_reminder,
    create_task,
    delete_goal,
    delete_habit,
    delete_reminder,
    delete_task,
    fire_reminder,
    get_goal_progress,
    list_goals,
    list_habits,
    list_reminders,
    list_tasks,
    log_habit,
    update_goal,
    update_habit,
    update_reminder,
    update_task,
)

ALL_TOOLS = [
    list_goals,
    create_goal,
    update_goal,
    delete_goal,
    get_goal_progress,
    list_tasks,
    create_task,
    update_task,
    delete_task,
    complete_task,
    list_habits,
    create_habit,
    update_habit,
    delete_habit,
    log_habit,
    list_reminders,
    create_reminder,
    update_reminder,
    delete_reminder,
    fire_reminder,
]

BASE = TASKS_SERVICE_URL


# ── AC: all tools importable as LangGraph tools ───────────────────────────────

def test_all_tools_are_langgraph_tools():
    for tool_instance in ALL_TOOLS:
        assert isinstance(tool_instance, BaseTool), f"{tool_instance} is not a BaseTool"


def test_all_tools_have_descriptions():
    for tool_instance in ALL_TOOLS:
        assert tool_instance.description, f"{tool_instance.name} has no description"


def test_tool_count():
    assert len(ALL_TOOLS) == 20


# ── AC: POST /tasks sends correct body and returns parsed response ─────────────

@pytest.mark.asyncio
async def test_create_task_sends_correct_body():
    task_response = {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "title": "buy milk",
        "due_datetime": None,
        "goal_id": None,
        "completed_at": None,
        "created_at": "2026-06-25T10:00:00",
    }
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/tasks").mock(return_value=httpx.Response(201, json=task_response))
        result = await create_task.ainvoke({"title": "buy milk"})

        assert route.called
        sent = json.loads(route.calls[0].request.content)
        assert sent["title"] == "buy milk"
        assert "due_datetime" not in sent
        assert result["title"] == "buy milk"
        assert result["id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@pytest.mark.asyncio
async def test_create_task_with_optional_fields():
    task_response = {
        "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "title": "sprint planning",
        "due_datetime": "2026-06-30T09:00:00",
        "goal_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "completed_at": None,
        "created_at": "2026-06-25T10:00:00",
    }
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/tasks").mock(return_value=httpx.Response(201, json=task_response))
        result = await create_task.ainvoke({
            "title": "sprint planning",
            "due_datetime": "2026-06-30T09:00:00",
            "goal_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        })

        sent = json.loads(route.calls[0].request.content)
        assert sent["due_datetime"] == "2026-06-30T09:00:00"
        assert sent["goal_id"] == "cccccccc-cccc-cccc-cccc-cccccccccccc"
        assert result["due_datetime"] == "2026-06-30T09:00:00"


# ── AC: GET /habits with date includes needs_log_today ────────────────────────

@pytest.mark.asyncio
async def test_list_habits_with_date_includes_needs_log_today():
    habits_response = [
        {
            "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
            "name": "morning run",
            "goal_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "frequency_target": 5,
            "frequency_unit": "week",
            "start_date": "2026-01-01",
            "active": True,
            "created_at": "2026-01-01T00:00:00",
            "needs_log_today": False,
            "completions_this_week": 3,
        }
    ]
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/habits").mock(return_value=httpx.Response(200, json=habits_response))
        result = await list_habits.ainvoke({"active": True, "date": "2026-06-25"})

        assert route.called
        params = dict(route.calls[0].request.url.params)
        assert params.get("date") == "2026-06-25"
        assert isinstance(result, list)
        assert "needs_log_today" in result[0]
        assert "completions_this_week" in result[0]
        assert result[0]["needs_log_today"] is False
        assert result[0]["completions_this_week"] == 3


@pytest.mark.asyncio
async def test_list_habits_without_date_omits_computed_fields():
    habits_response = [
        {
            "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
            "name": "morning run",
            "goal_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "frequency_target": 5,
            "frequency_unit": "week",
            "start_date": "2026-01-01",
            "active": True,
            "created_at": "2026-01-01T00:00:00",
        }
    ]
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/habits").mock(return_value=httpx.Response(200, json=habits_response))
        result = await list_habits.ainvoke({})

        params = dict(route.calls[0].request.url.params)
        assert "date" not in params
        assert "needs_log_today" not in result[0]


# ── AC: GET /goals/{id}/progress returns completion_rate per habit ─────────────

@pytest.mark.asyncio
async def test_get_goal_progress_returns_completion_rate():
    goal_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    progress_response = {
        "id": goal_id,
        "name": "Get fit",
        "description": None,
        "status": "active",
        "target_date": None,
        "parent_goal_id": None,
        "created_at": "2026-01-01T00:00:00",
        "habits": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "name": "morning run",
                "frequency_target": 5,
                "frequency_unit": "week",
                "completions_this_week": 3,
                "completion_rate": 0.6,
            }
        ],
        "tasks_completed": 2,
        "tasks_total": 5,
    }
    with respx.mock(base_url=BASE) as mock:
        mock.get(f"/goals/{goal_id}/progress").mock(
            return_value=httpx.Response(200, json=progress_response)
        )
        result = await get_goal_progress.ainvoke({"goal_id": goal_id})

        assert "habits" in result
        assert result["habits"][0]["completion_rate"] == 0.6
        assert result["habits"][0]["completions_this_week"] == 3
        assert result["tasks_completed"] == 2
        assert result["tasks_total"] == 5


# ── Additional coverage: action endpoints ─────────────────────────────────────

@pytest.mark.asyncio
async def test_complete_task_posts_to_correct_url():
    task_id = "22222222-2222-2222-2222-222222222222"
    task_response = {
        "id": task_id,
        "title": "buy milk",
        "due_datetime": None,
        "goal_id": None,
        "completed_at": "2026-06-25T12:00:00",
        "created_at": "2026-06-24T10:00:00",
    }
    with respx.mock(base_url=BASE) as mock:
        route = mock.post(f"/tasks/{task_id}/complete").mock(
            return_value=httpx.Response(200, json=task_response)
        )
        result = await complete_task.ainvoke({"task_id": task_id})

        assert route.called
        assert result["completed_at"] == "2026-06-25T12:00:00"


@pytest.mark.asyncio
async def test_log_habit_posts_note():
    habit_id = "33333333-3333-3333-3333-333333333333"
    log_response = {
        "id": "44444444-4444-4444-4444-444444444444",
        "habit_id": habit_id,
        "completed_at": "2026-06-25T08:00:00",
        "note": "felt great",
    }
    with respx.mock(base_url=BASE) as mock:
        route = mock.post(f"/habits/{habit_id}/log").mock(
            return_value=httpx.Response(201, json=log_response)
        )
        result = await log_habit.ainvoke({"habit_id": habit_id, "note": "felt great"})

        sent = json.loads(route.calls[0].request.content)
        assert sent["note"] == "felt great"
        assert result["habit_id"] == habit_id


@pytest.mark.asyncio
async def test_delete_task_returns_confirmation():
    task_id = "55555555-5555-5555-5555-555555555555"
    with respx.mock(base_url=BASE) as mock:
        mock.delete(f"/tasks/{task_id}").mock(return_value=httpx.Response(204))
        result = await delete_task.ainvoke({"task_id": task_id})

        assert result["deleted"] is True
        assert result["task_id"] == task_id


@pytest.mark.asyncio
async def test_fire_reminder_posts_to_correct_url():
    reminder_id = "66666666-6666-6666-6666-666666666666"
    reminder_response = {
        "id": reminder_id,
        "title": "call dentist",
        "trigger_datetime": "2026-06-25T09:00:00",
        "fired_at": "2026-06-25T09:00:01",
        "created_at": "2026-06-24T10:00:00",
    }
    with respx.mock(base_url=BASE) as mock:
        route = mock.post(f"/reminders/{reminder_id}/fire").mock(
            return_value=httpx.Response(200, json=reminder_response)
        )
        result = await fire_reminder.ainvoke({"reminder_id": reminder_id})

        assert route.called
        assert result["fired_at"] is not None


@pytest.mark.asyncio
async def test_list_reminders_passes_fired_false_param():
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/reminders").mock(return_value=httpx.Response(200, json=[]))
        await list_reminders.ainvoke({"fired": False, "due_by": "2026-06-25T23:59:59"})

        params = dict(route.calls[0].request.url.params)
        assert params["fired"] == "false"
        assert "due_by" in params


@pytest.mark.asyncio
async def test_list_tasks_completed_false_filter():
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/tasks").mock(return_value=httpx.Response(200, json=[]))
        await list_tasks.ainvoke({"completed": False, "due_by": "2026-06-25"})

        params = dict(route.calls[0].request.url.params)
        assert params["completed"] == "false"
        assert params["due_by"] == "2026-06-25"

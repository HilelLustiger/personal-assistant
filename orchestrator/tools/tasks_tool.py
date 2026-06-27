"""LangGraph tool definitions wrapping the tasks-service REST API.

Each tool's docstring is what the LLM reads to decide which tool to call.
No business logic lives here — tools are thin HTTP wrappers.
"""
import os
from typing import Optional

import httpx
from langchain_core.tools import tool

TASKS_SERVICE_URL = os.environ.get("TASKS_SERVICE_URL", "http://tasks-service:8001")


# ── Goals ─────────────────────────────────────────────────────────────────────


@tool
async def list_goals(status: Optional[str] = None) -> list:
    """List goals. Pass status='active', 'completed', or 'archived' to filter;
    omit to get all goals regardless of status."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        params = {}
        if status is not None:
            params["status"] = status
        response = await client.get("/goals", params=params)
        response.raise_for_status()
        return response.json()


@tool
async def create_goal(
    name: str,
    description: Optional[str] = None,
    status: Optional[str] = None,
    target_date: Optional[str] = None,
    parent_goal_id: Optional[str] = None,
) -> dict:
    """Create a new goal. Use when the user wants to set a new goal or objective.
    target_date is ISO 8601. parent_goal_id links to a parent for sub-goals.
    Returns the created goal with its id."""
    payload: dict = {"name": name}
    if description is not None:
        payload["description"] = description
    if status is not None:
        payload["status"] = status
    if target_date is not None:
        payload["target_date"] = target_date
    if parent_goal_id is not None:
        payload["parent_goal_id"] = parent_goal_id
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.post("/goals", json=payload)
        response.raise_for_status()
        return response.json()


@tool
async def update_goal(
    goal_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    target_date: Optional[str] = None,
    parent_goal_id: Optional[str] = None,
) -> dict:
    """Update an existing goal's name, description, status, target date, or parent goal.
    Provide only the fields to change; unmentioned fields stay the same.
    Use status='completed' or 'archived' to close out a goal."""
    payload: dict = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if status is not None:
        payload["status"] = status
    if target_date is not None:
        payload["target_date"] = target_date
    if parent_goal_id is not None:
        payload["parent_goal_id"] = parent_goal_id
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.patch(f"/goals/{goal_id}", json=payload)
        response.raise_for_status()
        return response.json()


@tool
async def delete_goal(goal_id: str) -> dict:
    """Delete a goal and all its habits, tasks, and logs permanently. This is irreversible.
    Use only when the user explicitly asks to remove a goal."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.delete(f"/goals/{goal_id}")
        response.raise_for_status()
        return {"deleted": True, "goal_id": goal_id}


@tool
async def get_goal_progress(goal_id: str) -> dict:
    """Get a goal's progress: habit completion rates this week and task completion counts.
    Returns completion_rate per habit (completions_this_week / frequency_target, capped at 1.0)
    plus tasks_completed and tasks_total under this goal."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.get(f"/goals/{goal_id}/progress")
        response.raise_for_status()
        return response.json()


# ── Tasks ─────────────────────────────────────────────────────────────────────


@tool
async def list_tasks(
    completed: Optional[bool] = None,
    due_by: Optional[str] = None,
    due_from: Optional[str] = None,
) -> list:
    """List tasks. Filter by completion status (completed=True for done, False for open),
    due date range (due_by=YYYY-MM-DD for tasks due on or before that date,
    due_from=YYYY-MM-DD for tasks due on or after). Omit all to get everything."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        params: dict = {}
        if completed is not None:
            params["completed"] = str(completed).lower()
        if due_by is not None:
            params["due_by"] = due_by
        if due_from is not None:
            params["due_from"] = due_from
        response = await client.get("/tasks", params=params)
        response.raise_for_status()
        return response.json()


@tool
async def create_task(
    title: str,
    due_datetime: Optional[str] = None,
    goal_id: Optional[str] = None,
) -> dict:
    """Create a new task. Use when the user wants to add something to their task list.
    due_datetime is an ISO 8601 datetime string (e.g. '2026-06-30T09:00:00').
    goal_id links the task to a goal. Returns the created task with its id."""
    payload: dict = {"title": title}
    if due_datetime is not None:
        payload["due_datetime"] = due_datetime
    if goal_id is not None:
        payload["goal_id"] = goal_id
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.post("/tasks", json=payload)
        response.raise_for_status()
        return response.json()


@tool
async def update_task(
    task_id: str,
    title: Optional[str] = None,
    due_datetime: Optional[str] = None,
    goal_id: Optional[str] = None,
) -> dict:
    """Update an existing task's title, due date/time, or linked goal.
    Provide only the fields to change; unmentioned fields stay the same."""
    payload: dict = {}
    if title is not None:
        payload["title"] = title
    if due_datetime is not None:
        payload["due_datetime"] = due_datetime
    if goal_id is not None:
        payload["goal_id"] = goal_id
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.patch(f"/tasks/{task_id}", json=payload)
        response.raise_for_status()
        return response.json()


@tool
async def delete_task(task_id: str) -> dict:
    """Delete a task permanently. Use only when the user explicitly wants to remove a task."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.delete(f"/tasks/{task_id}")
        response.raise_for_status()
        return {"deleted": True, "task_id": task_id}


@tool
async def complete_task(task_id: str) -> dict:
    """Mark a task as completed, recording the completion timestamp.
    Use when the user says they finished or did a task.
    Returns the updated task with completed_at set."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.post(f"/tasks/{task_id}/complete", json={})
        response.raise_for_status()
        return response.json()


# ── Habits ────────────────────────────────────────────────────────────────────


@tool
async def list_habits(
    active: Optional[bool] = None,
    date: Optional[str] = None,
) -> list:
    """List habits. Pass active=True/False to filter by active status.
    Pass date=YYYY-MM-DD to get computed fields per habit: needs_log_today (bool)
    and completions_this_week (int). Omit date to skip computed fields."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        params: dict = {}
        if active is not None:
            params["active"] = str(active).lower()
        if date is not None:
            params["date"] = date
        response = await client.get("/habits", params=params)
        response.raise_for_status()
        return response.json()


@tool
async def create_habit(
    name: str,
    goal_id: str,
    frequency_target: int,
    frequency_unit: str,
    start_date: str,
) -> dict:
    """Create a new recurring habit linked to a goal.
    frequency_unit is 'daily' or 'weekly'; frequency_target is how many times per unit.
    start_date is YYYY-MM-DD. Returns the created habit with its id."""
    payload = {
        "name": name,
        "goal_id": goal_id,
        "frequency_target": frequency_target,
        "frequency_unit": frequency_unit,
        "start_date": start_date,
    }
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.post("/habits", json=payload)
        response.raise_for_status()
        return response.json()


@tool
async def update_habit(
    habit_id: str,
    name: Optional[str] = None,
    frequency_target: Optional[int] = None,
    frequency_unit: Optional[str] = None,
    active: Optional[bool] = None,
) -> dict:
    """Update an existing habit's name, frequency, or active status.
    frequency_unit is 'daily' or 'weekly'. Set active=False to pause a habit without deleting it.
    Provide only the fields to change; unmentioned fields stay the same."""
    payload: dict = {}
    if name is not None:
        payload["name"] = name
    if frequency_target is not None:
        payload["frequency_target"] = frequency_target
    if frequency_unit is not None:
        payload["frequency_unit"] = frequency_unit
    if active is not None:
        payload["active"] = active
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.patch(f"/habits/{habit_id}", json=payload)
        response.raise_for_status()
        return response.json()


@tool
async def delete_habit(habit_id: str) -> dict:
    """Delete a habit and all its completion logs permanently. This is irreversible.
    Use only when the user explicitly asks to remove a habit."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.delete(f"/habits/{habit_id}")
        response.raise_for_status()
        return {"deleted": True, "habit_id": habit_id}


@tool
async def log_habit(habit_id: str, note: Optional[str] = None) -> dict:
    """Log a habit completion for today. Use when the user says they did a habit.
    note is optional free-text context. Returns the completion log entry with its id."""
    payload: dict = {}
    if note is not None:
        payload["note"] = note
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.post(f"/habits/{habit_id}/log", json=payload)
        response.raise_for_status()
        return response.json()


# ── Reminders ─────────────────────────────────────────────────────────────────


@tool
async def list_reminders(
    fired: Optional[bool] = None,
    due_by: Optional[str] = None,
) -> list:
    """List reminders. Pass fired=False to get only unfired reminders;
    fired=True for already-fired ones. Pass due_by=ISO8601-datetime to filter by due time.
    Omit all params to list everything."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        params: dict = {}
        if fired is not None:
            params["fired"] = str(fired).lower()
        if due_by is not None:
            params["due_by"] = due_by
        response = await client.get("/reminders", params=params)
        response.raise_for_status()
        return response.json()


@tool
async def create_reminder(title: str, trigger_datetime: str) -> dict:
    """Create a new reminder with a scheduled trigger time.
    trigger_datetime is an ISO 8601 datetime string (e.g. '2026-06-30T09:00:00').
    Returns the created reminder with its id and fired_at=null."""
    payload = {"title": title, "trigger_datetime": trigger_datetime}
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.post("/reminders", json=payload)
        response.raise_for_status()
        return response.json()


@tool
async def update_reminder(
    reminder_id: str,
    title: Optional[str] = None,
    trigger_datetime: Optional[str] = None,
) -> dict:
    """Update an existing reminder's title or trigger datetime.
    Provide only the fields to change; unmentioned fields stay the same."""
    payload: dict = {}
    if title is not None:
        payload["title"] = title
    if trigger_datetime is not None:
        payload["trigger_datetime"] = trigger_datetime
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.patch(f"/reminders/{reminder_id}", json=payload)
        response.raise_for_status()
        return response.json()


@tool
async def delete_reminder(reminder_id: str) -> dict:
    """Delete a reminder permanently. Use when the user no longer needs a scheduled reminder."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.delete(f"/reminders/{reminder_id}")
        response.raise_for_status()
        return {"deleted": True, "reminder_id": reminder_id}


@tool
async def fire_reminder(reminder_id: str) -> dict:
    """Mark a reminder as fired (sent to the user). Records the fired_at timestamp.
    Used by the proactive trigger flow after sending the Telegram notification.
    Returns the updated reminder with fired_at set."""
    async with httpx.AsyncClient(base_url=TASKS_SERVICE_URL) as client:
        response = await client.post(f"/reminders/{reminder_id}/fire", json={})
        response.raise_for_status()
        return response.json()


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

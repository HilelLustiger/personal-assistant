import os
from datetime import date, datetime, timezone
from typing import Optional

import httpx
from bot import sender
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from telegram import InlineKeyboardButton

router = APIRouter()


class TriggerRequest(BaseModel):
    secret: Optional[str] = None


def _check_secret(request: TriggerRequest) -> None:
    expected = os.environ.get("PROACTIVE_SECRET", "")
    if not request.secret or request.secret != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/trigger/morning")
async def trigger_morning(request: TriggerRequest) -> dict:
    _check_secret(request)
    today = date.today().isoformat()
    tasks_url = os.environ.get("TASKS_SERVICE_URL", "http://tasks-service:8001")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    async with httpx.AsyncClient(base_url=tasks_url) as client:
        response = await client.get(
            "/tasks", params={"completed": "false", "due_by": today}
        )
        response.raise_for_status()
        tasks = response.json()

    if tasks:
        lines = [f"- {task['title']}" for task in tasks]
        text = "Good morning! Here are your tasks for today:\n" + "\n".join(lines)
    else:
        text = "Good morning! No tasks due today. Enjoy your day!"

    await sender.send_message(chat_id, text)
    return {"status": "ok"}


@router.post("/trigger/eod")
async def trigger_eod(request: TriggerRequest) -> dict:
    _check_secret(request)
    today = date.today().isoformat()
    tasks_url = os.environ.get("TASKS_SERVICE_URL", "http://tasks-service:8001")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    async with httpx.AsyncClient(base_url=tasks_url) as client:
        response = await client.get("/habits", params={"active": "true", "date": today})
        response.raise_for_status()
        habits = response.json()

    habits_needing_log = [habit for habit in habits if habit.get("needs_log_today")]

    if habits_needing_log:
        lines = [f"- {habit['name']}" for habit in habits_needing_log]
        text = "End of day check-in! Did you complete these habits?\n" + "\n".join(
            lines
        )
        buttons = [
            [
                InlineKeyboardButton(
                    "Yes", callback_data=f"habit_log:{habit['id']}:yes"
                ),
                InlineKeyboardButton("No", callback_data=f"habit_log:{habit['id']}:no"),
            ]
            for habit in habits_needing_log
        ]
        await sender.send_message_with_buttons(chat_id, text, buttons)
    else:
        text = "End of day check-in! All habits logged for today. Great work!"
        await sender.send_message(chat_id, text)

    return {"status": "ok"}


@router.post("/trigger/check-reminders")
async def trigger_check_reminders(request: TriggerRequest) -> dict:
    _check_secret(request)
    tasks_url = os.environ.get("TASKS_SERVICE_URL", "http://tasks-service:8001")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    async with httpx.AsyncClient(base_url=tasks_url) as client:
        response = await client.get(
            "/reminders", params={"fired": "false", "due_by": now}
        )
        response.raise_for_status()
        reminders = response.json()

        for reminder in reminders:
            await sender.send_message(chat_id, f"Reminder: {reminder['title']}")
            await client.post(f"/reminders/{reminder['id']}/fire", json={})

    return {"status": "ok"}

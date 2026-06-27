import os
from unittest.mock import AsyncMock, patch

import httpx
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Set env vars before importing triggers
os.environ.setdefault("PROACTIVE_SECRET", "test-secret")
os.environ.setdefault("TASKS_SERVICE_URL", "http://tasks-service:8001")
os.environ.setdefault("TELEGRAM_CHAT_ID", "99999")

from proactive.triggers import router as proactive_router

_test_app = FastAPI()
_test_app.include_router(proactive_router)
client = TestClient(_test_app)

CORRECT_SECRET = {"secret": "test-secret"}
WRONG_SECRET = {"secret": "wrong-secret"}
TASKS_BASE = "http://tasks-service:8001"


# ── secret validation ──────────────────────────────────────────────────────────


def test_morning_wrong_secret_returns_401():
    response = client.post("/trigger/morning", json=WRONG_SECRET)
    assert response.status_code == 401


def test_morning_missing_secret_returns_401():
    response = client.post("/trigger/morning", json={})
    assert response.status_code == 401


def test_eod_wrong_secret_returns_401():
    response = client.post("/trigger/eod", json=WRONG_SECRET)
    assert response.status_code == 401


def test_check_reminders_wrong_secret_returns_401():
    response = client.post("/trigger/check-reminders", json=WRONG_SECRET)
    assert response.status_code == 401


# ── /trigger/morning ───────────────────────────────────────────────────────────


@respx.mock
def test_morning_calls_tasks_service_with_correct_params():
    from datetime import date

    today = date.today().isoformat()
    tasks_mock = respx.get(f"{TASKS_BASE}/tasks").mock(
        return_value=httpx.Response(
            200, json=[{"id": "abc", "title": "buy milk", "completed_at": None}]
        )
    )
    with patch("bot.sender.send_message", new_callable=AsyncMock):
        response = client.post("/trigger/morning", json=CORRECT_SECRET)
    assert response.status_code == 200
    assert tasks_mock.called
    request_url = str(tasks_mock.calls.last.request.url)
    assert "completed=false" in request_url
    assert f"due_by={today}" in request_url


@respx.mock
def test_morning_sends_message_containing_task_titles():
    respx.get(f"{TASKS_BASE}/tasks").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "abc", "title": "buy milk", "completed_at": None},
                {"id": "def", "title": "call dentist", "completed_at": None},
            ],
        )
    )
    with patch("bot.sender.send_message", new_callable=AsyncMock) as mock_send:
        response = client.post("/trigger/morning", json=CORRECT_SECRET)
    assert response.status_code == 200
    mock_send.assert_called_once()
    sent_text = mock_send.call_args[0][1]
    assert "buy milk" in sent_text
    assert "call dentist" in sent_text


@respx.mock
def test_morning_sends_message_even_when_no_tasks():
    respx.get(f"{TASKS_BASE}/tasks").mock(return_value=httpx.Response(200, json=[]))
    with patch("bot.sender.send_message", new_callable=AsyncMock) as mock_send:
        response = client.post("/trigger/morning", json=CORRECT_SECRET)
    assert response.status_code == 200
    mock_send.assert_called_once()


# ── /trigger/eod ──────────────────────────────────────────────────────────────


@respx.mock
def test_eod_calls_habits_with_active_and_date_params():
    from datetime import date

    today = date.today().isoformat()
    habits_mock = respx.get(f"{TASKS_BASE}/habits").mock(
        return_value=httpx.Response(200, json=[])
    )
    with patch("bot.sender.send_message", new_callable=AsyncMock):
        response = client.post("/trigger/eod", json=CORRECT_SECRET)
    assert response.status_code == 200
    request_url = str(habits_mock.calls.last.request.url)
    assert "active=true" in request_url
    assert f"date={today}" in request_url


@respx.mock
def test_eod_sends_buttons_for_habits_needing_log():
    habit_id = "habit-abc"
    respx.get(f"{TASKS_BASE}/habits").mock(
        return_value=httpx.Response(
            200, json=[{"id": habit_id, "name": "Exercise", "needs_log_today": True}]
        )
    )
    with patch(
        "bot.sender.send_message_with_buttons", new_callable=AsyncMock
    ) as mock_buttons:
        response = client.post("/trigger/eod", json=CORRECT_SECRET)
    assert response.status_code == 200
    mock_buttons.assert_called_once()
    buttons = mock_buttons.call_args[0][2]
    flat_buttons = [btn for row in buttons for btn in row]
    callback_datas = [btn.callback_data for btn in flat_buttons]
    assert f"habit_log:{habit_id}:yes" in callback_datas
    assert f"habit_log:{habit_id}:no" in callback_datas


@respx.mock
def test_eod_excludes_already_logged_habits_from_buttons():
    respx.get(f"{TASKS_BASE}/habits").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "needs", "name": "Run", "needs_log_today": True},
                {"id": "done", "name": "Read", "needs_log_today": False},
            ],
        )
    )
    with patch(
        "bot.sender.send_message_with_buttons", new_callable=AsyncMock
    ) as mock_buttons:
        response = client.post("/trigger/eod", json=CORRECT_SECRET)
    assert response.status_code == 200
    buttons = mock_buttons.call_args[0][2]
    flat_buttons = [btn for row in buttons for btn in row]
    callback_datas = [btn.callback_data for btn in flat_buttons]
    assert any("needs" in data for data in callback_datas)
    assert not any("done" in data for data in callback_datas)


@respx.mock
def test_eod_sends_plain_message_when_all_habits_already_logged():
    respx.get(f"{TASKS_BASE}/habits").mock(
        return_value=httpx.Response(
            200, json=[{"id": "done", "name": "Read", "needs_log_today": False}]
        )
    )
    with (
        patch("bot.sender.send_message", new_callable=AsyncMock) as mock_send,
        patch(
            "bot.sender.send_message_with_buttons", new_callable=AsyncMock
        ) as mock_buttons,
    ):
        response = client.post("/trigger/eod", json=CORRECT_SECRET)
    assert response.status_code == 200
    mock_buttons.assert_not_called()
    mock_send.assert_called_once()


@respx.mock
def test_eod_sends_plain_message_when_no_active_habits():
    respx.get(f"{TASKS_BASE}/habits").mock(return_value=httpx.Response(200, json=[]))
    with (
        patch("bot.sender.send_message", new_callable=AsyncMock) as mock_send,
        patch(
            "bot.sender.send_message_with_buttons", new_callable=AsyncMock
        ) as mock_buttons,
    ):
        response = client.post("/trigger/eod", json=CORRECT_SECRET)
    assert response.status_code == 200
    mock_buttons.assert_not_called()
    mock_send.assert_called_once()


# ── /trigger/check-reminders ──────────────────────────────────────────────────


@respx.mock
def test_check_reminders_sends_title_and_fires_reminder():
    reminder_id = "rem-xyz"
    respx.get(f"{TASKS_BASE}/reminders").mock(
        return_value=httpx.Response(
            200, json=[{"id": reminder_id, "title": "Call dentist", "fired_at": None}]
        )
    )
    fire_mock = respx.post(f"{TASKS_BASE}/reminders/{reminder_id}/fire").mock(
        return_value=httpx.Response(
            200, json={"id": reminder_id, "fired_at": "2026-06-27T10:00:00"}
        )
    )
    with patch("bot.sender.send_message", new_callable=AsyncMock) as mock_send:
        response = client.post("/trigger/check-reminders", json=CORRECT_SECRET)
    assert response.status_code == 200
    mock_send.assert_called_once()
    assert "Call dentist" in mock_send.call_args[0][1]
    assert fire_mock.called


@respx.mock
def test_check_reminders_fires_after_sending_not_before():
    reminder_id = "rem-xyz"
    call_order = []

    async def mock_send_ordered(chat_id, text):
        call_order.append("send")

    def fire_side_effect(request):
        call_order.append("fire")
        return httpx.Response(200, json={})

    respx.get(f"{TASKS_BASE}/reminders").mock(
        return_value=httpx.Response(
            200, json=[{"id": reminder_id, "title": "Check in", "fired_at": None}]
        )
    )
    respx.post(f"{TASKS_BASE}/reminders/{reminder_id}/fire").mock(
        side_effect=fire_side_effect
    )
    with patch("bot.sender.send_message", side_effect=mock_send_ordered):
        client.post("/trigger/check-reminders", json=CORRECT_SECRET)
    assert call_order == ["send", "fire"]


@respx.mock
def test_check_reminders_handles_multiple_reminders_individually():
    respx.get(f"{TASKS_BASE}/reminders").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "rem-1", "title": "First", "fired_at": None},
                {"id": "rem-2", "title": "Second", "fired_at": None},
            ],
        )
    )
    respx.post(f"{TASKS_BASE}/reminders/rem-1/fire").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.post(f"{TASKS_BASE}/reminders/rem-2/fire").mock(
        return_value=httpx.Response(200, json={})
    )
    with patch("bot.sender.send_message", new_callable=AsyncMock) as mock_send:
        response = client.post("/trigger/check-reminders", json=CORRECT_SECRET)
    assert response.status_code == 200
    assert mock_send.call_count == 2


@respx.mock
def test_check_reminders_no_due_reminders_returns_200_with_no_message():
    respx.get(f"{TASKS_BASE}/reminders").mock(return_value=httpx.Response(200, json=[]))
    with patch("bot.sender.send_message", new_callable=AsyncMock) as mock_send:
        response = client.post("/trigger/check-reminders", json=CORRECT_SECRET)
    assert response.status_code == 200
    mock_send.assert_not_called()

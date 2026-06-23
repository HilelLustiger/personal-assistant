"""API tests for /habits — T04."""
import uuid
import pytest


@pytest.fixture
def goal_id(client):
    return client.post("/goals", json={"name": "Test Goal"}).json()["id"]


def _create_habit(client, goal_id, name="Run", frequency_target=3):
    return client.post("/habits", json={
        "name": name,
        "goal_id": goal_id,
        "frequency_target": frequency_target,
        "frequency_unit": "weekly",
        "start_date": "2026-06-01",
    }).json()["id"]


def test_create_habit(client, goal_id):
    response = client.post("/habits", json={
        "name": "Morning run",
        "goal_id": goal_id,
        "frequency_target": 3,
        "frequency_unit": "weekly",
        "start_date": "2026-06-01",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Morning run"
    assert data["active"] is True
    assert "id" in data
    assert "created_at" in data


def test_list_habits_returns_all(client, goal_id):
    _create_habit(client, goal_id, name="Habit A")
    _create_habit(client, goal_id, name="Habit B")
    response = client.get("/habits")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_habits_filter_active(client, goal_id):
    active_habit_id = _create_habit(client, goal_id, name="Active")
    inactive_habit_id = _create_habit(client, goal_id, name="Inactive")
    client.patch(f"/habits/{inactive_habit_id}", json={"active": False})

    response = client.get("/habits?active=true")
    assert response.status_code == 200
    returned_ids = [habit["id"] for habit in response.json()]
    assert active_habit_id in returned_ids
    assert inactive_habit_id not in returned_ids


def test_list_habits_with_date_includes_computed_fields(client, goal_id):
    _create_habit(client, goal_id, name="Run", frequency_target=3)

    response = client.get("/habits?date=2026-06-23")
    assert response.status_code == 200
    habits = response.json()
    assert len(habits) == 1
    assert "needs_log_today" in habits[0]
    assert "completions_this_week" in habits[0]
    assert habits[0]["needs_log_today"] is True
    assert habits[0]["completions_this_week"] == 0


def test_list_habits_with_date_counts_completions(client, goal_id):
    habit_id = _create_habit(client, goal_id, name="Run", frequency_target=3)
    client.post(f"/habits/{habit_id}/log", json={})
    client.post(f"/habits/{habit_id}/log", json={})

    response = client.get("/habits?date=2026-06-23")
    habits = response.json()
    assert habits[0]["completions_this_week"] == 2
    assert habits[0]["needs_log_today"] is True  # 2 < 3


def test_list_habits_with_date_needs_log_false_when_at_target(client, goal_id):
    habit_id = _create_habit(client, goal_id, name="Run", frequency_target=2)
    client.post(f"/habits/{habit_id}/log", json={})
    client.post(f"/habits/{habit_id}/log", json={})

    response = client.get("/habits?date=2026-06-23")
    assert response.json()[0]["needs_log_today"] is False


def test_list_habits_without_date_omits_computed_fields(client, goal_id):
    _create_habit(client, goal_id, name="Run")
    response = client.get("/habits")
    habit = response.json()[0]
    assert "needs_log_today" not in habit
    assert "completions_this_week" not in habit


def test_log_habit(client, goal_id):
    habit_id = _create_habit(client, goal_id)
    response = client.post(f"/habits/{habit_id}/log", json={"note": "felt great"})
    assert response.status_code == 201
    data = response.json()
    assert data["habit_id"] == habit_id
    assert data["note"] == "felt great"
    assert "completed_at" in data


def test_log_habit_not_found(client):
    response = client.post(f"/habits/{uuid.uuid4()}/log", json={})
    assert response.status_code == 404


def test_patch_habit(client, goal_id):
    habit_id = _create_habit(client, goal_id, name="Old", frequency_target=3)
    response = client.patch(f"/habits/{habit_id}", json={"name": "New", "frequency_target": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New"
    assert data["frequency_target"] == 5


def test_patch_habit_not_found(client):
    response = client.patch(f"/habits/{uuid.uuid4()}", json={"name": "X"})
    assert response.status_code == 404


def test_delete_habit(client, goal_id):
    habit_id = _create_habit(client, goal_id)
    response = client.delete(f"/habits/{habit_id}")
    assert response.status_code == 204
    assert client.get("/habits").json() == []


def test_delete_habit_not_found(client):
    response = client.delete(f"/habits/{uuid.uuid4()}")
    assert response.status_code == 404

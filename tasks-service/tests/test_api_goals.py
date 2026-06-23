"""API tests for /goals — T04."""
import uuid
import pytest


@pytest.fixture
def goal_id(client):
    return client.post("/goals", json={"name": "Test Goal"}).json()["id"]


def test_create_goal(client):
    response = client.post("/goals", json={"name": "Run a marathon"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Run a marathon"
    assert data["status"] == "active"
    assert data["parent_goal_id"] is None
    assert "id" in data
    assert "created_at" in data


def test_create_nested_goal(client, goal_id):
    response = client.post("/goals", json={"name": "Child Goal", "parent_goal_id": goal_id})
    assert response.status_code == 201
    assert response.json()["parent_goal_id"] == goal_id


def test_list_goals_returns_all(client):
    client.post("/goals", json={"name": "Goal A"})
    client.post("/goals", json={"name": "Goal B"})
    response = client.get("/goals")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_goals_filter_by_status(client):
    client.post("/goals", json={"name": "Active Goal"})
    archived_goal_id = client.post("/goals", json={"name": "To Archive"}).json()["id"]
    client.patch(f"/goals/{archived_goal_id}", json={"status": "archived"})

    response = client.get("/goals?status=active")
    names = [goal["name"] for goal in response.json()]
    assert "Active Goal" in names
    assert "To Archive" not in names


def test_goal_progress_empty(client, goal_id):
    response = client.get(f"/goals/{goal_id}/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == goal_id
    assert data["habits"] == []
    assert data["tasks_completed"] == 0
    assert data["tasks_total"] == 0


def test_goal_progress_with_habits_and_tasks(client, goal_id):
    habit_id = client.post("/habits", json={
        "name": "Run", "goal_id": goal_id,
        "frequency_target": 4, "frequency_unit": "weekly", "start_date": "2026-06-01",
    }).json()["id"]
    client.post(f"/habits/{habit_id}/log", json={})
    client.post(f"/habits/{habit_id}/log", json={})

    task_a_id = client.post("/tasks", json={"title": "Task A", "goal_id": goal_id}).json()["id"]
    client.post("/tasks", json={"title": "Task B", "goal_id": goal_id})
    client.post(f"/tasks/{task_a_id}/complete")

    response = client.get(f"/goals/{goal_id}/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["tasks_completed"] == 1
    assert data["tasks_total"] == 2
    assert len(data["habits"]) == 1
    assert data["habits"][0]["completions_this_week"] == 2
    assert data["habits"][0]["completion_rate"] == 0.5


def test_goal_progress_completion_rate_capped_at_one(client, goal_id):
    habit_id = client.post("/habits", json={
        "name": "Run", "goal_id": goal_id,
        "frequency_target": 2, "frequency_unit": "weekly", "start_date": "2026-06-01",
    }).json()["id"]
    client.post(f"/habits/{habit_id}/log", json={})
    client.post(f"/habits/{habit_id}/log", json={})
    client.post(f"/habits/{habit_id}/log", json={})  # 3 logs for target of 2

    response = client.get(f"/goals/{goal_id}/progress")
    assert response.json()["habits"][0]["completion_rate"] == 1.0


def test_goal_progress_not_found(client):
    response = client.get(f"/goals/{uuid.uuid4()}/progress")
    assert response.status_code == 404


def test_patch_goal(client, goal_id):
    response = client.patch(f"/goals/{goal_id}", json={"name": "New Name", "status": "completed"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["status"] == "completed"


def test_patch_goal_not_found(client):
    response = client.patch(f"/goals/{uuid.uuid4()}", json={"name": "X"})
    assert response.status_code == 404


def test_delete_goal(client):
    goal_id = client.post("/goals", json={"name": "Delete me"}).json()["id"]
    response = client.delete(f"/goals/{goal_id}")
    assert response.status_code == 204
    assert client.get("/goals").json() == []


def test_delete_goal_not_found(client):
    response = client.delete(f"/goals/{uuid.uuid4()}")
    assert response.status_code == 404

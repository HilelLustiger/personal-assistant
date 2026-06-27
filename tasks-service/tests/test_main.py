"""Tests for tasks-service main.py endpoints."""

import uuid


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_goal_progress_returns_correct_shape(client):
    goal_resp = client.post("/goals", json={"name": "Get fit"})
    goal_id = goal_resp.json()["id"]
    client.post(
        "/habits",
        json={
            "name": "Run",
            "goal_id": goal_id,
            "frequency_target": 3,
            "frequency_unit": "weekly",
            "start_date": "2026-06-27",
        },
    )
    task_resp = client.post("/tasks", json={"title": "Buy shoes", "goal_id": goal_id})
    client.post(f"/tasks/{task_resp.json()['id']}/complete", json={})
    client.post("/tasks", json={"title": "Register for race", "goal_id": goal_id})

    response = client.get(f"/goals/{goal_id}/progress")
    assert response.status_code == 200
    data = response.json()
    assert "habits" in data
    assert "tasks_completed" in data
    assert "tasks_total" in data
    assert data["tasks_total"] == 2
    assert data["tasks_completed"] == 1
    assert len(data["habits"]) == 1
    assert "completion_rate" in data["habits"][0]


def test_get_goal_progress_unknown_id_returns_404(client):
    response = client.get(f"/goals/{uuid.uuid4()}/progress")
    assert response.status_code == 404


def test_get_goal_progress_empty_goal_returns_zero_counts(client):
    goal_resp = client.post("/goals", json={"name": "Empty goal"})
    goal_id = goal_resp.json()["id"]
    response = client.get(f"/goals/{goal_id}/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["habits"] == []
    assert data["tasks_completed"] == 0
    assert data["tasks_total"] == 0

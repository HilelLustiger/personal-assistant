"""API tests for /tasks — T04."""
import uuid


def test_create_task(client):
    response = client.post("/tasks", json={"title": "Buy milk"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy milk"
    assert data["completed_at"] is None
    assert "id" in data
    assert "created_at" in data


def test_list_tasks_returns_all(client):
    client.post("/tasks", json={"title": "Task A"})
    client.post("/tasks", json={"title": "Task B"})
    response = client.get("/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_tasks_filter_completed_false(client):
    open_task_id = client.post("/tasks", json={"title": "Open task"}).json()["id"]
    completed_task_id = client.post("/tasks", json={"title": "Completed task"}).json()["id"]
    client.post(f"/tasks/{completed_task_id}/complete")

    response = client.get("/tasks?completed=false")
    assert response.status_code == 200
    returned_ids = [task["id"] for task in response.json()]
    assert open_task_id in returned_ids
    assert completed_task_id not in returned_ids


def test_list_tasks_filter_completed_true(client):
    client.post("/tasks", json={"title": "Open task"})
    completed_task_id = client.post("/tasks", json={"title": "Completed task"}).json()["id"]
    client.post(f"/tasks/{completed_task_id}/complete")

    response = client.get("/tasks?completed=true")
    assert response.status_code == 200
    returned_ids = [task["id"] for task in response.json()]
    assert completed_task_id in returned_ids


def test_list_tasks_filter_due_by(client):
    client.post("/tasks", json={"title": "Due today", "due_datetime": "2026-06-23T09:00:00"})
    client.post("/tasks", json={"title": "Due next week", "due_datetime": "2026-06-30T09:00:00"})
    client.post("/tasks", json={"title": "No due date"})

    response = client.get("/tasks?due_by=2026-06-23")
    assert response.status_code == 200
    titles = [task["title"] for task in response.json()]
    assert "Due today" in titles
    assert "Due next week" not in titles
    assert "No due date" not in titles


def test_complete_task_sets_completed_at(client):
    task_id = client.post("/tasks", json={"title": "Finish me"}).json()["id"]
    response = client.post(f"/tasks/{task_id}/complete")
    assert response.status_code == 200
    assert response.json()["completed_at"] is not None


def test_complete_task_not_found(client):
    response = client.post(f"/tasks/{uuid.uuid4()}/complete")
    assert response.status_code == 404


def test_patch_task_title(client):
    task_id = client.post("/tasks", json={"title": "Old title"}).json()["id"]
    response = client.patch(f"/tasks/{task_id}", json={"title": "New title"})
    assert response.status_code == 200
    assert response.json()["title"] == "New title"


def test_patch_task_not_found(client):
    response = client.patch(f"/tasks/{uuid.uuid4()}", json={"title": "X"})
    assert response.status_code == 404


def test_delete_task(client):
    task_id = client.post("/tasks", json={"title": "Delete me"}).json()["id"]
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204
    assert client.get("/tasks").json() == []


def test_delete_task_not_found(client):
    response = client.delete(f"/tasks/{uuid.uuid4()}")
    assert response.status_code == 404

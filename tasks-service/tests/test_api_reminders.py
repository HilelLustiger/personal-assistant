"""API tests for /reminders — T04."""

import uuid


def test_create_reminder(client):
    response = client.post(
        "/reminders",
        json={
            "title": "Call mom",
            "trigger_datetime": "2026-06-24T09:00:00",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Call mom"
    assert data["fired_at"] is None
    assert "id" in data
    assert "created_at" in data


def test_list_reminders_returns_all(client):
    client.post(
        "/reminders", json={"title": "R1", "trigger_datetime": "2026-06-24T09:00:00"}
    )
    client.post(
        "/reminders", json={"title": "R2", "trigger_datetime": "2026-06-25T09:00:00"}
    )
    response = client.get("/reminders")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_reminders_filter_unfired(client):
    client.post(
        "/reminders",
        json={"title": "Unfired", "trigger_datetime": "2026-06-24T09:00:00"},
    )
    fired_reminder_id = client.post(
        "/reminders",
        json={
            "title": "Already fired",
            "trigger_datetime": "2026-06-23T08:00:00",
        },
    ).json()["id"]
    client.post(f"/reminders/{fired_reminder_id}/fire")

    response = client.get("/reminders?fired=false")
    assert response.status_code == 200
    titles = [reminder["title"] for reminder in response.json()]
    assert "Unfired" in titles
    assert "Already fired" not in titles


def test_list_reminders_filter_fired(client):
    client.post(
        "/reminders",
        json={"title": "Not fired", "trigger_datetime": "2026-06-24T09:00:00"},
    )
    fired_reminder_id = client.post(
        "/reminders",
        json={
            "title": "Was fired",
            "trigger_datetime": "2026-06-23T08:00:00",
        },
    ).json()["id"]
    client.post(f"/reminders/{fired_reminder_id}/fire")

    response = client.get("/reminders?fired=true")
    titles = [reminder["title"] for reminder in response.json()]
    assert "Was fired" in titles
    assert "Not fired" not in titles


def test_list_reminders_filter_due_by(client):
    client.post(
        "/reminders",
        json={"title": "Due soon", "trigger_datetime": "2026-06-23T10:00:00"},
    )
    client.post(
        "/reminders",
        json={"title": "Due later", "trigger_datetime": "2026-06-30T10:00:00"},
    )

    response = client.get("/reminders?due_by=2026-06-23T23:59:59")
    assert response.status_code == 200
    titles = [reminder["title"] for reminder in response.json()]
    assert "Due soon" in titles
    assert "Due later" not in titles


def test_fire_reminder_sets_fired_at(client):
    reminder_id = client.post(
        "/reminders",
        json={
            "title": "Fire me",
            "trigger_datetime": "2026-06-23T09:00:00",
        },
    ).json()["id"]
    response = client.post(f"/reminders/{reminder_id}/fire")
    assert response.status_code == 200
    assert response.json()["fired_at"] is not None


def test_fire_reminder_not_found(client):
    response = client.post(f"/reminders/{uuid.uuid4()}/fire")
    assert response.status_code == 404


def test_patch_reminder(client):
    reminder_id = client.post(
        "/reminders",
        json={
            "title": "Old title",
            "trigger_datetime": "2026-06-24T09:00:00",
        },
    ).json()["id"]
    response = client.patch(f"/reminders/{reminder_id}", json={"title": "New title"})
    assert response.status_code == 200
    assert response.json()["title"] == "New title"


def test_patch_reminder_not_found(client):
    response = client.patch(f"/reminders/{uuid.uuid4()}", json={"title": "X"})
    assert response.status_code == 404


def test_delete_reminder(client):
    reminder_id = client.post(
        "/reminders",
        json={
            "title": "Delete me",
            "trigger_datetime": "2026-06-24T09:00:00",
        },
    ).json()["id"]
    response = client.delete(f"/reminders/{reminder_id}")
    assert response.status_code == 204
    assert client.get("/reminders").json() == []


def test_delete_reminder_not_found(client):
    response = client.delete(f"/reminders/{uuid.uuid4()}")
    assert response.status_code == 404

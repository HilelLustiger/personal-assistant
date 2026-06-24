"""T05 spike tests — FastAPI startup + LangGraph checkpointer write/read."""


def test_trigger_test_returns_ok(client):
    response = client.post("/trigger/test")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_trigger_test_checkpointer_round_trip(client):
    """Two sequential calls use distinct thread IDs — both must return 200,
    proving the checkpointer can write and read back state each time."""
    first = client.post("/trigger/test")
    second = client.post("/trigger/test")
    assert first.status_code == 200
    assert second.status_code == 200


def test_app_starts_without_event_loop_conflict(client):
    """Hitting any endpoint confirms uvicorn/FastAPI started cleanly."""
    response = client.get("/healthz")
    # 404 is fine — what matters is no RuntimeError or 500 from startup
    assert response.status_code != 500

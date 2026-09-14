import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_chat_never_leaks_internal_state(client):
    resp = client.post("/api/chat", json={"session_id": "test-public", "message": "привет"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"session_id", "reply", "day", "media"}


def test_session_public_endpoint_has_no_internal_fields(client):
    client.post("/api/chat", json={"session_id": "test-public-2", "message": "привет, как дела?"})
    resp = client.get("/api/session/test-public-2")
    assert resp.status_code == 200
    assert set(resp.json().keys()) == {"session_id", "day"}


def test_report_endpoint_returns_educational_summary(client):
    client.post("/api/chat", json={"session_id": "test-report", "message": "привет"})
    resp = client.get("/api/session/test-report/report")
    assert resp.status_code == 200
    body = resp.json()
    assert "risk_level" in body and "recommendation" in body


def test_admin_requires_token(client):
    resp = client.get("/api/admin/sessions")
    assert resp.status_code == 401


def test_admin_with_token_lists_sessions(client):
    client.post("/api/chat", json={"session_id": "test-admin", "message": "привет"})
    resp = client.get("/api/admin/sessions", headers={"X-Admin-Token": "test-token"})
    assert resp.status_code == 200
    assert any(s["session_id"] == "test-admin" for s in resp.json())


def test_real_credential_never_stored_as_fact(client):
    resp = client.post("/api/chat", json={"session_id": "test-cred", "message": "вот мой пароль: Sup3rSecret1!"})
    assert resp.status_code == 200
    detail = client.get("/api/admin/sessions/test-cred", headers={"X-Admin-Token": "test-token"}).json()
    assert all(f["key"] != "password" for f in detail["state"]["facts"])

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_home():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200


def test_read_api_fails_closed_without_token(monkeypatch):
    monkeypatch.delenv("CHANGELOGS_READ_TOKEN", raising=False)
    monkeypatch.delenv("CHANGELOGS_ALLOW_UNAUTHENTICATED_READS", raising=False)
    with TestClient(app) as client:
        assert client.get("/api/v1/entries").status_code == 503


def test_read_api_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("CHANGELOGS_READ_TOKEN", "correct-token")
    monkeypatch.delenv("CHANGELOGS_ALLOW_UNAUTHENTICATED_READS", raising=False)
    with TestClient(app) as client:
        response = client.get("/api/v1/entries", headers={"Authorization": "Bearer wrong-token"})
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


def test_read_api_accepts_configured_token(monkeypatch):
    monkeypatch.setenv("CHANGELOGS_READ_TOKEN", "read-token")
    monkeypatch.delenv("CHANGELOGS_ALLOW_UNAUTHENTICATED_READS", raising=False)
    with TestClient(app) as client:
        response = client.get("/api/v1/projects", headers={"Authorization": "Bearer read-token"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_export_has_stable_envelope(monkeypatch):
    monkeypatch.setenv("CHANGELOGS_READ_TOKEN", "read-token")
    monkeypatch.delenv("CHANGELOGS_ALLOW_UNAUTHENTICATED_READS", raising=False)
    with TestClient(app) as client:
        response = client.get("/api/v1/export?limit=10", headers={"Authorization": "Bearer read-token"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["schema_version"] == 1
        assert "entries" in payload
        assert "ledger_total_entries" in payload


def test_write_api_fails_closed_without_token(monkeypatch):
    monkeypatch.delenv("CHANGELOGS_WRITE_TOKEN", raising=False)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/entries",
            json={
                "project_slug": "test",
                "project_name": "Test",
                "occurred_at": "2026-08-19T00:00:00-05:00",
                "title": "Test entry",
            },
        )
        assert response.status_code == 503

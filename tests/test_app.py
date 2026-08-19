import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import connect, init_db
from app.main import app
from scripts.verify_ledger import verify


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


def test_historical_entry_cannot_be_updated_or_deleted():
    init_db()
    slug = f"integrity-{uuid.uuid4().hex}"
    with connect() as cx:
        cx.execute("INSERT INTO projects(slug,name) VALUES(?,?)", (slug, "Integrity Test"))
        project_id = cx.execute("SELECT id FROM projects WHERE slug=?", (slug,)).fetchone()["id"]
        entry_id = cx.execute(
            "INSERT INTO entries(project_id,occurred_at,title,source_ref) VALUES(?,?,?,?)",
            (project_id, "2026-08-19T00:00:00-05:00", "Immutable test entry", "pytest"),
        ).lastrowid

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with connect() as cx:
            cx.execute("UPDATE entries SET title='Changed' WHERE id=?", (entry_id,))

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with connect() as cx:
            cx.execute("DELETE FROM entries WHERE id=?", (entry_id,))


def test_ledger_integrity_verifier_passes():
    report = verify()
    assert report["ok"] is True, report["failures"]

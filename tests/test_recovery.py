from pathlib import Path

import app.db as db
from scripts.backup_ledger import backup_ledger, sha256_file
from scripts.validate_restore import validate_restore
from scripts.verify_ledger import verify


def seed_ledger(path: Path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    with db.connect() as cx:
        cx.execute("INSERT INTO projects(slug,name) VALUES('recovery-test','Recovery Test')")
        project_id = cx.execute("SELECT id FROM projects WHERE slug='recovery-test'").fetchone()["id"]
        cx.execute(
            "INSERT INTO entries(project_id,occurred_at,title,purpose,source_ref) VALUES(?,?,?,?,?)",
            (
                project_id,
                "2026-08-19T02:00:00-05:00",
                "Recovery validation entry",
                "Prove clean-environment restoration.",
                "pytest",
            ),
        )


def test_verifier_does_not_create_missing_database(tmp_path):
    missing = tmp_path / "missing.sqlite3"
    report = verify(missing)
    assert report["ok"] is False
    assert not missing.exists()


def test_online_backup_and_disposable_restore_preserve_ledger(tmp_path, monkeypatch):
    source = tmp_path / "source.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    seed_ledger(source, monkeypatch)

    backup_report = backup_ledger(source, backup)
    assert backup_report["entries"] == 1
    assert backup_report["fts_entries"] == 1
    assert backup_report["sqlite_integrity"] == "ok"
    assert backup_report["foreign_key_violations"] == 0
    assert backup.stat().st_mode & 0o777 == 0o600
    assert backup_report["sha256"] == sha256_file(backup)

    restore_root = tmp_path / "restore"
    restore_report = validate_restore(backup, restore_root)
    assert restore_report["ok"] is True
    assert restore_report["projects"] == 1
    assert restore_report["entries"] == 1
    assert restore_report["fts_entries"] == 1
    assert restore_report["backup_sha256"] == restore_report["restored_sha256"]
    assert restore_report["newest_entry"]["title"] == "Recovery validation entry"
    assert restore_report["integrity"]["ok"] is True

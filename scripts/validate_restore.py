#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify_ledger import verify


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_restore(backup: Path, restore_root: Path | None = None) -> dict[str, object]:
    backup = backup.resolve()
    if not backup.is_file():
        raise ValueError(f"backup database does not exist: {backup}")

    backup_report = verify(backup)
    if not backup_report["ok"]:
        raise ValueError(f"backup failed integrity verification: {backup_report['failures']}")

    manager = None
    if restore_root is None:
        manager = tempfile.TemporaryDirectory(prefix="goreecloud-changelogs-restore-")
        restore_root = Path(manager.name)
    else:
        restore_root = restore_root.resolve()
        restore_root.mkdir(parents=True, exist_ok=True)

    restored = restore_root / "restored-changelogs.sqlite3"
    if restored.exists():
        raise ValueError(f"restore target already exists: {restored}")

    try:
        shutil.copy2(backup, restored)
        os.chmod(restored, 0o600)
        source_hash = sha256_file(backup)
        restored_hash = sha256_file(restored)
        if source_hash != restored_hash:
            raise ValueError("restored database SHA-256 does not match the selected backup")

        report = verify(restored)
        if not report["ok"]:
            raise ValueError(f"restored ledger failed integrity verification: {report['failures']}")

        cx = sqlite3.connect(restored)
        cx.row_factory = sqlite3.Row
        try:
            project_count = cx.execute("SELECT count(*) FROM projects").fetchone()[0]
            entry_count = cx.execute("SELECT count(*) FROM entries").fetchone()[0]
            search_probe = cx.execute("SELECT count(*) FROM entries_fts").fetchone()[0]
            newest = cx.execute(
                "SELECT p.slug project_slug,e.id,e.occurred_at,e.title,e.source_ref "
                "FROM entries e JOIN projects p ON p.id=e.project_id "
                "ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1"
            ).fetchone()
        finally:
            cx.close()

        result = {
            "schema_version": 1,
            "ok": True,
            "backup_file": backup.name,
            "backup_sha256": source_hash,
            "restored_sha256": restored_hash,
            "projects": project_count,
            "entries": entry_count,
            "fts_entries": search_probe,
            "newest_entry": dict(newest) if newest else None,
            "integrity": report,
        }
        return result
    finally:
        if manager is not None:
            manager.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a selected GoreeCloud Changelogs backup into an isolated path and validate it")
    parser.add_argument("backup", type=Path, help="Selected backup SQLite file")
    parser.add_argument("--restore-root", type=Path, help="Optional empty controlled directory for the disposable restore")
    parser.add_argument("--report", type=Path, help="Optional JSON evidence report path")
    args = parser.parse_args()

    try:
        report = validate_restore(args.backup, args.restore_root)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
        os.chmod(args.report, 0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

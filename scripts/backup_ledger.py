#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import DB_PATH
from scripts.verify_ledger import verify


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_ledger(source: Path, destination: Path, *, force: bool = False) -> dict[str, object]:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_file():
        raise ValueError(f"ledger database does not exist: {source}")
    if source == destination:
        raise ValueError("backup destination must differ from the source database")
    if destination.exists() and not force:
        raise ValueError(f"backup destination already exists: {destination}")

    source_report = verify(source)
    if not source_report["ok"]:
        raise ValueError(f"source ledger failed integrity verification: {source_report['failures']}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
    if temporary.exists():
        temporary.unlink()

    source_uri = f"file:{source}?mode=ro"
    try:
        src = sqlite3.connect(source_uri, uri=True)
        dst = sqlite3.connect(temporary)
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
            src.close()

        os.chmod(temporary, 0o600)
        backup_report = verify(temporary)
        if not backup_report["ok"]:
            raise ValueError(f"backup ledger failed integrity verification: {backup_report['failures']}")
        if backup_report["checks"].get("entries") != source_report["checks"].get("entries"):
            raise ValueError("backup entry count does not match source ledger")
        if backup_report["checks"].get("fts_entries") != source_report["checks"].get("fts_entries"):
            raise ValueError("backup FTS count does not match source ledger")

        if destination.exists():
            destination.unlink()
        temporary.replace(destination)
        os.chmod(destination, 0o600)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise

    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "backup_file": destination.name,
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "entries": backup_report["checks"].get("entries", 0),
        "fts_entries": backup_report["checks"].get("fts_entries", 0),
        "sqlite_integrity": backup_report["checks"].get("sqlite_integrity"),
        "foreign_key_violations": len(backup_report["checks"].get("foreign_key_violations", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a consistent GoreeCloud Changelogs SQLite backup using the SQLite Online Backup API")
    parser.add_argument("destination", type=Path, help="Backup SQLite file to create")
    parser.add_argument("--database", type=Path, default=DB_PATH, help="Source ledger database")
    parser.add_argument("--manifest", type=Path, help="Optional sanitized JSON manifest path")
    parser.add_argument("--force", action="store_true", help="Replace an existing destination after successful validation")
    args = parser.parse_args()

    try:
        report = backup_ledger(args.database, args.destination, force=args.force)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    payload = {"ok": True, **report}
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(rendered + "\n", encoding="utf-8")
        os.chmod(args.manifest, 0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

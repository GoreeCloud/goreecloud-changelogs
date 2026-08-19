#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import DB_PATH, connect, init_db


def verify() -> dict[str, object]:
    init_db()
    checks: dict[str, object] = {}
    failures: list[str] = []

    with connect() as cx:
        integrity = cx.execute("PRAGMA integrity_check").fetchone()[0]
        checks["sqlite_integrity"] = integrity
        if integrity != "ok":
            failures.append(f"SQLite integrity check returned: {integrity}")

        foreign_keys = [dict(row) for row in cx.execute("PRAGMA foreign_key_check")]
        checks["foreign_key_violations"] = foreign_keys
        if foreign_keys:
            failures.append(f"Foreign-key violations: {len(foreign_keys)}")

        entry_count = cx.execute("SELECT count(*) FROM entries").fetchone()[0]
        fts_count = cx.execute("SELECT count(*) FROM entries_fts").fetchone()[0]
        checks["entries"] = entry_count
        checks["fts_entries"] = fts_count
        if entry_count != fts_count:
            failures.append(f"FTS row count {fts_count} does not match entries {entry_count}")

        broken_supersedes = cx.execute(
            "SELECT count(*) FROM entries e LEFT JOIN entries old ON old.id=e.supersedes_id "
            "WHERE e.supersedes_id IS NOT NULL AND old.id IS NULL"
        ).fetchone()[0]
        checks["broken_supersedes"] = broken_supersedes
        if broken_supersedes:
            failures.append(f"Broken supersedes references: {broken_supersedes}")

        duplicate_sources = [
            dict(row)
            for row in cx.execute(
                "SELECT project_id,occurred_at,title,source_ref,count(*) AS count "
                "FROM entries GROUP BY project_id,occurred_at,title,source_ref HAVING count(*)>1"
            )
        ]
        checks["duplicate_source_identities"] = duplicate_sources
        if duplicate_sources:
            failures.append(f"Duplicate source identities: {len(duplicate_sources)}")

        empty_titles = cx.execute("SELECT count(*) FROM entries WHERE trim(title)='' ").fetchone()[0]
        checks["empty_titles"] = empty_titles
        if empty_titles:
            failures.append(f"Entries with empty titles: {empty_titles}")

    return {
        "database": str(DB_PATH),
        "ok": not failures,
        "checks": checks,
        "failures": failures,
    }


def main() -> int:
    report = verify()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

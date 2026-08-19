#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import DB_PATH


def verify(database: Path = DB_PATH) -> dict[str, object]:
    database = database.resolve()
    checks: dict[str, object] = {}
    failures: list[str] = []

    if not database.is_file():
        return {
            "database": str(database),
            "ok": False,
            "checks": checks,
            "failures": ["Ledger database does not exist"],
        }

    uri = f"file:{database}?mode=ro"
    try:
        cx = sqlite3.connect(uri, uri=True)
        cx.row_factory = sqlite3.Row
        cx.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error as exc:
        return {
            "database": str(database),
            "ok": False,
            "checks": checks,
            "failures": [f"Unable to open ledger read-only: {exc}"],
        }

    try:
        integrity = cx.execute("PRAGMA integrity_check").fetchone()[0]
        checks["sqlite_integrity"] = integrity
        if integrity != "ok":
            failures.append(f"SQLite integrity check returned: {integrity}")

        foreign_keys = [dict(row) for row in cx.execute("PRAGMA foreign_key_check")]
        checks["foreign_key_violations"] = foreign_keys
        if foreign_keys:
            failures.append(f"Foreign-key violations: {len(foreign_keys)}")

        required_tables = {"projects", "entries", "entries_fts"}
        tables = {row[0] for row in cx.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        missing_tables = sorted(required_tables - tables)
        checks["missing_required_tables"] = missing_tables
        if missing_tables:
            failures.append(f"Missing required tables: {', '.join(missing_tables)}")
            return {
                "database": str(database),
                "ok": False,
                "checks": checks,
                "failures": failures,
            }

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
    except sqlite3.Error as exc:
        failures.append(f"Ledger verification query failed: {exc}")
    finally:
        cx.close()

    return {
        "database": str(database),
        "ok": not failures,
        "checks": checks,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify GoreeCloud Changelogs ledger integrity without modifying the database")
    parser.add_argument("--database", type=Path, default=DB_PATH, help="Ledger database to verify")
    args = parser.parse_args()
    report = verify(args.database)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import connect, init_db
from scripts.import_docx import clean_project, parse, slugify


def source_documents(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and "Change Log" in path.name and not path.name.startswith("~$")
    )


def reconcile(folder: Path) -> dict[str, object]:
    init_db()
    docs = source_documents(folder)
    expected: dict[tuple[str, str, str, str], dict[str, str]] = {}
    source_counts: Counter[str] = Counter()

    for path in docs:
        project = clean_project(path)
        slug = slugify(project)
        for entry in parse(path):
            identity = (slug, entry["occurred_at"], entry["title"], path.name)
            expected[identity] = {
                "project": project,
                "project_slug": slug,
                "occurred_at": entry["occurred_at"],
                "title": entry["title"],
                "source_ref": path.name,
            }
            source_counts[slug] += 1

    with connect() as cx:
        rows = [
            dict(row)
            for row in cx.execute(
                "SELECT p.slug project_slug,p.name project_name,e.occurred_at,e.title,e.source_ref "
                "FROM entries e JOIN projects p ON p.id=e.project_id"
            )
        ]

    actual = {
        (row["project_slug"], row["occurred_at"], row["title"], row["source_ref"]): row
        for row in rows
        if row["source_ref"]
    }
    missing_keys = sorted(set(expected) - set(actual))
    unexpected_keys = sorted(set(actual) - set(expected))

    actual_counts: Counter[str] = Counter(row["project_slug"] for row in actual.values())
    projects: dict[str, dict[str, int]] = defaultdict(lambda: {"source": 0, "ledger": 0, "difference": 0})
    for slug, count in source_counts.items():
        projects[slug]["source"] = count
    for slug, count in actual_counts.items():
        projects[slug]["ledger"] = count
    for values in projects.values():
        values["difference"] = values["ledger"] - values["source"]

    report = {
        "ok": not missing_keys and not unexpected_keys,
        "source_documents": len(docs),
        "source_entries": len(expected),
        "ledger_imported_entries": len(actual),
        "missing_entries": [expected[key] for key in missing_keys],
        "unexpected_entries": [actual[key] for key in unexpected_keys],
        "project_counts": dict(sorted(projects.items())),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile DOCX change-log sources against the GoreeCloud Changelogs ledger")
    parser.add_argument("folder", type=Path, help="Folder containing historical DOCX change-log documents")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    report = reconcile(args.folder)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

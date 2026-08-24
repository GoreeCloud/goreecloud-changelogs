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
from scripts.import_docx import FIELD_NAMES, clean_project, parse_with_report, slugify, source_documents

IDENTITY_FIELDS = ("project_slug", "occurred_at", "title", "source_ref")
CONTENT_FIELDS = tuple(FIELD_NAMES)


def _identity(record: dict[str, object]) -> tuple[str, str, str, str]:
    return tuple(str(record[field]) for field in IDENTITY_FIELDS)  # type: ignore[return-value]


def _normalized(value: object) -> str:
    return "\n".join(line.rstrip() for line in str(value or "").strip().splitlines())


def reconcile(folder: Path) -> dict[str, object]:
    init_db()
    docs = source_documents(folder)
    expected: dict[tuple[str, str, str, str], dict[str, str]] = {}
    source_counts: Counter[str] = Counter()
    identity_counts: Counter[tuple[str, str, str, str]] = Counter()
    document_reports: list[dict[str, object]] = []

    for path in docs:
        project = clean_project(path)
        slug = slugify(project)
        entries, parse_report = parse_with_report(path)
        parse_report["project"] = project
        parse_report["project_slug"] = slug
        document_reports.append(parse_report)
        for entry in entries:
            record = {
                "project": project,
                "project_slug": slug,
                "occurred_at": entry["occurred_at"],
                "title": entry["title"],
                "source_ref": path.name,
                **{field: entry.get(field, "") for field in CONTENT_FIELDS},
            }
            identity = _identity(record)
            identity_counts[identity] += 1
            expected.setdefault(identity, record)
            source_counts[slug] += 1

    duplicate_source_identities = [
        {"project_slug": key[0], "occurred_at": key[1], "title": key[2], "source_ref": key[3], "count": count}
        for key, count in sorted(identity_counts.items())
        if count > 1
    ]
    source_errors = [report for report in document_reports if not report["ok"]]

    columns = ",".join(f"e.{field}" for field in CONTENT_FIELDS)
    with connect() as cx:
        rows = [
            dict(row)
            for row in cx.execute(
                "SELECT p.slug project_slug,p.name project_name,e.occurred_at,e.title,e.source_ref,"
                + columns
                + " FROM entries e JOIN projects p ON p.id=e.project_id"
            )
        ]

    ledger_identity_counts: Counter[tuple[str, str, str, str]] = Counter()
    actual: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for row in rows:
        if not row["source_ref"]:
            continue
        identity = _identity(row)
        ledger_identity_counts[identity] += 1
        actual.setdefault(identity, row)

    duplicate_ledger_identities = [
        {"project_slug": key[0], "occurred_at": key[1], "title": key[2], "source_ref": key[3], "count": count}
        for key, count in sorted(ledger_identity_counts.items())
        if count > 1
    ]

    missing_keys = sorted(set(expected) - set(actual))
    unexpected_keys = sorted(set(actual) - set(expected))

    content_mismatches: list[dict[str, object]] = []
    for key in sorted(set(expected) & set(actual)):
        differing = [
            field
            for field in CONTENT_FIELDS
            if _normalized(expected[key].get(field)) != _normalized(actual[key].get(field))
        ]
        if differing:
            content_mismatches.append(
                {
                    "project_slug": key[0],
                    "occurred_at": key[1],
                    "title": key[2],
                    "source_ref": key[3],
                    "fields": differing,
                }
            )

    actual_counts: Counter[str] = Counter(row["project_slug"] for row in actual.values())
    projects: dict[str, dict[str, int]] = defaultdict(lambda: {"source": 0, "ledger": 0, "difference": 0})
    for slug, count in source_counts.items():
        projects[slug]["source"] = count
    for slug, count in actual_counts.items():
        projects[slug]["ledger"] = count
    for values in projects.values():
        values["difference"] = values["ledger"] - values["source"]

    ok = not any(
        (
            missing_keys,
            unexpected_keys,
            source_errors,
            duplicate_source_identities,
            duplicate_ledger_identities,
            content_mismatches,
        )
    )
    return {
        "schema_version": 2,
        "ok": ok,
        "source_documents": len(docs),
        "source_entries": sum(source_counts.values()),
        "unique_source_entries": len(expected),
        "ledger_imported_entries": len(actual),
        "source_errors": source_errors,
        "duplicate_source_identities": duplicate_source_identities,
        "duplicate_ledger_identities": duplicate_ledger_identities,
        "content_mismatches": content_mismatches,
        "missing_entries": [expected[key] for key in missing_keys],
        "unexpected_entries": [actual[key] for key in unexpected_keys],
        "project_counts": dict(sorted(projects.items())),
        "document_reports": document_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile DOCX change-log sources against the GoreeCloud Changelogs ledger")
    parser.add_argument("folder", type=Path, help="Folder containing historical DOCX change-log documents")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    try:
        report = reconcile(args.folder)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

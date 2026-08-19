#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from dateutil import parser as dateparser, tz
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import connect, init_db

DATE_RE = re.compile(
    r"^(?P<date>(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+20\d{2}|20\d{2}-\d{2}-\d{2})(?:\s+(?:at\s+)?\d{1,2}:\d{2}(?:\s*[AP]M)?(?:\s+[A-Z]{2,5})?)?)\s+[—-]\s+(?P<title>.+)$",
    re.I,
)
PROBABLE_DATE_RE = re.compile(
    r"^(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+20\d{2}|20\d{2}-\d{2}-\d{2})",
    re.I,
)

LABELS = {
    "change type or category": "category",
    "change category": "category",
    "affected project and environment": "affected",
    "affected environment": "affected",
    "affected project": "affected",
    "affected application or service": "affected",
    "affected project/component": "affected",
    "purpose": "purpose",
    "summary": "summary",
    "previous behavior or configuration": "previous_state",
    "previous state": "previous_state",
    "changes completed": "changes",
    "changes made": "changes",
    "implementation": "implementation",
    "technical implementation details": "implementation",
    "validation and testing performed": "validation",
    "validation and verification performed": "validation",
    "validation and testing": "validation",
    "validation": "validation",
    "final state and safety boundary": "final_state",
    "final state": "final_state",
    "known issues or limitations": "limitations",
    "known issues, limitations, or follow-up work": "limitations",
    "rollback information": "rollback",
    "rollback or recovery information": "rollback",
    "rollback or recovery": "rollback",
    "follow-up actions": "follow_up",
    "follow-up": "follow_up",
}
FIELD_NAMES = tuple(sorted(set(LABELS.values())))


def normalize_date(raw: str) -> str:
    text = raw.replace("CDT", "-0500").replace("CST", "-0600")
    value = dateparser.parse(text)
    if value is None:
        raise ValueError(f"unable to parse historical timestamp: {raw}")
    if value.tzinfo is None:
        value = value.replace(tzinfo=tz.gettz("America/Chicago"))
    return value.isoformat()


def clean_project(path: Path) -> str:
    name = path.stem
    name = name.replace("GoreeCloud — Change Log — ", "")
    name = name.replace("GoreeCloud ", "").replace(" Change Log", "").strip(" —")
    return name or "GoreeCloud"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def source_documents(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise ValueError(f"historical source folder does not exist or is not a directory: {folder}")
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".docx"
        and "Change Log" in path.name
        and not path.name.startswith("~$")
    )


def parse_with_report(path: Path) -> tuple[list[dict[str, str]], dict[str, object]]:
    document = Document(path)
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    starts: list[tuple[int, re.Match[str]]] = []
    ambiguous_headings: list[dict[str, object]] = []

    for index, text in enumerate(paragraphs):
        match = DATE_RE.match(text)
        if match:
            starts.append((index, match))
        elif PROBABLE_DATE_RE.match(text):
            ambiguous_headings.append({"paragraph": index + 1, "text": text})

    output: list[dict[str, str]] = []
    invalid_dates: list[dict[str, object]] = []
    for offset, (start, match) in enumerate(starts):
        end = starts[offset + 1][0] if offset + 1 < len(starts) else len(paragraphs)
        body = paragraphs[start + 1 : end]
        fields = {key: "" for key in FIELD_NAMES}
        current = "summary"
        for text in body:
            label = None
            value = ""
            if ":" in text:
                lhs, rhs = text.split(":", 1)
                key = lhs.strip().lower()
                if key in LABELS:
                    label = LABELS[key]
                    value = rhs.strip()
            if label:
                current = label
                if value:
                    fields[current] = (fields[current] + "\n" + value).strip()
            else:
                fields[current] = (fields[current] + "\n" + text.lstrip("• ").strip()).strip()

        raw_date = match.group("date").strip()
        try:
            occurred_at = normalize_date(raw_date)
        except (TypeError, ValueError, OverflowError) as exc:
            invalid_dates.append(
                {"paragraph": start + 1, "raw": raw_date, "title": match.group("title").strip(), "error": str(exc)}
            )
            continue
        output.append({"occurred_at": occurred_at, "title": match.group("title").strip(), **fields})

    report = {
        "source_ref": path.name,
        "paragraphs": len(paragraphs),
        "entries": len(output),
        "preamble_paragraphs": starts[0][0] if starts else len(paragraphs),
        "ambiguous_headings": ambiguous_headings,
        "invalid_dates": invalid_dates,
        "has_entries": bool(output),
        "ok": bool(output) and not ambiguous_headings and not invalid_dates,
    }
    return output, report


def parse(path: Path) -> list[dict[str, str]]:
    entries, _ = parse_with_report(path)
    return entries


def import_folder(folder: Path, *, dry_run: bool = False, strict: bool = False) -> dict[str, object]:
    if not dry_run:
        init_db()
    documents = source_documents(folder)
    reports: list[dict[str, object]] = []
    parsed: list[tuple[Path, str, str, dict[str, str]]] = []
    identities: Counter[tuple[str, str, str, str]] = Counter()

    for path in documents:
        project = clean_project(path)
        slug = slugify(project)
        entries, report = parse_with_report(path)
        report["project"] = project
        report["project_slug"] = slug
        reports.append(report)
        for entry in entries:
            identity = (slug, entry["occurred_at"], entry["title"], path.name)
            identities[identity] += 1
            parsed.append((path, project, slug, entry))

    duplicate_source_identities = [
        {"project_slug": key[0], "occurred_at": key[1], "title": key[2], "source_ref": key[3], "count": count}
        for key, count in sorted(identities.items())
        if count > 1
    ]
    source_errors = [report for report in reports if not report["ok"]]
    if strict and (source_errors or duplicate_source_identities):
        return {
            "ok": False,
            "strict": True,
            "dry_run": dry_run,
            "documents": len(documents),
            "parsed_entries": len(parsed),
            "inserted_entries": 0,
            "existing_entries": 0,
            "source_errors": source_errors,
            "duplicate_source_identities": duplicate_source_identities,
            "document_reports": reports,
        }

    inserted = 0
    existing = 0
    if not dry_run:
        with connect() as cx:
            project_ids: dict[str, int] = {}
            for path, project, slug, entry in parsed:
                if slug not in project_ids:
                    cx.execute(
                        "INSERT INTO projects(slug,name) VALUES(?,?) ON CONFLICT(slug) DO NOTHING",
                        (slug, project),
                    )
                    project_ids[slug] = cx.execute("SELECT id FROM projects WHERE slug=?", (slug,)).fetchone()["id"]
                project_id = project_ids[slug]
                exists = cx.execute(
                    "SELECT 1 FROM entries WHERE project_id=? AND occurred_at=? AND title=? AND source_ref=?",
                    (project_id, entry["occurred_at"], entry["title"], path.name),
                ).fetchone()
                if exists:
                    existing += 1
                    continue
                cx.execute(
                    "INSERT INTO entries(project_id,occurred_at,title,category,summary,purpose,affected,previous_state,changes,implementation,validation,final_state,limitations,rollback,follow_up,source_ref) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        project_id,
                        entry["occurred_at"],
                        entry["title"],
                        entry["category"],
                        entry["summary"],
                        entry["purpose"],
                        entry["affected"],
                        entry["previous_state"],
                        entry["changes"],
                        entry["implementation"],
                        entry["validation"],
                        entry["final_state"],
                        entry["limitations"],
                        entry["rollback"],
                        entry["follow_up"],
                        path.name,
                    ),
                )
                inserted += 1

    return {
        "ok": not source_errors and not duplicate_source_identities,
        "strict": strict,
        "dry_run": dry_run,
        "documents": len(documents),
        "parsed_entries": len(parsed),
        "inserted_entries": inserted,
        "existing_entries": existing,
        "source_errors": source_errors,
        "duplicate_source_identities": duplicate_source_identities,
        "document_reports": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import GoreeCloud historical DOCX change logs into the append-only ledger")
    parser.add_argument("folder", nargs="?", type=Path, default=Path("/mnt/data"))
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate sources without writing the ledger")
    parser.add_argument("--strict", action="store_true", help="Reject the entire import when any source ambiguity is detected")
    parser.add_argument("--report", type=Path, help="Optional JSON diagnostic report path")
    args = parser.parse_args()

    try:
        report = import_folder(args.folder, dry_run=args.dry_run, strict=args.strict)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Parse historical GoreeCloud DOCX change logs into non-authoritative staging records.

This tool deliberately does not write the Changelogs ledger. It preserves source provenance and
historical text for later reviewed mapping into Core v1 without inventing lifecycle evidence.
Only Python's standard library is used; DOCX paragraph text is read directly from the OOXML ZIP.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DATE_RE = re.compile(
    r"^(?P<date>(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+20\d{2}|20\d{2}-\d{2}-\d{2})(?:\s+(?:at\s+)?\d{1,2}:\d{2}(?:\s*[AP]M)?(?:\s+(?:CST|CDT|UTC))?)?)\s+[—-]\s+(?P<title>.+)$",
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
CONTENT_FIELDS = tuple(sorted(set(LABELS.values())))


def clean_project(path: Path) -> str:
    name = path.stem
    for prefix in ("GoreeCloud — Change Log — ", "Change Log — "):
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
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


def _docx_paragraphs(path: Path) -> list[str]:
    try:
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise ValueError(f"unable to read DOCX source {path.name}: {type(exc).__name__}") from exc

    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise ValueError(f"invalid DOCX XML in {path.name}") from exc

    paragraphs: list[str] = []
    namespace = {"w": W_NS}
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def _parse_local_datetime(text: str) -> datetime:
    normalized = re.sub(r"\s+at\s+", " ", text.strip(), flags=re.I).replace("Sept ", "Sep ")
    named_tz = None
    tz_match = re.search(r"\s+(CST|CDT|UTC)$", normalized, flags=re.I)
    if tz_match:
        token = tz_match.group(1).upper()
        normalized = normalized[: tz_match.start()].strip()
        named_tz = {
            "CST": timezone(timedelta(hours=-6)),
            "CDT": timezone(timedelta(hours=-5)),
            "UTC": timezone.utc,
        }[token]

    formats = (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d",
        "%B %d, %Y %H:%M",
        "%B %d, %Y %I:%M %p",
        "%B %d, %Y",
        "%b %d, %Y %H:%M",
        "%b %d, %Y %I:%M %p",
        "%b %d, %Y",
    )
    parsed = None
    for fmt in formats:
        try:
            parsed = datetime.strptime(normalized, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        raise ValueError(f"unable to parse historical timestamp: {text}")
    return parsed.replace(tzinfo=named_tz or ZoneInfo("America/Chicago"))


def normalize_date(raw: str) -> str:
    return _parse_local_datetime(raw).isoformat()


def parse_with_report(path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    paragraphs = _docx_paragraphs(path)
    starts: list[tuple[int, re.Match[str]]] = []
    ambiguous_headings: list[dict[str, object]] = []

    for index, text in enumerate(paragraphs):
        match = DATE_RE.match(text)
        if match:
            starts.append((index, match))
        elif PROBABLE_DATE_RE.match(text):
            ambiguous_headings.append({"paragraph": index + 1, "text": text})

    project = clean_project(path)
    project_slug = slugify(project)
    candidates: list[dict[str, object]] = []
    invalid_dates: list[dict[str, object]] = []

    for offset, (start, match) in enumerate(starts):
        end = starts[offset + 1][0] if offset + 1 < len(starts) else len(paragraphs)
        fields = {key: "" for key in CONTENT_FIELDS}
        current = "summary"
        for text in paragraphs[start + 1 : end]:
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
        except ValueError as exc:
            invalid_dates.append(
                {
                    "paragraph": start + 1,
                    "raw": raw_date,
                    "title": match.group("title").strip(),
                    "error": str(exc),
                }
            )
            continue

        candidates.append(
            {
                "staging_schema_version": 1,
                "source_ref": path.name,
                "project": project,
                "project_slug": project_slug,
                "occurred_at": occurred_at,
                "title": match.group("title").strip(),
                "historical_fields": fields,
            }
        )

    report = {
        "source_ref": path.name,
        "project": project,
        "project_slug": project_slug,
        "paragraphs": len(paragraphs),
        "entries": len(candidates),
        "preamble_paragraphs": starts[0][0] if starts else len(paragraphs),
        "ambiguous_headings": ambiguous_headings,
        "invalid_dates": invalid_dates,
        "has_entries": bool(candidates),
        "ok": bool(candidates) and not ambiguous_headings and not invalid_dates,
    }
    return candidates, report


def stage_folder(folder: Path) -> tuple[dict[str, object], dict[str, object]]:
    documents = source_documents(folder)
    candidates: list[dict[str, object]] = []
    document_reports: list[dict[str, object]] = []
    identities: Counter[tuple[str, str, str, str]] = Counter()

    for path in documents:
        parsed, report = parse_with_report(path)
        candidates.extend(parsed)
        document_reports.append(report)
        for candidate in parsed:
            identity = (
                str(candidate["project_slug"]),
                str(candidate["occurred_at"]),
                str(candidate["title"]),
                str(candidate["source_ref"]),
            )
            identities[identity] += 1

    duplicates = [
        {
            "project_slug": key[0],
            "occurred_at": key[1],
            "title": key[2],
            "source_ref": key[3],
            "count": count,
        }
        for key, count in sorted(identities.items())
        if count > 1
    ]
    source_errors = [report for report in document_reports if not report["ok"]]
    ok = bool(documents) and not source_errors and not duplicates

    diagnostics = {
        "schema_version": 1,
        "ok": ok,
        "source_documents": len(documents),
        "staged_entries": len(candidates),
        "source_errors": source_errors,
        "duplicate_source_identities": duplicates,
        "document_reports": document_reports,
        "ledger_written": False,
    }
    bundle = {
        "schema_version": 1,
        "authoritative": False,
        "purpose": "historical-docx-migration-staging",
        "candidates": candidates,
    }
    return bundle, diagnostics


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse GoreeCloud historical DOCX change logs into non-authoritative staging records"
    )
    parser.add_argument("folder", type=Path)
    parser.add_argument("--report", type=Path, help="Write privacy-minimized parser diagnostics")
    parser.add_argument(
        "--candidates-output",
        type=Path,
        help="Write the full staging bundle. Treat this output as internal historical data.",
    )
    args = parser.parse_args()

    try:
        bundle, diagnostics = stage_folder(args.folder)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2

    rendered = json.dumps(diagnostics, indent=2, sort_keys=True)
    print(rendered)
    if args.report:
        _write_json(args.report, diagnostics)
    if args.candidates_output:
        _write_json(args.candidates_output, bundle)
    return 0 if diagnostics["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

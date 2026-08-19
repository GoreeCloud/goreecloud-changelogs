#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

from dateutil import parser as dateparser, tz
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import connect, init_db

DATE_RE = re.compile(r"^(?P<date>(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+20\d{2}|20\d{2}-\d{2}-\d{2})(?:\s+(?:at\s+)?\d{1,2}:\d{2}(?:\s*[AP]M)?(?:\s+[A-Z]{2,5})?)?)\s+[—-]\s+(?P<title>.+)$", re.I)

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
    "implementation": "implementation",
    "technical implementation details": "implementation",
    "validation and testing performed": "validation",
    "validation and testing": "validation",
    "validation": "validation",
    "final state": "final_state",
    "known issues or limitations": "limitations",
    "known issues, limitations, or follow-up work": "limitations",
    "rollback information": "rollback",
    "rollback or recovery information": "rollback",
    "follow-up actions": "follow_up",
    "follow-up": "follow_up",
}


def normalize_date(raw: str) -> str:
    text = raw.replace("CDT", "-0500").replace("CST", "-0600")
    try:
        value = dateparser.parse(text)
        if value.tzinfo is None:
            value = value.replace(tzinfo=tz.gettz("America/Chicago"))
        return value.isoformat()
    except Exception:
        return raw


def clean_project(path: Path) -> str:
    name = path.name.replace("GoreeCloud — Change Log — ", "").replace("GoreeCloud ", "").replace(" Change Log", "").strip(" —")
    return name or "GoreeCloud"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def parse(path: Path):
    document = Document(path)
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    starts = []
    for index, text in enumerate(paragraphs):
        match = DATE_RE.match(text)
        if match:
            starts.append((index, match))

    output = []
    for offset, (start, match) in enumerate(starts):
        end = starts[offset + 1][0] if offset + 1 < len(starts) else len(paragraphs)
        body = paragraphs[start + 1 : end]
        fields = {key: "" for key in set(LABELS.values())}
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
        output.append({"occurred_at": normalize_date(match.group("date").strip()), "title": match.group("title").strip(), **fields})
    return output


def main(folder: str) -> None:
    init_db()
    root = Path(folder)
    documents = [path for path in root.iterdir() if path.is_file() and "Change Log" in path.name and not path.name.startswith("~$")]
    inserted = 0
    with connect() as cx:
        for path in documents:
            project = clean_project(path)
            slug = slugify(project)
            cx.execute("INSERT INTO projects(slug,name) VALUES(?,?) ON CONFLICT(slug) DO NOTHING", (slug, project))
            project_id = cx.execute("SELECT id FROM projects WHERE slug=?", (slug,)).fetchone()["id"]
            for entry in parse(path):
                exists = cx.execute("SELECT 1 FROM entries WHERE project_id=? AND occurred_at=? AND title=?", (project_id, entry["occurred_at"], entry["title"])).fetchone()
                if exists:
                    continue
                cx.execute(
                    "INSERT INTO entries(project_id,occurred_at,title,category,summary,purpose,affected,previous_state,changes,implementation,validation,final_state,limitations,rollback,follow_up,source_ref) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (project_id, entry["occurred_at"], entry["title"], entry["category"], entry["summary"], entry["purpose"], entry["affected"], entry["previous_state"], entry["changes"], entry["implementation"], entry["validation"], entry["final_state"], entry["limitations"], entry["rollback"], entry["follow_up"], path.name),
                )
                inserted += 1
    print(f"Imported {inserted} new entries from {len(documents)} change-log documents")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/data")

from pathlib import Path

from docx import Document

import app.db as db
from scripts.import_docx import import_folder, parse_with_report
from scripts.reconcile_docx import reconcile


def write_docx(path: Path, paragraphs: list[str]) -> None:
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(path)


def test_parser_preserves_structured_fields_and_reports_clean_source(tmp_path):
    path = tmp_path / "GoreeCloud — Change Log — Example.docx"
    write_docx(
        path,
        [
            "Example Change Log",
            "August 19, 2026 at 2:00 AM CDT — Structured migration entry",
            "Change type or category: Migration",
            "Purpose: Preserve historical data.",
            "Changes made: Added deterministic parsing.",
            "Validation and verification performed: Parser regression passed.",
            "Final state and safety boundary: Source remained read-only.",
            "Rollback or recovery: Retain the source document.",
        ],
    )

    entries, report = parse_with_report(path)
    assert report["ok"] is True
    assert report["preamble_paragraphs"] == 1
    assert len(entries) == 1
    entry = entries[0]
    assert entry["title"] == "Structured migration entry"
    assert entry["category"] == "Migration"
    assert entry["changes"] == "Added deterministic parsing."
    assert entry["validation"] == "Parser regression passed."
    assert entry["final_state"] == "Source remained read-only."
    assert entry["rollback"] == "Retain the source document."
    assert entry["occurred_at"].endswith("-05:00")


def test_strict_dry_run_fails_on_ambiguous_historical_heading(tmp_path):
    path = tmp_path / "GoreeCloud — Change Log — Example.docx"
    write_docx(path, ["August 19, 2026 historical entry missing required separator"])

    report = import_folder(tmp_path, dry_run=True, strict=True)
    assert report["ok"] is False
    assert report["inserted_entries"] == 0
    assert len(report["source_errors"]) == 1
    assert report["source_errors"][0]["ambiguous_headings"]


def test_import_is_idempotent_and_reconciliation_is_exact(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "ledger.sqlite3")
    source = tmp_path / "sources"
    source.mkdir()
    path = source / "GoreeCloud — Change Log — Example.docx"
    write_docx(
        path,
        [
            "August 19, 2026 at 2:10 AM CDT — Idempotent import entry",
            "Purpose: Prove repeatable migration execution.",
            "Validation: Repeat import does not duplicate history.",
        ],
    )

    first = import_folder(source, strict=True)
    second = import_folder(source, strict=True)
    assert first["ok"] is True
    assert first["inserted_entries"] == 1
    assert first["existing_entries"] == 0
    assert second["ok"] is True
    assert second["inserted_entries"] == 0
    assert second["existing_entries"] == 1

    report = reconcile(source)
    assert report["ok"] is True
    assert report["source_documents"] == 1
    assert report["source_entries"] == 1
    assert report["unique_source_entries"] == 1
    assert report["ledger_imported_entries"] == 1
    assert report["missing_entries"] == []
    assert report["unexpected_entries"] == []

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.docx_migration.parse_docx import parse_with_report, stage_folder


def write_docx(path: Path, paragraphs: list[str]) -> None:
    def escape(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
        for text in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document)


class DocxMigrationParserTests(unittest.TestCase):
    def test_valid_source_stages_provenance_without_ledger_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "Change Log — Terminal.docx"
            write_docx(
                source,
                [
                    "August 20, 2026 at 6:35 AM CDT — Added native session model",
                    "Purpose: Continue the native Terminal migration.",
                    "Changes completed: Added isolated session state.",
                    "Validation: Exact-head CI passed.",
                ],
            )

            bundle, diagnostics = stage_folder(folder)
            self.assertTrue(diagnostics["ok"])
            self.assertFalse(diagnostics["ledger_written"])
            self.assertFalse(bundle["authoritative"])
            self.assertEqual(len(bundle["candidates"]), 1)
            candidate = bundle["candidates"][0]
            self.assertEqual(candidate["project_slug"], "terminal")
            self.assertEqual(candidate["source_ref"], source.name)
            self.assertEqual(candidate["title"], "Added native session model")
            self.assertTrue(str(candidate["occurred_at"]).endswith("-05:00"))
            self.assertIn("Continue the native Terminal migration.", candidate["historical_fields"]["purpose"])

    def test_ambiguous_date_heading_fails_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "Change Log — Manager.docx"
            write_docx(source, ["August 20, 2026 Manager work without separator"])
            candidates, report = parse_with_report(source)
            self.assertEqual(candidates, [])
            self.assertFalse(report["ok"])
            self.assertEqual(len(report["ambiguous_headings"]), 1)

    def test_duplicate_source_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "Change Log — Location.docx"
            heading = "2026-08-20 — Same historical event"
            write_docx(source, [heading, "Summary: first", heading, "Summary: second"])
            _, diagnostics = stage_folder(folder)
            self.assertFalse(diagnostics["ok"])
            self.assertEqual(len(diagnostics["duplicate_source_identities"]), 1)

    def test_diagnostics_do_not_copy_historical_body_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "Change Log — Changelogs.docx"
            sentinel = "PRIVATE-HISTORICAL-BODY-SENTINEL"
            write_docx(
                source,
                [
                    "2026-08-20 — Historical entry",
                    f"Implementation: {sentinel}",
                ],
            )
            _, diagnostics = stage_folder(folder)
            self.assertTrue(diagnostics["ok"])
            self.assertNotIn(sentinel, repr(diagnostics))

    def test_non_docx_and_temporary_files_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "notes.txt").write_text("ignore", encoding="utf-8")
            write_docx(folder / "~$Change Log — Temp.docx", ["2026-08-20 — ignored"])
            bundle, diagnostics = stage_folder(folder)
            self.assertFalse(diagnostics["ok"])
            self.assertEqual(diagnostics["source_documents"], 0)
            self.assertEqual(bundle["candidates"], [])


if __name__ == "__main__":
    unittest.main()

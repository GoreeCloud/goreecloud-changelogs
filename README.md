# GoreeCloud Changelogs

GoreeCloud Changelogs is the authoritative historical change ledger for GoreeCloud. It replaces per-project long-form change-log documents with structured, searchable, append-only historical entries.

## Product surfaces

- Web: `https://changelogs.goreecloud.com`
- Installable Glaze UI PWA for phones and tablets
- Native Android client foundation under `mobile/android`
- JSON API under `/api/v1`

## Core guarantees

- Append-only historical entries; corrections create superseding entries rather than rewriting history.
- Project/component timelines and a global cross-GoreeCloud timeline.
- Full-text search and project filtering.
- Local-first assets with no analytics, advertising, third-party fonts, or remote UI dependencies.
- Wardveil Security presentation on security-sensitive administrative surfaces.
- Import tooling for the existing GoreeCloud Microsoft Word change-log documents.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Initialize or import existing history:

```bash
python scripts/import_docx.py /path/to/change-log-folder
```

Run validation:

```bash
pytest -q
python -m compileall -q app scripts
```

## Production boundary

The initial source foundation uses SQLite as a single-node ledger backend. Production deployment must remain behind GoreeCloud's approved HTTPS publication path, use a dedicated service identity, keep reusable secrets outside the repository, and complete backup/restore validation before this application replaces the Google Drive change logs as the authoritative historical record.

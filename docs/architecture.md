# GoreeCloud Changelogs Architecture

## Role

GoreeCloud Changelogs is the structured historical ledger for material GoreeCloud changes. It is designed to replace the maintenance burden of separate long-form change-log documents while preserving their historical detail.

## Data model

Each project or component has one project record and any number of append-only change entries. An entry records the event time, title, category, purpose, affected scope, prior state, changes, implementation details, validation, final state, limitations, recovery information, follow-up work, release context, environment, and source provenance.

Historical corrections are represented by later entries through the `supersedes_id` relationship rather than by silently rewriting prior history.

## Interfaces

The web interface provides the human-readable global timeline, project filtering, full-text search, and record-detail views. `/api/v1` provides the shared JSON contract for future GoreeCloud integrations and native clients. The Android project consumes the same API boundary rather than maintaining an independent history store.

## Security boundary

Read access and service publication are deployment-policy decisions. API writes fail closed when no write token is configured and require a bearer credential when enabled. Secrets remain external to the repository and must not be stored in historical records.

## Persistence

SQLite is the first single-node persistence implementation and uses FTS5 for search. Before approving concurrent multi-writer production use, the persistence layer should be migrated to the approved PostgreSQL production model or otherwise validated for the final workload.

## Migration

`scripts/import_docx.py` imports the existing Microsoft Word change-log documents. The old documents remain recovery/migration source material until import completeness, backups, restore testing, and application production acceptance are complete.

# Changelog

All notable source releases of GoreeCloud Changelogs will be documented here. This repository changelog tracks releases of the Changelogs application itself; historical GoreeCloud operational events belong in the application ledger.

## 0.1.0 — Initial foundation

- Added FastAPI web and JSON API service.
- Added SQLite append-only historical ledger schema with FTS5 search.
- Added database-enforced immutability for historical entries so UPDATE and DELETE operations fail closed.
- Added source-identity and timeline indexes plus supersedes-reference integrity constraints.
- Added a non-mutating read-only ledger verifier covering SQLite integrity, foreign keys, FTS synchronization, supersedes references, duplicate source identities, required titles, and missing-schema failures.
- Hardened the DOCX importer with strict dry-run preflight, per-document parser diagnostics, ambiguous date-heading detection, invalid-date reporting, duplicate source-identity detection, source-reference-aware idempotency, and machine-readable reports.
- Added deterministic DOCX-to-ledger reconciliation reporting with parser/source errors, duplicate-source identities, per-project source-versus-ledger counts, and missing/unexpected identity detection.
- Added SQLite Online Backup API tooling, sanitized SHA-256 backup manifests, isolated restore validation, and disposable backup/restore CI proof.
- Added Glaze UI timeline, project filter, search, and entry-detail surfaces.
- Added fail-closed scoped read/write API authentication and controlled JSON export for integrations.
- Added hardened Docker and Docker Compose foundation with a read-only root filesystem, restricted temporary filesystem, dropped Linux capabilities, no-new-privileges, bounded process count, bounded local logs, graceful shutdown, and explicit fail-closed read/write API environment controls.
- Added source, ledger, migration, and recovery validation through GitHub Actions.
- Added native Android Jetpack Compose project foundation.
- Added migration, backup/restore, architecture, API, security, and production-readiness documentation.

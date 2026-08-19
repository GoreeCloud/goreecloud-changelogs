# Changelog

All notable source releases of GoreeCloud Changelogs will be documented here. This repository changelog tracks releases of the Changelogs application itself; historical GoreeCloud operational events belong in the application ledger.

## 0.1.0 — Initial foundation

- Added FastAPI web and JSON API service.
- Added SQLite append-only historical ledger schema with FTS5 search.
- Added database-enforced immutability for historical entries so UPDATE and DELETE operations fail closed.
- Added source-identity and timeline indexes plus supersedes-reference integrity constraints.
- Added an automated ledger verifier covering SQLite integrity, foreign keys, FTS synchronization, supersedes references, duplicate source identities, and required titles.
- Added DOCX-to-ledger migration reconciliation reporting with per-project source-versus-ledger counts and missing/unexpected identity detection.
- Added Glaze UI timeline, project filter, search, and entry-detail surfaces.
- Added fail-closed scoped read/write API authentication and controlled JSON export for integrations.
- Added historical Microsoft Word change-log importer.
- Added hardened Docker and Docker Compose foundation with a read-only root filesystem, restricted temporary filesystem, dropped Linux capabilities, no-new-privileges, bounded process count, bounded local logs, graceful shutdown, and explicit fail-closed read/write API environment controls.
- Added source and ledger validation through GitHub Actions.
- Added native Android Jetpack Compose project foundation.
- Added migration, architecture, API, security, and production-readiness documentation.

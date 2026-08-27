# Application Foundation Reconciliation

## Purpose

This document records the source-history reconciliation boundary for issue #6.

Current `main` remains the architectural baseline for GoreeCloud Changelogs Core v1. The earlier `agent/initial-application-foundation` branch contains validated historical-migration and recovery ideas, but its FastAPI/SQLite application architecture does not replace the newer Node/Cloudflare Core v1 implementation by branch selection or wholesale merge.

## Reconciliation rules

1. Start every reconciled slice from current `main`.
2. Preserve the current canonical JSON Schema, Change ID model, Node core, Cloudflare service, and current documentation unless an explicit reviewed replacement is required.
3. Transplant capabilities rather than obsolete product architecture.
4. Do not treat the old FastAPI service or SQLite ledger as authoritative merely because its historical branch passed its own CI.
5. Run exact-head current-repository CI for every reconciled slice.
6. Preserve source provenance and historical source documents.
7. Do not invent implementation, testing, deployment, verification, release, or production evidence during historical migration.
8. Do not make Google Drive historical change-log documents non-authoritative until the separate migration, reconciliation, backup/restore, access-control, monitoring, target-host, and cutover gates are satisfied.

## First reconciled capability: DOCX staging parser

`tools/docx_migration/parse_docx.py` carries forward the useful historical DOCX parsing concepts without carrying forward the old ledger writer.

The parser:

- reads `.docx` paragraph text directly from OOXML using only Python's standard library;
- recognizes existing GoreeCloud historical date-heading and labeled-section conventions;
- preserves source document name, project identity, timestamp, title, and parsed historical fields;
- reports ambiguous headings, invalid timestamps, empty sources, and duplicate source identities;
- emits a staging bundle marked `authoritative: false`;
- does not allocate Change IDs;
- does not assign Core v1 maturity or status;
- does not create evidence that is absent from the source;
- does not write the Node/Cloudflare service, filesystem record store, D1 database, or any production ledger;
- keeps full historical body content out of the default diagnostic report.

A full staging bundle can be written only when an explicit `--candidates-output` path is supplied. That file is internal historical data and must be handled according to GoreeCloud privacy, data-protection, and sensitive-information requirements.

## Remaining reconciliation work

Subsequent issue #6 slices may reconcile:

- deterministic source-to-candidate reconciliation;
- reviewed mapping from staging candidates into the Core v1 schema;
- idempotent migration planning and Change ID allocation;
- backup/restore and preservation tooling appropriate to the current architecture;
- native Android capability after the current application foundation is integrated;
- documentation from the historical branch where it remains accurate.

The old FastAPI runtime, old SQLite schema, and direct SQLite importer are not accepted into current `main` by this first slice.

## Lifecycle boundary

This work is Development source reconciliation only. It does not establish historical migration acceptance, authoritative cutover, production deployment, monitoring readiness, recovery proof, mobile acceptance, or Stable qualification.

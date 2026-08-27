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

## Second reconciled capability: deterministic Core v1 review planning

`tools/docx_migration/plan_core_v1.py` converts a staging bundle into a deterministic **review plan**, not into authoritative Core v1 records.

For each staged source identity, the planner creates a stable `migration_key` from the source document, project slug, occurred-at timestamp, and historical title. Candidate order does not change the resulting plan, and duplicate deterministic identities fail closed rather than being silently deduplicated.

Only fields directly supported by the staging identity are proposed automatically:

- `schema_version: 1.0.0`;
- `occurred_at` from the parsed historical heading;
- `summary` from the historical heading title;
- `components` from the source changelog's project identity;
- source provenance pointing back to the historical DOCX staging source.

The following required Core v1 fields deliberately remain review/import blockers:

- `change_id`;
- `created_at`;
- `change_type`;
- `maturity`;
- `status`;
- `visibility`;
- `evidence`.

The planner does not infer those values from prose, section headings, filenames, or a prior branch's validation state. In particular, a historical `Validation` section does not become verified Core v1 evidence merely because the text exists, and an implementation-oriented heading does not prove current `Implemented`, `Tested`, `Deployed`, `Verified`, or `Released` lifecycle state.

Historical narrative is not copied into the review plan. The plan records only which historical sections are present and requires the reviewer to consult the protected staging bundle when mapping narrative fields. Default planner diagnostics likewise exclude historical body content.

Every generated plan is explicitly marked:

- `authoritative: false`;
- `import_authorized: false`;
- `ledger_written: false`;
- `change_ids_allocated: false`.

The planner has no import or ledger-writing code path. A future separately reviewed import slice must consume approved review decisions, allocate Change IDs through the current Core v1 allocator, construct schema-valid records, preserve idempotency, and prove rollback/recovery before any authority transition is considered.

## Current migration sequence

The controlled historical migration path is now:

1. authoritative Google Drive historical changelog remains unchanged;
2. read-only DOCX parser creates an internal non-authoritative staging bundle;
3. deterministic planner creates a non-authoritative review plan;
4. a human/reviewed process resolves every required field and any narrative mapping;
5. a future authorized importer performs Change ID allocation and canonical Core v1 validation/persistence;
6. migration reconciliation, backup/restore, access control, monitoring, target-host, and cutover acceptance are completed;
7. only then may any historical source-authority transition be evaluated.

Steps 4 through 7 are not implemented or accepted by the current planner slice.

## Remaining reconciliation work

Subsequent issue #6 slices may reconcile:

- reviewed mapping decisions from migration plans into complete Core v1 records;
- idempotent authorized import and Change ID allocation;
- migration reconciliation and duplicate/conflict handling against existing Core v1 records;
- backup/restore and preservation tooling appropriate to the current architecture;
- native Android capability after the current application foundation is integrated;
- documentation from the historical branch where it remains accurate.

The old FastAPI runtime, old SQLite schema, and direct SQLite importer are not accepted into current `main` by these reconciliation slices.

## Lifecycle boundary

This work is Development source reconciliation only. It does not establish historical migration acceptance, authoritative cutover, production deployment, monitoring readiness, recovery proof, mobile acceptance, or Stable qualification.

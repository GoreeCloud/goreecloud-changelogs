# Historical Migration

The existing GoreeCloud Google Drive change-log documents remain the migration source and recovery copy until the Changelogs service is accepted for production.

## Controlled migration workflow

1. Export or otherwise stage the intended historical change-log documents as `.docx` files in one controlled folder.
2. Run a fail-closed parser preflight before writing anything: `python scripts/import_docx.py /path/to/change-logs --dry-run --strict --report data/migration-preflight.json`.
3. Require the preflight report to show every intended document with at least one parsed entry, zero ambiguous date-like headings, zero invalid timestamps, and zero duplicate source identities. Resolve every reported source problem before importing.
4. Import the exact accepted source set with `python scripts/import_docx.py /path/to/change-logs --strict --report data/migration-import.json`.
5. Re-run the exact import command and require `inserted_entries: 0`; this proves idempotency for the accepted source identity set.
6. Run `python scripts/verify_ledger.py` and require an `ok: true` result.
7. Run `python scripts/reconcile_docx.py /path/to/change-logs --output data/migration-reconciliation.json`.
8. Require the reconciliation report to show `ok: true`, zero parser/source errors, zero duplicate source identities, zero missing identities, and zero unexpected imported identities before acceptance.
9. Review project-level source and ledger counts and investigate every non-zero difference.
10. Spot-check representative old, middle, and recent records across multiple projects for field-level fidelity.
11. Scan imported history for sensitive values before production cutover.
12. Back up the accepted ledger and prove restoration into an isolated target.
13. Run the ledger verifier again against the restored database and validate all user/API read paths.

The reconciliation identity is project slug + occurred timestamp + title + source document reference. This is deliberately stricter than title-only matching. The importer uses the same identity for idempotency so two separate source documents cannot accidentally suppress one another merely because they contain entries with the same timestamp and title.

## Parser diagnostics

The importer does not treat successful DOCX opening as successful migration. Each source document receives a diagnostic record containing its paragraph count, parsed-entry count, preamble length, ambiguous date-like headings, invalid timestamps, project mapping, and source reference.

A probable historical heading that begins with a recognized date but does not conform to the accepted `date — title` heading contract is reported rather than silently absorbed into another entry. In strict mode, any such ambiguity rejects the entire import before ledger writes begin.

Only `.docx` files whose names contain `Change Log` are considered historical migration sources. Temporary Microsoft Word files beginning with `~$` are ignored.

## Migration acceptance requirements

- Import all intended historical change-log documents.
- Preserve deterministic source diagnostics and reconciliation reports as acceptance evidence.
- Compare imported project counts and entry counts against the source set.
- Preserve source-document references for traceability.
- Prove a second import of the unchanged source set creates no duplicate records.
- Spot-check old, middle, and recent records from multiple projects.
- Verify timestamps, titles, categories, purpose, implementation, validation, final state, limitations, recovery, and follow-up text where present.
- Confirm no reusable secrets were introduced into the new ledger.
- Require the append-only controls and automated integrity verifier to pass.
- Back up the production ledger using the approved GoreeCloud backup system.
- Perform and document a restore test.
- Validate web, authenticated API, search, filtering, export, and native-client read paths against restored data.
- Only after those gates pass, designate GoreeCloud Changelogs as the authoritative operational change-history system and retire the requirement to keep appending to the old Drive documents.

Historical source documents should be archived rather than destructively deleted immediately after cutover.

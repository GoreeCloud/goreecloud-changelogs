# Historical Migration

The existing GoreeCloud Google Drive change-log documents remain the migration source and recovery copy until the Changelogs service is accepted for production.

## Controlled migration workflow

1. Export or otherwise stage the intended historical change-log documents as DOCX files in one controlled folder.
2. Import the source set with `python scripts/import_docx.py /path/to/change-logs`.
3. Run `python scripts/verify_ledger.py` and require an `ok: true` result.
4. Run `python scripts/reconcile_docx.py /path/to/change-logs --output data/migration-reconciliation.json`.
5. Require the reconciliation report to show zero missing and zero unexpected imported identities before acceptance.
6. Review project-level source and ledger counts and investigate every non-zero difference.
7. Spot-check representative old, middle, and recent records across multiple projects for field-level fidelity.
8. Scan imported history for sensitive values before production cutover.
9. Back up the accepted ledger and prove restoration into an isolated target.
10. Run the ledger verifier again against the restored database and validate all user/API read paths.

The reconciliation identity is project slug + occurred timestamp + title + source document reference. This is deliberately stricter than title-only matching and makes repeated imports idempotent while still exposing source drift.

## Migration acceptance requirements

- Import all intended historical change-log documents.
- Compare imported project counts and entry counts against the source set.
- Preserve source-document references for traceability.
- Spot-check old, middle, and recent records from multiple projects.
- Verify timestamps, titles, categories, purpose, implementation, validation, final state, limitations, recovery, and follow-up text where present.
- Confirm no reusable secrets were introduced into the new ledger.
- Require the append-only controls and automated integrity verifier to pass.
- Back up the production ledger using the approved GoreeCloud backup system.
- Perform and document a restore test.
- Validate web, authenticated API, search, filtering, export, and native-client read paths against restored data.
- Only after those gates pass, designate GoreeCloud Changelogs as the authoritative operational change-history system and retire the requirement to keep appending to the old Drive documents.

Historical source documents should be archived rather than destructively deleted immediately after cutover.

# Production Readiness Gates

GoreeCloud Changelogs is not production-approved merely because the source runs successfully.

Before `changelogs.goreecloud.com` becomes authoritative, complete the following gates:

1. Validate the exact source revision in CI.
2. Require the automated ledger integrity verifier to pass, including SQLite integrity, foreign-key, FTS synchronization, supersedes-reference, duplicate-source-identity, and required-title checks.
3. Build and run the container on the intended GoreeCloud host.
4. Confirm the service is not directly exposed through an application port.
5. Publish HTTPS only through the approved Caddy and GoreeCloud network path.
6. Configure a dedicated service identity and least-privilege filesystem ownership.
7. Keep read/write API credentials and all other reusable secrets outside Git and ordinary documentation.
8. Import and reconcile all intended historical records and retain an import reconciliation report.
9. Confirm the append-only database controls reject direct historical entry UPDATE and DELETE operations.
10. Back up the ledger and perform a successful restore test.
11. Run the integrity verifier against the restored ledger before accepting the restore.
12. Validate restored web, authenticated API, search, filter, export, and record-detail behavior.
13. Add service health monitoring and alerting.
14. Complete manual Glaze UI accessibility and responsive-layout acceptance.
15. Complete the official Changelogs visual-identity approval process; the source SVG in this repository remains a candidate until approved.
16. Build, sign, install, and real-device test the Android client before declaring the mobile client Stable.
17. Preserve the Google Drive source documents until migration, reconciliation, backup, restore, and integrity gates are satisfied.

## Authoritative transition rule

The historical Google Drive documents remain migration and recovery sources until the production ledger has passed every data-preservation gate above. Only after successful reconciliation and restore proof should GoreeCloud Changelogs become the authoritative location for new historical records.

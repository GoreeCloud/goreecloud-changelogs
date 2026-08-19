# Production Readiness Gates

GoreeCloud Changelogs is not production-approved merely because the source runs successfully.

Before `changelogs.goreecloud.com` becomes authoritative, complete the following gates:

1. Validate exact source revision in CI.
2. Build and run the container on the intended GoreeCloud host.
3. Confirm the service is not directly exposed through an application port.
4. Publish HTTPS only through the approved Caddy and GoreeCloud network path.
5. Configure a dedicated service identity and least-privilege filesystem ownership.
6. Keep write credentials and other secrets outside Git and ordinary documentation.
7. Import and reconcile all intended historical records.
8. Back up the ledger and perform a successful restore test.
9. Validate restored web, API, search, filter, and record-detail behavior.
10. Add service health monitoring and alerting.
11. Complete manual Glaze UI accessibility and responsive-layout acceptance.
12. Complete the official Changelogs visual-identity approval process; the source SVG in this repository remains a candidate until approved.
13. Build, sign, install, and real-device test the Android client before declaring the mobile client Stable.
14. Preserve the Google Drive source documents until migration and recovery gates are satisfied.

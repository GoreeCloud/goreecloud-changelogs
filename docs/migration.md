# Historical Migration

The existing GoreeCloud Google Drive change-log documents remain the migration source and recovery copy until the Changelogs service is accepted for production.

Migration acceptance requires:

- Import all intended historical change-log documents.
- Compare imported project counts and entry counts against the source set.
- Spot-check old, middle, and recent records from multiple projects.
- Verify timestamps, titles, categories, purpose, implementation, validation, final state, limitations, recovery, and follow-up text where present.
- Confirm no reusable secrets were introduced into the new ledger.
- Back up the production ledger using the approved GoreeCloud backup system.
- Perform and document a restore test.
- Validate web, API, search, filtering, and native-client read paths against restored data.
- Only after those gates pass, designate GoreeCloud Changelogs as the authoritative operational change-history system and retire the requirement to keep appending to the old Drive documents.

Historical source documents should be archived rather than destructively deleted immediately after cutover.

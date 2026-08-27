# Issue 4 Development Status

This branch is intentionally based on the unmerged initial application foundation PR #1 because the Android source tree does not yet exist on `main`.

Implemented in this follow-on slice:
- typed project, entry, and export-envelope models;
- strict HTTPS API-base validation;
- rejection of credentials embedded in URLs;
- schema-version fail-closed validation;
- Authorization-header construction with control-character rejection;
- documented credential and offline-cache boundaries.

Still required:
- protected Android credential storage;
- real HTTPS client implementation;
- authenticated project/timeline/search/detail surfaces;
- bounded encrypted offline read cache;
- explicit stale/offline UI state;
- pagination and large-ledger behavior;
- Android CI/build evidence;
- signed real-device acceptance.

No production or Stable acceptance is claimed.

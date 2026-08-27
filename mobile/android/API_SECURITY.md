# Android API Security Boundary

The native GoreeCloud Changelogs Android client consumes the authoritative web/API ledger rather than creating a second historical store.

The client contract requires an HTTPS base URL with a valid host. Credentials are forbidden in URL user-info, query, and fragment fields. Read credentials are supplied only through the Authorization header and must be stored using Android protected credential storage when runtime credential persistence is implemented.

The Android client currently accepts API schema version 1 only. Unsupported schema versions fail closed instead of being partially interpreted.

The future offline cache must be bounded and encrypted and must never contain read credentials. Cached data must be visibly identified as stale/offline when the authoritative API cannot be reached.

This slice defines typed models and transport/security invariants only. It does not yet claim networking, protected credential persistence, encrypted offline caching, timeline UI, search/filter UI, or real-device acceptance.

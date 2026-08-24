# GoreeCloud Changelogs API

Base path: `/api/v1`

## Security model

The JSON API is fail-closed by default.

Read endpoints require `Authorization: Bearer <token>` using the externally configured `CHANGELOGS_READ_TOKEN`. If no read token is configured, read API requests return service unavailable. A deliberate deployment may set `CHANGELOGS_ALLOW_UNAUTHENTICATED_READS=1`, but this is not the GoreeCloud default and should only be used where the surrounding access boundary has been explicitly approved.

Write access uses a separate `CHANGELOGS_WRITE_TOKEN`. A read token does not grant write access, and a write token should not be distributed to read-only integrations.

Both tokens must be supplied through the deployment secret-management path and must never be committed to Git, embedded in application source, or stored inside changelog entries.

## Read endpoints

- `GET /projects` — list known GoreeCloud projects/components with entry counts and latest-entry timestamps.
- `GET /entries` — list historical entries, newest first.
- `GET /entries?q=<query>` — full-text search.
- `GET /entries?project=<slug>` — filter by project.
- `GET /entries?from=<ISO timestamp>&to=<ISO timestamp>` — constrain results by occurrence time.
- `GET /entries/{id}` — retrieve one structured historical record.
- `GET /export` — return a stable, versioned JSON export envelope for read-only integrations, auditing, migration reconciliation, and controlled AI/agent access.

`GET /export` accepts `project`, `from`, `to`, and `limit` filters. Its response contains `schema_version`, the number of exported entries, the total ledger entry count, the applied filters, and the structured entries.

The normal `/entries` limit accepts values from 1 through 500. The controlled `/export` endpoint accepts up to 5,000 entries in one response.

## Write endpoint

`POST /entries` creates a new historical record. It is fail-closed by default. When `CHANGELOGS_WRITE_TOKEN` is not configured the endpoint returns service unavailable. When enabled it requires the write bearer token.

Corrections should be submitted as new entries and may reference an older entry with `supersedes_id`; existing historical records should not be silently rewritten. The API validates that a supplied `supersedes_id` refers to an existing record before accepting the correction.

## Integration intent

The read API is the preferred future access boundary for GoreeCloud Manager, approved mobile clients, administrative automation, and AI agents that need to inspect historical change data. Integrations should receive only the least-privileged token necessary for their role. The application database remains the authoritative runtime store; the live database file must not be committed to Git merely to provide integrations with access.

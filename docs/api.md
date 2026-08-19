# GoreeCloud Changelogs API

Base path: `/api/v1`

## Read endpoints

- `GET /projects` — list known GoreeCloud projects/components.
- `GET /entries` — list historical entries, newest first.
- `GET /entries?q=<query>` — full-text search.
- `GET /entries?project=<slug>` — filter by project.
- `GET /entries/{id}` — retrieve one structured historical record.

The `limit` query parameter accepts values from 1 through 500.

## Write endpoint

`POST /entries` creates a new historical record. It is fail-closed by default. When `CHANGELOGS_WRITE_TOKEN` is not configured the endpoint returns service unavailable. When enabled it requires `Authorization: Bearer <token>`.

The token must be supplied through the deployment secret-management path and must never be committed to Git or embedded in mobile/web client source.

Corrections should be submitted as new entries and may reference an older entry with `supersedes_id`; existing historical records should not be silently rewritten.

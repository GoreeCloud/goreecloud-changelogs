# GoreeCloud Changelogs Cloudflare Service

This document describes the production-oriented service layer implemented for GoreeCloud Changelogs Core v1. Source presence is implementation evidence only; it is not deployment or verification evidence.

## Architecture

The service uses two Cloudflare storage roles:

- **Durable Object: `ChangeIdAllocator`** — strongly coordinated Change ID allocation. One Durable Object instance is addressed by canonical calendar date, so all allocations for one date serialize through one authority.
- **D1: `CHANGELOGS_DB`** — canonical queryable ledger storage for validated change records and searchable component/environment indexes.

The allocation and persistence responsibilities are deliberately separate. If an ID is allocated but the D1 insert later fails, that identifier remains consumed and is never reused. Gaps are preferable to duplicate or recycled identifiers.

## API

The Worker implementation currently defines:

- `GET /health` — basic process health response. This does not prove database or Durable Object readiness.
- `POST /v1/changes` — authenticated allocation, schema validation, and canonical ledger insertion.
- `GET /v1/changes/:change_id` — authenticated record retrieval.
- `GET /v1/changes` — authenticated filtering by status, maturity, type, visibility, component, environment, and created-at range.

List results are capped at 100 records per request in the initial implementation.

## Authentication

The initial service contract uses a bearer token stored in the Worker secret `CHANGELOGS_API_TOKEN`. The repository must never contain the live token.

This is a bootstrap authorization mechanism, not the final GoreeCloud Identity/Mesh authorization model. Future service-to-service authorization can replace the token without changing Change IDs or canonical record semantics.

## Database model

`service/migrations/0001_init.sql` defines:

- `changes` — one immutable canonical JSON snapshot per Change ID plus indexed top-level query fields.
- `change_components` — normalized component membership for filtering.
- `change_environments` — normalized environment membership for filtering.

The full canonical JSON record remains stored in `changes.record_json` so the database index does not become a second competing record model.

## Distributed Change ID allocation

The Worker derives the allocation date from `created_at`, or from current time when it is omitted. It addresses a Durable Object by that date and requests the next sequence. The allocator transactionally increments its persisted sequence and returns `GC-YYYY-MM-DD-NNN`.

Allocation is globally coordinated within the deployed service for a given date. The existing filesystem allocator remains for offline and local development workflows and is not the production authority.

## Validation

Both the local Core v1 implementation and Worker service use Ajv's Draft 2020-12 validator against `schema/change.schema.json`. The service allocates the Change ID and establishes `created_at` before validating the complete canonical record.

Validation failure does not recycle the already allocated identifier.

## Provisioning boundary

`service/wrangler.example.jsonc` is intentionally a template. It contains no fabricated D1 database identifier and cannot be treated as deployment evidence.

Before deployment, an authorized Cloudflare environment must:

1. create or select the GoreeCloud Changelogs D1 database;
2. replace the database ID placeholder in an operational Wrangler configuration;
3. create the `CHANGELOGS_API_TOKEN` secret;
4. apply D1 migrations;
5. deploy the Worker and its SQLite-backed Durable Object migration;
6. execute runtime acceptance tests against allocation, insert, retrieval, filtering, authentication, and concurrent allocation;
7. capture deployment and runtime evidence before promoting maturity to Deployed or Verified.

## Integrity boundaries

- Change IDs are never reused.
- Database insertion uses parameterized statements.
- Related component/environment rows are written with the main record through a D1 batch.
- Read and write endpoints require authorization in the initial implementation.
- A repository commit is implementation evidence, not production evidence.
- `/health` proves only that the Worker handler can respond; it does not constitute ledger verification.

## Current maturity

This service layer is **Implemented** in source control. It must remain below **Deployed** and **Verified** until Cloudflare resources are provisioned, migrations are applied, deployment succeeds, and runtime behavior is explicitly verified.

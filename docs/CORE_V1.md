# Changelogs Core v1

Changelogs Core v1 is the foundation for GoreeCloud's canonical evidence-backed change ledger.

## Objective

Core v1 turns change history into a structured lifecycle model that can distinguish design intent from implemented, tested, deployed, and verified operational state.

## Lifecycle

`Change event → Change ID → implementation evidence → testing → deployment → verification → release → preservation`

Each stage can contribute evidence without automatically advancing the record to the next maturity level.

## State dimensions

### Maturity

- Designed
- Implemented
- Tested
- Deployed
- Verified

Maturity represents the strongest evidenced lifecycle stage reached by the change.

### Status

- Proposed
- In Progress
- Implemented
- Tested
- Deployed
- Verified
- Released
- Rolled Back

Status describes the current workflow or disposition of the change. It is intentionally independent of maturity.

### Deployment state

A deployment record can independently be Planned, In Progress, Succeeded, Failed, Rolled Back, or Verified for a specific environment.

## Evidence contract

Evidence is attached explicitly rather than inferred. Supported evidence types include commits, pull requests, issues, automated tests, manual verification, deployments, documentation, build artifacts, runtime observations, monitoring observations, and other verifiable records.

An evidence reference does not by itself elevate maturity. Promotion rules must require evidence appropriate to the target maturity level.

Examples:

- `Implemented` requires evidence that implementation exists.
- `Tested` requires test or verification evidence covering the implemented behavior.
- `Deployed` requires evidence that the implementation exists in a named environment.
- `Verified` requires evidence that the deployed or otherwise operational behavior was observed and validated.

## Component model

A change may affect one or many GoreeCloud components. Shared architectural work should avoid duplicate disconnected records by using one change record where appropriate, with parent/child relationships when independently traceable work is required.

Platform systems such as Privacy Shield, Wardveil Security, Everkeep, Glaze UI, and GoreeCloud Mesh are attached only when genuinely affected and must not be used as decorative labels or unsupported capability claims.

## Environment model

Core environments are:

- local
- development
- testing
- staging
- production

Additional environments may be introduced later without changing historical semantics.

Implementation history and deployment history remain separate. Code existing in a repository is not proof of production deployment.

## Visibility and sensitivity

Visibility levels are:

- public
- internal
- restricted
- confidential

Sensitivity tags include:

- security
- privacy
- infrastructure
- operational
- administrative

Public release-note generation must never automatically expose restricted, confidential, or otherwise sensitive internal details.

## Relationships

Supported relationship types are:

- parent
- child
- depends_on
- supersedes
- fixes
- reverts
- extends
- replaces

Relationships reference durable Change IDs rather than provider-specific issue or commit identifiers.

## Corrections and rollback

Verified historical events are durable. Significant inaccuracies are corrected through amendments that record when, why, and how the historical record changed.

Rollback history is preserved. A rolled-back change is not deleted, and its implementation evidence remains part of GoreeCloud's historical record.

## Provenance

Provenance records identify the source system or workflow that supplied change information. Provenance and evidence are related but different: provenance describes where the record information came from; evidence supports claims made by the record.

## Release notes

Release notes are filtered projections of appropriate verified changelog records. The canonical technical ledger remains authoritative. Release eligibility and a public-safe summary can be stored separately from internal implementation details.

## Core v1 implementation sequence

1. Canonical JSON Schema
2. Change ID allocation contract
3. Schema validation tooling
4. Atomic Change ID allocator
5. Record storage and indexing
6. Evidence ingestion adapters
7. Maturity promotion validation
8. Deployment mapping
9. Query/filter API
10. Release-note projection
11. Mesh ingestion integration
12. Manager/Monitoring/AI read integrations
13. Everkeep preservation integration

## Migration

Existing GoreeCloud changelog documents should be migrated incrementally. Historical source documents remain preserved. Migration should produce structured records linked back to the original source and should not invent implementation, deployment, testing, or verification evidence that does not exist.

## Core v1 completion definition

Core v1 is not complete merely because the schema exists. Completion requires the canonical record model, automatic Change ID allocation, validation, persistence/indexing, evidence handling, lifecycle enforcement, and at least one working ingestion/query path to be implemented and tested.

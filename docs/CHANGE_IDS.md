# GoreeCloud Change IDs

GoreeCloud Change IDs provide durable references for significant changes across GoreeCloud.

## Format

`GC-YYYY-MM-DD-NNN`

Example:

`GC-2026-08-26-004`

The date segment represents the calendar date on which the canonical change record is allocated. The numeric suffix is a zero-padded daily sequence starting at `001`.

## Rules

1. Change IDs are immutable after allocation.
2. IDs are never reused, including after rollback, rejection, cancellation, or archival.
3. The sequence is scoped to a calendar date, not to a repository or component.
4. One cross-component initiative should use one parent Change ID plus child Change IDs only when independently traceable implementation work is necessary.
5. Corrections to verified records do not receive replacement IDs solely because a correction occurred; amendments remain attached to the original record unless the correction represents a distinct new change.
6. A rollback is recorded against the original change and may also receive a distinct Change ID when the rollback itself is a meaningful implementation or deployment event.
7. Repository commits, pull requests, issues, deployments, documents, tests, and incidents reference the Change ID but do not define it.

## Allocation

Automatic allocation must be performed through the canonical Changelogs service or an authorized ingestion workflow. An allocator must atomically reserve the next sequence number for the date to prevent duplicate IDs from concurrent writers.

Pseudocode:

```text
allocate_change_id(now):
  date = canonical_calendar_date(now)
  sequence = atomically_increment(date)
  return "GC-" + date + "-" + zero_pad(sequence, 3)
```

The allocator should support suffixes beyond three digits if daily volume exceeds 999 records. Existing identifiers are never renumbered.

## Validation

Canonical IDs must match:

```regex
^GC-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3,}$
```

Syntax validation alone does not prove that an ID was legitimately allocated. Authoritative validation must confirm that the identifier exists in the canonical change ledger.

## References

Change IDs should be included where meaningful in:

- commit messages
- pull requests
- issues
- deployment records
- build metadata
- automated test evidence
- operational verification records
- incident investigations
- architecture and implementation documentation
- release manifests
- rollback records

## Source independence

Change IDs belong to GoreeCloud rather than GitHub, a deployment provider, a documentation platform, or any other external system. Provider migrations must not invalidate existing identifiers.

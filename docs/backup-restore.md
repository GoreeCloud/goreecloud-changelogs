# Ledger Backup and Restore

GoreeCloud Changelogs treats the historical ledger as operationally significant data. A configured backup job is not production-acceptance evidence by itself; restoration must be demonstrated against a clean or disposable target.

## Backup contract

Create a consistent SQLite backup with the SQLite Online Backup API rather than copying a live database file directly:

```bash
python scripts/backup_ledger.py /protected/backup/path/changelogs.sqlite3 \
  --database /app/data/changelogs.sqlite3 \
  --manifest /protected/backup/path/changelogs.json
```

The command fails closed if the source ledger does not pass the read-only integrity verifier. The selected destination must not already exist unless `--force` is explicitly supplied. Backup output is created through a temporary file, verified before promotion, and restricted to mode `0600`.

The sanitized manifest records the backup filename, creation time, byte size, SHA-256 digest, entry and FTS counts, SQLite integrity result, and foreign-key violation count. It does not contain API tokens or other reusable credentials.

The command is a recovery-point creation primitive, not the complete production retention policy. Production scheduling, repository selection, retention, independent backup-health monitoring, encryption, and off-host/off-system copies remain governed by GoreeCloud backup policy and target-environment acceptance.

## Restore-validation contract

Validate a selected backup in an isolated path:

```bash
python scripts/validate_restore.py /protected/backup/path/changelogs.sqlite3 \
  --restore-root /controlled/disposable/restore \
  --report /controlled/evidence/changelogs-restore.json
```

The validator copies the selected backup into a clean restore path, compares source and restored SHA-256 identities, runs the non-mutating ledger integrity verifier against the restored copy, verifies project/entry/FTS readability, and records a representative newest historical entry when one exists.

The restore validator never overwrites an existing restored database. A pre-existing restore target is treated as an error so acceptance evidence cannot silently reuse stale state.

## Read-only integrity verification

`scripts/verify_ledger.py` opens the selected SQLite database in read-only mode. Verification must not initialize, repair, rebuild, or otherwise modify the database it is evaluating. A missing database therefore fails verification rather than being created as an empty ledger.

A specific database can be checked with:

```bash
python scripts/verify_ledger.py --database /path/to/changelogs.sqlite3
```

## CI evidence boundary

The permanent CI workflow creates a disposable online backup from the test ledger and validates an isolated restoration on every pull-request head. This proves that the source tooling can execute the recovery workflow in a clean automated environment.

CI recovery proof does **not** satisfy the real target-environment production gate. Production acceptance still requires a recovery point created from the intended deployment, storage and permission validation, approved backup-system integration, independent backup-health monitoring, an isolated target restore, restored application/API/search validation, and documented operator evidence.

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "changelogs.sqlite3"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = r"""
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'application',
  status TEXT NOT NULL DEFAULT 'active',
  description TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id),
  occurred_at TEXT NOT NULL,
  title TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL DEFAULT '',
  purpose TEXT NOT NULL DEFAULT '',
  affected TEXT NOT NULL DEFAULT '',
  previous_state TEXT NOT NULL DEFAULT '',
  changes TEXT NOT NULL DEFAULT '',
  implementation TEXT NOT NULL DEFAULT '',
  validation TEXT NOT NULL DEFAULT '',
  final_state TEXT NOT NULL DEFAULT '',
  limitations TEXT NOT NULL DEFAULT '',
  rollback TEXT NOT NULL DEFAULT '',
  follow_up TEXT NOT NULL DEFAULT '',
  release TEXT NOT NULL DEFAULT '',
  environment TEXT NOT NULL DEFAULT '',
  source_ref TEXT NOT NULL DEFAULT '',
  supersedes_id INTEGER REFERENCES entries(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (length(trim(title)) > 0),
  CHECK (supersedes_id IS NULL OR supersedes_id != id)
);
CREATE UNIQUE INDEX IF NOT EXISTS entries_source_identity
  ON entries(project_id, occurred_at, title, source_ref);
CREATE INDEX IF NOT EXISTS entries_project_time
  ON entries(project_id, occurred_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS entries_supersedes
  ON entries(supersedes_id) WHERE supersedes_id IS NOT NULL;
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
  title, category, summary, purpose, affected, changes, implementation, validation, final_state, limitations, follow_up,
  content='entries', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
  INSERT INTO entries_fts(rowid,title,category,summary,purpose,affected,changes,implementation,validation,final_state,limitations,follow_up)
  VALUES (new.id,new.title,new.category,new.summary,new.purpose,new.affected,new.changes,new.implementation,new.validation,new.final_state,new.limitations,new.follow_up);
END;
CREATE TRIGGER IF NOT EXISTS entries_no_update BEFORE UPDATE ON entries BEGIN
  SELECT RAISE(ABORT, 'historical entries are append-only; create a superseding entry');
END;
CREATE TRIGGER IF NOT EXISTS entries_no_delete BEFORE DELETE ON entries BEGIN
  SELECT RAISE(ABORT, 'historical entries are append-only and cannot be deleted');
END;
"""


def init_db() -> None:
    with connect() as cx:
        cx.executescript(SCHEMA)
        # Rebuild the external-content FTS index so imported databases created by
        # older versions are reconciled when this schema is first applied.
        cx.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild')")


@contextmanager
def connect():
    cx = sqlite3.connect(DB_PATH)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys=ON")
    cx.execute("PRAGMA busy_timeout=5000")
    try:
        yield cx
        cx.commit()
    except Exception:
        cx.rollback()
        raise
    finally:
        cx.close()

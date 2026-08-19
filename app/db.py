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
  CHECK (length(trim(title)) > 0)
);
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
  title, category, summary, purpose, affected, changes, implementation, validation, final_state, limitations, follow_up,
  content='entries', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
  INSERT INTO entries_fts(rowid,title,category,summary,purpose,affected,changes,implementation,validation,final_state,limitations,follow_up)
  VALUES (new.id,new.title,new.category,new.summary,new.purpose,new.affected,new.changes,new.implementation,new.validation,new.final_state,new.limitations,new.follow_up);
END;
CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts,rowid,title,category,summary,purpose,affected,changes,implementation,validation,final_state,limitations,follow_up)
  VALUES('delete',old.id,old.title,old.category,old.summary,old.purpose,old.affected,old.changes,old.implementation,old.validation,old.final_state,old.limitations,old.follow_up);
END;
"""


def init_db() -> None:
    with connect() as cx:
        cx.executescript(SCHEMA)


@contextmanager
def connect():
    cx = sqlite3.connect(DB_PATH)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys=ON")
    try:
        yield cx
        cx.commit()
    finally:
        cx.close()

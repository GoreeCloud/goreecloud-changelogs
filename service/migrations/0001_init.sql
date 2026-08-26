PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS changes (
  change_id TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  occurred_at TEXT,
  summary TEXT NOT NULL,
  change_type TEXT NOT NULL,
  maturity TEXT NOT NULL,
  status TEXT NOT NULL,
  visibility TEXT NOT NULL,
  record_json TEXT NOT NULL,
  inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS change_components (
  change_id TEXT NOT NULL,
  component TEXT NOT NULL,
  PRIMARY KEY (change_id, component),
  FOREIGN KEY (change_id) REFERENCES changes(change_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS change_environments (
  change_id TEXT NOT NULL,
  environment TEXT NOT NULL,
  PRIMARY KEY (change_id, environment),
  FOREIGN KEY (change_id) REFERENCES changes(change_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_changes_created_at ON changes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_changes_type ON changes(change_type);
CREATE INDEX IF NOT EXISTS idx_changes_maturity ON changes(maturity);
CREATE INDEX IF NOT EXISTS idx_changes_status ON changes(status);
CREATE INDEX IF NOT EXISTS idx_changes_visibility ON changes(visibility);
CREATE INDEX IF NOT EXISTS idx_components_component ON change_components(component);
CREATE INDEX IF NOT EXISTS idx_environments_environment ON change_environments(environment);

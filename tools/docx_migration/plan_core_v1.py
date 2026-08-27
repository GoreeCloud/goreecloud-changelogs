#!/usr/bin/env python3
"""Build a deterministic, non-authoritative Core v1 migration review plan.

The planner consumes the read-only DOCX staging bundle produced by ``parse_docx.py``. It does
not allocate Change IDs, create canonical records, infer lifecycle state, manufacture evidence,
or write any Core v1 ledger. Historical narrative remains in the staging bundle rather than
being duplicated into the plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

STAGING_REQUIRED_KEYS = {
    "staging_schema_version",
    "source_ref",
    "project",
    "project_slug",
    "occurred_at",
    "title",
    "historical_fields",
}
CORE_V1_REQUIRED_FIELDS = (
    "change_id",
    "created_at",
    "summary",
    "change_type",
    "components",
    "maturity",
    "status",
    "visibility",
    "evidence",
)
AUTO_MAPPED_REQUIRED_FIELDS = {"summary", "components"}
REVIEW_REQUIRED_FIELDS = tuple(
    field for field in CORE_V1_REQUIRED_FIELDS if field not in AUTO_MAPPED_REQUIRED_FIELDS
)


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _migration_key(candidate: dict[str, Any]) -> str:
    identity = "\x1f".join(
        (
            candidate["source_ref"],
            candidate["project_slug"],
            candidate["occurred_at"],
            candidate["title"],
        )
    )
    return "hist-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        candidate["source_ref"],
        candidate["occurred_at"],
        candidate["project_slug"],
        candidate["title"],
    )


def _validate_candidate(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != STAGING_REQUIRED_KEYS:
        raise ValueError("staging candidate contains missing or unapproved fields")
    if raw.get("staging_schema_version") != 1:
        raise ValueError("unsupported staging candidate schema version")

    candidate = dict(raw)
    for key in ("source_ref", "project", "project_slug", "occurred_at", "title"):
        candidate[key] = _nonempty_string(candidate.get(key), key)

    historical_fields = candidate.get("historical_fields")
    if not isinstance(historical_fields, dict):
        raise ValueError("historical_fields must be an object")
    for key, value in historical_fields.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("historical_fields must contain string keys and values")
    return candidate


def _plan_entry(candidate: dict[str, Any]) -> dict[str, Any]:
    source_sections = sorted(
        key for key, value in candidate["historical_fields"].items() if value.strip()
    )
    return {
        "migration_key": _migration_key(candidate),
        "review_state": "needs_review",
        "source_identity": {
            "source_ref": candidate["source_ref"],
            "project": candidate["project"],
            "project_slug": candidate["project_slug"],
            "occurred_at": candidate["occurred_at"],
            "title": candidate["title"],
        },
        "proposed_record": {
            "schema_version": "1.0.0",
            "occurred_at": candidate["occurred_at"],
            "summary": candidate["title"],
            "components": [candidate["project"]],
            "provenance": [
                {
                    "source": "historical-docx-staging",
                    "reference": candidate["source_ref"],
                }
            ],
        },
        "source_sections_present": source_sections,
        "review_required_fields": list(REVIEW_REQUIRED_FIELDS),
        "review_notes": [
            "Historical narrative remains in the staging bundle and must be reviewed before mapping.",
            "Do not infer lifecycle state or verified evidence from section labels or prose.",
            "Allocate a Change ID only during a separately authorized import after review approval.",
        ],
    }


def build_plan(bundle: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(bundle, dict):
        raise ValueError("staging bundle must be a JSON object")
    if set(bundle) != {"schema_version", "authoritative", "purpose", "candidates"}:
        raise ValueError("staging bundle contains missing or unapproved fields")
    if bundle.get("schema_version") != 1:
        raise ValueError("unsupported staging bundle schema version")
    if bundle.get("authoritative") is not False:
        raise ValueError("migration planning accepts only non-authoritative staging bundles")
    if bundle.get("purpose") != "historical-docx-migration-staging":
        raise ValueError("unexpected staging bundle purpose")
    if not isinstance(bundle.get("candidates"), list):
        raise ValueError("staging candidates must be an array")

    candidates = [_validate_candidate(item) for item in bundle["candidates"]]
    candidates.sort(key=_candidate_sort_key)
    entries = [_plan_entry(candidate) for candidate in candidates]
    keys = [entry["migration_key"] for entry in entries]
    duplicate_keys = sorted({key for key in keys if keys.count(key) > 1})
    if duplicate_keys:
        raise ValueError("duplicate deterministic source identities are not migration-safe")

    plan = {
        "schema_version": 1,
        "authoritative": False,
        "purpose": "historical-docx-core-v1-migration-review-plan",
        "entries": entries,
        "import_authorized": False,
        "ledger_written": False,
        "change_ids_allocated": False,
    }
    diagnostics = {
        "schema_version": 1,
        "ok": True,
        "planned_entries": len(entries),
        "review_required_entries": len(entries),
        "ledger_written": False,
        "change_ids_allocated": False,
        "historical_body_in_diagnostics": False,
    }
    return plan, diagnostics


def load_bundle(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read staging bundle: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise ValueError("staging bundle must be a JSON object")
    return value


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a non-authoritative reviewed migration plan from DOCX staging data"
    )
    parser.add_argument("staging_bundle", type=Path)
    parser.add_argument("--output", required=True, type=Path, help="Internal migration review plan")
    parser.add_argument("--report", type=Path, help="Optional privacy-minimized diagnostics")
    args = parser.parse_args()

    try:
        plan, diagnostics = build_plan(load_bundle(args.staging_bundle))
        write_json(args.output, plan)
        if args.report:
            write_json(args.report, diagnostics)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2

    print(json.dumps(diagnostics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

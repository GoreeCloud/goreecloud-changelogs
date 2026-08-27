import copy
import unittest

from tools.docx_migration.plan_core_v1 import build_plan


def candidate(
    *,
    source_ref="Change Log — Terminal.docx",
    project="Terminal",
    project_slug="terminal",
    occurred_at="2026-08-20T06:42:00-05:00",
    title="Repository foundation",
):
    return {
        "staging_schema_version": 1,
        "source_ref": source_ref,
        "project": project,
        "project_slug": project_slug,
        "occurred_at": occurred_at,
        "title": title,
        "historical_fields": {
            "summary": "Historical narrative that stays in staging.",
            "implementation": "Implementation prose stays in staging too.",
            "validation": "",
        },
    }


def bundle(candidates):
    return {
        "schema_version": 1,
        "authoritative": False,
        "purpose": "historical-docx-migration-staging",
        "candidates": candidates,
    }


class MigrationPlanTests(unittest.TestCase):
    def test_plan_is_deterministic_and_order_independent(self):
        first = candidate()
        second = candidate(
            source_ref="Change Log — Location.docx",
            project="Location",
            project_slug="location",
            occurred_at="2026-08-22T00:00:00-05:00",
            title="Project established",
        )

        plan_a, diagnostics_a = build_plan(bundle([first, second]))
        plan_b, diagnostics_b = build_plan(bundle([copy.deepcopy(second), copy.deepcopy(first)]))

        self.assertEqual(plan_a, plan_b)
        self.assertEqual(diagnostics_a, diagnostics_b)
        self.assertEqual(len({entry["migration_key"] for entry in plan_a["entries"]}), 2)

    def test_plan_maps_only_direct_source_identity_and_keeps_lifecycle_for_review(self):
        plan, diagnostics = build_plan(bundle([candidate()]))
        entry = plan["entries"][0]
        proposed = entry["proposed_record"]

        self.assertEqual(proposed["summary"], "Repository foundation")
        self.assertEqual(proposed["components"], ["Terminal"])
        self.assertEqual(proposed["occurred_at"], "2026-08-20T06:42:00-05:00")
        self.assertEqual(entry["review_state"], "needs_review")
        for field in (
            "change_id",
            "created_at",
            "change_type",
            "maturity",
            "status",
            "visibility",
            "evidence",
        ):
            self.assertNotIn(field, proposed)
            self.assertIn(field, entry["review_required_fields"])

        self.assertFalse(plan["authoritative"])
        self.assertFalse(plan["import_authorized"])
        self.assertFalse(plan["ledger_written"])
        self.assertFalse(plan["change_ids_allocated"])
        self.assertFalse(diagnostics["ledger_written"])
        self.assertFalse(diagnostics["change_ids_allocated"])

    def test_historical_body_is_not_duplicated_into_plan_or_diagnostics(self):
        secret_marker = "HISTORICAL-NARRATIVE-MARKER-MUST-STAY-IN-STAGING"
        item = candidate()
        item["historical_fields"]["summary"] = secret_marker
        item["historical_fields"]["implementation"] = secret_marker

        plan, diagnostics = build_plan(bundle([item]))
        rendered = repr(plan) + repr(diagnostics)

        self.assertNotIn(secret_marker, rendered)
        self.assertEqual(
            plan["entries"][0]["source_sections_present"],
            ["implementation", "summary"],
        )
        self.assertFalse(diagnostics["historical_body_in_diagnostics"])

    def test_duplicate_source_identity_fails_closed(self):
        item = candidate()
        with self.assertRaisesRegex(ValueError, "duplicate deterministic source identities"):
            build_plan(bundle([item, copy.deepcopy(item)]))

    def test_authoritative_input_is_rejected(self):
        value = bundle([candidate()])
        value["authoritative"] = True

        with self.assertRaisesRegex(ValueError, "only non-authoritative"):
            build_plan(value)

    def test_unapproved_candidate_field_is_rejected(self):
        item = candidate()
        item["invented"] = "not allowed"

        with self.assertRaisesRegex(ValueError, "missing or unapproved"):
            build_plan(bundle([item]))


if __name__ == "__main__":
    unittest.main()

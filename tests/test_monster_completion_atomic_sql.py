"""Offline tests of the parameterized single-monster SQL template."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from monster_completion_atomic_sql import conditional_update_sql, sql_bindings


class AtomicSqlTests(unittest.TestCase):
    def test_review_reset_respects_not_null_schema_defaults(self):
        # These review columns and translation_error are NOT NULL in Supabase.
        # The timestamp is the only nullable field in the reset operation.
        sql = conditional_update_sql()
        assignments = dict(
            line.strip().rstrip(",").split(" = ", 1)
            for line in sql.split("WHERE", 1)[0].splitlines()
            if " = " in line
        )
        expected = {
            "translation_error": "''",
            "translation_review_fingerprint": "''",
            "translation_review_notes": "''",
            "translation_review_conflict_fields": "'[]'::jsonb",
            "translation_review_confidence": "0",
            "translation_review_model": "''",
            "translation_reviewed_at": "NULL",
        }
        for column, default in expected.items():
            with self.subTest(column=column):
                self.assertEqual(assignments[column], default)

    def test_compare_and_swap_guards(self):
        sql = conditional_update_sql()
        for guard in ("updated_at IS NOT DISTINCT FROM", "source_refs IS NOT DISTINCT FROM",
                      "translation_lease_id", "translation_lease_expires_at",
                      "source_attributes IS NOT DISTINCT FROM", "RETURNING id"):
            self.assertIn(guard, sql)
        self.assertIn("translation_review_status = 'pending'", sql)
        self.assertNotIn("ai_verified", sql)

    def test_record_id_must_match(self):
        with self.assertRaises(ValueError):
            sql_bindings({"id": "a"}, {"id": "b"})

    def test_bindings_keep_source_fields_out_of_set_clause(self):
        original = {
            "id": "a", "source_name": "Original", "source_language": "es",
            "source_attributes": {"velocita": "30 ft."},
            "source_refs": [{"page": 3}], "updated_at": "2026-01-01",
            "translation_status": "processing",
        }
        candidate = {"id": "a", "name": "Tradotto", "description": "Testo",
                     "attributes": {"velocita": "9 m"}}
        sql = conditional_update_sql()
        self.assertNotIn("SET source_name", sql)
        self.assertNotIn("SET source_attributes", sql)
        bindings = sql_bindings(original, candidate)
        self.assertEqual(bindings["expected_source_name"], "Original")
        self.assertEqual(bindings["name"], "Tradotto")


if __name__ == "__main__":
    unittest.main()

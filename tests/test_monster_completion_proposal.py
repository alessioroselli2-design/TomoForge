"""Tests for dry-run update plans. Never writes to Supabase."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from monster_completion_proposal import build_proposal
from test_monster_completion_preflight import SOURCE, ATTRS


class ProposalTests(unittest.TestCase):
    def test_proposal_is_blocked_without_evidence(self):
        candidate = {
            **SOURCE, "name": "Esempio", "description": "Descrizione",
            "attributes": ATTRS, "translation_status": "translated",
        }
        result = build_proposal(SOURCE, candidate)
        self.assertFalse(result["ready"])
        self.assertEqual(result["writes_performed"], 0)
        self.assertTrue(result["requires_independent_source_review"])
        self.assertIsNone(result["proposed_fingerprint"])

    def test_plan_does_not_include_source_fields(self):
        candidate = {
            **SOURCE, "name": "Esempio", "description": "Descrizione",
            "attributes": ATTRS, "translation_status": "translated",
        }
        result = build_proposal(SOURCE, candidate)
        self.assertNotIn("source_attributes", result["proposed_fields"])
        self.assertNotIn("review_status", result["proposed_fields"])
        self.assertEqual(result["required_match"]["id"], SOURCE["id"])


if __name__ == "__main__":
    unittest.main()

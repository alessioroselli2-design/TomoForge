"""Offline tests: no database, network, translation service, or write access."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from monster_completion_preflight import preflight

SOURCE = {
    "id": "test-monster", "source_name": "Example", "source_language": "fr",
    "source_description": "", "source_full_text": "",
    "source_attributes": {"velocita": "9 m"},
    "source_refs": [{"filename": "source.pdf", "page": 3}],
    "translation_status": "not_required", "translation_lease_id": "",
    "translation_lease_expires_at": 0,
}
ATTRS = {
    "tipo": "Mostruosità", "taglia": "Media", "allineamento": "neutrale",
    "classe_armatura": "12", "punti_ferita": "19 (3d8 + 6)",
    "velocita": "9 m", "caratteristiche": {
        "for": 10, "des": 11, "cos": 14, "int": 6, "sag": 8, "car": 3,
    }, "sensi": "Scurovisione 18 m", "linguaggi": "Nessuno",
    "grado_sfida": "1/2", "tratti": [], "azioni": [],
}


class CompletionPreflightTests(unittest.TestCase):
    def candidate(self):
        return {**SOURCE, "name": "Esempio", "description": "Descrizione italiana.",
                "attributes": ATTRS.copy(), "translation_status": "translated"}

    def test_multilingual_valid_candidate(self):
        result = preflight(SOURCE, self.candidate(),
                           source_page_checked=True, independent_review=True)
        self.assertTrue(result.ready)
        self.assertEqual(len(result.proposed_fingerprint), 64)

    def test_no_source_verification_means_blocked(self):
        result = preflight(SOURCE, self.candidate())
        self.assertFalse(result.ready)
        self.assertIn("source_page_not_checked", result.blockers)

    def test_original_language_fields_are_immutable(self):
        candidate = self.candidate()
        candidate["source_language"] = "en"
        result = preflight(SOURCE, candidate, source_page_checked=True,
                           independent_review=True)
        self.assertIn("immutable_source_changed:source_language", result.blockers)

    def test_missing_stat_blocks_approval(self):
        candidate = self.candidate()
        candidate["attributes"].pop("velocita")
        result = preflight(SOURCE, candidate, source_page_checked=True,
                           independent_review=True)
        self.assertIn("required_field_missing:velocita", result.blockers)


if __name__ == "__main__":
    unittest.main()

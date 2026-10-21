"""Offline audit/CAS tests; all source evidence is synthetic."""
import copy
import json
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from monster_completion_atomic_sql import (
    audited_sql_bindings,
    audited_update_sql,
    render_audited_update,
)
from translation_integrity import translation_verification_fingerprint


class AuditedSqlTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            "id": "synthetic-monster", "user_id": "synthetic-owner",
            "reference_type": "monster", "updated_at": "2026-01-01 00:00:00+00",
            "name": "Synthetic", "description": "", "full_text": "", "attributes": {},
            "source_name": "Synthetic", "source_description": "", "source_full_text": "",
            "source_attributes": {}, "source_language": "en", "source_key": "synthetic.pdf",
            "source_text_checksum": "", "source_normalized_name": "synthetic",
            "source_refs": [{"physical_sha256": "a" * 64, "page": 3}],
            "translation_status": "processing", "translation_review_status": "pending",
            "translation_lease_id": "", "translation_lease_expires_at": 0,
            "review_status": "verified",
        }
        self.candidate = copy.deepcopy(self.original)
        self.candidate.update({
            "name": "Sintetico", "description": "Descrizione sintetica.",
            "full_text": "Testo sintetico completo.", "translation_status": "translated",
            "attributes": {
                "tipo": "Elementale", "taglia": "Media", "allineamento": "neutrale",
                "classe_armatura": "12", "punti_ferita": "9 (2d8)", "velocita": "9 m",
                "caratteristiche": {key: 10 for key in ("for", "des", "cos", "int", "sag", "car")},
                "sensi": "Percezione passiva 10", "linguaggi": "Nessuno", "grado_sfida": "1",
                "tratti": [], "azioni": [], "reazioni": [], "azioni_leggendarie": [],
            },
        })
        self.audit = {
            "record_id": self.original["id"],
            "candidate_fingerprint": translation_verification_fingerprint(self.candidate),
            "source_evidence_sha256": "a" * 64, "source_page": 3,
            "source_url": "https://example.invalid/synthetic.pdf",
            "reviewer_id": "synthetic-independent-reviewer", "review_notes": "Synthetic completed audit.",
            "source_page_checked": True, "independent_review": True, "source_sections_checked": True,
            "review_confidence": 0.98, "reviewed_at": "2026-01-02T00:00:00Z",
        }

    def test_completed_audit_binds_exact_original_and_reviewed_content(self):
        before = copy.deepcopy((self.original, self.candidate, self.audit))
        payload = json.loads(audited_sql_bindings(self.original, self.candidate, self.audit)["payload"])
        self.assertEqual(payload["original"], self.original)
        self.assertEqual(payload["candidate"]["attributes"], self.candidate["attributes"])
        self.assertEqual(payload["audit"]["review_confidence"], 0.98)
        self.assertEqual((self.original, self.candidate, self.audit), before)

    def test_missing_or_false_audit_evidence_is_rejected(self):
        for key in self.audit:
            with self.subTest(key=key):
                audit = {k: v for k, v in self.audit.items() if k != key}
                with self.assertRaises(ValueError):
                    audited_sql_bindings(self.original, self.candidate, audit)
        for flag in ("source_page_checked", "independent_review", "source_sections_checked"):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                audited_sql_bindings(self.original, self.candidate, {**self.audit, flag: "true"})

    def test_confidence_alone_never_replaces_evidence(self):
        with self.assertRaises(ValueError):
            audited_sql_bindings(self.original, self.candidate, {"review_confidence": 1})
        for confidence in (True, 0.96, 1.01, float("nan"), float("inf"), "0.99"):
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                audited_sql_bindings(self.original, self.candidate, {**self.audit, "review_confidence": confidence})

    def test_receipt_must_match_record_page_and_content_fingerprint(self):
        for key, value in (("record_id", "other"), ("source_page", 4),
                           ("source_evidence_sha256", "b" * 64), ("candidate_fingerprint", "c" * 64)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                audited_sql_bindings(self.original, self.candidate, {**self.audit, key: value})
        changed = {**self.candidate, "description": "Different reviewed content."}
        with self.assertRaises(ValueError):
            audited_sql_bindings(self.original, changed, self.audit)

    def minecraft_receipt(self):
        original = copy.deepcopy(self.original)
        original["source_refs"] = [{
            "filename": "701858566-RRN5YRR.pdf", "page": 29,
            "physical_sha256": "b7fb95c7519fb0936bb2cb37cfb6a5493134c86e0dc31196a4c62a67887e8ada",
            "logical_source_id": "mc_v3_minecraft_2023_en",
        }]
        candidate = {**self.candidate, "source_refs": copy.deepcopy(original["source_refs"])}
        official_url = (
            "https://www.minecraft.net/content/dam/minecraftnet/games/minecraft/"
            "software/Minecraft-Monstrous-Compendium.pdf"
        )
        official_digest = "559802923408bb57ccea250e6806603ee20b1ad4ed28e58c2e1608bf5ba79521"
        audit = {
            **self.audit, "source_url": official_url, "source_evidence_sha256": official_digest,
            "provenance_mapping": {
                "original_filename": "701858566-RRN5YRR.pdf", "original_page": 29,
                "original_sha256": original["source_refs"][0]["physical_sha256"],
                "logical_source_id": "mc_v3_minecraft_2023_en",
                "authoritative_sha256": official_digest, "authoritative_page": 3,
                "authoritative_url": official_url,
                "mapping_reason": "Synthetic review receipt for registered source priority and cover offset.",
                "reviewer_id": self.audit["reviewer_id"], "independently_checked": True,
                "original_digest_from_record_only": True,
            },
        }
        return original, candidate, audit

    def test_registered_official_minecraft_source_requires_explicit_mapping_receipt(self):
        original, candidate, audit = self.minecraft_receipt()
        payload = json.loads(audited_sql_bindings(original, candidate, audit)["payload"])
        self.assertEqual(payload["original"]["source_refs"], original["source_refs"])
        self.assertTrue(payload["audit"]["provenance_mapping"]["original_digest_from_record_only"])
        for key in audit["provenance_mapping"]:
            changed = copy.deepcopy(audit)
            del changed["provenance_mapping"][key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                audited_sql_bindings(original, candidate, changed)

    def test_minecraft_mapping_cannot_bypass_url_digest_page_or_registry_policy(self):
        original, candidate, audit = self.minecraft_receipt()
        for key, value in (("source_url", "https://example.invalid/other.pdf"),
                           ("source_evidence_sha256", "c" * 64), ("source_page", 4)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                audited_sql_bindings(original, candidate, {**audit, key: value})
        with patch("reference_sources.source_metadata_for_page", return_value={}):
            with self.assertRaisesRegex(ValueError, "registry does not authorize"):
                audited_sql_bindings(original, candidate, audit)

    def test_nonmonster_and_all_unknown_or_active_leases_are_rejected(self):
        for change in ({"reference_type": "spell"}, {"translation_lease_id": "leased"},
                       {"translation_lease_expires_at": 1}, {"translation_lease_expires_at": None}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                audited_sql_bindings({**self.original, **change}, {**self.candidate, **change}, self.audit)

    def test_all_source_and_identity_fields_are_immutable(self):
        for key in ("source_key", "source_text_checksum", "source_normalized_name", "user_id"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                audited_sql_bindings(self.original, {**self.candidate, key: "changed"}, self.audit)
        with self.assertRaises(ValueError):
            audited_sql_bindings(self.original, {**self.candidate, "source_extra": "extra"}, self.audit)

    def test_preflight_blocks_missing_stat_section_and_premature_approval(self):
        candidate = copy.deepcopy(self.candidate)
        del candidate["attributes"]["reazioni"]
        for changed in (candidate, {**self.candidate, "translation_review_status": "ai_verified"}):
            with self.assertRaisesRegex(ValueError, "preflight failed"):
                audited_sql_bindings(self.original, changed, self.audit)

    def test_review_timestamp_requires_explicit_utc(self):
        for timestamp in ("2026-01-02T00:00:00", "2026-01-02T00:00:00+01:00", "invalid", None):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                audited_sql_bindings(self.original, self.candidate, {**self.audit, "reviewed_at": timestamp})

    def test_evidence_locator_never_accepts_credentials_or_signed_queries(self):
        for url in ("https://user:secret@example.invalid/source.pdf", "https://example.invalid/a?token=secret"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                audited_sql_bindings(self.original, self.candidate, {**self.audit, "source_url": url})

    def test_sql_uses_typed_whole_row_cas_and_never_sets_source_fields(self):
        sql = audited_update_sql()
        self.assertIn("jsonb_populate_record(NULL::public.private_reference_records", sql)
        self.assertIn("target IS NOT DISTINCT FROM expected.snapshot", sql)
        self.assertIn("jsonb_object_keys(expected.data->'original')", sql)
        assignments = sql.split("\nSET ", 1)[1].split("\nFROM expected", 1)[0]
        columns = re.findall(r"(?:^|\n)\s*([a-z_]+) =", assignments)
        self.assertFalse(any(column.startswith("source_") for column in columns))
        self.assertNotIn("user_id", columns)
        self.assertNotIn("reference_type", columns)
        self.assertIn("translation_review_fingerprint", columns)

    def test_sql_like_manual_text_stays_inside_one_json_literal(self):
        malicious = "'); DROP TABLE public.private_reference_records; -- $tf_monster_0$"
        candidate = {**self.candidate, "name": malicious, "full_text": malicious}
        audit = {**self.audit, "candidate_fingerprint": translation_verification_fingerprint(candidate)}
        sql = render_audited_update(self.original, candidate, audit)
        delimiter = "$tf_monster_1$"
        self.assertEqual(sql.count(delimiter), 2)
        encoded = sql.split(delimiter)[1]
        self.assertEqual(json.loads(encoded)["candidate"]["name"], malicious)
        self.assertEqual(
            sql.replace(f"{delimiter}{encoded}{delimiter}", "%(payload)s"),
            audited_update_sql(),
        )


if __name__ == "__main__":
    unittest.main()

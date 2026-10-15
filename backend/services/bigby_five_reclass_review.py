"""Read-only, five independent Bigby source-locked monster reclassification gates.

Each ID refers to one existing row misclassified as 'other'. This review never
writes Supabase and cannot be used to accept any different source or stat block.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

SOURCE = "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf"
TITLE = "Bigby Presenta: La Gloria dei Giganti"
TARGETS = {
    "ref_df2773e308da52269e7a546b78263197": {
        "name": "Furia Di Kostchtchie", "page": 139, "stat_page": 139,
        "status": "verified", "corrections": {},
        "checksum": "4f59f901a3d16ea18b22b6c173090fa1d5ea30cf41ebb2fc4475da01029854da",
        "raw_hash": "8f6e4ce2008b7d0abaed87fc9bf9d2b4cacbaa85ea4555656747d402acfb79f7",
        "attrs": {"classe_armatura": "16 (armatura naturale)",
                  "punti_ferita": "216 (16d12 + 112)", "velocita": "12 m"},
        "hp": 216, "dice": 16, "faces": 12, "bonus": 112,
    },
    "ref_995df9449a30503b98317cea591de39b": {
        "name": "Gelovivente", "page": 144, "stat_page": 144,
        "status": "needs_review", "corrections": {"_source_changed": True},
        "checksum": "28a9dbe19af4c1d4c7afb1206279b4f1a8f776386b54665264b9efb642e6fba8",
        "raw_hash": "b9d4237cfd5005a5806aadbf6c7275e82bf8b828d08cf5ed11e6bfe7844dc0da",
        "attrs": {"classe_armatura": "13 (armatura naturale)",
                  "punti_ferita": "195 (17d12 + 85)", "velocita": "12 m"},
        "hp": 195, "dice": 17, "faces": 12, "bonus": 85,
    },
    "ref_73e5654442de579c8fbcd8185426b031": {
        "name": "Infernale Del Fuoco", "page": 165, "stat_page": 165,
        "status": "verified", "corrections": {},
        "checksum": "7d0278ea27733b18b121d38259c6028c155137070e9f3d018c0b715137ef20d0",
        "raw_hash": "7465dec1ac71285d2a26e9b465456824926358639bbee9ee95ef1c6bc6274799",
        "attrs": {"classe_armatura": "18 (piastre)",
                  "punti_ferita": "175 (14d12 + 84)", "velocita": "9 m"},
        "hp": 175, "dice": 14, "faces": 12, "bonus": 84,
    },
    "ref_b921e7e721755bbbac1b62bd6d70240b": {
        "name": "Rampollo Di Surtur", "page": 178, "stat_page": 179,
        "status": "verified", "corrections": {},
        "checksum": "ba3c6380537cbf0e2029cc39e5da6376ea27abeabaaa46b3fb899b072c1c1618",
        "raw_hash": "7b7e4893ddad1899d89a657c8e23219cc33677ce90fe819b93d58924b924380f",
        "attrs": {"classe_armatura": "20 (armatura naturale)",
                  "punti_ferita": "546 (28d20 + 252)", "velocita": "18 m"},
        "hp": 546, "dice": 28, "faces": 20, "bonus": 252,
    },
    "ref_1c9f8b60117d5649a6742b1de5e09b52": {
        "name": "Rampollo Di Thrym", "page": 180, "stat_page": 181,
        "status": "verified", "corrections": {},
        "checksum": "3559188391508279c4f05f2909239a94637b848a1266bcddf5a406b246e36d3b",
        "raw_hash": "72a43b8ed12e2ad8741b9323a689eb0bd51c9a8440298c1be189be8308dd05e6",
        "attrs": {"classe_armatura": "19 (armatura naturale)",
                  "punti_ferita": "499 (27d20 + 216)", "velocita": "18 m"},
        "hp": 499, "dice": 27, "faces": 20, "bonus": 216,
    },
}


def authority(page: int) -> dict[str, Any]:
    """Exact registered licensed Italian source reference, not inferred."""
    return {
        "page": page, "logical_page": page, "logical_source_id": "bgg_2023_it",
        "ruleset": "2014", "filename": SOURCE,
        "source_role": "authority", "source_status": "active",
        "authority_class": "licensed_translation", "source_title": TITLE,
    }


def assess_bigby_registered_other(
    record: dict[str, Any] | None, target_id: str
) -> dict[str, Any]:
    """Fail closed on every independent source, identity or numeric gate."""
    spec = TARGETS.get(target_id)
    if spec is None or not isinstance(record, dict):
        raise ValueError("unknown_or_missing_registered_source")
    name = spec["name"]
    expected = {
        "id": target_id, "name": name, "source_name": name,
        "normalized_name": name.casefold(), "reference_type": "other",
        "review_status": spec["status"], "review_flags": [],
        "source_language": "it", "source_key": SOURCE,
        "canonical_id": None, "source_text_checksum": spec["checksum"],
        "source_refs": [authority(spec["page"])],
        "attributes": {}, "source_attributes": {},
        "review_corrections": spec["corrections"],
    }
    if any(record.get(key) != val for key, val in expected.items()):
        raise ValueError("existing_record_identity_or_source_drift")

    raw = record.get("source_full_text")
    if not isinstance(raw, str) or record.get("full_text") != raw:
        raise ValueError("original_text_or_evidence_drift")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != spec["raw_hash"]:
        raise ValueError("original_source_sha256_drift")

    hp = (spec["dice"] * (spec["faces"] + 1)) // 2 + spec["bonus"]
    if hp != spec["hp"]:
        raise ValueError("statblock_hit_dice_math_failed")
    if spec["attrs"]["punti_ferita"] != (
        f'{spec["hp"]} ({spec["dice"]}d{spec["faces"]} + {spec["bonus"]})'
    ):
        raise ValueError("statblock_hp_expression_mismatch")
    if monster_semantic_numeric_flags(spec["attrs"]):
        raise ValueError("global_strict_monster_numeric_gate_failed")

    refs = [authority(spec["page"])]
    if spec["stat_page"] != spec["page"]:
        # The stat block has its own NAMED title and numeric fields.
        # Narrative p178/180 is not the Culla del Rampollo stat block p178/180.
        refs.append(authority(spec["stat_page"]))
    return {
        "id": target_id, "name": name,
        "status": "eligible_single_record_reclassification",
        "original_type": "other", "new_type": "monster",
        "narrative_page": spec["page"], "statblock_page": spec["stat_page"],
        "proposed_attributes": spec["attrs"], "proposed_refs": refs,
        "original_raw_preserved": True, "historical_ocr_preserved": True,
        "writes": 0,
    }

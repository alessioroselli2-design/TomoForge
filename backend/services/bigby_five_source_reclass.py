"""Read-only, sealed original-source audits for five misclassified Bigby monsters.

Five pre-existing records were incorrectly typed 'other'. Only the boxed
Italian stat block of the *same named entity* may supply operational fields.
The source narrative/OCR is not rewritten; cross-page stat blocks get a new
source reference only after a separately guarded write.
"""
from __future__ import annotations

import hashlib
from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags

SOURCE = "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf"
USER_ID = "user_fabf28726a20"
SPECS = {
    "Furia Di Kostchtchie": {
        "id": "ref_df2773e308da52269e7a546b78263197",
        "page": 139, "stats_page": 139, "status": "verified",
        "checksum": "4f59f901a3d16ea18b22b6c173090fa1d5ea30cf41ebb2fc4475da01029854da",
        "raw_sha256": "8f6e4ce2008b7d0abaed87fc9bf9d2b4cacbaa85ea4555656747d402acfb79f7",
        "corrections": {},
        "attrs": {"classe_armatura": "16 (armatura naturale)", "punti_ferita": "216 (16d12 + 112)", "velocita": "12 m"},
        "dice": (216, 16, 12, 112),
    },
    "Gelovivente": {
        "id": "ref_995df9449a30503b98317cea591de39b",
        "page": 144, "stats_page": 144, "status": "needs_review",
        "checksum": "28a9dbe19af4c1d4c7afb1206279b4f1a8f776386b54665264b9efb642e6fba8",
        "raw_sha256": "b9d4237cfd5005a5806aadbf6c7275e82bf8b828d08cf5ed11e6bfe7844dc0da",
        "corrections": {"_source_changed": True},
        "attrs": {"classe_armatura": "13 (armatura naturale)", "punti_ferita": "195 (17d12 + 85)", "velocita": "12 m"},
        "dice": (195, 17, 12, 85),
    },
    "Infernale Del Fuoco": {
        "id": "ref_73e5654442de579c8fbcd8185426b031",
        "page": 165, "stats_page": 165, "status": "verified",
        "checksum": "7d0278ea27733b18b121d38259c6028c155137070e9f3d018c0b715137ef20d0",
        "raw_sha256": "7465dec1ac71285d2a26e9b465456824926358639bbee9ee95ef1c6bc6274799",
        "corrections": {},
        "attrs": {"classe_armatura": "18 (piastre)", "punti_ferita": "175 (14d12 + 84)", "velocita": "9 m"},
        "dice": (175, 14, 12, 84),
    },
    "Rampollo Di Surtur": {
        "id": "ref_b921e7e721755bbbac1b62bd6d70240b",
        "page": 178, "stats_page": 179, "status": "verified",
        "checksum": "ba3c6380537cbf0e2029cc39e5da6376ea27abeabaaa46b3fb899b072c1c1618",
        "raw_sha256": "7b7e4893ddad1899d89a657c8e23219cc33677ce90fe819b93d58924b924380f",
        "corrections": {},
        "attrs": {"classe_armatura": "20 (armatura naturale)", "punti_ferita": "546 (28d20 + 252)", "velocita": "18 m"},
        "dice": (546, 28, 20, 252),
    },
    "Rampollo Di Thrym": {
        "id": "ref_1c9f8b60117d5649a6742b1de5e09b52",
        "page": 180, "stats_page": 181, "status": "verified",
        "checksum": "3559188391508279c4f05f2909239a94637b848a1266bcddf5a406b246e36d3b",
        "raw_sha256": "72a43b8ed12e2ad8741b9323a689eb0bd51c9a8440298c1be189be8308dd05e6",
        "corrections": {},
        "attrs": {"classe_armatura": "19 (armatura naturale)", "punti_ferita": "499 (27d20 + 216)", "velocita": "18 m"},
        "dice": (499, 27, 20, 216),
    },
}


def authority(page: int) -> dict[str, Any]:
    """Return a source authority for one exact licensed manual PDF page."""
    return {
        "page": page, "ruleset": "2014", "filename": SOURCE,
        "source_role": "authority", "logical_page": page,
        "source_title": "Bigby Presenta: La Gloria dei Giganti",
        "source_status": "active", "authority_class": "licensed_translation",
        "logical_source_id": "bgg_2023_it",
    }


def assess_bigby_reclassification(name: str, record: dict[str, Any] | None) -> dict[str, Any]:
    """Review one target; fail closed on drift, copied values, or bad dice math."""
    if name not in SPECS or not isinstance(record, dict):
        raise ValueError("unregistered_target_or_missing_record")
    spec = SPECS[name]
    required = {
        "id": spec["id"],
        "user_id": USER_ID,
        "name": name, "source_name": name,
        "normalized_name": name.casefold(),
        "reference_type": "other",
        "source_language": "it",
        "source_key": SOURCE,
        "review_status": spec["status"],
        "review_flags": [], "canonical_id": None,
        "attributes": {}, "source_attributes": {},
        "source_text_checksum": spec["checksum"],
        "review_corrections": spec["corrections"],
        "source_refs": [authority(spec["page"])],
    }
    if any(record.get(field) != value for field, value in required.items()):
        raise ValueError("original_registered_snapshot_drift")
    source_text = record.get("source_full_text")
    if not isinstance(source_text, str) or source_text != record.get("full_text"):
        raise ValueError("original_raw_not_preserved")
    if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != spec["raw_sha256"]:
        raise ValueError("original_raw_digest_changed")
    if not source_text.strip():
        raise ValueError("empty_original_description")
    hp, count, sides, bonus = spec["dice"]
    if count * (sides + 1) // 2 + bonus != hp:
        raise ValueError("incoherent_dice_average")
    if monster_semantic_numeric_flags(spec["attrs"]):
        raise ValueError("global_numeric_gate_failed")
    return {
        "status": "eligible_exact_record_reclassification",
        "name": name, "record_id": spec["id"],
        "source_description_page": spec["page"],
        "source_statblock_page": spec["stats_page"],
        "proposed_attributes": spec["attrs"],
        "append_statblock_authority": spec["stats_page"] != spec["page"],
        "raw_preserved": True, "historical_ocr_preserved": True,
        "writes": 0,
    }

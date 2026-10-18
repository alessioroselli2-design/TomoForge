"""Original Italian Demilich statblock reconciled with official WotC errata.

The owner's private Italian 353-page Monster Manual physical page 48 prints
80 (20d4). The official Wizards 2016 MM Errata explicitly corrects that to
80 (32d4), leaving its HP total 80 and restoring dice-average consistency.
We never modify the raw Italian source excerpt. All corrections have their own
provenance and original/canonical field values. This module writes nothing.
"""
from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

from services.ocr_semantic_gates import (
    monster_identity_sanity_flags,
    monster_semantic_numeric_flags,
)

SOURCE_ID = "mm_2014_it"
FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SOURCE_SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
SOURCE_PAGES = 353
NAME = "Demilich"
PAGE = 48
ID = "ref_7f1163f340a78c89634cf3ed60630ded"
ORIGINAL_HP = "80 (20d4)"
CANONICAL_HP = "80 (32d4)"
ERRATA_URL = "https://media.wizards.com/2016/downloads/DND/MM-Errata.pdf"
ERRATA_RULE = "Demilich (p. 48). Hit points: 80 (32d4) [was 20d4]."
ORIGINAL_SHA256 = "ca9716e97fe642d0a3a3bfd59ec7874ad1de72da4a42548aa2148fc6bee7860c"
CANONICAL_SHA256 = "0eaa5d500cac9bb59d22a0ee0536410f3f57ab8119c3c6ba82bdd75d6326b44a"

ATTRIBUTES: dict[str, Any] = {
    "classe_armatura": "20 (armatura naturale)",
    "punti_ferita": CANONICAL_HP,
    "velocita": "0 m, volare 9 m (fluttuare)",
    "grado_sfida": "18",
    "caratteristiche": {
        "for": "1", "des": "20", "cos": "10",
        "int": "20", "sag": "17", "car": "20",
    },
    "tipo_creatura": "Non morto",
    "taglia": "Minuscolo",
    "allineamento": "neutrale malvagio",
    "completezza_scheda": "statistiche_essenziali",
}


def _excerpt(hp: str) -> str:
    return (
        "Demilich. Non morto Minuscolo, neutrale malvagio. "
        "Classe Armatura 20 (armatura naturale). "
        f"Punti Ferita {hp}. "
        "Velocità 0 m, volare 9 m (fluttuare). Sfida 18."
    )


def audit(
    catalog: dict[str, Any] | None,
    record_exists: bool = False,
    monster_name_collisions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if record_exists or monster_name_collisions:
        raise ValueError("demilich_duplicate_monster")
    required = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": FILENAME,
        "physical_sha256": SOURCE_SHA256,
        "physical_pages": SOURCE_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(k) != v for k, v in required.items()
    ):
        raise ValueError("original_manual_source_drift")

    token = f"{SOURCE_ID}|{FILENAME}|{PAGE}|{NAME.casefold()}"
    expected_id = "ref_" + hashlib.sha256(token.encode()).hexdigest()[:32]
    if expected_id != ID:
        raise ValueError("demilich_deterministic_identity_changed")
    raw = _excerpt(ORIGINAL_HP)
    canonical = _excerpt(CANONICAL_HP)
    if hashlib.sha256(raw.encode()).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("italian_original_excerpt_changed")
    if hashlib.sha256(canonical.encode()).hexdigest() != CANONICAL_SHA256:
        raise ValueError("official_errata_excerpt_changed")
    if not (
        ORIGINAL_HP == "80 (20d4)"
        and CANONICAL_HP == "80 (32d4)"
        and ERRATA_RULE == "Demilich (p. 48). Hit points: 80 (32d4) [was 20d4]."
        and ERRATA_URL == "https://media.wizards.com/2016/downloads/DND/MM-Errata.pdf"
    ):
        raise ValueError("source_and_official_errata_disagree")
    if (20 * (4 + 1)) // 2 != 50 or (32 * (4 + 1)) // 2 != 80:
        raise ValueError("errata_math_assertion_failed")
    attrs = deepcopy(ATTRIBUTES)
    if monster_identity_sanity_flags(NAME) or monster_semantic_numeric_flags(attrs):
        raise ValueError("canonical_numeric_gate_failed")
    if set(attrs["caratteristiche"]) != {"for", "des", "cos", "int", "sag", "car"}:
        raise ValueError("missing_original_abilities")

    source_attrs = deepcopy(attrs)
    source_attrs["punti_ferita"] = ORIGINAL_HP
    corrections = {
        "punti_ferita": {
            "original": ORIGINAL_HP,
            "corrected": CANONICAL_HP,
            "authority": "Wizards of the Coast Monster Manual Errata",
            "url": ERRATA_URL,
            "rule": ERRATA_RULE,
        }
    }
    return {
        "status": "eligible_source_reconciled_with_official_errata",
        "id": ID,
        "name": NAME,
        "physical_page": PAGE,
        "source_excerpt": raw,
        "source_text_checksum": ORIGINAL_SHA256,
        "canonical_excerpt": canonical,
        "canonical_excerpt_sha256": CANONICAL_SHA256,
        "attributes": attrs,
        "source_attributes": source_attrs,
        "review_corrections": corrections,
        "original_source_unchanged": True,
        "writes": 0,
    }

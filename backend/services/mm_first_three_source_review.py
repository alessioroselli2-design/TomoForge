"""Read-only source gates for three independent angels in the Italian Monster Manual.

The private original 353-page licensed PDF was checked by full-file SHA256,
rendered pages 16–18, and two independently configured local OCR passes.
Neither original PDF bytes nor full source pages are committed to this repo.
This module only checks *eligibility*, never writes or calls Supabase.
"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any

from services.ocr_semantic_gates import (
    monster_identity_sanity_flags,
    monster_semantic_numeric_flags,
)

SOURCE_ID = "mm_2014_it"
SOURCE_FILENAME = "847921086-Manuale-Dei-Mostri-5e.pdf"
SOURCE_SHA256 = "b33eb72e5eb78fe3e3dcbde5315f5b9afbe42e4a457a518cc93f7766979a381c"
SOURCE_PAGES = 353

ANGELS: dict[str, dict[str, Any]] = {
    "Deva": {
        "id": "ref_fdc32fd9d349cfdc4691f5c23f48cb94",
        "page": 16,
        "taglia": "Medio",
        "classe_armatura": "17 (armatura naturale)",
        "punti_ferita": "136 (16d8 + 64)",
        "velocita": "9 m, volare 27 m",
        "grado_sfida": "10",
        "caratteristiche": {
            "for": "18", "des": "18", "cos": "18",
            "int": "17", "sag": "20", "car": "20",
        },
        "excerpt_sha256": "849c8892d2ab25991ca6a17461a199aa3903a2f1130be2d9687a2081ce529518",
    },
    "Planetar": {
        "id": "ref_6eb5d30bbe38c52fb7f6eb913a0d45f1",
        "page": 17,
        "taglia": "Grande",
        "classe_armatura": "19 (armatura naturale)",
        "punti_ferita": "200 (16d10 + 112)",
        "velocita": "12 m, volare 36 m",
        "grado_sfida": "16",
        "caratteristiche": {
            "for": "24", "des": "20", "cos": "24",
            "int": "19", "sag": "22", "car": "25",
        },
        "excerpt_sha256": "7dde2f773d497dcea92c2bcbb0c5fe39fa232bc4774178f06e8bb0289b75e9b5",
    },
    "Solar": {
        "id": "ref_011a266126809e8ffff0ec362e4728a7",
        "page": 18,
        "taglia": "Grande",
        "classe_armatura": "21 (armatura naturale)",
        "punti_ferita": "243 (18d10 + 144)",
        "velocita": "15 m, volare 45 m",
        "grado_sfida": "21",
        "caratteristiche": {
            "for": "26", "des": "22", "cos": "26",
            "int": "25", "sag": "25", "car": "30",
        },
        "excerpt_sha256": "31633a7e501d2291c8a74440f01db47d0fe712eefd94b6de111140fa62b30a1e",
    },
}

_HP_DICE = re.compile(r"(\\d+) \\((\\d+)d(\\d+) \\+ (\\d+)\\)\\Z")


def _excerpt(name: str, attrs: dict[str, Any]) -> str:
    return (
        f"{name}. Celestiale {attrs['taglia']}, legale buono. "
        f"Classe Armatura {attrs['classe_armatura']}. "
        f"Punti Ferita {attrs['punti_ferita']}. "
        f"Velocità {attrs['velocita']}. Sfida {attrs['grado_sfida']}."
    )


def audit_mm_angel(
    name: str,
    existing_id: dict[str, Any] | None,
    existing_name: list[dict[str, Any]],
    catalog: dict[str, Any] | None,
) -> dict[str, Any]:
    """Fail closed on missing authority, identity drift or core-field mismatch."""
    if name not in ANGELS:
        raise ValueError("unexpected_monster_identity")
    if existing_id is not None or existing_name:
        raise ValueError("monster_identity_already_present")
    expected_source = {
        "logical_source_id": SOURCE_ID,
        "physical_filename": SOURCE_FILENAME,
        "physical_sha256": SOURCE_SHA256,
        "physical_pages": SOURCE_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }
    if not isinstance(catalog, dict) or any(
        catalog.get(k) != v for k, v in expected_source.items()
    ):
        raise ValueError("original_manual_authority_missing_or_changed")

    attrs = ANGELS[name]
    page = attrs["page"]
    if page not in (16, 17, 18):
        raise ValueError("page_outside_sealed_visual_window")
    token = f"{SOURCE_ID}|{SOURCE_FILENAME}|{page}|{name.casefold()}"
    expected_id = "ref_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
    if attrs["id"] != expected_id:
        raise ValueError("deterministic_record_id_drift")

    excerpt = _excerpt(name, attrs)
    digest = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
    if digest != attrs["excerpt_sha256"]:
        raise ValueError("visually_sealed_statblock_core_changed")
    core = {
        "classe_armatura": attrs["classe_armatura"],
        "punti_ferita": attrs["punti_ferita"],
        "velocita": attrs["velocita"],
        "caratteristiche": attrs["caratteristiche"],
        "grado_sfida": attrs["grado_sfida"],
    }
    if monster_identity_sanity_flags(name) or monster_semantic_numeric_flags(core):
        raise ValueError("monster_semantic_gate_failed")
    hp = _HP_DICE.fullmatch(attrs["punti_ferita"])
    if hp is None:
        raise ValueError("hit_dice_expression_unparseable")
    average, dice, die, modifier = map(int, hp.groups())
    if (dice * (die + 1)) // 2 + modifier != average:
        raise ValueError("hit_dice_average_disagrees")
    stats = attrs["caratteristiche"]
    if set(stats) != {"for", "des", "cos", "int", "sag", "car"} or any(
        not str(v).isdigit() or not 1 <= int(v) <= 30
        for v in stats.values()
    ):
        raise ValueError("ability_score_gate_failed")
    return {
        "status": "eligible_original_visual_statblock",
        "id": expected_id,
        "name": name,
        "source_page": page,
        "source_excerpt": excerpt,
        "source_excerpt_sha256": digest,
        "attributes": deepcopy(core),
        "automatic_ocr_not_accepted_as_truth": True,
        "writes": 0,
    }

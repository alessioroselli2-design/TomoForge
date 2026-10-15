"""Read-only source-locked naming corrections for seven verified Bigby monsters.

These are NOT new monsters: seven existing verified records have names
truncated from their original Italian same-name statblock titles.
All source and numeric fields must stay unchanged in any later review.
"""
from __future__ import annotations

import hashlib
from typing import Any

SOURCE = "760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf"
TARGETS = {
    "Invocatore": (
        "ref_0001847c82b3517895ac990182ad5b9a", 146,
        "Gigante Del Fuoco Invocatore",
        "8b7ffb44d327342a05c12fc8d28a56ffe70f62190d0de8878afdf5ca8750cd92",
        "137622a5621419c848187f31c56d117da4131b98a38ff241916843e716f1401c",
    ),
    "Modellaghiaccio": (
        "ref_a4ca7d65762650dc8e24dcbde06a6342", 148,
        "Gigante Del Gelo Modellaghiaccio",
        "0980bdaf9d426461e5666e89042b035985c551f66219878446fd7ca6621f0d4b",
        "c55bd25ef583929557c1220d426188302f4f8836698ba771643e1b05ee62dae3",
    ),
    "Valanghivo": (
        "ref_84f117205a46505d890ed8c41874166c", 149,
        "Gigante Delle Colline Valanghivo",
        "613c0328db48f0bc089356fd86bd66f1442eae688f3af441c0d95030254cba2a",
        "154c219a426c66a5f37f825231921f3206eb513556c23fb4d53503ba68705d53",
    ),
    "Giocatore Del Destino": (
        "ref_6faaa21da20450fda325799312cf0817", 151,
        "Gigante Delle Nuvole Giocatore Del Destino",
        "394652ab4febedb196a0ec5f186f1936259391a744ae651ddc629c990ec385fc",
        "2dc16caec8c756d1f4dc1b7f69a476db20f571e4fe6ec3e377ac9c2128c23d96",
    ),
    "T'Erra Malvagia": (
        "ref_6b5c8da8abbf545e9f2ea14f88155b78", 152,
        "Gigante Delle Pietre Della Terra Malvagia",
        "6c01eae905b17ddbe67d9854820a8b6cbe88afb25525e7c7f63eb41763481ff4",
        "5162364b9494e438be6b91c0f57a401dd77f318e67955f5c7cfdce5d2c6776cb",
    ),
    "Linguarupestre": (
        "ref_c5f631a36b5f51dc9123a728f65c2ec9", 153,
        "Gigante Delle Pietre Linguarupestre",
        "9aee292abcf550f1a6e1abd97f366c0eaa793ee8b91b576132def21910e5c05f",
        "4f91568198bd685aced325508031135d6c416a10699a5185652f0085be0078cb",
    ),
    "Chiamaburrasche": (
        "ref_e075432f79145e36a484fb6ce88eb62a", 154,
        "Gigante Delle Tempeste Chiamaburrasche",
        "411c45449c2b747462e5fa62b10a032a1d9672248d0c5a5b77b85ff2678fce17",
        "00eed9618b49146d280f41426e6610478515e7bc0684120f839a0ac5fd0a16b1",
    ),
}


def source_locked_name_review(row: dict[str, Any] | None, old_name: str) -> dict[str, Any]:
    """Propose only a display-name correction, fail closed on source drift."""
    if not isinstance(row, dict) or old_name not in TARGETS:
        raise ValueError("target_record_or_name_missing")
    id_, page, original_title, checksum, raw_sha = TARGETS[old_name]
    required = {
        "id": id_,
        "user_id": "user_fabf28726a20",
        "name": old_name,
        "normalized_name": old_name.casefold().replace("'", " "),
        "source_name": old_name,
        "reference_type": "monster",
        "review_status": "verified",
        "review_flags": [],
        "source_key": SOURCE,
        "source_language": "it",
        "canonical_id": None,
        "source_text_checksum": checksum,
    }
    if any(row.get(field) != val for field, val in required.items()):
        raise ValueError("existing_verified_record_identity_drift")
    refs = row.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 1:
        raise ValueError("original_registered_page_missing")
    authority = refs[0]
    expected_ref = {
        "page": page, "logical_page": page, "ruleset": "2014",
        "filename": SOURCE, "source_role": "authority",
        "source_status": "active", "authority_class": "licensed_translation",
        "logical_source_id": "bgg_2023_it",
    }
    if any(authority.get(k) != v for k, v in expected_ref.items()):
        raise ValueError("registered_authority_drift")
    raw = row.get("source_full_text")
    if not isinstance(raw, str) or row.get("full_text") != raw:
        raise ValueError("original_raw_changed")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != raw_sha:
        raise ValueError("original_raw_hash_drift")
    attrs = row.get("attributes")
    if not isinstance(attrs, dict) or not all(
        isinstance(attrs.get(k), str) and attrs[k]
        for k in ("classe_armatura", "punti_ferita", "velocita")
    ):
        raise ValueError("existing_verified_attributes_missing")
    return {
        "status": "eligible_verified_name_only_correction",
        "id": id_, "previous_name": old_name,
        "source_title": original_title,
        "source_page": page,
        "name_only": True,
        "old_original_name_preserved_in_source_name": True,
        "writes": 0,
    }

"""Fail-closed, read-only preflight for a batch of monster localizations.

Input files are PRIVATE and must not be committed. No network access, no
Supabase writes, no canonical data changes, no automatic translation approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

CORE_FIELDS = frozenset({
    "classe_armatura", "punti_ferita", "velocita", "grado_sfida",
    "caratteristiche", "for", "des", "cos", "int", "sag", "car",
})
TRANSLATED_FIELDS = frozenset({
    "taglia", "tipo", "allineamento", "abilita", "immunita_danni",
    "immunita_condizioni", "sensi", "linguaggi", "bonus_competenza",
    "esperienza", "tratti", "azioni",
})
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class GateFailure(ValueError):
    """The proposed localization is not sufficiently grounded."""


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()


def _features(items: Any, *, label: str, expected: Any) -> None:
    if not isinstance(items, list) or type(expected) is not int or expected < 0:
        raise GateFailure(f"{label} is not a source-counted feature list")
    if len(items) != expected:
        raise GateFailure(f"{label} count differs from the source inventory")
    seen = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"nome", "descrizione"}:
            raise GateFailure(f"Each {label} needs a name and a description")
        for key in ("nome", "descrizione"):
            if not isinstance(item[key], str) or not item[key].strip():
                raise GateFailure(f"Missing {key} in {label}")
        key = item["nome"].strip().casefold()
        if key in seen:
            raise GateFailure(f"Duplicate {label} name")
        seen.add(key)


def preview(snapshot: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Propose a private phase-two patch without mutating any existing field."""
    if not isinstance(snapshot, dict) or not isinstance(candidate, dict):
        raise GateFailure("Both inputs must be JSON objects")
    for field in (
        "record_id", "name_en", "name_it",
        "source_id", "source_sha256", "source_page"
    ):
        if not candidate.get(field):
            raise GateFailure(f"Candidate missing {field}")
    if not SHA256.fullmatch(str(candidate["source_sha256"])):
        raise GateFailure("Invalid source SHA256")
    if snapshot.get("reference_type") != "monster":
        raise GateFailure("Target is not a monster")
    if snapshot.get("review_status") != "verified":
        raise GateFailure("Mechanical core not verified")
    if snapshot.get("id") != candidate["record_id"]:
        raise GateFailure("Different target record ID")
    if (
        snapshot.get("source_name"), snapshot.get("name")
    ) != (candidate["name_en"], candidate["name_en"]):
        raise GateFailure("Original name or alias disagrees")
    name_it = candidate["name_it"]
    if not isinstance(name_it, str) or not name_it.strip():
        raise GateFailure("Missing Italian name")
    if name_it != name_it.strip():
        raise GateFailure("Invalid whitespace around Italian name")
    if candidate.get("name_basis") not in {
        "official_it", "licensed_it", "proper_name_retained"
    }:
        raise GateFailure("Unverified Italian name basis")
    if not isinstance(candidate.get("name_reference"), str):
        raise GateFailure("Missing name evidence")
    if not candidate["name_reference"].strip():
        raise GateFailure("Empty name evidence")
    if candidate.get("translation_status") != "draft":
        raise GateFailure("Cannot claim translated/verified status in a pilot")
    if candidate.get("translation_review_status") != "pending":
        raise GateFailure("Independent translation review required")
    if snapshot.get("translation_review_status") not in ("pending", ""):
        raise GateFailure("This translation is already in review or finished")

    source_matches = [
        source for source in snapshot.get("source_refs", [])
        if source.get("logical_source_id") == candidate["source_id"]
        and source.get("physical_sha256") == candidate["source_sha256"]
        and source.get("page") == candidate["source_page"]
    ]
    if len(source_matches) != 1:
        raise GateFailure("Original source, page or SHA256 not unique/matching")

    current = snapshot.get("attributes")
    raw = snapshot.get("source_attributes")
    new_attrs = candidate.get("attributes_it")
    if not all(isinstance(x, dict) for x in (current, raw, new_attrs)):
        raise GateFailure("Expected structured original/translated attributes")
    if CORE_FIELDS.intersection(new_attrs):
        raise GateFailure("Refusing modification of any verified core field")
    extras = set(new_attrs) - TRANSLATED_FIELDS
    if extras:
        raise GateFailure(f"Unexpected fields: {sorted(extras)}")
    for key in new_attrs:
        if key in current and current[key] not in (None, "", [], {}):
            raise GateFailure(f"Cannot overwrite populated field: {key}")

    _features(
        new_attrs.get("tratti"), label="tratti",
        expected=candidate.get("expected_trait_count")
    )
    _features(
        new_attrs.get("azioni"), label="azioni",
        expected=candidate.get("expected_action_count")
    )
    has_actions = candidate.get("source_has_actions_section")
    if not isinstance(has_actions, bool):
        raise GateFailure("Actions section must be independently reviewed")
    if has_actions != (candidate["expected_action_count"] > 0):
        raise GateFailure("Actions invented or omitted relative to source")
    description = candidate.get("description_it")
    if not isinstance(description, str) or not 25 <= len(description.strip()) <= 500:
        raise GateFailure("Missing short description in Italian")
    if snapshot.get("description") not in (None, ""):
        raise GateFailure("Would overwrite an existing description")
    if (
        snapshot.get("name") != name_it
        and candidate.get("name_collision_clear") is not True
    ):
        raise GateFailure("Name collision/alias audit not complete")

    return {
        "mode": "dry_run", "writes": 0,
        "record_id": snapshot["id"],
        "source_id": candidate["source_id"],
        "source_page": candidate["source_page"],
        "source_sha256": candidate["source_sha256"],
        "name_original": candidate["name_en"],
        "name_italian": name_it,
        "name_basis": candidate["name_basis"],
        "name_reference": candidate["name_reference"],
        "description_it": description,
        "attributes_it": new_attrs,
        "translation_status": "draft",
        "translation_review_status": "pending",
        "source_core_hash": _canonical_hash(raw),
        "record_core_hash": _canonical_hash({
            key: current[key] for key in CORE_FIELDS if key in current
        }),
    }


def preview_batch(
    snapshots: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fail the entire batch on a single failed candidate."""
    if not isinstance(snapshots, list) or not isinstance(candidates, list):
        raise GateFailure("Lists required")
    if not candidates or len(candidates) > 25:
        raise GateFailure("Batch must contain 1 to 25 monsters")
    by_id = {record["id"]: record for record in snapshots}
    if len(by_id) != len(snapshots):
        raise GateFailure("Repeated source record IDs")
    if len({item.get("record_id") for item in candidates}) != len(candidates):
        raise GateFailure("Duplicated candidate record ID")
    if len({
        str(item.get("name_it", "")).strip().casefold() for item in candidates
    }) != len(candidates):
        raise GateFailure("Collision among Italian names within the batch")
    proposed = []
    for candidate in candidates:
        original = by_id.get(candidate.get("record_id"))
        if original is None:
            raise GateFailure("Missing source snapshot for candidate")
        proposed.append(preview(original, candidate))
    return {
        "mode": "dry_run", "writes": 0, "candidates": len(proposed),
        "passed": len(proposed), "blocked": 0, "records": proposed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    args = parser.parse_args()
    try:
        originals = json.loads(args.snapshots.read_text(encoding="utf-8"))
        proposed = json.loads(args.candidates.read_text(encoding="utf-8"))
        result = preview_batch(originals, proposed)
    except (GateFailure, KeyError, ValueError, TypeError, OSError) as exc:
        print(json.dumps({
            "mode": "dry_run", "writes": 0,
            "passed": 0, "blocked": True, "error": str(exc),
        }, ensure_ascii=False))
        return 1
    # The full translated text is private; stdout emits only the audit counts.
    print(json.dumps({
        key: result[key]
        for key in ("mode", "writes", "candidates", "passed", "blocked")
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Fail-closed, read-only checks for a multilingual monster completion pilot.

This module deliberately does NOT translate, call AI services, write to a
database, or mark records as verified. A later runner must supply independently
source-checked fields and explicit write authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from translation_integrity import translation_verification_fingerprint

REQUIRED_STAT_FIELDS = (
    "tipo", "taglia", "allineamento", "classe_armatura",
    "punti_ferita", "velocita", "caratteristiche",
    "sensi", "linguaggi", "grado_sfida",
)
ABILITY_KEYS = ("for", "des", "cos", "int", "sag", "car")
OPTIONAL_SECTIONS = ("tratti", "azioni", "reazioni", "azioni_leggendarie")


@dataclass(frozen=True)
class Preflight:
    ready: bool
    blockers: tuple[str, ...]
    proposed_fingerprint: str | None


def preflight(
    original: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    source_page_checked: bool = False,
    independent_review: bool = False,
    source_sections_checked: bool = False,
) -> Preflight:
    """Inspect one candidate without changing either input.

    An absent optional section is not invented; source comparison must establish
    whether it is absent in the book or missing from extraction.
    """
    problems: list[str] = []
    if not source_page_checked:
        problems.append("source_page_not_checked")
    if not independent_review:
        problems.append("independent_review_missing")
    if not source_sections_checked:
        problems.append("source_sections_not_checked")
    if not original.get("id"):
        problems.append("record_id_missing")
    if candidate.get("id") != original.get("id"):
        problems.append("record_identity_changed")
    if candidate.get("source_refs") != original.get("source_refs"):
        problems.append("source_provenance_changed")
    if original.get("translation_lease_id"):
        problems.append("active_or_unknown_translation_lease")
    if original.get("translation_status") == "processing" and original.get("translation_lease_expires_at", 0):
        problems.append("processing_lease_requires_recheck")
    if candidate.get("translation_status") != "translated":
        problems.append("candidate_not_translated")
    for key in ("source_name", "source_description", "source_full_text", "source_attributes", "source_language"):
        if candidate.get(key) != original.get(key):
            problems.append(f"immutable_source_changed:{key}")
    attributes = candidate.get("attributes")
    if not isinstance(attributes, dict):
        problems.append("attributes_missing")
        attributes = {}
    for key in REQUIRED_STAT_FIELDS:
        if not attributes.get(key):
            problems.append(f"required_field_missing:{key}")
    scores = attributes.get("caratteristiche")
    if not isinstance(scores, dict) or any(not isinstance(scores.get(k), int) for k in ABILITY_KEYS):
        problems.append("ability_scores_incomplete")
    for key in OPTIONAL_SECTIONS:
        if key not in attributes:
            problems.append(f"section_unaccounted_for:{key}")
        elif not isinstance(attributes[key], list):
            problems.append(f"invalid_section:{key}")
    if not candidate.get("description"):
        problems.append("description_missing")
    if not original.get("source_refs"):
        problems.append("source_provenance_missing")
    fingerprint = translation_verification_fingerprint(dict(candidate)) if not problems else None
    return Preflight(not problems, tuple(problems), fingerprint)

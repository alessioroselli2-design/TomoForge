"""Fail-closed handling of source-resolved OCR debris in the human review queue.

Source-confirmed OCR fragments remain unverified and in their original records.
Only the *active* review list omits fragments with complete, auditable
disposition metadata. Normal library lookup and review history are untouched.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

_DISPOSITION_KINDS = frozenset(
    {
        "source_confirmed_redundant_statblock_fragment",
        "source_confirmed_contextual_prose_for_verified_monster",
        "source_confirmed_section_plus_megera_statblock",
        "source_confirmed_multi_monster_boundary_splice",
    }
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def is_source_resolved_ocr_fragment(record: Mapping[str, Any]) -> bool:
    """Return True only for fully documented, deliberately excluded OCR debris.

    Merely setting ai_review_status='excluded', giving a record a fragment-like
    name, or populating a note is not sufficient to hide it from reviewers.
    An incomplete or altered disposition is shown for human review instead.
    """
    if (
        record.get("reference_type") != "other"
        or record.get("review_status") != "pending"
        or record.get("ai_review_status") != "excluded"
    ):
        return False

    flags = record.get("review_flags")
    if not isinstance(flags, list) or "source_confirmed_redundant_fragment" not in flags:
        return False
    corrections = record.get("review_corrections")
    if not isinstance(corrections, dict):
        return False
    disposition = corrections.get("_duplicate_disposition")
    if not isinstance(disposition, dict):
        return False

    kind = disposition.get("kind")
    if kind not in _DISPOSITION_KINDS:
        return False
    physical_sha = disposition.get("physical_sha256")
    if not isinstance(physical_sha, str) or not _SHA256.fullmatch(physical_sha):
        return False
    page = disposition.get("original_pdf_page")
    if not isinstance(page, int) or isinstance(page, bool) or page <= 0:
        return False
    if not isinstance(disposition.get("evidence"), str) or not disposition["evidence"].strip():
        return False

    if kind == "source_confirmed_multi_monster_boundary_splice":
        targets = disposition.get("target_reference_ids")
        return (
            isinstance(targets, list)
            and len(targets) >= 2
            and all(isinstance(t, str) and t.startswith("ref_") for t in targets)
            and len(set(targets)) == len(targets)
        )
    target = disposition.get("target_reference_id")
    return isinstance(target, str) and target.startswith("ref_")

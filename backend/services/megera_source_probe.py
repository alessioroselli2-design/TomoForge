"""Read-only privacy-safe geometry probe for Eberron Megera Crepuscolare.

Emits counters and booleans only, never third-party source text or OCR images.
This is NOT a verification or authorization to modify review status.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from services.ocr_semantic_gates import monster_semantic_numeric_flags


def compact_word(value: Any) -> str:
    folded = unicodedata.normalize("NFKD", str(value or "")).casefold()
    folded = "".join(x for x in folded if not unicodedata.combining(x))
    return re.sub(r"[^a-z0-9]", "", folded)


def page_safe_geometry(page: Any, page_number: int) -> dict[str, Any]:
    words = page.get_text("words", sort=True)
    lines: dict[tuple[int, int], list[Any]] = {}
    for word in words:
        if len(word) < 7:
            continue
        lines.setdefault((int(word[5]), int(word[6])), []).append(word)
    targets = []
    all_words = [compact_word(w[4]) for w in words]
    for line in lines.values():
        tokens = [compact_word(w[4]) for w in line]
        phrase = "".join(tokens)
        title = "megeracrepuscolare" in phrase
        ca_label = "classearmatura" in phrase
        hp_label = "puntiferita" in phrase
        speed_label = "velocita" in phrase
        if title or ca_label or hp_label or speed_label:
            targets.append({
                "x": round(min(float(w[0]) for w in line) / page.rect.width, 3),
                "y": round(min(float(w[1]) for w in line) / page.rect.height, 3),
                "title": title,
                "ca_label": ca_label,
                "hp_label": hp_label,
                "speed_label": speed_label,
                "has_17": "17" in tokens,
                "has_82": "82" in tokens,
                "has_15d8": "15d8" in tokens,
                "has_9": "9" in tokens,
                "has_15": "15" in tokens,
                "has_natural": "naturale" in tokens,
                "has_m": "m" in tokens,
            })
    return {
        "page": page_number,
        "words": len(words),
        "megera_mentions": all_words.count("megera"),
        "crepuscolare_mentions": all_words.count("crepuscolare"),
        "title_lines": sum(x["title"] for x in targets),
        "ca_labels": sum(x["ca_label"] for x in targets),
        "hp_labels": sum(x["hp_label"] for x in targets),
        "speed_labels": sum(x["speed_label"] for x in targets),
        "lines": targets[:15],
    }


# The original Italian prose stored in full_text does not include the statblock;
# verify the authenticated registered PDF page natively before any promotion.
RECORD_ID = "ref_1be623f67ff55c40aebefd7b8445f16f"
SOURCE_CHECKSUM = "d3a64df2296716ce03238ac2f27bae5050993a2fc3bce03fc736183f4dbb9816"
RAW_SHA256 = "b6b504f1ce8be0d72188f4a2c9357f488da726b8eca69626f37ccfee6f577a0f"
ATTRIBUTES = {
    "classe_armatura": "17 (armatura naturale)",
    "punti_ferita": "82 (15d8 + 15)",
    "velocita": "9 m",
}


def assess_megera_registered_source(
    record: dict[str, Any], page: dict[str, Any] | None
) -> dict[str, Any]:
    """Check the exact source PDF geometry, not only saved lore or OCR."""
    if not isinstance(record, dict) or not isinstance(page, dict):
        raise ValueError("missing_sealed_source_or_page")
    if not all(
        (
            record.get("id") == RECORD_ID,
            record.get("reference_type") == "monster",
            record.get("name") == "Megera Crepuscolare",
            record.get("review_status") == "pending",
            record.get("canonical_id") is None,
            record.get("review_flags") == [
                "ocr_da_verificare", "source_guided_repair"
            ],
            record.get("source_text_checksum") == SOURCE_CHECKSUM,
            record.get("attributes") == ATTRIBUTES,
            isinstance(record.get("full_text"), str),
            hashlib.sha256(
                str(record.get("full_text") or "").encode("utf-8")
            ).hexdigest() == RAW_SHA256,
        )
    ):
        raise ValueError("registered_record_or_text_drift")
    refs = record.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 1:
        raise ValueError("registered_ref_count_drift")
    ref = refs[0]
    if not isinstance(ref, dict) or not all(
        (
            ref.get("page") == 305,
            ref.get("logical_page") == 305,
            ref.get("logical_source_id") == "erlw_2019_it",
            ref.get("source_role") == "authority",
            ref.get("source_status") == "active",
            ref.get("authority_class") == "licensed_translation",
            ref.get("filename") == "618795464-Eberron.pdf",
            ref.get("ruleset") == "2014",
        )
    ):
        raise ValueError("source_provenance_changed")
    if page.get("page") != 305 or int(page.get("words") or 0) < 250:
        raise ValueError("incorrect_or_empty_registered_page")
    lines = page.get("lines")
    if not isinstance(lines, list):
        raise ValueError("missing_native_text_geometry")
    headings = [
        line for line in lines
        if line.get("title") is True
        and 0 <= line.get("x", 2) < 0.25
        and 0.35 <= line.get("y", 2) <= 0.47
    ]
    region = [
        line for line in lines
        if 0.48 <= line.get("x", -1) < 0.95
        and 0.27 <= line.get("y", -1) <= 0.37
    ]
    ca = [x for x in region if x.get("ca_label") and x.get("has_17") and x.get("has_natural")]
    hp = [
        x for x in region
        if x.get("hp_label") and x.get("has_82")
        and x.get("has_15d8") and x.get("has_15")
    ]
    speed = [x for x in region if x.get("speed_label") and x.get("has_9") and x.get("has_m")]
    if not (len(headings) == len(ca) == len(hp) == len(speed) == 1):
        raise ValueError("no_unique_native_source_statblock_agreement")
    # Global HP math must still pass. The English original independently
    # confirms AC17 / 82 (15d8+15) / Speed30ft: Eberron ERLW p292.
    if monster_semantic_numeric_flags(ATTRIBUTES):
        raise ValueError("numeric_gates_failed")
    if (15 * (8 + 1)) // 2 + 15 != 82:
        raise ValueError("hit_dice_math_disagrees")
    return {
        "status": "eligible_status_only_source_review",
        "source": "erlw_2019_it",
        "page": 305,
        "attributes_unchanged": True,
        "numeric_gates_passed": True,
        "registered_pdf_native_core_passed": True,
    }

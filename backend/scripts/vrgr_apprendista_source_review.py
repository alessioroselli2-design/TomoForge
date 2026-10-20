"""Source-locked human-reviewed core facts for Van Richten's Apprendista.

This is a review record, not a bulk OCR override or a database writer.
The 257-page original PDF was visually inspected for p201 and matched its
registered SHA256; see TomoForge issue #493, comment 6287199086.
Actions and traits are not certified by this core-only record.
"""
from __future__ import annotations

import re

SOURCE_ID = "vrgr_2021_it"
SOURCE_FILENAME = "667440680-Guida-Di-Von-Richten-a-Ravenloft.pdf"
SOURCE_SHA256 = "7d8e6479f592df1630fc3abb02d3612a1d8514b3faff8d558288005185980209"
SOURCE_PAGES = 257
PAGE = 201
REVIEW_EVIDENCE_URL = (
    "https://github.com/alessioroselli2-design/TomoForge/"
    "issues/493#issuecomment-6287199086"
)
APPRENDISTA_CORE = {
    "name": "Apprendista",
    "logical_source_id": SOURCE_ID,
    "physical_page": PAGE,
    "type": "Umanoide",
    "size": "Medio",
    "classe_armatura": "10",
    "punti_ferita": "7 (2d8 - 2)",
    "velocita": "9 m",
    "caratteristiche": {"for": "8", "des": "10", "cos": "9", "int": "13", "sag": "11", "car": "12"},
    "grado_sfida": "—",
    "completezza_scheda": "statistiche_essenziali",
}
BAD_OCR_HP = "7 (248 - 2)"
DICE = re.compile(r"^(\d+)\s*\((\d+)d(\d+)(?:\s*([+-])\s*(\d+))?\)$")


def hit_dice_coherent(text: str) -> bool:
    """Fail closed on malformed dice or wrong HP mean, including the original OCR."""
    m = DICE.fullmatch(text.strip())
    if not m:
        return False
    hp, count, sides, sign, amount = m.groups()
    dice, faces = int(count), int(sides)
    if dice < 1 or dice > 100 or faces not in {4, 6, 8, 10, 12, 20}:
        return False
    modifier = int(amount or 0) * (-1 if sign == "-" else 1)
    return int(hp) == (dice * (faces + 1)) // 2 + modifier


def validate_review(core: dict, registered_sha256: str, existing_names: list[str]) -> None:
    """Validate a proposed *reviewed* record, never authorize a write from OCR alone."""
    if registered_sha256 != SOURCE_SHA256:
        raise ValueError("van_richten_source_hash_mismatch")
    if core != APPRENDISTA_CORE:
        raise ValueError("reviewed_core_facts_changed")
    if not hit_dice_coherent(core["punti_ferita"]):
        raise ValueError("hit_dice_invalid")
    if core["grado_sfida"] != "—":
        raise ValueError("do_not_invent_numeric_challenge_rating")
    if any(name.casefold().strip() == "apprendista" for name in existing_names):
        raise ValueError("duplicate_exact_apprendista")
    # MPMM's Mago Apprendista has different HP and abilities: never merge by suffix.

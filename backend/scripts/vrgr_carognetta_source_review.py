"""Van Richten p228: visually source-reviewed Carognetta core statblock.

Original 257-page R2-authority PDF has been SHA256-checked against Supabase.
No licensed page image or full descriptive text is committed. This metadata
does NOT certify complete traits/actions, and never writes to Supabase.
"""
from __future__ import annotations

from scripts.vrgr_apprendista_source_review import hit_dice_coherent

SOURCE_ID = "vrgr_2021_it"
SOURCE_SHA256 = "7d8e6479f592df1630fc3abb02d3612a1d8514b3faff8d558288005185980209"
SOURCE_FILENAME = "667440680-Guida-Di-Von-Richten-a-Ravenloft.pdf"
PAGE = 228
BAD_OCR_HP = "27 ( 6 d 6 + 6 ) D 12"
CAROGNETTA_CORE = {
    "name": "Carognetta",
    "logical_source_id": SOURCE_ID,
    "physical_page": PAGE,
    "type": "Costrutto",
    "size": "Piccolo",
    "classe_armatura": "15 (armatura naturale)",
    "punti_ferita": "27 (6d6 + 6)",
    "velocita": "7,5 m",
    "caratteristiche": {"for": "10", "des": "15", "cos": "12", "int": "8", "sag": "14", "car": "14"},
    "grado_sfida": "1",
    "bonus_competenza": "+2",
    "resistenze_nomi": ["psichici", "veleno"],
    "immunita_condizioni_nomi": ["affascinato", "avvelenato", "spaventato"],
    "tratti_nomi_da_completare": ["Oggetto ingannevole", "Natura insolita"],
    "azioni_nomi_da_completare": ["Ago d'argento", "Scambio d'anima"],
    "completezza_scheda": "statistiche_essenziali",
}


def validate_review(core: dict, sha256: str, existing_names: list[str]) -> None:
    """Fail closed on unpinned sources, modified values, or duplicate identity."""
    if sha256 != SOURCE_SHA256:
        raise ValueError("source_sha256_mismatch")
    if core != CAROGNETTA_CORE:
        raise ValueError("reviewed_core_changed")
    if not hit_dice_coherent(core["punti_ferita"]):
        raise ValueError("hp_dice_not_coherent")
    if any(name.casefold().strip() == "carognetta" for name in existing_names):
        raise ValueError("duplicate_carognetta")

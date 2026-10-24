"""Regression gates for owner-manual playable species extraction.

All samples are synthetic: no private manual text is copied into the repo.
"""

import pytest

from reference_library import (
    parse_reference_page,
    reference_is_trusted,
    reference_review_reason,
    reference_review_state,
)


RAVNICA = "Guildmasters’ Guide to Ravnica.2 .pdf"
RAVNICA_VISUAL = "468887356-Guildmasters-Guide-to-Ravnica-AnyFlip-pdf.pdf"
THEROS = "953338587-Mythic-Odysseys-of-Theros.pdf"
FIZBAN = "950799222-D-D-5e-Il-Tesoro-dei-Draghi-di-Fizban.pdf"
DRAGONLANCE = (
    "682072052-5e-DnD-Dragonlance-Shadow-of-the-Dragon-Queen-Mong-IcYPD5.pdf"
)
VAN_RICHTEN = "667440680-Guida-Di-Von-Richten-a-Ravenloft.pdf"
STRIXHAVEN = (
    "779447314-Toaz-info-Strixhaven-a-Curriculum-of-Chaos-Dampd-5e-Pr-"
    "Ddb9ac0faaf75f03b8889d75914d10c4.pdf"
)
ACQUISITIONS = "556883105-Acquisitions-Incorporated-D-D5e.pdf"
LOCATHAH = "432286579-Locathah-Rising-5e.pdf"

ENGLISH_RULES = (
    "Ability Score Increase. This option adjusts the character's ability scores.\n"
    "Size. The character is a Medium humanoid, as described in the species traits.\n"
    "Speed. The character has a walking speed set out in its own traits.\n"
    "Languages. The character knows the languages specified by this species."
)
ITALIAN_RULES = (
    "Incremento dei Punteggi di Caratteristica. La razza dispone dei propri aumenti.\n"
    "Taglia. La creatura giocabile è di taglia Media.\n"
    "Velocità. La velocità base è di 9 metri.\n"
    "Linguaggi. Conosce le lingue previste dai tratti della razza."
)


@pytest.mark.parametrize(
    ("manual", "species", "language", "rules"),
    [
        (RAVNICA, "Loxodon", "en", ENGLISH_RULES),
        (RAVNICA, "Simic Hybrid", "en", ENGLISH_RULES),
        (RAVNICA, "Vedalken", "en", ENGLISH_RULES),
        (RAVNICA, "Centaur", "en", ENGLISH_RULES),
        (RAVNICA, "Goblin", "en", ENGLISH_RULES),
        (RAVNICA, "Minotaur", "en", ENGLISH_RULES),
        (THEROS, "Leonin", "en", ENGLISH_RULES),
        (THEROS, "Satyr", "en", ENGLISH_RULES),
        (THEROS, "Triton", "en", ENGLISH_RULES),
        (FIZBAN, "DRAGONIDI CROMATICI", "it", ITALIAN_RULES),
        (FIZBAN, "DRAGONIDI DELLE GEMME", "it", ITALIAN_RULES),
        (FIZBAN, "DRAGONIDI METALLICI", "it", ITALIAN_RULES),
        (DRAGONLANCE, "Kender", "en", ENGLISH_RULES),
        (VAN_RICHTEN, "Dhampir", "it", ITALIAN_RULES),
        (VAN_RICHTEN, "SANGUE STRIGO", "it", ITALIAN_RULES),
        (VAN_RICHTEN, "Rinato", "it", ITALIAN_RULES),
        (STRIXHAVEN, "Owlin", "en", ENGLISH_RULES),
        (ACQUISITIONS, "Verdan", "en", ENGLISH_RULES),
        (LOCATHAH, "Locathah", "en", ENGLISH_RULES),
    ],
)
def test_scoped_species_have_provenance_and_explicit_review_gate(
    manual, species, language, rules
):
    records = parse_reference_page(
        f"{species}\n{rules}", manual, 12, source_language=language
    )
    candidates = [
        record
        for record in records
        if record["reference_type"] == "race"
        and record["name"].casefold() == species.casefold()
    ]
    assert len(candidates) == 1
    record = candidates[0]
    assert "razza_sorgente_da_verificare" in record["review_flags"]
    assert reference_review_state(record) == "review"
    assert not reference_is_trusted(record)
    assert "Scheda razziale candidata" in reference_review_reason(record)
    assert record["source_refs"][0]["filename"] == manual
    assert record["source_refs"][0]["page"] == 12


@pytest.mark.parametrize("title", ["Loxodon", "Simic Hybrid", "Vedalken"])
def test_ravnica_table_of_contents_never_becomes_verified_species(title):
    text = (
        f"{title}\n"
        "This alphabetical index contains only page headings and campaign "
        "descriptions, not species abilities or mechanically associated traits.\n"
        "Another index heading follows the entry."
    )
    records = parse_reference_page(text, RAVNICA, 2, source_language="en")
    assert not any(record["reference_type"] == "race" for record in records)


def test_name_without_own_species_rules_is_not_promoted():
    text = (
        "LEONIN\n"
        "The people appear here as neighbors and rivals in a regional "
        "travel account. This paragraph is only narrative context about "
        "the local culture and does not provide playable statistics."
    )
    records = parse_reference_page(text, THEROS, 88, source_language="en")
    assert not any(record["reference_type"] == "race" for record in records)


def test_scope_does_not_promote_same_name_from_unlisted_book():
    records = parse_reference_page(
        f"Loxodon\n{ENGLISH_RULES}",
        "Other-fictional-manual.pdf",
        3,
        source_language="en",
    )
    assert not any(record["reference_type"] == "race" for record in records)


def test_monster_stat_block_is_not_promoted_as_playable_race():
    text = (
        "KENDER\n"
        "Armor Class 14 (natural armor)\n"
        "Hit Points 18 (4d8)\n"
        "Size. Medium creature in this monster statistic block.\n"
        "Speed. 30 feet.\n"
        "Languages. Common. The creature is an antagonist in this encounter."
    )
    records = parse_reference_page(text, DRAGONLANCE, 20, source_language="en")
    assert not any(record["reference_type"] == "race" for record in records)


def test_visual_aid_ravnica_name_is_candidate_only():
    records = parse_reference_page(
        f"Loxodon\n{ENGLISH_RULES}", RAVNICA_VISUAL, 25, source_language="en"
    )
    matched = [r for r in records if r["normalized_name"] == "loxodon"]
    assert len(matched) == 1
    assert matched[0]["reference_type"] == "race"
    assert "razza_sorgente_da_verificare" in matched[0]["review_flags"]
    assert not reference_is_trusted(matched[0])


def test_underscored_owlin_heading_keeps_clean_candidate_name():
    records = parse_reference_page(
        f"Owlin______________________________\n{ENGLISH_RULES}",
        STRIXHAVEN,
        29,
        source_language="en",
    )
    matched = [r for r in records if r["normalized_name"] == "owlin"]
    assert len(matched) == 1
    assert matched[0]["name"] == "Owlin"
    assert "razza_sorgente_da_verificare" in matched[0]["review_flags"]


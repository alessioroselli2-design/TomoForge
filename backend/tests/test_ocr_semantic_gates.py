from services.ocr_semantic_gates import (
    CA_FORMAT_ERROR_FLAG,
    CA_OUT_OF_BOUNDS_FLAG,
    HP_FORMAT_ERROR_FLAG,
    OCR_REVIEW_FLAG,
    apply_ocr_review_gates,
    monster_semantic_numeric_flags,
)
from reference_library import reference_is_trusted, reference_review_state


def _monster(ac: str, hp: str) -> dict:
    return {
        "reference_type": "monster",
        "name": "Mostro di prova",
        "attributes": {
            "classe_armatura": ac,
            "punti_ferita": hp,
            "velocita": "9 m",
        },
        "review_flags": [],
    }


def test_ca_numeric_gate_flags_values_below_5_and_above_30():
    assert CA_OUT_OF_BOUNDS_FLAG in monster_semantic_numeric_flags(
        _monster("4", "7 (2d6)")["attributes"]
    )
    assert CA_OUT_OF_BOUNDS_FLAG in monster_semantic_numeric_flags(
        _monster("31", "7 (2d6)")["attributes"]
    )


def test_ca_numeric_gate_accepts_inclusive_boundaries():
    assert CA_OUT_OF_BOUNDS_FLAG not in monster_semantic_numeric_flags(
        _monster("5", "7 (2d6)")["attributes"]
    )
    assert CA_OUT_OF_BOUNDS_FLAG not in monster_semantic_numeric_flags(
        _monster("30 (armatura naturale)", "7 (2d6)")["attributes"]
    )


def test_ca_unparseable_value_is_fail_closed():
    assert CA_FORMAT_ERROR_FLAG in monster_semantic_numeric_flags(
        _monster("armatura naturale", "7 (2d6)")["attributes"]
    )


def test_hp_gate_rejects_zuggtmoy_style_ocr_letters_and_split_numbers():
    flags = monster_semantic_numeric_flags(
        _monster("18", "304 (32dl0 + 1 28)")["attributes"]
    )
    assert HP_FORMAT_ERROR_FLAG in flags


def test_hp_gate_rejects_split_leading_hit_dice_even_if_valid_subtoken_exists():
    flags = monster_semantic_numeric_flags(
        _monster("14", "71 (1 3d8 + 13)")["attributes"]
    )
    assert HP_FORMAT_ERROR_FLAG in flags


def test_hp_gate_accepts_canonical_dice_notation():
    flags = monster_semantic_numeric_flags(
        _monster("14", "45 (7d8 + 14)")["attributes"]
    )
    assert HP_FORMAT_ERROR_FLAG not in flags


def test_all_ocr_records_are_pending_and_cannot_be_trusted_automatically():
    gated = apply_ocr_review_gates(_monster("14", "45 (7d8 + 14)"))

    assert gated["review_status"] == "pending"
    assert OCR_REVIEW_FLAG in gated["review_flags"]
    assert reference_review_state(gated) == "review"
    assert reference_is_trusted(gated) is False


def test_non_monster_ocr_records_still_start_pending():
    gated = apply_ocr_review_gates(
        {
            "reference_type": "spell",
            "name": "Incantesimo di prova",
            "attributes": {"level": "1"},
            "review_flags": [],
        }
    )

    assert gated["review_status"] == "pending"
    assert gated["review_flags"] == [OCR_REVIEW_FLAG]

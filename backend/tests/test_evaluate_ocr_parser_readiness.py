from scripts.evaluate_ocr_parser_readiness import (
    PARSER_CANDIDATE,
    REVIEW_REQUIRED,
    evaluate_ocr_parser_readiness,
)


def _padding() -> str:
    return " ".join(["creatura"] * 90)


def test_complete_italian_statblock_shape_is_candidate_but_stays_review_only():
    text = f"""
    Classe Armatura 15
    Punti Ferita 68
    Velocità 9 m
    FOR 16 DES 14 COS 15 INT 8 SAG 12 CAR 9
    Azioni
    Morso. Attacco con arma da mischia.
    {_padding()}
    """

    result = evaluate_ocr_parser_readiness(text)

    assert result["classification"] == PARSER_CANDIDATE
    assert result["ability_marker_count"] == 6
    assert {"armor_class", "hit_points", "speed"}.issubset(result["core_marker_hits"])
    assert result["requires_manual_review"] is True
    assert result["parser_execution_authorized"] is False
    assert result["automatic_import_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_full_ability_names_are_supported_without_requiring_actions_on_same_page():
    text = f"""
    Classe Armatura 13
    Punti Ferita 45
    Velocità 12 m
    Forza 14 Destrezza 15 Costituzione 12 Intelligenza 10 Saggezza 11 Carisma 8
    {_padding()}
    """

    result = evaluate_ocr_parser_readiness(text)

    assert result["classification"] == PARSER_CANDIDATE
    assert result["ability_marker_count"] == 6
    assert "actions" not in result["core_marker_hits"]


def test_missing_core_structure_requires_review():
    text = f"FOR 16 DES 14 COS 15 INT 8 SAG 12 CAR 9 Azioni {_padding()}"

    result = evaluate_ocr_parser_readiness(text)

    assert result["classification"] == REVIEW_REQUIRED
    assert result["parser_execution_authorized"] is False


def test_short_fragment_cannot_pass_even_with_markers():
    text = "Classe Armatura 15 Punti Ferita 20 Velocità 9 m FOR DES COS INT SAG CAR"

    result = evaluate_ocr_parser_readiness(text)

    assert result["classification"] == REVIEW_REQUIRED
    assert result["word_count"] < 80


def test_empty_text_requires_review_and_never_authorizes_side_effects():
    result = evaluate_ocr_parser_readiness("")

    assert result["classification"] == REVIEW_REQUIRED
    assert result["core_marker_count"] == 0
    assert result["ability_marker_count"] == 0
    assert result["automatic_import_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False

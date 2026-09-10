from scripts.evaluate_text_extraction_quality import (
    EMPTY_TEXT,
    TEXT_USABLE,
    VISION_REVIEW_REQUIRED,
    evaluate_text_extraction_quality,
)


def test_clean_text_remains_usable_without_authorizing_side_effects():
    result = evaluate_text_extraction_quality(
        "Tortle Traits\nNatural Armor. Your shell provides protection."
    )

    assert result["classification"] == TEXT_USABLE
    assert result["requires_vision_review"] is False
    assert result["suspicious_control_count"] == 0
    assert result["replacement_character_count"] == 0
    assert result["automatic_repair_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_repeated_raw_control_bytes_require_vision_review():
    result = evaluate_text_extraction_quality(
        "Readable prefix \x18garbled\x18content\x18 readable suffix"
    )

    assert result["classification"] == VISION_REVIEW_REQUIRED
    assert result["requires_vision_review"] is True
    assert result["suspicious_control_count"] == 3
    assert result["replacement_character_count"] == 0


def test_replacement_character_requires_vision_review():
    result = evaluate_text_extraction_quality("Mostly readable text with one \ufffd replacement")

    assert result["classification"] == VISION_REVIEW_REQUIRED
    assert result["requires_vision_review"] is True
    assert result["replacement_character_count"] == 1


def test_single_control_artifact_does_not_force_vision_when_ratio_is_small():
    result = evaluate_text_extraction_quality(
        "A" * 200 + "\x18" + "B" * 200
    )

    assert result["classification"] == TEXT_USABLE
    assert result["requires_vision_review"] is False
    assert result["suspicious_control_count"] == 1


def test_empty_text_requires_review_but_does_not_authorize_ocr():
    result = evaluate_text_extraction_quality("  \n\t")

    assert result["classification"] == EMPTY_TEXT
    assert result["requires_vision_review"] is True
    assert result["ocr_authorized"] is False
    assert result["database_write_authorized"] is False

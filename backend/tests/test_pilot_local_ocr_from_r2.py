from scripts.pilot_local_ocr_from_r2 import _text_quality


def test_text_quality_scores_readable_text():
    quality = _text_quality("Aarakocra umanoide medio, CA 12, velocità 6 m.")
    assert quality["chars"] > 20
    assert quality["letter_ratio"] > 0.6
    assert quality["printable_ratio"] == 1.0
    assert quality["word_count"] >= 5


def test_text_quality_handles_empty_text():
    assert _text_quality("") == {
        "chars": 0,
        "nonspace_chars": 0,
        "letter_ratio": 0.0,
        "printable_ratio": 0.0,
        "word_count": 0,
    }

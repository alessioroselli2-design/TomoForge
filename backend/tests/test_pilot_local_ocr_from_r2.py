from scripts.pilot_local_ocr_from_r2 import _agreement_metrics, _text_quality


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


def test_agreement_metrics_reward_consistent_transcriptions():
    base = (
        "Creatura descritta con classe armatura, punti ferita, velocità, forza, "
        "destrezza, costituzione, intelligenza, saggezza, carisma e azioni. "
    ) * 20
    comparison = base.replace("Creatura", "Creatura", 1)
    metrics = _agreement_metrics(base, comparison)
    assert metrics["token_dice"] == 1.0
    assert metrics["unique_jaccard"] == 1.0
    assert metrics["length_ratio"] == 1.0
    assert metrics["primary_marker_hits"] >= 8
    assert metrics["quality_pass"] is True


def test_agreement_metrics_reject_divergent_transcriptions():
    primary = ("classe armatura punti ferita velocità azioni creatura " * 120)
    comparison = ("alfabeto rumore diverso senza corrispondenza testuale " * 120)
    metrics = _agreement_metrics(primary, comparison)
    assert metrics["token_dice"] < 0.2
    assert metrics["unique_jaccard"] < 0.2
    assert metrics["quality_pass"] is False

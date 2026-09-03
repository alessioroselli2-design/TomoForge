"""Regression coverage for the R2 worker entry point."""

import services.library as library
from scripts import run_r2_manual_import as runner


def _reset_guard(monkeypatch):
    monkeypatch.delattr(library, "_r2_ocr_fallback_enabled", raising=False)


def test_non_spanish_text_manual_gets_page_level_ocr_fallback(monkeypatch):
    _reset_guard(monkeypatch)
    monkeypatch.setattr(library, "manual_requires_ocr", lambda _filename: False)
    monkeypatch.setattr(library, "manual_source_language", lambda _filename: "it")

    runner.enable_worker_ocr_fallback()

    assert library.manual_requires_ocr("Ranger__1787233073462.pdf") is True


def test_spanish_text_manual_keeps_no_ocr_policy(monkeypatch):
    _reset_guard(monkeypatch)
    monkeypatch.setattr(library, "manual_requires_ocr", lambda _filename: False)
    monkeypatch.setattr(library, "manual_source_language", lambda _filename: "es")

    runner.enable_worker_ocr_fallback()

    assert library.manual_requires_ocr("731764731-D-D-Manual-Del-Jugador-5e.pdf") is False


def test_registry_required_ocr_stays_enabled(monkeypatch):
    _reset_guard(monkeypatch)
    monkeypatch.setattr(library, "manual_requires_ocr", lambda _filename: True)
    monkeypatch.setattr(library, "manual_source_language", lambda _filename: "it")

    runner.enable_worker_ocr_fallback()

    assert library.manual_requires_ocr("847921086-Manuale-Dei-Mostri-5e.pdf") is True


def test_reversed_card_footer_header_is_normalized():
    transcription = (
        "ALLARME\n"
        "1° livello Abiurazione\n"
        "Tempo di Lancio: 1 minuto\n"
        "Gittata: 9 metri\n"
        "Componenti: V, S, M\n"
        "Durata: 8 ore\n"
        "Testo della regola."
    )

    normalized = runner._normalize_spell_card_transcription(transcription)

    assert "Abiurazione di 1° livello" in normalized.splitlines()
    assert "1° livello Abiurazione" not in normalized


def test_reversed_ritual_header_preserves_ritual_marker():
    normalized = runner._normalize_spell_card_transcription(
        "INDIVIDUAZIONE DEL MAGICO\n1° livello Divinazione (rituale)"
    )

    assert normalized.splitlines()[1] == "Divinazione di 1° livello (rituale)"

"""Synthetic extraction cases; no private manual text in test fixtures."""

from scripts.eberron_three_dragonmark_fields import TARGETS, factual_signals, fold


def test_source_page_contract():
    assert sorted(TARGETS) == [41, 43, 51]


def test_simple_stat_score_and_heading_are_detected_without_prose():
    text = (
        "Marchio della Sentinella.\n"
        "Incremento dei Punteggi di Caratteristica. "
        "Il punteggio di Costituzione del personaggio aumenta di 2 "
        "e quello di Saggezza aumenta di 1.\n"
        "Protezione. Il personaggio ha un tratto sintetico.\n"
        "Incantesimi del Marchio. Il personaggio ottiene un'altra regola."
    )
    result = factual_signals(text, "Sentinella")
    assert result["named_heading_seen"]
    assert {"stat": "costituzione", "increase": 2} in result["explicit_score_increases"]
    assert {"stat": "saggezza", "increase": 1} in result["explicit_score_increases"]
    assert result["spell_mark_heading_seen"]
    assert text not in str(result)
    assert "aumenta di 2" not in str(result)


def test_no_heading_or_ability_bonus_not_fabricated():
    result = factual_signals(
        "Il nome appare solo in un indice lontano dal testo dei tratti.",
        "Guarigione",
    )
    assert not result["named_heading_seen"]
    assert result["explicit_score_increases"] == []
    assert not result["ability_increase_heading_seen"]


def test_unicode_fold_for_italian_accents():
    assert fold("Saggézza  –  d'Addestramento") == "saggezza – d'addestramento"


def test_reject_out_of_range_values():
    result = factual_signals(
        "Marchio dell'Addestramento. "
        "Il punteggio di Saggezza del personaggio aumenta di 14.",
        "Addestramento",
    )
    assert result["named_heading_seen"]
    assert result["explicit_score_increases"] == []

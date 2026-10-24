"""Only synthetic fixtures: real source text must never leave the private worker."""

from scripts.eberron_three_column_ocr import (
    TARGETS,
    WINDOW_LIMIT,
    fold,
    page_signals,
)


def test_each_original_source_page_is_one_window():
    assert sorted(TARGETS) == [41, 43, 51]
    assert WINDOW_LIMIT == 12


def test_accents_and_spaces_normalize_without_exporting_text():
    assert fold("Più   Grossi Sono") == "piu grossi sono"
    sample = (
        "Marchio dell'Addestramento\n"
        "Incremento dei Punteggi di Caratteristica.\n"
        "Intuito Selvaggio. Fictional prose private.\n"
        "Legame Primordiale. Fictional prose.\n"
        "Più Grossi Sono. Fictional prose.\n"
        "Incantesimi del Marchio.\n"
        "Amicizia con gli animali, parlare con gli animali, "
        "Saggezza, Natura."
    )
    result = page_signals(sample, TARGETS[41])
    assert result["heading"]
    assert result["score_heading"]
    assert all(result["trait_labels_present"].values())
    assert all(result["trait_terms_present"].values())
    assert "Fictional" not in str(result)


def test_table_of_contents_heading_is_not_evidence_of_full_rules():
    result = page_signals("Marchio della Guarigione . . . 43", TARGETS[43])
    assert result["heading"]
    assert not result["score_heading"]
    assert not any(result["trait_labels_present"].values())


def test_sentinel_missing_trait_cannot_pass_labels_gate():
    sample = (
        "Marchio della Sentinella. Incremento dei Punteggi di Caratteristica."
        " Intuito della Sentinella. Scudo del Guardiano. Incantesimi del Marchio."
    )
    result = page_signals(sample, TARGETS[51])
    assert not result["trait_labels_present"]["Guardiano Vigile"]


def test_no_private_source_data_emitted_for_empty_page():
    result = page_signals("", TARGETS[41])
    assert result["characters"] == 0
    assert not result["heading"]

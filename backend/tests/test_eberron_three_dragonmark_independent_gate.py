from scripts.eberron_three_dragonmark_independent_gate import compare, phrase, score


def test_normalized_phrase_and_delta():
    assert phrase("Più Grossi Sono", "Piu Grossi Sono")
    assert not phrase("interdizione", "dizione")
    assert score("Il punteggio di Saggezza aumenta di 2", "SAG", 2)
    assert not score("Il punteggio di Saggezza aumenta di 1", "SAG", 2)


def test_two_pass_fail_closed_without_semantic_claim():
    row = {"attributes": {"incremento_caratteristiche": {"SAG": 1},
                          "tratti_razziali": [{"nome": "Intuito Medico"}],
                          "incantesimi_del_marchio": {"1": ["cura ferite"]}}}
    text = "Marchio della Guarigione. Saggezza aumenta di 1. Intuito Medico. cura ferite."
    good = compare(row, {"native": "", "psm4": text, "psm11": text}, "Guarigione")
    assert good["checks_total"] == good["checks_passed"] == 4
    assert good["full_semantic_verification"] is False
    bad = compare(row, {"native": "", "psm4": text, "psm11": ""}, "Guarigione")
    assert bad["checks_passed"] == 0


def test_missing_mechanics_fail_closed():
    row = {"attributes": {"incremento_caratteristiche": {"altro_a_scelta": 1}}}
    result = compare(row, {"psm4": "Addestramento", "psm11": "Addestramento"}, "Addestramento")
    assert result["checks_passed"] < result["checks_total"]


def test_choice_ability_requires_explicit_additional_score():
    text = "Un altro punteggio di caratteristica a tua scelta aumenta di 1."
    assert score(text, "altro_a_scelta", 1)
    assert not score(text, "altro_a_scelta", 2)
    assert not score("Il punteggio di Saggezza aumenta di 1.", "altro_a_scelta", 1)

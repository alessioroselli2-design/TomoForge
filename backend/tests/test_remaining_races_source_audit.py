"""Synthetic tests: detect possible race evidence only, never mark verified."""

from scripts.remaining_races_source_audit import MAX_WINDOW, SOURCES, structural_signals


def test_each_source_window_under_twelve_pages():
    assert len(SOURCES) == 3
    assert MAX_WINDOW == 12
    assert all(s["last"] - s["first"] + 1 <= MAX_WINDOW for s in SOURCES)
    assert all(len(s["sha256"]) == 64 for s in SOURCES)


def test_italian_dragonid_rule_hints_are_metadata_only():
    sample = (
        "Dragonidi delle Gemme\n"
        "Incremento dei Punteggi di Caratteristica. Dato fittizio.\n"
        "Velocità. La velocità è descritta nelle regole.\n"
        "Taglia. La taglia della creatura è presente.\n"
        "Arma a Soffio. Un tratto fittizio."
    )
    result = structural_signals(sample, SOURCES[0]["names"])
    assert "Dragonidi delle Gemme" in result["heading_candidates"]
    assert result["markers"]["breath_weapon"]
    assert result["markers"]["speed_it"]
    assert "Dato fittizio" not in repr(result)


def test_lineage_name_without_mechanics_is_only_mention():
    text = "Dhampir\nIntroduzione narrativa senza tratti razziali né valori"
    result = structural_signals(text, SOURCES[1]["names"])
    assert "Dhampir" in result["heading_candidates"]
    assert result["markers"]["lineage"] is False


def test_kender_heading_can_be_seen_with_rules():
    sample = "Kender\nAbility Score Increase. An example.\nSize. Small.\nSpeed. A speed is printed."
    result = structural_signals(sample, SOURCES[2]["names"])
    assert "Kender" in result["heading_candidates"]
    assert result["markers"]["speed"]

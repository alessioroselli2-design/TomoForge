"""Synthetic tests for privacy-preserving Eberron source quality audit."""

from scripts.eberron_dragonmarks_source_audit import (
    FIRST,
    LAST,
    REVIEW_PAGES,
    TARGETS,
    page_markers,
)


def test_bounded_window_and_twelve_dragonmarks():
    assert LAST - FIRST + 1 == 12
    assert set(TARGETS) == set(range(FIRST, LAST + 1))
    assert REVIEW_PAGES.issubset(TARGETS.keys())


def test_positive_source_markers_without_returning_source_content():
    text = (
        "MARCHIO DELL'INTERDIZIONE\n"
        "Un personaggio nano appartiene a questa sottorazza.\n"
        "Incremento dei Punteggi di Caratteristica. Un valore aumenta.\n"
        "Intuito del Guardiano. Un tratto locale.\n"
        "Incantesimi del Marchio. La lista fa riferimento a questa fonte."
    )
    out = page_markers(text, "Interdizione")
    assert out["named_heading_seen"]
    assert out["race_parent_context"]
    assert out["ability_increase_heading"]
    assert out["spell_table_reference"]
    assert out["at_least_one_feature_label"]
    assert text not in str(out)


def test_fragment_does_not_satisfy_complete_semantics():
    text = (
        "MARCHIO DELLA SENTINELLA\n"
        "Un personaggio umano usa tratti di questa variante."
    )
    out = page_markers(text, "Sentinella")
    assert out["named_heading_seen"]
    assert out["race_parent_context"]
    assert not out["ability_increase_heading"]
    assert not out["spell_table_reference"]


def test_alternative_heading_works_with_italian_apostrophe():
    sample = "Marchio dell'Ombra\nUn personaggio elfo appartiene a questa sottorazza."
    assert page_markers(sample, "Ombra")["named_heading_seen"]
    assert not page_markers(sample, "Tempesta")["named_heading_seen"]

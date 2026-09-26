from pathlib import Path
import sys

SERVICES = Path(__file__).resolve().parents[1] / "services"
if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

from monster_statblock_ocr import agreed_monster_records, parse_monster_statblocks


def _goblin_text(ac="15 (armatura di cuoio, scudo)", title="GOBLIN"):
    return f"""{title}
Piccolo umanoide (goblinoide), neutrale malvagio
Classe Armatura {ac}
Punti Ferita 7 (2d6)
Velocità 9 m
FOR DES COS INT SAG CAR
8 14 10 10 8 8
Abilità Furtività +6
Sensi scurovisione 18 m, Percezione passiva 9
Linguaggi Comune, Goblin
Grado di Sfida 1/4 (50 PE)

Azioni
Scimitarra. Attacco con Arma da Mischia: +4 al tiro per colpire.
Arco Corto. Attacco con Arma a Distanza: +4 al tiro per colpire.
"""


def test_parses_one_complete_monster_and_keeps_review_gate():
    records = parse_monster_statblocks(
        [(166, _goblin_text())], "manuale_dei_mostri.pdf"
    )

    assert len(records) == 1
    record = records[0]
    assert record["reference_type"] == "monster"
    assert record["name"] == "GOBLIN"
    assert record["start_page"] == 166
    assert record["end_page"] == 166
    assert record["attributes"]["classe_armatura"].startswith("15")
    assert record["attributes"]["punti_ferita"].startswith("7")
    assert record["attributes"]["velocita"].startswith("9 m")
    assert record["attributes"]["ha_azioni"] is True
    assert "ocr_da_verificare" in record["review_flags"]
    assert record["source_refs"] == [
        {
            "filename": "manuale_dei_mostri.pdf",
            "page": 166,
            "logical_page": 166,
            "language": "it",
        }
    ]


def test_hit_points_wrap_with_open_parenthesis_is_joined_conservatively():
    text = """RANA
Minuscola bestia, senza allineamento
Classe Armatura 11
Punti Ferita 1 (1d4
- 1)
Velocità 6 m, nuotare 6 m
FOR DES COS INT SAG CAR
1 13 8 1 8 3
"""

    records = parse_monster_statblocks([(310, text)], "manuale.pdf")

    assert len(records) == 1
    assert records[0]["attributes"]["punti_ferita"] == "1 (1d4 - 1)"


def test_hit_points_wrap_does_not_cross_structural_field():
    text = """RANA
Minuscola bestia, senza allineamento
Classe Armatura 11
Punti Ferita 1 (1d4
Velocità 6 m, nuotare 6 m
FOR DES COS INT SAG CAR
1 13 8 1 8 3
"""

    records = parse_monster_statblocks([(310, text)], "manuale.pdf")

    assert len(records) == 1
    assert records[0]["attributes"]["punti_ferita"] == "1 (1d4"


def test_speed_wrap_with_open_parenthesis_is_joined_conservatively():
    text = """IMP
Minuscolo immondo, legale malvagio
Classe Armatura 13
Punti Ferita 10 (3d4 + 3)
Velocità 6 m, volare 12 m (6 m in forma di topo; 6 m, volare 18
m in forma di corvo; 6 m, scalare 6 m in forma di ragno)
FOR DES COS INT SAG CAR
6 17 13 11 12 14
"""

    records = parse_monster_statblocks([(306, text)], "manuale.pdf")

    assert len(records) == 1
    assert records[0]["attributes"]["velocita"] == (
        "6 m, volare 12 m (6 m in forma di topo; 6 m, volare 18 "
        "m in forma di corvo; 6 m, scalare 6 m in forma di ragno)"
    )


def test_speed_wrap_does_not_cross_into_structural_field():
    text = """IMP
Minuscolo immondo, legale malvagio
Classe Armatura 13
Punti Ferita 10 (3d4 + 3)
Velocità 6 m, volare 12 m (6 m in forma di topo
FOR DES COS INT SAG CAR
6 17 13 11 12 14
"""

    records = parse_monster_statblocks([(306, text)], "manuale.pdf")

    assert len(records) == 1
    assert records[0]["attributes"]["velocita"] == (
        "6 m, volare 12 m (6 m in forma di topo"
    )


def test_rejects_attack_like_text_without_statblock_header():
    text = """SPADA LUNGA
Arma da mischia, marziale
Classe Armatura 15
Una descrizione narrativa senza punti ferita né velocità.
"""
    assert parse_monster_statblocks([(10, text)], "manuale.pdf") == []


def test_requires_independent_ocr_agreement_on_core_stats():
    primary = parse_monster_statblocks([(166, _goblin_text())], "manuale.pdf")
    same = parse_monster_statblocks([(166, _goblin_text())], "manuale.pdf")
    different_ac = parse_monster_statblocks(
        [(166, _goblin_text("14 (armatura di cuoio)"))], "manuale.pdf"
    )

    agreed = agreed_monster_records(primary, same)
    assert len(agreed) == 1
    assert "ocr_independent_agreement" in agreed[0]["review_flags"]
    assert agreed[0]["attributes"]["ocr_independent_agreement"] is True
    # Independent agreement does not remove the manual-review requirement.
    assert "ocr_da_verificare" in agreed[0]["review_flags"]

    assert agreed_monster_records(primary, different_ac) == []


def test_missing_core_marker_is_fail_closed():
    text = _goblin_text().replace("Punti Ferita 7 (2d6)\n", "")
    assert parse_monster_statblocks([(166, text)], "manuale.pdf") == []


def test_innocuous_ocr_separators_in_same_name_match_without_changing_provenance_or_review():
    primary = parse_monster_statblocks([(166, _goblin_text())], "manuale.pdf")
    comparison = parse_monster_statblocks(
        [(166, _goblin_text(title="G Ó B L I N"))],
        "manuale.pdf",
    )

    agreed = agreed_monster_records(primary, comparison)

    assert len(agreed) == 1
    assert agreed[0]["source_refs"] == primary[0]["source_refs"]
    assert "ocr_da_verificare" in agreed[0]["review_flags"]
    assert "ocr_independent_agreement" in agreed[0]["review_flags"]


def test_internal_ocr_separator_in_same_name_matches():
    primary = parse_monster_statblocks([(166, _goblin_text())], "manuale.pdf")
    comparison = parse_monster_statblocks(
        [(166, _goblin_text(title="GOB|LIN"))],
        "manuale.pdf",
    )

    assert len(agreed_monster_records(primary, comparison)) == 1


def test_different_or_incomplete_name_does_not_match_on_same_page():
    primary = parse_monster_statblocks([(166, _goblin_text())], "manuale.pdf")
    different = parse_monster_statblocks(
        [(166, _goblin_text(title="HOBGOBLIN"))],
        "manuale.pdf",
    )
    missing_word_primary = parse_monster_statblocks(
        [(166, _goblin_text(title="GOBLIN REALE"))],
        "manuale.pdf",
    )

    assert agreed_monster_records(primary, different) == []
    assert agreed_monster_records(missing_word_primary, primary) == []


def test_multiple_same_page_candidates_require_one_unique_exact_name_match():
    primary = parse_monster_statblocks([(166, _goblin_text())], "manuale.pdf")
    exact = parse_monster_statblocks([(166, _goblin_text())], "manuale.pdf")[0]
    other = parse_monster_statblocks(
        [(166, _goblin_text(title="HOBGOBLIN"))],
        "manuale.pdf",
    )[0]

    assert len(agreed_monster_records(primary, [exact, other])) == 1
    assert agreed_monster_records(primary, [exact, dict(exact)]) == []


def test_target_bound_core_only_same_page_pairing_accepts_one_unique_candidate():
    primary = parse_monster_statblocks(
        [(166, _goblin_text(title="GOBLIN"))],
        "manuale.pdf",
    )
    comparison = parse_monster_statblocks(
        [(166, _goblin_text(title="G0BL1N"))],
        "manuale.pdf",
    )

    agreed = agreed_monster_records(
        primary,
        comparison,
        target_name="GOBLIN",
    )

    assert len(agreed) == 1
    assert agreed[0]["name"] == "GOBLIN"
    assert "ocr_core_only_same_page_agreement" in agreed[0]["review_flags"]
    assert agreed[0]["attributes"]["ocr_core_only_same_page_agreement"] is True
    assert agreed[0]["attributes"]["ocr_clean_deterministic_core_agreement"] is True


def test_core_only_pairing_remains_disabled_without_explicit_target():
    primary = parse_monster_statblocks(
        [(166, _goblin_text(title="GOBLIN"))],
        "manuale.pdf",
    )
    comparison = parse_monster_statblocks(
        [(166, _goblin_text(title="G0BL1N"))],
        "manuale.pdf",
    )

    assert agreed_monster_records(primary, comparison) == []


def test_target_bound_core_only_pairing_rejects_ambiguous_same_page_candidates():
    primary = parse_monster_statblocks(
        [(166, _goblin_text(title="GOBLIN"))],
        "manuale.pdf",
    )
    first = parse_monster_statblocks(
        [(166, _goblin_text(title="DRAGON ALPHA"))],
        "manuale.pdf",
    )[0]
    second = parse_monster_statblocks(
        [(166, _goblin_text(title="DRAGON BETA"))],
        "manuale.pdf",
    )[0]

    assert (
        agreed_monster_records(
            primary,
            [first, second],
            target_name="GOBLIN",
        )
        == []
    )


def test_target_bound_core_only_pairing_rejects_core_disagreement():
    primary = parse_monster_statblocks(
        [(166, _goblin_text(title="GOBLIN"))],
        "manuale.pdf",
    )
    comparison = parse_monster_statblocks(
        [(166, _goblin_text(ac="14", title="G0BL1N"))],
        "manuale.pdf",
    )

    assert (
        agreed_monster_records(
            primary,
            comparison,
            target_name="GOBLIN",
        )
        == []
    )

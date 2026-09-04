from pathlib import Path
import sys

SERVICES = Path(__file__).resolve().parents[1] / "services"
if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

from monster_statblock_ocr import agreed_monster_records, parse_monster_statblocks


def _goblin_text(ac="15 (armatura di cuoio, scudo)"):
    return f"""GOBLIN
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
    records = parse_monster_statblocks([(166, _goblin_text())], "manuale_dei_mostri.pdf")

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

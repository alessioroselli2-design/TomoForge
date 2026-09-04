from scripts.pilot_local_ocr_parse_from_r2 import _monster_parser_summary, _record_summary


def test_record_summary_exposes_only_aggregate_parser_metrics():
    records = [
        {
            "reference_type": "monster",
            "name": "Private source title that must not be exposed",
            "full_text": "Private source text that must not be exposed",
            "review_flags": ["ocr_da_verificare"],
            "source_refs": [{"page": 12}],
        },
        {
            "reference_type": "monster",
            "name": "Another private source title",
            "full_text": "More private source text",
            "review_flags": [],
            "source_refs": [{"page": 13}],
        },
    ]
    summary = _record_summary(records)
    assert summary == {
        "records_detected": 2,
        "record_types": {"monster": 2},
        "records_flagged_for_review": 1,
        "records_with_ocr_review_flag": 1,
        "source_pages_represented": 2,
    }
    serialized = str(summary)
    assert "Private source" not in serialized


def test_monster_parser_summary_requires_independent_ocr_agreement_and_is_aggregate_only():
    primary = """LUPO TERRIBILE
Grande bestia, senza allineamento
Classe Armatura 14
Punti Ferita 37 (5d10+10)
Velocità 15 m
FOR DES COS INT SAG CAR
17 15 15 3 12 7
Sensi Percezione passiva 13
Linguaggi -
Grado di Sfida 1 (200 PE)
Azioni
Morso. Attacco con arma da mischia.
"""
    comparison = primary.replace("Morso. Attacco con arma da mischia.", "Morso. Attacco in mischia.")
    summary = _monster_parser_summary(
        [(12, primary)],
        [(12, comparison)],
        "private-monster-manual.pdf",
        "it",
    )
    assert summary == {
        "monster_candidates_primary": 1,
        "monster_candidates_comparison": 1,
        "monster_candidates_independently_agreed": 1,
    }
    serialized = str(summary)
    assert "LUPO TERRIBILE" not in serialized
    assert "Morso" not in serialized


def test_monster_parser_summary_rejects_core_stat_disagreement():
    primary = """LUPO TERRIBILE
Grande bestia, senza allineamento
Classe Armatura 14
Punti Ferita 37 (5d10+10)
Velocità 15 m
Azioni
Morso. Attacco con arma da mischia.
"""
    comparison = primary.replace("Classe Armatura 14", "Classe Armatura 13")
    summary = _monster_parser_summary(
        [(12, primary)],
        [(12, comparison)],
        "private-monster-manual.pdf",
        "it",
    )
    assert summary["monster_candidates_primary"] == 1
    assert summary["monster_candidates_comparison"] == 1
    assert summary["monster_candidates_independently_agreed"] == 0

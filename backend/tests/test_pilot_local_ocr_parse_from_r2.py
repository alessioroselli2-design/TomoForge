from scripts.pilot_local_ocr_parse_from_r2 import (
    _monster_agreement_diagnostics,
    _monster_parser_summary,
    _record_summary,
)


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
        "monster_primary_with_same_start_page_candidate": 1,
        "monster_primary_with_same_name_candidate": 1,
        "monster_primary_with_exact_key_candidate": 1,
        "monster_primary_with_exact_key_and_core_match": 1,
        "monster_exact_key_classe_armatura_match": 1,
        "monster_exact_key_punti_ferita_match": 1,
        "monster_exact_key_velocita_match": 1,
        "monster_exact_key_classe_armatura_semantic_match": 1,
        "monster_exact_key_punti_ferita_semantic_match": 1,
        "monster_exact_key_velocita_semantic_match": 1,
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
    assert summary["monster_primary_with_exact_key_candidate"] == 1
    assert summary["monster_primary_with_exact_key_and_core_match"] == 0
    assert summary["monster_exact_key_classe_armatura_match"] == 0
    assert summary["monster_exact_key_punti_ferita_match"] == 1
    assert summary["monster_exact_key_velocita_match"] == 1
    assert summary["monster_exact_key_classe_armatura_semantic_match"] == 0
    assert summary["monster_exact_key_punti_ferita_semantic_match"] == 1
    assert summary["monster_exact_key_velocita_semantic_match"] == 1


def test_agreement_diagnostics_separate_page_name_and_core_failures_without_exposing_text():
    base = {
        "start_page": 12,
        "normalized_name": "private monster",
        "attributes": {
            "classe_armatura": "14",
            "punti_ferita": "37 (5d10+10)",
            "velocita": "15 m",
        },
    }
    different_name = {
        **base,
        "normalized_name": "private monste r",
    }
    diagnostics = _monster_agreement_diagnostics([base], [different_name])
    assert diagnostics == {
        "monster_primary_with_same_start_page_candidate": 1,
        "monster_primary_with_same_name_candidate": 0,
        "monster_primary_with_exact_key_candidate": 0,
        "monster_primary_with_exact_key_and_core_match": 0,
        "monster_exact_key_classe_armatura_match": 0,
        "monster_exact_key_punti_ferita_match": 0,
        "monster_exact_key_velocita_match": 0,
        "monster_exact_key_classe_armatura_semantic_match": 0,
        "monster_exact_key_punti_ferita_semantic_match": 0,
        "monster_exact_key_velocita_semantic_match": 0,
    }
    assert "private monster" not in str(diagnostics)


def test_agreement_diagnostics_counts_semantic_matches_without_persisting_source_values():
    primary = {
        "start_page": 12,
        "normalized_name": "private monster",
        "attributes": {
            "classe_armatura": "14 (armatura naturale)",
            "punti_ferita": "37 (5d10+10)",
            "velocita": "15 m, nuoto 9 m",
        },
    }
    comparison = {
        "start_page": 12,
        "normalized_name": "private monster",
        "attributes": {
            "classe_armatura": "CA: 14 armatura naturale",
            "punti_ferita": "PF 37; formula OCR differente",
            "velocita": "Velocita 15m / nuoto 9m",
        },
    }
    diagnostics = _monster_agreement_diagnostics([primary], [comparison])
    assert diagnostics["monster_primary_with_exact_key_and_core_match"] == 0
    assert diagnostics["monster_exact_key_classe_armatura_match"] == 0
    assert diagnostics["monster_exact_key_punti_ferita_match"] == 0
    assert diagnostics["monster_exact_key_velocita_match"] == 0
    assert diagnostics["monster_exact_key_classe_armatura_semantic_match"] == 1
    assert diagnostics["monster_exact_key_punti_ferita_semantic_match"] == 1
    assert diagnostics["monster_exact_key_velocita_semantic_match"] == 1
    serialized = str(diagnostics)
    assert "armatura naturale" not in serialized
    assert "formula OCR" not in serialized
    assert "nuoto" not in serialized

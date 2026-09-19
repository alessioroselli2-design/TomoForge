from scripts.pilot_local_ocr_parse_from_r2 import _monster_agreement_diagnostics


def test_semantic_diagnostics_count_each_exact_key_record_with_equivalent_ocr_formatting():
    primary = [
        {
            "start_page": page,
            "normalized_name": f"private-{page}",
            "attributes": {
                "classe_armatura": "14 (armatura naturale)",
                "punti_ferita": "37 (5d10+10)",
                "velocita": "12 m, volare 24 m",
            },
        }
        for page in (12, 13)
    ]
    comparison = [
        {
            "start_page": page,
            "normalized_name": f"private-{page}",
            "attributes": {
                "classe_armatura": "14 armatura naturale",
                "punti_ferita": "37 5d10 + 10",
                "velocita": "12 metri; volare 24 metri",
            },
        }
        for page in (12, 13)
    ]

    diagnostics = _monster_agreement_diagnostics(primary, comparison)

    assert diagnostics["monster_primary_with_exact_key_and_core_match"] == 0
    assert diagnostics["monster_exact_key_classe_armatura_semantic_match"] == 2
    assert diagnostics["monster_exact_key_punti_ferita_semantic_match"] == 2
    assert diagnostics["monster_exact_key_velocita_semantic_match"] == 2


def test_semantic_diagnostics_reject_numeric_difference_and_missing_field():
    primary = [
        {
            "start_page": 12,
            "normalized_name": "private",
            "attributes": {
                "classe_armatura": "14",
                "punti_ferita": "37 (5d10+10)",
                "velocita": "12 m",
            },
        }
    ]
    comparison = [
        {
            "start_page": 12,
            "normalized_name": "private",
            "attributes": {
                "classe_armatura": "13",
                "punti_ferita": "",
                "velocita": "9 m",
            },
        }
    ]

    diagnostics = _monster_agreement_diagnostics(primary, comparison)

    assert diagnostics["monster_primary_with_exact_key_candidate"] == 1
    assert diagnostics["monster_exact_key_classe_armatura_semantic_match"] == 0
    assert diagnostics["monster_exact_key_punti_ferita_semantic_match"] == 0
    assert diagnostics["monster_exact_key_velocita_semantic_match"] == 0

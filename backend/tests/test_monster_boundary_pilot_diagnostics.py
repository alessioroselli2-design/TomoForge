from scripts.pilot_local_ocr_parse_from_r2 import _monster_agreement_diagnostics


def _record(name: str, page: int = 12) -> dict:
    return {
        "start_page": page,
        "normalized_name": name,
        "attributes": {
            "classe_armatura": "14",
            "punti_ferita": "37 (5d10+10)",
            "velocita": "15 m",
        },
    }


def test_boundary_diagnostic_counts_same_page_ocr_split_without_accepting_exact_key():
    diagnostics = _monster_agreement_diagnostics(
        [_record("private monster")],
        [_record("private mon ster")],
    )

    assert diagnostics["monster_primary_with_same_start_page_candidate"] == 1
    assert diagnostics["monster_primary_with_same_name_candidate"] == 0
    assert diagnostics["monster_primary_with_same_page_boundary_name_candidate"] == 1
    assert diagnostics["monster_primary_with_exact_key_candidate"] == 0


def test_boundary_diagnostic_rejects_real_name_difference():
    diagnostics = _monster_agreement_diagnostics(
        [_record("private monster")],
        [_record("private monater")],
    )

    assert diagnostics["monster_primary_with_same_start_page_candidate"] == 1
    assert diagnostics["monster_primary_with_same_page_boundary_name_candidate"] == 0
    assert diagnostics["monster_primary_with_exact_key_candidate"] == 0


def test_boundary_diagnostic_is_aggregate_only():
    diagnostics = _monster_agreement_diagnostics(
        [_record("private monster")],
        [_record("private mon ster")],
    )

    serialized = str(diagnostics)
    assert "private monster" not in serialized
    assert "private mon ster" not in serialized

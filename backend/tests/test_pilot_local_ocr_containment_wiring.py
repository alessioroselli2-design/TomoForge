from scripts.pilot_local_ocr_parse_from_r2 import _monster_agreement_diagnostics


def test_containment_diagnostic_counts_same_page_strict_fragment_only():
    primary = [
        {
            "start_page": 12,
            "normalized_name": "private-long-name",
            "attributes": {},
        },
        {
            "start_page": 13,
            "normalized_name": "other-name",
            "attributes": {},
        },
    ]
    comparison = [
        {
            "start_page": 12,
            "normalized_name": "private-long",
            "attributes": {},
        },
        {
            "start_page": 13,
            "normalized_name": "different-name",
            "attributes": {},
        },
    ]

    diagnostics = _monster_agreement_diagnostics(primary, comparison)

    assert diagnostics["monster_primary_with_same_page_containment_name_candidate"] == 1
    assert "private-long-name" not in str(diagnostics)
    assert "private-long" not in str(diagnostics)


def test_containment_diagnostic_does_not_count_exact_or_tiny_fragments():
    primary = [
        {"start_page": 12, "normalized_name": "same-name", "attributes": {}},
        {"start_page": 13, "normalized_name": "abc", "attributes": {}},
    ]
    comparison = [
        {"start_page": 12, "normalized_name": "same-name", "attributes": {}},
        {"start_page": 13, "normalized_name": "abcdef", "attributes": {}},
    ]

    diagnostics = _monster_agreement_diagnostics(primary, comparison)

    assert diagnostics["monster_primary_with_same_page_containment_name_candidate"] == 0

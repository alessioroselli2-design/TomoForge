from scripts.audit_source_registry_drift import _diff, _expected_row, _segment_key


def test_expected_row_normalizes_registry_keys():
    row = _expected_row(
        {
            "physical_filename": "Manual.pdf",
            "logical_source_id": "manual_it",
            "page_start": 1,
            "page_end": 10,
            "language": "it",
            "ruleset": "2014",
            "authority_class": "licensed_translation",
            "role": "authority",
            "status": "active",
            "text_mode": "text",
            "notes": "ok",
        }
    )
    assert row["source_role"] == "authority"
    assert row["source_status"] == "active"
    assert _segment_key(row) == ("Manual.pdf", "manual_it", 1, 10)


def test_diff_reports_only_changed_metadata():
    expected = {
        "language": "it",
        "ruleset": "2014",
        "authority_class": "licensed_translation",
        "source_role": "authority",
        "source_status": "active",
        "text_mode": "text",
        "notes": "",
    }
    actual = {**expected, "text_mode": "vision_required"}
    assert _diff(expected, actual) == {
        "text_mode": ("vision_required", "text")
    }

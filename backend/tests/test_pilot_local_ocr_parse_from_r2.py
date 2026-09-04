from scripts.pilot_local_ocr_parse_from_r2 import _record_summary


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

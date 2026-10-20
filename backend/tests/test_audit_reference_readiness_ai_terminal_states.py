from scripts.audit_reference_readiness import summarize_readiness


def test_summarize_readiness_reports_all_ai_terminal_states():
    records = [
        {"ai_review_status": "verified"},
        {"ai_review_status": "pending"},
        {"ai_review_status": "excluded"},
        {"ai_review_status": "failed"},
        {"ai_review_status": "not_required"},
        {"ai_review_status": "conflict"},
        {"ai_review_status": "low_confidence"},
    ]

    result = summarize_readiness(records, [], [])

    assert result["records_ai_verified"] == 1
    assert result["records_ai_pending"] == 1
    assert result["records_ai_excluded"] == 1
    assert result["records_ai_failed"] == 1
    assert result["records_ai_not_required"] == 1
    assert result["records_ai_conflict"] == 1
    assert result["records_ai_low_confidence"] == 1
    assert result["ai_review_unexpected_states"] == {}
    assert result["ai_review_statuses_valid"] is True
    assert sum(result["ai_review_status_breakdown"].values()) == result["records_total"]


def test_summarize_readiness_flags_unexpected_ai_review_state():
    records = [
        {"ai_review_status": "pending"},
        {"ai_review_status": "future_state"},
        {"ai_review_status": None},
    ]

    result = summarize_readiness(records, [], [])

    assert result["ai_review_unexpected_states"] == {"future_state": 1, "unknown": 1}
    assert result["ai_review_statuses_valid"] is False
    assert sum(result["ai_review_status_breakdown"].values()) == result["records_total"]

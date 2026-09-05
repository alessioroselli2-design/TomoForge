from scripts.audit_review_status_validity import summarize_review_status_validity


def test_accepts_only_known_human_review_states():
    result = summarize_review_status_validity([
        {"review_status": "verified"},
        {"review_status": "needs_review"},
        {"review_status": "pending"},
    ])

    assert result == {
        "records_total": 3,
        "review_status_breakdown": {
            "needs_review": 1,
            "pending": 1,
            "verified": 1,
        },
        "review_status_unexpected_states": {},
        "review_statuses_valid": True,
    }


def test_flags_unknown_or_null_human_review_states_without_content():
    result = summarize_review_status_validity([
        {"review_status": "verified", "full_text": "private source text"},
        {"review_status": "unexpected_state", "name": "private name"},
        {"review_status": None},
    ])

    assert result["records_total"] == 3
    assert result["review_status_breakdown"] == {
        "unexpected_state": 1,
        "unknown": 1,
        "verified": 1,
    }
    assert result["review_status_unexpected_states"] == {
        "unexpected_state": 1,
        "unknown": 1,
    }
    assert result["review_statuses_valid"] is False
    rendered = str(result)
    assert "private source text" not in rendered
    assert "private name" not in rendered

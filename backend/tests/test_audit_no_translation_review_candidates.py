from scripts.audit_no_translation_review_candidates import summarize_candidates


def test_summarize_candidates_splits_status_and_type_without_content():
    records = [
        {
            "review_status": "needs_review",
            "source_language": "it",
            "translation_status": "not_required",
            "reference_type": "weapon",
            "name": "private name",
            "full_text": "private text",
        },
        {
            "review_status": "needs_review",
            "source_language": "it",
            "translation_status": "not_required",
            "reference_type": "weapon",
        },
        {
            "review_status": "pending",
            "source_language": "it",
            "translation_status": "not_required",
            "reference_type": "spell",
        },
        {
            "review_status": "verified",
            "source_language": "it",
            "translation_status": "not_required",
            "reference_type": "weapon",
        },
        {
            "review_status": "needs_review",
            "source_language": "es",
            "translation_status": "not_required",
            "reference_type": "weapon",
        },
        {
            "review_status": "needs_review",
            "source_language": "it",
            "translation_status": "failed",
            "reference_type": "weapon",
        },
    ]

    result = summarize_candidates(records)

    assert result == {
        "candidate_total": 3,
        "candidate_by_review_status_and_reference_type": {
            "needs_review": {"weapon": 2},
            "pending": {"spell": 1},
        },
        "reconciled": True,
    }
    rendered = str(result)
    assert "private name" not in rendered
    assert "private text" not in rendered


def test_summarize_candidates_orders_types_deterministically():
    records = [
        {"review_status": "needs_review", "source_language": "it", "translation_status": "not_required", "reference_type": "spell"},
        {"review_status": "needs_review", "source_language": "it", "translation_status": "not_required", "reference_type": "weapon"},
        {"review_status": "needs_review", "source_language": "it", "translation_status": "not_required", "reference_type": "weapon"},
        {"review_status": "needs_review", "source_language": "it", "translation_status": "not_required"},
    ]

    result = summarize_candidates(records)

    assert list(result["candidate_by_review_status_and_reference_type"]["needs_review"].items()) == [
        ("weapon", 2),
        ("spell", 1),
        ("unknown", 1),
    ]
    assert result["candidate_total"] == 4
    assert result["reconciled"] is True


def test_summarize_candidates_handles_empty_queue():
    result = summarize_candidates([])

    assert result == {
        "candidate_total": 0,
        "candidate_by_review_status_and_reference_type": {},
        "reconciled": True,
    }

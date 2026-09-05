from scripts.build_deterministic_review_update_plan import MODEL, build_update_plan


def make_record(record_id="a", **overrides):
    record = {
        "id": record_id,
        "review_status": "needs_review",
        "ai_review_status": "pending",
        "source_language": "it",
        "translation_status": "not_required",
        "source_key": "source:book",
        "source_refs": [{"source": "source:book", "page": 1}],
        "review_flags": [],
        "name": "Nome",
        "source_name": "Nome",
        "normalized_name": "nome",
        "source_normalized_name": "nome",
        "description": "Descrizione",
        "source_description": "Descrizione",
        "full_text": "Testo",
        "source_full_text": "Testo",
        "attributes": {"kind": "x"},
        "source_attributes": {"kind": "x"},
        "canonical_id": None,
    }
    record.update(overrides)
    return record


def test_plan_is_bounded_deterministic_and_ai_metadata_only():
    records = [make_record("c"), make_record("a"), make_record("b")]
    before = [dict(record) for record in records]

    plan = build_update_plan(records, limit=2)

    assert [item["id"] for item in plan] == ["a", "b"]
    assert all(item["ai_review_status"] == "verified" for item in plan)
    assert all(item["ai_review_model"] == MODEL for item in plan)
    assert all(item["ai_confidence"] == 1.0 for item in plan)
    assert all(item["ai_review_corrections"] == {} for item in plan)
    assert all("review_status" not in item for item in plan)
    assert all("canonical_id" not in item for item in plan)
    assert all("source_key" not in item and "source_refs" not in item for item in plan)
    assert records == before


def test_plan_excludes_records_that_fail_existing_gate():
    records = [
        make_record("ok"),
        make_record("translated", translation_status="translated"),
        make_record("flagged", review_flags=["check"]),
        make_record("changed", description="diversa"),
        make_record("already", ai_review_status="verified"),
    ]

    assert [item["id"] for item in build_update_plan(records, limit=5)] == ["ok"]

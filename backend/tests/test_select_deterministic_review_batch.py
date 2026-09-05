import pytest

from scripts.select_deterministic_review_batch import (
    is_deterministic_review_candidate,
    select_deterministic_review_batch,
)


def make_record(record_id="b", **overrides):
    record = {
        "id": record_id,
        "review_status": "needs_review",
        "ai_review_status": None,
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
    }
    record.update(overrides)
    return record


def test_candidate_requires_exact_source_equality_and_provenance():
    assert is_deterministic_review_candidate(make_record())
    assert not is_deterministic_review_candidate(make_record(source_key=""))
    assert not is_deterministic_review_candidate(make_record(source_refs=[]))
    assert not is_deterministic_review_candidate(make_record(description="diversa"))
    assert not is_deterministic_review_candidate(make_record(attributes={"kind": "y"}))


def test_candidate_preserves_review_and_translation_gates():
    assert not is_deterministic_review_candidate(make_record(review_status="verified"))
    assert not is_deterministic_review_candidate(make_record(ai_review_status="verified"))
    assert not is_deterministic_review_candidate(make_record(source_language="en"))
    assert not is_deterministic_review_candidate(make_record(translation_status="pending"))
    assert not is_deterministic_review_candidate(make_record(review_flags=["check"] ))


def test_candidate_rejects_digit_bearing_names_that_need_interpretation():
    assert not is_deterministic_review_candidate(
        make_record(name="0Rcus", source_name="0Rcus", normalized_name="0rcus", source_normalized_name="0rcus")
    )
    assert not is_deterministic_review_candidate(
        make_record(name="Orcus2", source_name="Orcus2", normalized_name="orcus2", source_normalized_name="orcus2")
    )
    assert is_deterministic_review_candidate(make_record(name="Orcus", source_name="Orcus"))


def test_batch_is_bounded_and_deterministic_without_mutation():
    records = [make_record("c"), make_record("a"), make_record("b")]
    original = [dict(record) for record in records]

    batch = select_deterministic_review_batch(records, limit=2)

    assert [record["id"] for record in batch] == ["a", "b"]
    assert records == original
    assert all(record["review_status"] == "needs_review" for record in records)


def test_limit_must_be_positive():
    with pytest.raises(ValueError):
        select_deterministic_review_batch([make_record()], limit=0)

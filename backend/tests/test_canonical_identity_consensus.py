import asyncio

from services.canonical_identity_consensus import (
    resolve_identity_consensus,
)


def record(identifier, **changes):
    value = {
        "id": identifier,
        "user_id": "owner",
        "reference_type": "ability",
        "name": "Colpo Fortunato",
        "normalized_name": "colpo fortunato",
        "source_name": "Golpe De Suerte",
        "full_text": (
            "Quando effettui una prova puoi ottenere "
            "un risultato favorevole."
        ),
        "source_full_text": "",
        "source_key": f"{identifier}.pdf",
        "source_language": "es",
        "translation_status": "translated",
        "parent_class": "",
        "parent_subclass": "",
        "level": "",
        "attributes": {},
        "ai_review_corrections": {},
    }
    value.update(changes)
    return value


def matched(candidate_id, confidence=0.99):
    return {
        "status": "matched",
        "candidate_source_record_id": candidate_id,
        "confidence": confidence,
        "notes": "Stessa identità.",
    }


def test_consensus_confirms_same_candidate_twice():
    source = record("source")
    candidate = record(
        "candidate",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_language="it",
        translation_status="not_required",
    )

    result = asyncio.run(
        resolve_identity_consensus(
            source,
            [source, candidate],
            first_comparator=lambda r, c: matched(
                "candidate",
                0.98,
            ),
            second_comparator=lambda r, c: matched(
                "candidate",
                0.97,
            ),
        )
    )

    assert result["status"] == "matched"
    assert result["consensus"] == "confirmed"
    assert result["consensus_passes"] == 2
    assert result["matched_source_record_id"] == "candidate"
    assert result["confidence"] == 0.97


def test_first_uncertain_does_not_call_second_verifier():
    source = record("source")
    candidate = record(
        "candidate",
        source_language="it",
        translation_status="not_required",
    )

    def must_not_run(record, candidates):
        raise AssertionError("second verifier should not run")

    result = asyncio.run(
        resolve_identity_consensus(
            source,
            [source, candidate],
            first_comparator=lambda r, c: {
                "status": "uncertain",
                "candidate_source_record_id": "",
                "confidence": 0.80,
                "notes": "Dati insufficienti.",
            },
            second_comparator=must_not_run,
        )
    )

    assert result["status"] == "uncertain"
    assert result["consensus"] == "not_required"
    assert result["consensus_passes"] == 1


def test_second_uncertain_blocks_first_match():
    source = record("source")
    candidate = record(
        "candidate",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_language="it",
        translation_status="not_required",
    )

    result = asyncio.run(
        resolve_identity_consensus(
            source,
            [source, candidate],
            first_comparator=lambda r, c: matched(
                "candidate",
                1.0,
            ),
            second_comparator=lambda r, c: {
                "status": "uncertain",
                "candidate_source_record_id": "",
                "confidence": 0.90,
                "notes": "Non abbastanza sicuro.",
            },
        )
    )

    assert result["status"] == "uncertain"
    assert result["consensus"] == "disagreed"
    assert result["matched_source_record_id"] == ""
    assert result["identity_normalized_name"] == ""


def test_different_second_candidate_blocks_consensus():
    source = record("source")

    first_candidate = record(
        "first",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_language="it",
        translation_status="not_required",
    )

    second_candidate = record(
        "second",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_language="it",
        translation_status="not_required",
    )

    result = asyncio.run(
        resolve_identity_consensus(
            source,
            [
                source,
                first_candidate,
                second_candidate,
            ],
            first_comparator=lambda r, c: matched(
                "first",
                0.99,
            ),
            second_comparator=lambda r, c: matched(
                "second",
                0.99,
            ),
        )
    )

    assert result["status"] == "uncertain"
    assert result["consensus"] == "disagreed"
    assert result["matched_source_record_id"] == ""


def test_second_no_match_blocks_first_match():
    source = record("source")
    candidate = record(
        "candidate",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_language="it",
        translation_status="not_required",
    )

    result = asyncio.run(
        resolve_identity_consensus(
            source,
            [source, candidate],
            first_comparator=lambda r, c: matched(
                "candidate",
                0.99,
            ),
            second_comparator=lambda r, c: {
                "status": "no_match",
                "candidate_source_record_id": "",
                "confidence": 0.99,
                "notes": "Regole differenti.",
            },
        )
    )

    assert result["status"] == "uncertain"
    assert result["consensus"] == "disagreed"
    assert result["matched_source_record_id"] == ""

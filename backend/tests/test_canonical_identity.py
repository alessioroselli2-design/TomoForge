import asyncio

from services.canonical_identity import (
    identity_candidate_score,
    identity_candidates,
    identity_catalog_fingerprint,
    identity_name,
    resolve_identity,
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
            "Quando effettui una prova puoi ottenere un risultato favorevole."
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


def test_similar_translated_name_ranks_above_unrelated_rule():
    source = record("es")

    equivalent = record(
        "it",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_name="Colpo Di Fortuna",
        source_language="it",
        translation_status="not_required",
        full_text=(
            "Quando effettui una prova puoi ottenere un risultato favorevole."
        ),
    )

    unrelated = record(
        "other",
        name="Forma Selvatica",
        normalized_name="forma selvatica",
        source_language="it",
        translation_status="not_required",
        full_text="Puoi assumere magicamente la forma di una bestia.",
    )

    assert (
        identity_candidate_score(source, equivalent)
        > identity_candidate_score(source, unrelated)
    )


def test_progression_mismatch_is_not_a_candidate():
    source = record(
        "one",
        reference_type="class_feature",
        parent_class="Druido",
        level="2",
    )

    wrong_level = record(
        "two",
        reference_type="class_feature",
        parent_class="Druido",
        level="10",
    )

    assert identity_candidate_score(source, wrong_level) == -1.0


def test_candidate_filter_keeps_best_equivalent():
    source = record("source")

    equivalent = record(
        "equivalent",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_language="it",
        translation_status="not_required",
    )

    unrelated = record(
        "unrelated",
        name="Forma Selvatica",
        normalized_name="forma selvatica",
        full_text="Assumi la forma di una bestia.",
        source_language="it",
        translation_status="not_required",
    )

    candidates = identity_candidates(
        source,
        [source, unrelated, equivalent],
    )

    assert candidates
    assert candidates[0]["id"] == "equivalent"


def test_high_confidence_match_creates_alias_only():
    source = record("source")

    equivalent = record(
        "equivalent",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_language="it",
        translation_status="not_required",
    )

    result = asyncio.run(
        resolve_identity(
            source,
            [source, equivalent],
            comparator=lambda record, candidates: {
                "status": "matched",
                "candidate_source_record_id": "equivalent",
                "confidence": 0.97,
                "notes": "Stessa regola con titolo tradotto diversamente.",
            },
        )
    )

    assert result["status"] == "matched"
    assert result["identity_normalized_name"] == "colpo di fortuna"
    assert result["matched_source_record_id"] == "equivalent"


def test_low_confidence_match_remains_uncertain():
    source = record("source")

    equivalent = record(
        "equivalent",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_language="it",
        translation_status="not_required",
    )

    result = asyncio.run(
        resolve_identity(
            source,
            [source, equivalent],
            comparator=lambda record, candidates: {
                "status": "matched",
                "candidate_source_record_id": "equivalent",
                "confidence": 0.70,
                "notes": "Non abbastanza sicuro.",
            },
        )
    )

    assert result["status"] == "uncertain"
    assert result["identity_normalized_name"] == ""


def test_unknown_candidate_from_ai_is_rejected():
    source = record("source")

    equivalent = record(
        "equivalent",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_language="it",
        translation_status="not_required",
    )

    result = asyncio.run(
        resolve_identity(
            source,
            [source, equivalent],
            comparator=lambda record, candidates: {
                "status": "matched",
                "candidate_source_record_id": "invented",
                "confidence": 0.99,
                "notes": "",
            },
        )
    )

    assert result["status"] == "uncertain"
    assert result["confidence"] == 0.0


def test_high_confidence_no_match_is_allowed():
    source = record("source")

    candidate = record(
        "candidate",
        name="Colpo Di Fortuna",
        normalized_name="colpo di fortuna",
        source_language="it",
        translation_status="not_required",
    )

    result = asyncio.run(
        resolve_identity(
            source,
            [source, candidate],
            comparator=lambda record, candidates: {
                "status": "no_match",
                "candidate_source_record_id": "",
                "confidence": 0.98,
                "notes": "Sono regole differenti.",
            },
        )
    )

    assert result["status"] == "no_match"
    assert result["identity_normalized_name"] == ""


def test_existing_identity_alias_is_reused():
    aliased = record(
        "alias",
        ai_review_corrections={
            "identity_status": "matched",
            "identity_normalized_name": "colpo di fortuna",
        },
    )

    assert identity_name(aliased) == "colpo di fortuna"


def test_catalog_fingerprint_changes_when_candidate_changes():
    source = record("source")
    candidate = record("candidate")

    before = identity_catalog_fingerprint(source, [candidate])

    changed = dict(candidate)
    changed["full_text"] = "Testo differente."

    after = identity_catalog_fingerprint(source, [changed])

    assert before != after

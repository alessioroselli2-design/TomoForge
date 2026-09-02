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

def test_high_confidence_ai_match_with_weak_local_candidate_is_rejected():
    source = record(
        "source-weak",
        name="Ricolmi Di Energia",
        normalized_name="ricolmi di energia",
        full_text=(
            "Gli gnomi manifestano energia, entusiasmo "
            "e vitalita nelle loro espressioni."
        ),
    )

    weak = record(
        "weak",
        name="Raggio Di Infermità",
        normalized_name="raggio di infermita",
        source_language="it",
        translation_status="not_required",
        full_text="",
    )

    assert 0.18 <= identity_candidate_score(source, weak) < 0.45

    result = asyncio.run(
        resolve_identity(
            source,
            [source, weak],
            comparator=lambda record, candidates: {
                "status": "matched",
                "candidate_source_record_id": "weak",
                "confidence": 1.0,
                "notes": "Match dichiarato dal modello.",
            },
        )
    )

    assert result["status"] == "uncertain"
    assert result["matched_source_record_id"] == ""
    assert result["identity_normalized_name"] == ""
    assert "controllo deterministico" in result["notes"]


def test_ai_cannot_choose_candidate_too_far_down_local_ranking():
    source = record(
        "source-rank",
        name="Ricolmi Di Energia",
        normalized_name="ricolmi di energia",
        full_text=(
            "Manifesti energia ed entusiasmo "
            "attraverso una caratteristica."
        ),
    )

    candidates = [
        record(
            "rank-1",
            name="Ricolmi Di Energia",
            normalized_name="ricolmi di energia",
            source_language="it",
            translation_status="not_required",
            full_text=source["full_text"],
        ),
        record(
            "rank-2",
            name="Ricolmo Di Energia",
            normalized_name="ricolmo di energia",
            source_language="it",
            translation_status="not_required",
            full_text=source["full_text"],
        ),
        record(
            "rank-3",
            name="Energia Ricolma",
            normalized_name="energia ricolma",
            source_language="it",
            translation_status="not_required",
            full_text=source["full_text"],
        ),
        record(
            "rank-4",
            name="Energia",
            normalized_name="energia",
            source_language="it",
            translation_status="not_required",
            full_text=source["full_text"],
        ),
    ]

    ranked = identity_candidates(
        source,
        [source, *candidates],
    )

    assert len(ranked) >= 4
    rank_four_id = ranked[3]["id"]

    result = asyncio.run(
        resolve_identity(
            source,
            [source, *candidates],
            comparator=lambda record, candidates: {
                "status": "matched",
                "candidate_source_record_id": rank_four_id,
                "confidence": 1.0,
                "notes": "Il modello ha scelto un candidato debole.",
            },
        )
    )

    assert result["status"] == "uncertain"
    assert result["matched_source_record_id"] == ""
    assert "candidate_rank=4" in result["notes"]


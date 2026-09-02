import asyncio

from services.translation_verification import (
    TRANSLATION_AI_VERIFIED,
    TRANSLATION_CONFLICT,
    TRANSLATION_FAILED,
    TRANSLATION_LOW_CONFIDENCE,
    TRANSLATION_NOT_REQUIRED,
    TRANSLATION_PENDING,
    build_translation_verification_prompt,
    mechanical_tokens,
    translation_verification_fingerprint,
    translation_verification_is_current,
    verify_translation,
)


def record(**overrides):
    base = {
        "id": "ref-1",
        "source_language": "en",
        "source_name": "Fire Bolt",
        "source_description": "A mote of fire deals 1d10 fire damage.",
        "source_full_text": "Make a ranged spell attack. On a hit, the target takes 1d10 fire damage at 120 feet.",
        "source_attributes": {"damage": "1d10", "range": "120 feet"},
        "name": "Dardo di Fuoco",
        "description": "Una scintilla di fuoco infligge 1d10 danni da fuoco.",
        "full_text": "Effettua un attacco a distanza con incantesimo. Se colpisce, il bersaglio subisce 1d10 danni da fuoco a 120 piedi.",
        "attributes": {"damage": "1d10", "range": "120 piedi"},
        "translation_status": "translated",
        "review_flags": [],
    }
    base.update(overrides)
    return base


def run(record_value, answer):
    return asyncio.run(verify_translation(record_value, comparator=lambda _record: answer, model="test-model"))


def test_high_confidence_faithful_translation_is_ai_verified():
    result = run(record(), {
        "status": "verified",
        "confidence": 0.99,
        "conflict_fields": [],
        "notes": "Traduzione fedele e completa.",
    })
    assert result["status"] == TRANSLATION_AI_VERIFIED
    assert result["confidence"] == 0.99
    assert result["model"] == "test-model"
    assert result["fingerprint"]


def test_verified_below_strict_threshold_becomes_low_confidence():
    result = run(record(), {
        "status": "verified",
        "confidence": 0.96,
        "conflict_fields": [],
        "notes": "Quasi certo.",
    })
    assert result["status"] == TRANSLATION_LOW_CONFIDENCE
    assert "translation_fidelity" in result["conflict_fields"]


def test_conflict_is_preserved_when_confident():
    result = run(record(), {
        "status": "conflict",
        "confidence": 0.93,
        "conflict_fields": ["full_text"],
        "notes": "Manca una condizione.",
    })
    assert result["status"] == TRANSLATION_CONFLICT
    assert result["conflict_fields"] == ["full_text"]


def test_low_confidence_conflict_does_not_become_certain_conflict():
    result = run(record(), {
        "status": "conflict",
        "confidence": 0.62,
        "conflict_fields": ["attributes"],
        "notes": "Confronto incerto.",
    })
    assert result["status"] == TRANSLATION_LOW_CONFIDENCE


def test_mechanical_token_mismatch_blocks_before_ai_call():
    called = []

    def comparator(_record):
        called.append(True)
        return {"status": "verified", "confidence": 1, "conflict_fields": [], "notes": ""}

    changed = record(
        full_text="Effettua un attacco a distanza. Se colpisce, il bersaglio subisce 2d10 danni da fuoco a 120 piedi.",
        description="Una scintilla infligge 2d10 danni.",
        attributes={"damage": "2d10", "range": "120 piedi"},
    )
    result = asyncio.run(verify_translation(changed, comparator=comparator))

    assert result["status"] == TRANSLATION_CONFLICT
    assert result["conflict_fields"] == ["mechanical_tokens"]
    assert called == []


def test_incomplete_source_snapshot_is_deterministic_conflict():
    result = asyncio.run(verify_translation(record(source_full_text=""), comparator=lambda _r: {}))
    assert result["status"] == TRANSLATION_CONFLICT
    assert result["conflict_fields"] == ["source_snapshot"]


def test_non_ready_translation_is_pending_and_does_not_call_ai():
    called = []
    result = asyncio.run(verify_translation(
        record(translation_status="failed"),
        comparator=lambda _r: called.append(True),
    ))
    assert result["status"] == TRANSLATION_PENDING
    assert called == []


def test_italian_source_does_not_require_translation_verification():
    result = asyncio.run(verify_translation(record(source_language="it", translation_status="not_required")))
    assert result["status"] == TRANSLATION_NOT_REQUIRED
    assert result["confidence"] == 1.0


def test_provider_or_invalid_verdict_failure_is_not_certified():
    def broken(_record):
        raise RuntimeError("provider down")

    result = asyncio.run(verify_translation(record(), comparator=broken, model="test-model"))
    assert result["status"] == TRANSLATION_FAILED
    assert result["confidence"] == 0
    assert result["conflict_fields"] == ["translation_verifier"]


def test_invalid_ai_status_is_not_certified():
    result = run(record(), {
        "status": "perfect",
        "confidence": 1,
        "conflict_fields": [],
        "notes": "",
    })
    assert result["status"] == TRANSLATION_FAILED


def test_fingerprint_changes_when_source_or_translation_changes():
    original = record()
    first = translation_verification_fingerprint(original)
    assert first != translation_verification_fingerprint(record(source_full_text=original["source_full_text"] + " Extra."))
    assert first != translation_verification_fingerprint(record(full_text=original["full_text"] + " Extra."))


def test_current_verdict_requires_matching_fingerprint():
    value = record()
    value["translation_review_fingerprint"] = translation_verification_fingerprint(value)
    assert translation_verification_is_current(value)
    value["name"] = "Nome cambiato"
    assert not translation_verification_is_current(value)


def test_prompt_is_strictly_translation_fidelity_only():
    prompt = build_translation_verification_prompt(record(review_flags=["ocr_da_verificare"]))
    assert "Non usare conoscenze esterne di D&D" in prompt
    assert "non scegliere una fonte canonica" in prompt
    assert "source_review_flags" in prompt
    assert "ocr_da_verificare" in prompt
    assert "Fire Bolt" in prompt
    assert "Dardo di Fuoco" in prompt


def test_mechanical_tokens_keep_dice_and_numbers_stable():
    assert mechanical_tokens("CD 15, 1d8 + 3 danni, 30 piedi e 50%") == mechanical_tokens(
        "DC 15, 1d8 + 3 damage, 30 feet and 50%"
    )

import copy

import pytest

from services.reference_translation import (
    TRANSLATION_REVIEW_FLAG,
    apply_translation,
    build_translation_prompt,
    translation_failure,
    translation_required,
    translation_source_record,
    validate_translation_payload,
)


def source_record(record_id="r1", language="en"):
    return {
        "id": record_id,
        "reference_type": "spell",
        "name": "Fire Bolt",
        "normalized_name": "fire bolt",
        "description": "Original description.",
        "full_text": "Original complete rules text with 1d10 damage.",
        "attributes": {"level": 0, "damage": "1d10", "school": "evocation"},
        "source_language": language,
        "source_name": "Fire Bolt",
        "source_description": "Original description.",
        "source_full_text": "Original complete rules text with 1d10 damage.",
        "source_attributes": {"level": 0, "damage": "1d10", "school": "evocation"},
        "review_flags": [],
    }


@pytest.mark.parametrize("language", ["en", "es", "ru", "EN-us"])
def test_translation_required_for_supported_non_italian_sources(language):
    assert translation_required(language)


def test_translation_not_required_for_italian_or_unknown_source():
    assert not translation_required("it")
    assert not translation_required("")
    assert not translation_required("fr")


def test_prompt_is_language_specific_and_forbids_external_corrections():
    record = source_record(language="ru")
    prompt = build_translation_prompt([record], "ru")

    assert "dal russo all'italiano" in prompt
    assert "non usare conoscenze esterne" in prompt
    assert "non correggere il contenuto" in prompt
    assert "1d10" in prompt
    assert '"id":"r1"' in prompt


def test_prompt_rejects_unsupported_language_and_empty_batch():
    with pytest.raises(ValueError, match="unsupported_source_language"):
        build_translation_prompt([source_record()], "fr")
    with pytest.raises(ValueError, match="translation_batch_empty"):
        build_translation_prompt([], "en")


def test_translation_source_record_uses_immutable_source_snapshot():
    record = source_record()
    record["name"] = "Localized Name"
    record["full_text"] = "Localized text"

    payload = translation_source_record(record)

    assert payload["name"] == "Fire Bolt"
    assert payload["full_text"].startswith("Original complete")
    assert payload["attributes"] == record["source_attributes"]
    assert payload["attributes"] is not record["source_attributes"]


def test_validator_accepts_complete_exact_batch():
    records = [source_record("r1"), source_record("r2")]
    payload = {
        "records": [
            {
                "id": "r1",
                "name": "Dardo di Fuoco",
                "description": "Descrizione uno.",
                "full_text": "Testo completo uno con 1d10 danni.",
                "attributes": {"level": 0, "damage": "1d10"},
            },
            {
                "id": "r2",
                "name": "Secondo Record",
                "description": "Descrizione due.",
                "full_text": "Testo completo due.",
                "attributes": {"level": 1},
            },
        ]
    }

    translated, error = validate_translation_payload(payload, records)

    assert error == ""
    assert set(translated) == {"r1", "r2"}
    assert translated["r1"]["attributes"]["damage"] == "1d10"


@pytest.mark.parametrize(
    "payload,error",
    [
        ({}, "provider_translation_invalid"),
        ({"records": [{"id": "invented", "name": "x", "description": "y", "full_text": "z", "attributes": {}}]}, "provider_translation_invalid"),
        ({"records": [{"id": "r1", "name": "x", "description": "y", "full_text": "z", "attributes": {}}]}, "provider_translation_incomplete"),
        ({"records": [
            {"id": "r1", "name": "x", "description": "y", "full_text": "z", "attributes": {}},
            {"id": "r1", "name": "x", "description": "y", "full_text": "z", "attributes": {}},
        ]}, "provider_translation_invalid"),
    ],
)
def test_validator_rejects_partial_extra_or_duplicate_ids(payload, error):
    records = [source_record("r1"), source_record("r2")]
    translated, actual_error = validate_translation_payload(payload, records)
    assert translated == {}
    assert actual_error == error


def test_apply_translation_preserves_original_and_forces_review():
    record = source_record()
    original = copy.deepcopy(record)
    localized = apply_translation(
        record,
        {
            "name": "Dardo di Fuoco",
            "description": "Descrizione tradotta.",
            "full_text": "Testo tradotto completo con 1d10 danni.",
            "attributes": {"level": 0, "damage": "1d10", "school": "invocazione"},
        },
    )

    assert record == original
    assert localized["name"] == "Dardo di Fuoco"
    assert localized["source_name"] == "Fire Bolt"
    assert localized["source_full_text"] == original["source_full_text"]
    assert localized["translation_status"] == "translated"
    assert TRANSLATION_REVIEW_FLAG in localized["review_flags"]


def test_translation_failure_never_mutates_source_and_requires_review():
    record = source_record(language="es")
    original = copy.deepcopy(record)

    failed = translation_failure(record, "provider_rate_limited")

    assert record == original
    assert failed["translation_status"] == "failed"
    assert failed["translation_error"] == "provider_rate_limited"
    assert TRANSLATION_REVIEW_FLAG in failed["review_flags"]

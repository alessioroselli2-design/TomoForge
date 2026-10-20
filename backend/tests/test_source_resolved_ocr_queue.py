"""Regression gates for the 21 original-source-resolved legacy OCR fragments."""

import pytest

from services.source_resolved_ocr_queue import is_source_resolved_ocr_fragment


@pytest.fixture
def documented_fragment():
    return {
        "reference_type": "other",
        "review_status": "pending",
        "ai_review_status": "excluded",
        "review_flags": ["ocr_da_verificare", "source_confirmed_redundant_fragment"],
        "review_corrections": {
            "_duplicate_disposition": {
                "kind": "source_confirmed_redundant_statblock_fragment",
                "target_reference_id": "ref_verified_monster",
                "physical_sha256": "a" * 64,
                "original_pdf_page": 135,
                "evidence": "Original licensed page and exact CA/PF/velocita agreement.",
            }
        },
    }


def test_only_documented_source_resolved_fragment_is_hidden(documented_fragment):
    assert is_source_resolved_ocr_fragment(documented_fragment)
    # The source, record, and review state are not changed by the queue helper.
    assert documented_fragment["review_status"] == "pending"
    assert "ocr_da_verificare" in documented_fragment["review_flags"]


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("reference_type", "monster"),
        ("reference_type", "spell"),
        ("review_status", "needs_review"),
        ("review_status", "verified"),
        ("ai_review_status", "pending"),
        ("ai_review_status", "verified"),
    ],
)
def test_changed_classification_or_review_status_stays_visible(
    documented_fragment, field, replacement
):
    documented_fragment[field] = replacement
    assert not is_source_resolved_ocr_fragment(documented_fragment)


def test_excluded_ai_status_alone_never_hides_record(documented_fragment):
    documented_fragment["review_flags"] = ["ocr_da_verificare"]
    assert not is_source_resolved_ocr_fragment(documented_fragment)


@pytest.mark.parametrize(
    ("key", "replacement"),
    [
        ("kind", "unverified_guess"),
        ("target_reference_id", ""),
        ("target_reference_id", "not_an_id"),
        ("physical_sha256", ""),
        ("physical_sha256", "b" * 63),
        ("original_pdf_page", 0),
        ("original_pdf_page", True),
        ("original_pdf_page", "135"),
        ("evidence", " "),
    ],
)
def test_missing_evidence_must_remain_in_active_queue(
    documented_fragment, key, replacement
):
    documented_fragment["review_corrections"]["_duplicate_disposition"][key] = replacement
    assert not is_source_resolved_ocr_fragment(documented_fragment)


@pytest.mark.parametrize(
    "kind",
    [
        "source_confirmed_contextual_prose_for_verified_monster",
        "source_confirmed_section_plus_megera_statblock",
    ],
)
def test_documented_non_statblock_fragments_are_resolved(documented_fragment, kind):
    documented_fragment["review_corrections"]["_duplicate_disposition"]["kind"] = kind
    assert is_source_resolved_ocr_fragment(documented_fragment)


def test_two_statblocks_require_both_distinct_targets(documented_fragment):
    disposition = documented_fragment["review_corrections"]["_duplicate_disposition"]
    disposition["kind"] = "source_confirmed_multi_monster_boundary_splice"
    disposition.pop("target_reference_id")
    disposition["target_reference_ids"] = ["ref_mago_divinatore", "ref_mago_evocatore"]
    assert is_source_resolved_ocr_fragment(documented_fragment)
    disposition["target_reference_ids"] = ["ref_mago_divinatore"]
    assert not is_source_resolved_ocr_fragment(documented_fragment)
    disposition["target_reference_ids"] = ["ref_mago_divinatore"] * 2
    assert not is_source_resolved_ocr_fragment(documented_fragment)


def test_no_mutation_of_record_or_legacy_review_flags(documented_fragment):
    import copy

    before = copy.deepcopy(documented_fragment)
    assert is_source_resolved_ocr_fragment(documented_fragment)
    assert documented_fragment == before

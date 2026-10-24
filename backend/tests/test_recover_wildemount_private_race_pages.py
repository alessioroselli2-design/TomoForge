"""Synthetic safety checks for five original Wildemount source pages."""
from scripts.recover_five_race_source_pages import accepted
from scripts.recover_wildemount_private_race_pages import (
    PDF_PAGES, SHA256, SOURCE, TARGETS, old_record_gate,
)


def sample_text(target):
    return (
        target[3] + "\n"
        + "\n".join(label + ": synthetic test text" for label in target[5])
        + "\n" + ("Only invented test material. " * 50)
    )


def record(target):
    return {
        "id": target[0],
        "name": target[1],
        "reference_type": target[2],
        "source_key": SOURCE,
        "review_status": "verified",
        "ai_review_status": "pending",
        "source_full_text": "",
        "source_text_checksum": "",
        "source_refs": [
            {"filename": SOURCE, "page": target[4], "sha256": SHA256}
        ],
        "attributes": {},
    }


def test_exact_registered_source_and_bounded_ocr_pages():
    assert len(SHA256) == 64
    assert PDF_PAGES == 307
    assert len(TARGETS) == len({x[0] for x in TARGETS}) == 5
    assert all(1 <= x[4] <= PDF_PAGES for x in TARGETS)
    assert len({x[4] for x in TARGETS}) <= 5


def test_each_heading_requires_two_original_specific_traits_in_two_reads():
    for target in TARGETS:
        synthetic = sample_text(target)
        proxy = (None, None, target[3], None, target[5])
        assert accepted(synthetic, synthetic, proxy)
        without_traits = target[3] + "\n" + ("Invented words only. " * 50)
        assert not accepted(synthetic, without_traits, proxy)


def test_source_snapshot_rejects_ambiguous_or_previously_approved_rows():
    for target in TARGETS:
        old = record(target)
        assert old_record_gate(old, target)
        assert not old_record_gate({**old, "ai_review_status": "verified"}, target)
        assert not old_record_gate({**old, "source_full_text": "existing OCR"}, target)
        assert not old_record_gate({**old, "source_text_checksum": "old checksum"}, target)
        assert not old_record_gate({**old, "source_refs": []}, target)
        assert not old_record_gate({**old, "reference_type": "monster"}, target)
        assert not old_record_gate(
            {**old, "attributes": {"original_pdf_page_ocr_recovered": {}}},
            target,
        )
        assert not old_record_gate(
            {**old, "source_refs": [{"filename": SOURCE, "page": target[4],
                                      "sha256": "0" * 64}]},
            target,
        )

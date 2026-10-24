"""Synthetic tests for column-aware OCR of 2018 MToF missing entries."""
from scripts.recover_mtof_four_column_pages import (
    HASH, SOURCE, TARGETS, WINDOW_MAX, page_score, valid_row,
)

def test_four_exact_targets_and_bounded_windows():
    assert len(TARGETS) == 4
    assert len({t[0] for t in TARGETS}) == 4
    assert WINDOW_MAX == 12
    assert all(t[1] in (23, 81) for t in TARGETS)

def test_tiefling_signature_must_agree_with_heading():
    for target in TARGETS[:3]:
        good = target[2] + "\n" + "\n".join(target[3]) + "\n" + ("Synthetic OCR paragraph. " * 35)
        assert page_score(good, target)["sufficient"]
        bad = "Unrelated character page\n" + "\n".join(target[3]) + "\n" + ("Synthetic OCR paragraph. " * 35)
        assert not page_score(bad, target)["sufficient"]

def test_only_original_pending_page_can_be_updated():
    t=TARGETS[-1]
    row={
        "name":t[0], "source_key":SOURCE, "reference_type":"subrace",
        "review_status":"verified", "ai_review_status":"pending",
        "source_full_text":"", "source_text_checksum":"",
        "id":"ref_synthetic","user_id":"owner_synthetic",
        "updated_at":"2026-10-24T17:00:00+00:00",
        "source_refs":[{"filename":SOURCE,"page":t[1]}],
    }
    assert valid_row(row, {"target":t})
    assert not valid_row({**row,"ai_review_status":"verified"},{"target":t})
    assert not valid_row({**row,"source_refs":[]},{"target":t})
    assert not valid_row({**row,"source_key":"not-original.pdf"},{"target":t})
    assert not valid_row({**row,"updated_at":None},{"target":t})
    assert not valid_row({**row,"user_id":None},{"target":t})
    assert len(HASH)==64

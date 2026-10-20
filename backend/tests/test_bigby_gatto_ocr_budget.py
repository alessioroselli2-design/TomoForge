"""Bounds focused Bigby Gatto Ghignante OCR retry to a single record."""

from scripts import repair_monsters_from_source as repair


def test_gatto_ghignante_retry_preserves_global_budget_isolation():
    target = "ref_ac1a0de0ddba58219b21b506119cd1f6"
    other = "ref_00000000000000000000000000000000"
    assert repair._ocr_budget_seconds(target, "bigby_single_pending_readonly") == 150.0
    assert repair._ocr_budget_seconds(other, "bigby_single_pending_readonly") == 60.0
    assert repair.HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS == 15.0

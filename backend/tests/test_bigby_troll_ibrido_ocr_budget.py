"""Target-bound OCR retry for Troll Ibrido stays fail-closed."""

from scripts import repair_monsters_from_source as repair


def test_bigby_troll_ibrido_budget_is_exactly_scoped():
    target = "ref_815c9a5b017658a3859b977a0cfd6f35"
    unrelated = "ref_00000000000000000000000000000000"
    assert repair._ocr_budget_seconds(target, "bigby_single_pending_readonly") == 150.0
    assert repair._ocr_budget_seconds(unrelated, "bigby_single_pending_readonly") == 60.0
    assert repair.HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS == 15.0

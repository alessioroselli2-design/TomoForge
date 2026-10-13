"""Keep Bigby OCR timeout extensions isolated and fail-closed."""

from scripts import repair_monsters_from_source as repair


def test_cacciatore_specific_ocr_budget_does_not_affect_other_monsters():
    cacciatore = "ref_abaf4a8fe2395260991a96729a200351"
    other = "ref_00000000000000000000000000000000"
    assert repair._ocr_budget_seconds(cacciatore, "bigby_single_pending_readonly") == 150.0
    assert repair._ocr_budget_seconds(other, "bigby_single_pending_readonly") == 60.0
    assert repair.HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS == 15.0

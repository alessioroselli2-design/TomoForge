"""Target-specific OCR budget guard for the Ettin Ceremorfo review."""

from scripts import repair_monsters_from_source as repair


def test_ettin_ocr_extension_is_scoped_and_tesseract_remains_bounded():
    ettin = "ref_7a26728f8410582ba70ddc7b44f5d4df"
    unrelated = "ref_00000000000000000000000000000000"
    assert repair._ocr_budget_seconds(ettin, "bigby_single_pending_readonly") == 150.0
    assert repair._ocr_budget_seconds(unrelated, "bigby_single_pending_readonly") == 60.0
    assert repair.HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS == 15.0

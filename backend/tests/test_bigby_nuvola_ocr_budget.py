"""Bound Nuvola Spettrale OCR retry to its registered record."""

from scripts import repair_monsters_from_source as repair


def test_nuvola_spettrale_source_retry_is_bounded_and_isolated():
    nuvola = "ref_f1d7b2c1ee66563587537988b9399a29"
    other = "ref_00000000000000000000000000000000"
    assert repair._ocr_budget_seconds(nuvola, "bigby_single_pending_readonly") == 150.0
    assert repair._ocr_budget_seconds(other, "bigby_single_pending_readonly") == 60.0
    assert repair.HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS == 15.0

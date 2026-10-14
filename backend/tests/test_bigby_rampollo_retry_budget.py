"""Bounded source OCR budgets for the four remaining Rampollo audit targets."""

from scripts import repair_monsters_from_source as repair


def test_bigby_rampollo_budgets_are_strictly_target_scoped():
    ids = {
        "ref_4e249fc0d86753919cbb7bec5b96b661",
        "ref_7bc4d1c262b355668531f7e2331550f4",
        "ref_f0ebcfa60b9256a8afa871cfd9d0bbb8",
        "ref_4dc0cbc8340d5958bf4d85756ef9027c",
    }
    for record_id in ids:
        assert repair._ocr_budget_seconds(record_id, "bigby_single_pending_readonly") == 150.0
    assert (
        repair._ocr_budget_seconds(
            "ref_00000000000000000000000000000000",
            "bigby_single_pending_readonly",
        )
        == 60.0
    )
    assert repair.HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS == 15.0

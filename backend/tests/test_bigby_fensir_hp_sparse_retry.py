"""Fail-closed sparse OCR fallback is strictly bound to one Bigby pending record."""

from scripts import repair_monsters_from_source as repair


TARGET = "ref_be4830300bfe50f09331951afaf26eb6"


def test_fensir_sparse_retry_requires_exact_registered_source_and_identity():
    record = {
        "id": TARGET,
        "name": "Schermagliatore Fensir",
        "review_status": "pending",
    }
    source = {"logical_source_id": "bgg_2023_it"}
    assert repair._bigby_hp_sparse_retry_eligible(record, source, 134)
    assert not repair._bigby_hp_sparse_retry_eligible(record, source, 135)
    assert not repair._bigby_hp_sparse_retry_eligible(
        {**record, "review_status": "verified"}, source, 134
    )
    assert not repair._bigby_hp_sparse_retry_eligible(
        {**record, "name": "Divoratore Fensir"}, source, 134
    )
    assert not repair._bigby_hp_sparse_retry_eligible(
        {**record, "id": "ref_00000000000000000000000000000000"}, source, 134
    )
    assert not repair._bigby_hp_sparse_retry_eligible(
        record, {"logical_source_id": "mpmm_2022_it"}, 134
    )


def test_fensir_ocr_budget_remains_bounded_and_other_monsters_unchanged():
    assert repair._ocr_budget_seconds(TARGET, "bigby_single_pending_readonly") == 150.0
    assert (
        repair._ocr_budget_seconds(
            "ref_00000000000000000000000000000000",
            "bigby_single_pending_readonly",
        )
        == 60.0
    )
    assert repair.HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS == 15.0

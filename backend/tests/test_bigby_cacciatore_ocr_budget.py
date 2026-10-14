"""Keep Bigby OCR timeout extensions isolated and fail-closed."""

from scripts import repair_monsters_from_source as repair


def test_cacciatore_specific_ocr_budget_does_not_affect_other_monsters():
    cacciatore = "ref_abaf4a8fe2395260991a96729a200351"
    other = "ref_00000000000000000000000000000000"
    assert repair._ocr_budget_seconds(cacciatore, "bigby_single_pending_readonly") == 150.0
    assert repair._ocr_budget_seconds(other, "bigby_single_pending_readonly") == 60.0
    assert repair.HIT_POINTS_MICRO_OCR_TIMEOUT_SECONDS == 15.0


def test_cacciatore_alternate_ocr_modes_are_source_locked():
    select = repair._bigby_cacciatore_scoped_psms
    source = {"logical_source_id": "bgg_2023_it"}
    assert select(source, "Cacciatore Di Baphomet", 124, 3, 4) == (3, 4)
    assert select(source, "Cacciatore Di Baphomet", 125, 3, 4) == (3, 4)
    assert select(source, "Cacciatore Di Baphomet", 123, 3, 4) == (3, 4)
    assert select(source, "Cacciatore", 124, 3, 4) == (3, 4)
    other_source = {"logical_source_id": "erlw_2019_it"}
    assert select(other_source, "Cacciatore Di Baphomet", 124, 3, 4) == (3, 4)


def test_cacciatore_native_pdf_title_crop_is_source_scoped():
    select = repair._bigby_cacciatore_source_crop
    source = {"logical_source_id": "bgg_2023_it"}
    expected = ("right", (0.50, 0.255, 0.965, 0.93))
    assert select(source, "Cacciatore Di Baphomet", 124, True) == expected
    assert select(source, "Cacciatore Di Baphomet", 124, False) is None
    assert select(source, "Cacciatore Di Baphomet", 125, True) is None
    assert select(source, "Cacciatore Di Baphomet", 123, True) is None
    assert select(source, "Cacciatore", 124, True) is None
    assert select({"logical_source_id": "erlw_2019_it"}, "Cacciatore Di Baphomet", 124, True) is None

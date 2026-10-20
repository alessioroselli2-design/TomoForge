"""Fail-closed source page census; never promote to verified by inventory."""
import pytest
from services import mm_census_pages_297_304 as census

def catalog():
    return {
        "logical_source_id": census.SOURCE_ID,
        "physical_filename": census.FILENAME,
        "physical_sha256": census.SOURCE_SHA256,
        "physical_pages": census.SOURCE_PAGE_COUNT,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }

def test_all_eight_original_page_boxes():
    result = census.checked_inventory(catalog())
    assert tuple(result) == tuple(range(297, 305))
    assert sum(map(len, result.values())) == 8
    assert len({n for names in result.values() for n in names}) == 8
    assert census.WRITES == 0
    assert "not_integral_statblock_verified" in census.STATUS

def test_source_mismatch_blocks():
    source = catalog()
    source["physical_sha256"] = "wrong"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        census.checked_inventory(source)

def test_copy_and_no_mutations():
    first = census.checked_inventory(catalog())
    first[297] = ("inventato",)
    assert census.checked_inventory(catalog())[297] == ("Vampiro",)

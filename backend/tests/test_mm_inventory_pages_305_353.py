"""Source-census gates, not automated promotion to verified."""
from copy import deepcopy
import pytest
from services import mm_inventory_pages_305_353 as mm


def catalog():
    return {
        "logical_source_id": mm.SOURCE_ID, "physical_filename": mm.FILENAME,
        "physical_sha256": mm.SHA256, "physical_pages": 353,
        "source_status": "active", "source_role": "authority",
        "authority_class": "licensed_translation", "text_mode": "vision_required",
    }


def test_complete_physical_pages_through_back_cover():
    data = mm.inventory(catalog())
    assert sorted(data) == list(range(305, 354))
    assert not data[351] and not data[352] and not data[353]
    assert all(not data[p] for p in (307, 311, 312, 315))
    assert data[316] == ("Zombi", "Zombi Ogre", "Zombi Beholder")
    assert "Alce" in data[317] and "Arcimago" in data[342]
    assert "Veterano" in data[350]
    assert mm.WRITES == 0 and mm.COMPLETE_STATISTICS_VERIFIED is False


def test_source_wrong_sha_fails_closed():
    c = catalog()
    c["physical_sha256"] = "different"
    with pytest.raises(ValueError, match="original_source_mismatch"):
        mm.inventory(c)


def test_no_mutated_source_or_duplicate():
    original = deepcopy(mm.SOURCE_PAGE_NAMES)
    try:
        mm.SOURCE_PAGE_NAMES[317] = ("Alce", "Alce")
        with pytest.raises(ValueError, match="census_modified"):
            mm.inventory(catalog())
    finally:
        mm.SOURCE_PAGE_NAMES.clear()
        mm.SOURCE_PAGE_NAMES.update(original)


def test_defensive_copy():
    copy = mm.inventory(catalog())
    copy[342] = ("Inventato",)
    assert mm.inventory(catalog())[342] == ("Accolito", "Arcimago")

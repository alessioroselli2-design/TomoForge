"""Protected MM page 46–48 audit, including Demilich math exception."""
from copy import deepcopy

import pytest

from services import mm_pages_46_48_source_review as source


def catalog():
    return {
        "logical_source_id": source.SOURCE_ID,
        "physical_filename": source.FILENAME,
        "physical_sha256": source.SHA256,
        "physical_pages": source.PHYSICAL_PAGES,
        "source_status": "active",
        "source_role": "authority",
        "authority_class": "licensed_translation",
        "text_mode": "vision_required",
    }


@pytest.mark.parametrize(
    ("name", "page", "hp", "gs"),
    [
        ("Cumulo Strisciante", 46, "136 (16d10 + 48)", "5"),
        ("Cuspide Letale", 47, "22 (3d8 + 9)", "1/2"),
    ],
)
def test_original_statblock_identity_and_hp(name, page, hp, gs):
    row = source.audit(name, catalog())
    assert row["source_page"] == page
    assert row["attributes"]["punti_ferita"] == hp
    assert row["attributes"]["grado_sfida"] == gs
    assert row["writes"] == 0


@pytest.mark.parametrize("name", ["Cumulo Strisciante", "Cuspide Letale"])
def test_duplicate_fails_closed(name):
    with pytest.raises(ValueError, match="already_exists"):
        source.audit(name, catalog(), id_collision=True)
    with pytest.raises(ValueError, match="already_exists"):
        source.audit(name, catalog(), existing_monsters=[{"name": name}])


@pytest.mark.parametrize("field,value", [
    ("physical_sha256", "0" * 64),
    ("physical_pages", 150),
    ("source_status", "duplicate"),
    ("physical_filename", "manuale.pdf"),
])
def test_wrong_source_fails_closed(field, value):
    modified = catalog()
    modified[field] = value
    with pytest.raises(ValueError, match="registry"):
        source.audit("Cumulo Strisciante", modified)


@pytest.mark.parametrize("field,value", [
    ("ac", "16 (armatura naturale)"),
    ("hp", "137 (16d10 + 49)"),
    ("gs", "6"),
])
def test_plausible_wrong_numbers_fail_sealed_fields(field, value, monkeypatch):
    changed = deepcopy(source.MONSTERS)
    changed["Cumulo Strisciante"][field] = value
    monkeypatch.setattr(source, "MONSTERS", changed)
    with pytest.raises(ValueError, match="original_source_statblock_fields_changed"):
        source.audit("Cumulo Strisciante", catalog())


def test_demilich_exception_not_promoted_and_source_kept_verbatim():
    problem = source.demilich_original_hp_discrepancy()
    assert problem["source_hit_points"] == "80 (20d4)"
    assert problem["calculated_average"] == 50
    assert problem["status"] == "blocked_original_printed_hp_math"
    assert problem["review_status_not_forced"] is True
    assert problem["writes"] == 0
    with pytest.raises(ValueError, match="not_an_eligible"):
        source.audit("Demilich", catalog())

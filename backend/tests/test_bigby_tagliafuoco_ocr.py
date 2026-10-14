"""Ensure Tagliafuoco p183 layout alternatives cannot affect other records."""

from scripts import repair_monsters_from_source as repair


def test_bigby_tagliafuoco_ocr_psm_is_source_locked():
    choose = repair._bigby_tagliafuoco_source_scoped_psms
    source = {"logical_source_id": "bgg_2023_it"}
    assert choose(source, "Tagliafuoco", 183, 3, 4) == (3, 6)
    assert choose(source, "Tagliafuoco", 182, 3, 4) == (3, 4)
    assert choose(source, "Tagliafuoco", 184, 3, 4) == (3, 4)
    assert choose(source, "Gatto Ghignante", 183, 3, 4) == (3, 4)
    other = {"logical_source_id": "erlw_2019_it"}
    assert choose(other, "Tagliafuoco", 183, 3, 4) == (3, 4)

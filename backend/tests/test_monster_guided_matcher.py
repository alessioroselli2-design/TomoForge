from services.monster_guided_matcher import guided_core_merge
from services.monster_statblock_ocr import agreed_monster_records


def _attributes(
    ac: str = "14 scudo",
    hp: str = "37 (5d10+10)",
    speed: str = "9 m",
) -> dict[str, object]:
    return {
        "classe_armatura": ac,
        "punti_ferita": hp,
        "velocita": speed,
    }


def _record(
    attributes: dict[str, object],
    *,
    name: str = "MOSTRO PROVA",
    normalized_name: str = "mostro prova",
    start_page: int = 12,
) -> dict:
    return {
        "id": "ref_test",
        "reference_type": "monster",
        "name": name,
        "normalized_name": normalized_name,
        "attributes": attributes,
        "review_flags": ["ocr_da_verificare"],
        "source_refs": [
            {
                "filename": "manuale.pdf",
                "page": start_page,
                "logical_page": start_page,
                "language": "it",
            }
        ],
        "start_page": start_page,
        "end_page": start_page,
    }


def _guided_comparison_attributes() -> dict[str, object]:
    return _attributes(
        ac="14 + scudo",
        hp="37 (5d10+10) pf",
        speed="9 m camminare terreno normale",
    )


def test_guided_core_merge_accepts_only_proven_shapes_and_chooses_richer_values():
    primary = _attributes(
        ac="14 scudo",
        hp="37 (5d10+10)",
        speed="9 m",
    )
    comparison = _guided_comparison_attributes()

    merged = guided_core_merge(primary, comparison)

    assert merged == {
        "classe_armatura": "14 + scudo",
        "punti_ferita": "37 (5d10+10) pf",
        "velocita": "9 m camminare terreno normale",
    }


def test_guided_core_merge_fails_closed_when_speed_has_only_two_extra_tokens():
    primary = _attributes()
    comparison = _attributes(
        ac="14 + scudo",
        hp="37 (5d10+10) pf",
        speed="9 m terreno normale",
    )

    assert guided_core_merge(primary, comparison) is None


def test_guided_core_merge_fails_closed_on_semantic_numeric_disagreement():
    primary = _attributes()
    comparison = _attributes(
        ac="14 + scudo",
        hp="38 (5d10+10) pf",
        speed="9 m camminare terreno normale",
    )

    assert guided_core_merge(primary, comparison) is None


def test_agreed_records_use_guided_merge_but_keep_manual_review_and_primary_provenance():
    primary = _record(
        _attributes(
            ac="14 scudo",
            hp="37 (5d10+10)",
            speed="9 m",
        )
    )
    comparison = _record(_guided_comparison_attributes())

    result = agreed_monster_records([primary], [comparison])

    assert len(result) == 1
    merged = result[0]
    assert merged["attributes"]["classe_armatura"] == "14 + scudo"
    assert merged["attributes"]["punti_ferita"] == "37 (5d10+10) pf"
    assert merged["attributes"]["velocita"] == "9 m camminare terreno normale"
    assert merged["attributes"]["ocr_independent_agreement"] is True
    assert merged["attributes"]["ocr_guided_core_merge"] is True
    assert "ocr_independent_agreement" in merged["review_flags"]
    assert "ocr_guided_core_merge" in merged["review_flags"]
    assert "ocr_da_verificare" in merged["review_flags"]
    assert merged["source_refs"] == primary["source_refs"]


def test_agreed_records_accept_one_unique_same_page_name_containment_via_guided_path():
    primary = _record(_attributes())
    comparison = _record(
        _guided_comparison_attributes(),
        name="MOSTRO PROVA ALFA",
        normalized_name="mostro prova alfa",
    )

    result = agreed_monster_records([primary], [comparison])

    assert len(result) == 1
    merged = result[0]
    assert merged["name"] == primary["name"]
    assert merged["normalized_name"] == primary["normalized_name"]
    assert merged["source_refs"] == primary["source_refs"]
    assert merged["attributes"]["ocr_independent_agreement"] is True
    assert merged["attributes"]["ocr_guided_core_merge"] is True
    assert "ocr_da_verificare" in merged["review_flags"]
    assert "ocr_guided_core_merge" in merged["review_flags"]


def test_abishai_rosso_clean_same_page_containment_is_independently_agreed():
    clean_core = _attributes(
        ac="18 (armatura naturale)",
        hp="289 (34d8 + 136)",
        speed="9 m, volare 12 m",
    )
    primary = _record(
        clean_core,
        name="ABISHAI ROSSO",
        normalized_name="abishai rosso",
        start_page=43,
    )
    comparison = _record(
        clean_core,
        name="ABISHAI ROSSO GRANDE",
        normalized_name="abishai rosso grande",
        start_page=43,
    )

    # An all-clean merge remains unavailable to generic callers; only the
    # independently paired, unique same-page containment path may enable it.
    assert guided_core_merge(clean_core, clean_core) is None

    result = agreed_monster_records([primary], [comparison])

    assert len(result) == 1
    merged = result[0]
    assert merged["name"] == "ABISHAI ROSSO"
    assert merged["attributes"]["ocr_independent_agreement"] is True
    assert merged["attributes"]["ocr_guided_core_merge"] is True
    assert "ocr_independent_agreement" in merged["review_flags"]
    assert "ocr_guided_core_merge" in merged["review_flags"]


def test_agreed_records_reject_ambiguous_same_page_name_containment_candidates():
    primary = _record(_attributes())
    comparison_alpha = _record(
        _guided_comparison_attributes(),
        name="MOSTRO PROVA ALFA",
        normalized_name="mostro prova alfa",
    )
    comparison_beta = _record(
        _guided_comparison_attributes(),
        name="MOSTRO PROVA BETA",
        normalized_name="mostro prova beta",
    )

    assert agreed_monster_records([primary], [comparison_alpha, comparison_beta]) == []


def test_agreed_records_reject_name_containment_on_different_page():
    primary = _record(_attributes())
    comparison = _record(
        _guided_comparison_attributes(),
        name="MOSTRO PROVA ALFA",
        normalized_name="mostro prova alfa",
        start_page=13,
    )

    assert agreed_monster_records([primary], [comparison]) == []


def test_agreed_records_still_reject_unknown_residual_shape():
    primary = _record(_attributes())
    comparison = _record(
        _attributes(
            ac="14 scudo diverso",
            hp="37 (5d10+10) pf",
            speed="9 m camminare terreno normale",
        )
    )

    assert agreed_monster_records([primary], [comparison]) == []

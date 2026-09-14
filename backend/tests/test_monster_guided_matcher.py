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


def _record(attributes: dict[str, object]) -> dict:
    return {
        "id": "ref_test",
        "reference_type": "monster",
        "name": "MOSTRO PROVA",
        "normalized_name": "mostro prova",
        "attributes": attributes,
        "review_flags": ["ocr_da_verificare"],
        "source_refs": [
            {
                "filename": "manuale.pdf",
                "page": 12,
                "logical_page": 12,
                "language": "it",
            }
        ],
        "start_page": 12,
        "end_page": 12,
    }


def test_guided_core_merge_accepts_only_proven_shapes_and_chooses_richer_values():
    primary = _attributes(
        ac="14 scudo",
        hp="37 (5d10+10)",
        speed="9 m",
    )
    comparison = _attributes(
        ac="14 + scudo",
        hp="37 (5d10+10) pf",
        speed="9 m camminare terreno normale",
    )

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
    comparison = _record(
        _attributes(
            ac="14 + scudo",
            hp="37 (5d10+10) pf",
            speed="9 m camminare terreno normale",
        )
    )

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

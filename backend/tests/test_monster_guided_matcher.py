from services.monster_guided_matcher import guided_core_merge
from services.monster_name_diagnostics import compact_name_bounded_edit_match
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
        name="ABISHAI ROSSON",
        normalized_name="abishai rosson",
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


def test_exact_same_page_name_accepts_all_clean_deterministic_core_alignment():
    primary = _record(
        _attributes(
            ac="18 (armatura naturale)",
            hp="289 (34d8 + 136)",
            speed="9 metri, volare 12 m",
        ),
        name="RAK TULKHESH",
        normalized_name="rak tulkhesh",
        start_page=77,
    )
    comparison = _record(
        _attributes(
            ac="18 [armatura naturale]",
            hp="289 [34 d 8+136]",
            speed="9 m; volare 12 m",
        ),
        name="Rak Tulkhesh",
        normalized_name="rak tulkhesh",
        start_page=77,
    )

    result = agreed_monster_records([primary], [comparison])

    assert len(result) == 1
    assert result[0]["attributes"]["ocr_independent_agreement"] is True
    assert result[0]["attributes"]["ocr_guided_core_merge"] is True
    assert "ocr_da_verificare" in result[0]["review_flags"]


def test_clean_exact_name_alignment_remains_same_page_and_unique():
    primary = _record(_attributes(), name="BAEL", normalized_name="bael")
    comparison = _record(
        _attributes(ac="14 (scudo)", hp="37 [5 d 10+10]", speed="9 metri"),
        name="Bael",
        normalized_name="bael",
        start_page=13,
    )

    assert agreed_monster_records([primary], [comparison]) == []
    same_page = {**comparison, "start_page": 12}
    assert agreed_monster_records([primary], [same_page, dict(same_page)]) == []


def test_unique_same_page_single_edit_name_requires_clean_core_agreement():
    core = _attributes(ac="17", hp="30 (4d10 + 8)", speed="9 m")
    primary = _record(core, name="BAE1", normalized_name="bae1")
    comparison = _record(core, name="BAEL", normalized_name="bael")

    result = agreed_monster_records([primary], [comparison])

    assert len(result) == 1
    assert result[0]["attributes"]["ocr_independent_agreement"] is True
    mismatched = _record(
        _attributes(ac="18", hp="30 (4d10 + 8)", speed="9 m"),
        name="BAEL",
        normalized_name="bael",
    )
    assert agreed_monster_records([primary], [mismatched]) == []


def test_unique_same_page_ocr_boundary_name_requires_clean_core_agreement():
    core = _attributes(ac="13", hp="30 (4d10 + 8)", speed="3 m, volare 24 m")
    primary = _record(
        core,
        name="QUETZALCOATLUS",
        normalized_name="quetzalcoatlus",
    )
    comparison = _record(
        core,
        name="QUETZALCOAT|LUS",
        normalized_name="quetzalcoat lus",
    )

    assert len(agreed_monster_records([primary], [comparison])) == 1


def test_same_page_fuzzy_name_pair_must_be_unique():
    core = _attributes()
    primary = _record(core, name="RANA", normalized_name="rana")
    comparison_one = _record(core, name="RANAE", normalized_name="ranae")
    comparison_two = _record(core, name="RAMA", normalized_name="rama")

    assert agreed_monster_records([primary], [comparison_one, comparison_two]) == []


def test_long_name_allows_three_ocr_edits_but_shorter_name_does_not():
    assert compact_name_bounded_edit_match("quetzalcoatlus", "xuetxalcoatluz")
    assert not compact_name_bounded_edit_match("abcdefghi", "abcxefgzy")


def test_ambiguous_fuzzy_names_select_only_unique_clean_core_pair():
    clean_core = _attributes(ac="17", hp="93 (11d10 + 33)", speed="9 m")
    primary = _record(
        clean_core,
        name="MIRMIDONE ELEMENTALE",
        normalized_name="mirmidone elementale",
    )
    clean_candidate = _record(
        clean_core,
        name="MIRMID0NE ELEMENTA1E",
        normalized_name="mirmid0ne elementa1e",
    )
    debris_candidate = _record(
        _attributes(ac="12", hp="22 (4d8 + 4)", speed="6 m"),
        name="MIRMIDONE ELEMENYALE",
        normalized_name="mirmidone elemenyale",
    )

    result = agreed_monster_records([primary], [clean_candidate, debris_candidate])

    assert len(result) == 1
    assert result[0]["attributes"]["ocr_independent_agreement"] is True


def test_ambiguous_fuzzy_names_do_not_resolve_on_armor_class_alone():
    primary = _record(
        _attributes(ac="17", hp="93 (11d10 + 33)", speed="9 m"),
        name="MIRMIDONE ELEMENTALE",
        normalized_name="mirmidone elementale",
    )
    first = _record(
        _attributes(ac="17", hp="94 (11d10 + 33)", speed="9 m"),
        name="MIRMID0NE ELEMENTA1E",
        normalized_name="mirmid0ne elementa1e",
    )
    second = _record(
        _attributes(ac="17", hp="93 (11d10 + 33)", speed="12 m"),
        name="MIRMIDONE ELEMENYALE",
        normalized_name="mirmidone elemenyale",
    )

    assert agreed_monster_records([primary], [first, second]) == []


def test_ambiguous_fuzzy_names_remain_blocked_with_two_clean_core_pairs():
    core = _attributes(ac="17", hp="93 (11d10 + 33)", speed="9 m")
    primary = _record(
        core,
        name="MIRMIDONE ELEMENTALE",
        normalized_name="mirmidone elementale",
    )
    first = _record(
        core,
        name="MIRMID0NE ELEMENTA1E",
        normalized_name="mirmid0ne elementa1e",
    )
    second = _record(
        core,
        name="MIRMIDONE ELEMENYALE",
        normalized_name="mirmidone elemenyale",
    )

    assert agreed_monster_records([primary], [first, second]) == []


def test_adjacent_page_alignment_requires_multi_token_name_and_clean_core():
    core = _attributes(ac="16", hp="136 (16d10 + 48)", speed="9 m")
    primary = _record(
        core,
        name="PROGENIE STELLARE HULK",
        normalized_name="progenie stellare hulk",
        start_page=19,
    )
    comparison = _record(
        core,
        name="PROGENIE STELLARE HULK",
        normalized_name="progenie stellare hulk",
        start_page=20,
    )

    result = agreed_monster_records([primary], [comparison])

    assert len(result) == 1
    assert result[0]["attributes"]["ocr_clean_deterministic_core_agreement"] is True
    single_primary = _record(core, name="RANA", normalized_name="rana", start_page=19)
    single_comparison = _record(
        core, name="RANA", normalized_name="rana", start_page=20
    )
    assert agreed_monster_records([single_primary], [single_comparison]) == []


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

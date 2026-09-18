from scripts.repair_monsters_from_source import (
    EXPECTED_HEALTHY22_COUNT,
    HEALTHY22_TARGETS,
    OCR_REVIEW_FLAG,
    REPAIR_FLAG,
    RepairBlocked,
    _layout_ocr_settings,
    _layout_profile,
    _layout_segments,
    build_repair_proposal,
    resolve_source,
    select_corrupted_name_monsters,
    select_failed_monsters,
    select_healthy22_targets,
)


def _monster(name, ac, hp, *, record_id="m1", flags=None):
    return {
        "id": record_id,
        "name": name,
        "reference_type": "monster",
        "attributes": {
            "classe_armatura": ac,
            "punti_ferita": hp,
            "velocita": "9 m",
        },
        "review_flags": list(flags or []),
        "review_status": "verified",
        "source_refs": [{"filename": "Mostri del multiverso 201-294.pdf", "page": 85}],
        "canonical_id": None,
    }


def test_select_failed_monsters_keeps_real_corruption_and_excludes_heading():
    records = [
        _monster("Zuggtmoy", "1", "304 (32dl0 + 1 28)", record_id="bad"),
        _monster("Yuan-Ti Guardia Della Stirpe", "14", "45 (7d8 + 14)", record_id="good"),
        _monster("Capitolo 2 I Bestiario", "1", "20 (3d8 + 6)", record_id="heading"),
    ]

    selected = select_failed_monsters(records)
    assert [row["id"] for row in selected] == ["bad"]


def test_select_failed_monsters_isolates_corrupted_legacy_names():
    records = [
        _monster("Graz'Zt", "20", "346 (33dl0 + 1 65)", record_id="real"),
        _monster("M:::,, $S$", "1", "20 (3d8 + 6)", record_id="symbols"),
        _monster(
            "Fo R M E P R E S C E Lte D E L L1A Rc I D R U I Do",
            "14",
            "1",
            record_id="letterspaced",
        ),
    ]

    selected = select_failed_monsters(records)
    isolated = select_corrupted_name_monsters(records)

    assert [row["id"] for row in selected] == ["real"]
    assert {row["id"] for row in isolated} == {"symbols", "letterspaced"}


def test_resolve_source_accepts_active_authority():
    record = _monster("Zuggtmoy", "1", "304 (32dl0 + 1 28)")
    active_sources = [{
        "physical_filename": "Mostri del multiverso 201-294.pdf",
        "logical_source_id": "mpmm_2022_it",
        "source_role": "authority",
        "source_status": "active",
        "physical_pages": 94,
    }]

    source, ref = resolve_source(record, active_sources)
    assert source["source_role"] == "authority"
    assert ref["page"] == 85


def test_resolve_source_blocks_extraction_aid_alias():
    record = {
        **_monster("Legacy Spanish Monster", "1", "20 (3d8 + 6)"),
        "source_refs": [{
            "filename": "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf",
            "page": 915,
        }],
    }
    active_sources = [{
        "physical_filename": "731764731-D-D-Manual-Del-Jugador-5e(1).pdf",
        "source_role": "extraction_aid",
        "source_status": "active",
        "physical_pages": 1018,
    }]

    try:
        resolve_source(record, active_sources)
    except RepairBlocked as exc:
        assert exc.reason == "source_ineligible_role"
    else:
        raise AssertionError("extraction_aid must be blocked")


def test_mpmm_layout_profile_splits_columns_and_uses_independent_ocr_modes():
    source = {"logical_source_id": "mpmm_2022_it"}

    assert _layout_profile(source) == "two_column_vertical"
    assert _layout_segments(source) == (
        ("left", (0.0, 0.0, 0.5, 1.0)),
        ("right", (0.5, 0.0, 1.0, 1.0)),
    )
    assert _layout_ocr_settings(
        source,
        dpi=220,
        psm=6,
        comparison_psm=4,
    ) == (300, 3, 4)


def test_non_two_column_source_keeps_full_page_settings():
    source = {"logical_source_id": "tce_2020_it"}

    assert _layout_profile(source) == "full_page"
    assert _layout_segments(source) == (
        ("full", (0.0, 0.0, 1.0, 1.0)),
    )
    assert _layout_ocr_settings(
        source,
        dpi=220,
        psm=6,
        comparison_psm=4,
    ) == (220, 6, 4)


def test_build_repair_proposal_replaces_only_core_and_forces_pending_review():
    legacy = _monster(
        "Zuggtmoy",
        "1",
        "304 (32dl0 + 1 28)",
        flags=["CA_out_of_bounds", "HP_format_error", "legacy_note"],
    )
    legacy["attributes"]["grado_sfida"] = "23"
    candidate = {
        "name": "Zuggtmoy",
        "reference_type": "monster",
        "attributes": {
            "classe_armatura": "18 (armatura naturale)",
            "punti_ferita": "304 (32d10 + 128)",
            "velocita": "9 m",
            "grado_sfida": "999",
        },
    }

    proposal = build_repair_proposal(legacy, candidate)

    assert proposal["attributes"]["classe_armatura"] == "18 (armatura naturale)"
    assert proposal["attributes"]["punti_ferita"] == "304 (32d10 + 128)"
    assert proposal["attributes"]["velocita"] == "9 m"
    assert proposal["attributes"]["grado_sfida"] == "23"
    assert proposal["review_status"] == "pending"
    assert "CA_out_of_bounds" not in proposal["review_flags"]
    assert "HP_format_error" not in proposal["review_flags"]
    assert "legacy_note" in proposal["review_flags"]
    assert OCR_REVIEW_FLAG in proposal["review_flags"]
    assert REPAIR_FLAG in proposal["review_flags"]


def test_build_repair_proposal_rejects_still_corrupt_candidate():
    legacy = _monster("Zuggtmoy", "1", "304 (32dl0 + 1 28)")
    candidate = {
        "name": "Zuggtmoy",
        "reference_type": "monster",
        "attributes": {
            "classe_armatura": "1",
            "punti_ferita": "304 (32dl0 + 128)",
            "velocita": "9 m",
        },
    }

    try:
        build_repair_proposal(legacy, candidate)
    except RepairBlocked as exc:
        assert exc.reason == "repaired_candidate_failed_gates"
    else:
        raise AssertionError("corrupt candidate must be rejected")


def test_build_repair_proposal_rejects_corrupted_candidate_name():
    legacy = _monster("Zuggtmoy", "1", "304 (32dl0 + 1 28)")
    candidate = {
        "name": "M:::,, $S$",
        "reference_type": "monster",
        "attributes": {
            "classe_armatura": "18",
            "punti_ferita": "304 (32d10 + 128)",
            "velocita": "9 m",
        },
    }

    try:
        build_repair_proposal(legacy, candidate)
    except RepairBlocked as exc:
        assert exc.reason == "repaired_candidate_corrupted_name"
    else:
        raise AssertionError("candidate with corrupt identity must be rejected")



def test_healthy22_sealed_target_set_resolves_exact_reviewed_batch():
    records = []
    for expected in HEALTHY22_TARGETS:
        row = _monster(
            expected["name"],
            "1",
            "20 (3d8 + 6)",
            record_id=expected["id"],
        )
        row["source_text_checksum"] = expected["source_text_checksum"]
        records.append(row)

    selected = select_healthy22_targets(records)

    assert len(selected) == EXPECTED_HEALTHY22_COUNT == 22
    assert {row["id"] for row in selected} == {
        expected["id"] for expected in HEALTHY22_TARGETS
    }


def test_healthy22_sealed_target_set_rejects_preexisting_review_flags():
    records = []
    for expected in HEALTHY22_TARGETS:
        row = _monster(
            expected["name"],
            "1",
            "20 (3d8 + 6)",
            record_id=expected["id"],
        )
        row["source_text_checksum"] = expected["source_text_checksum"]
        records.append(row)

    records[0]["review_flags"] = ["unexpected"]

    try:
        select_healthy22_targets(records)
    except RuntimeError as exc:
        assert "review flags" in str(exc)
    else:
        raise AssertionError("sealed healthy22 batch must reject pre-existing flags")

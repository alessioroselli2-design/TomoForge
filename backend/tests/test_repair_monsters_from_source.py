from scripts.repair_monsters_from_source import (
    OCR_REVIEW_FLAG,
    REPAIR_FLAG,
    RepairBlocked,
    build_repair_proposal,
    resolve_source,
    select_failed_monsters,
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


def test_resolve_source_accepts_active_authority():
    record = _monster("Zuggtmoy", "1", "304 (32dl0 + 1 28)")
    active_sources = [{
        "physical_filename": "Mostri del multiverso 201-294.pdf",
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
            "grado_sfida": "999",  # must not overwrite non-core legacy fields
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

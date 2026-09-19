import asyncio
from datetime import datetime
from subprocess import CompletedProcess
from unittest.mock import patch

import fitz

from scripts.repair_monsters_from_source import (
    BIGBY19_TARGETS,
    BIGBY4_TARGETS,
    EXPECTED_BIGBY19_COUNT,
    EXPECTED_BIGBY4_COUNT,
    EXPECTED_HEALTHY22_COUNT,
    HEALTHY22_TARGETS,
    OCR_REVIEW_FLAG,
    REPAIR_FLAG,
    RepairBlocked,
    _apply_update,
    _layout_ocr_settings,
    _layout_profile,
    _layout_segments,
    _micro_ocr_hit_points_line,
    build_repair_proposal,
    resolve_source,
    select_bigby19_targets,
    select_bigby4_targets,
    select_corrupted_name_monsters,
    select_failed_monsters,
    select_healthy22_targets,
)


def test_hp_micro_ocr_contrast_crop_and_character_whitelist(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t20\t50\t45\t20\t95\tPunti\n"
        "5\t1\t1\t1\t1\t2\t72\t50\t50\t20\t95\tFerita\n"
        "5\t1\t1\t1\t1\t3\t135\t50\t30\t20\t90\t127\n"
        "5\t1\t1\t1\t1\t4\t175\t50\t70\t20\t80\t(15d12\n"
        "5\t1\t1\t1\t1\t5\t250\t50\t35\t20\t90\t+30)\n"
    )
    responses = [
        CompletedProcess([], 0, stdout=tsv, stderr=""),
        CompletedProcess([], 0, stdout="127 (15d12 + 30)\n", stderr=""),
    ]

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        side_effect=responses,
    ) as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Classe Armatura 17\nPunti Ferita 127 (15412 + 30)\nVelocità 3 m",
        )

    assert "Punti Ferita 127 (15d12 + 30)" in result
    assert len(run.call_args_list) == 2
    assert "tsv" in run.call_args_list[0].args[0]
    micro_command = run.call_args_list[1].args[0]
    assert "--psm" in micro_command
    assert "7" in micro_command
    assert "tessedit_char_whitelist=0123456789d+() " in micro_command


def test_hp_micro_ocr_does_not_touch_non_hp_text(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 100, 100), False)
    image.clear_with(255)
    image.save(image_path)

    with patch("scripts.repair_monsters_from_source.subprocess.run") as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Classe Armatura 17\nVelocità 3 m",
        )

    assert result == "Classe Armatura 17\nVelocità 3 m"
    run.assert_not_called()


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


def test_bigby_layout_profile_splits_columns_and_uses_independent_ocr_modes():
    source = {"logical_source_id": "bgg_2023_it"}

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



class _UpdateResult:
    matched_count = 1


class _SerializableUpdateCollection:
    def __init__(self, legacy):
        self.row = dict(legacy)
        self.last_payload = None

    async def update_one(self, query, update):
        assert query["id"] == self.row["id"]
        self.last_payload = dict(update["$set"])
        # Regression guard: this mirrors JSON serialization requirements.
        assert isinstance(self.last_payload["updated_at"], str)
        datetime.fromisoformat(self.last_payload["updated_at"])
        self.row.update(self.last_payload)
        return _UpdateResult()

    async def find_one(self, query):
        assert query["id"] == self.row["id"]
        return dict(self.row)


def test_apply_update_serializes_updated_at_as_utc_iso_string():
    legacy = _monster(
        "Zuggtmoy",
        "1",
        "304 (32dl0 + 1 28)",
    )
    legacy["source_text_checksum"] = "checksum"
    legacy["updated_at"] = "2026-09-04T05:00:00+00:00"
    proposal = {
        "attributes": {
            **legacy["attributes"],
            "classe_armatura": "18 (armatura naturale)",
            "punti_ferita": "304 (32d10 + 128)",
            "velocita": "9 m",
        },
        "review_flags": [OCR_REVIEW_FLAG, REPAIR_FLAG],
        "review_status": "pending",
    }
    collection = _SerializableUpdateCollection(legacy)

    asyncio.run(_apply_update(collection, legacy, proposal))

    timestamp = collection.last_payload["updated_at"]
    parsed = datetime.fromisoformat(timestamp)
    assert parsed.utcoffset().total_seconds() == 0



def test_bigby19_sealed_target_set_resolves_exact_reviewed_batch():
    records = []
    for expected in BIGBY19_TARGETS:
        row = _monster(
            expected["name"],
            "1",
            "20 (3d8 + 6)",
            record_id=expected["id"],
        )
        row["source_text_checksum"] = expected["source_text_checksum"]
        records.append(row)

    selected = select_bigby19_targets(records)

    assert len(selected) == EXPECTED_BIGBY19_COUNT == 19
    assert {row["id"] for row in selected} == {
        expected["id"] for expected in BIGBY19_TARGETS
    }



def test_bigby4_sealed_target_set_resolves_exact_approved_batch():
    records = []
    for expected in BIGBY4_TARGETS:
        row = _monster(
            expected["name"],
            "1",
            "20 (3d8 + 6)",
            record_id=expected["id"],
        )
        row["source_text_checksum"] = expected["source_text_checksum"]
        records.append(row)

    selected = select_bigby4_targets(records)

    assert len(selected) == EXPECTED_BIGBY4_COUNT == 4
    assert {row["id"] for row in selected} == {
        expected["id"] for expected in BIGBY4_TARGETS
    }


def test_bigby4_sealed_target_set_rejects_review_flag_drift():
    records = []
    for expected in BIGBY4_TARGETS:
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
        select_bigby4_targets(records)
    except RuntimeError as exc:
        assert "review flags" in str(exc)
    else:
        raise AssertionError("sealed bigby4 batch must reject pre-existing flags")

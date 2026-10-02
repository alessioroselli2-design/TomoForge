import asyncio
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch
from types import SimpleNamespace

import fitz
import pytest
from scripts import repair_monsters_from_source as repair


from scripts.repair_monsters_from_source import (
    BIGBY19_TARGETS,
    RESIDUAL_BATCH_TARGETS,
    EXPECTED_RESIDUAL_BATCH_COUNTS,
    EXPECTED_RESIDUAL_BATCH_IDS_MD5,
    BIGBY4_TARGETS,
    APPROVED5_TARGETS,
    OBLEX1_TARGETS,
    READY6_TARGETS,
    EXPECTED_BIGBY19_COUNT,
    EXPECTED_BIGBY4_COUNT,
    EXPECTED_HEALTHY22_COUNT,
    EXPECTED_APPROVED1_COUNT,
    EXPECTED_APPROVED5_COUNT,
    EXPECTED_OBLEX1_COUNT,
    EXPECTED_READY6_COUNT,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED20_COUNT,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED20_IDS_MD5,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED16_COUNT,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED16_IDS_MD5,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED12_COUNT,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED12_IDS_MD5,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED11_COUNT,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED11_IDS_MD5,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED9_COUNT,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED9_IDS_MD5,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED8_COUNT,
    EXPECTED_PLAYERS_HANDBOOK_BLOCKED8_IDS_MD5,
    HIT_POINTS_FULL_SPECTRUM_CONTRASTS,
    HIT_POINTS_WHITELIST,
    OCR_GLOBAL_TIMEOUT_BY_RECORD_ID,
    PHB_QUALITY_GATE_PRE_OTSU_TARGETS,
    PHB_SPARSE_BOTTOM_FRACTION_BY_NAME,
    PHB_SPARSE_CONTINUATION_CLIPS,
    PHB_SPARSE_QUALITY_CONTEXT_TARGETS,
    PLAYERS_HANDBOOK_HP_SPARSE_RETRY_IDS,
    PLAYERS_HANDBOOK_TIMEOUT4_NAMES,
    TARGET_SEGMENT_BY_NAME,
    HEALTHY22_TARGETS,
    APPROVED1_TARGETS,
    OCR_REVIEW_FLAG,
    REPAIR_FLAG,
    RepairBlocked,
    SourcePdfCache,
    _agreed_target_candidate,
    _apply_update,
    _background_luminance_stats,
    _candidate_matches_target,
    _dilate_dark_pixels,
    _erode_dark_pixels,
    _layout_ocr_settings,
    _layout_profile,
    _layout_segments,
    _local_adaptive_inverted_samples,
    _local_otsu_inverted_samples,
    _remove_isolated_foreground_noise,
    _remaining_global_ocr_budget,
    _repair_numeric_dice_separator_confusion,
    _micro_ocr_hit_points_line,
    _micro_target_line_matches,
    _otsu_inverted_samples,
    _phb_quality_pre_otsu_clip,
    _phb_sparse_uses_quality_pre_otsu,
    _phb_sparse_comparison_uses_adaptive_source,
    _phb_sparse_comparison_psm,
    _restore_cavallo_sparse_title_from_anchor,
    _sample_variance,
    _should_retry_dynamic_layout,
    _sparse_anchor_crop_fractions,
    _sparse_anchor_matches,
    _verified_core_agreement,
    build_repair_proposal,
    resolve_source,
    select_bigby19_targets,
    select_residual_batch_targets,
    select_bigby4_targets,
    select_corrupted_name_monsters,
    select_failed_monsters,
    select_healthy22_targets,
    select_approved1_targets,
    select_approved5_targets,
    select_oblex1_targets,
    select_ready6_targets,
    select_players_handbook_blocked20_targets,
    select_players_handbook_blocked16_targets,
    select_players_handbook_blocked12_targets,
    select_players_handbook_blocked11_targets,
    select_players_handbook_blocked9_targets,
    select_players_handbook_blocked8_targets,
)


def test_players_handbook_blocked20_is_sealed_from_full_phb_batch():
    from scripts.repair_monsters_from_source import PLAYERS_HANDBOOK_TARGETS

    records = []
    for expected in PLAYERS_HANDBOOK_TARGETS:
        status = expected["status"]
        records.append(
            {
                "id": expected["id"],
                "name": expected["name"],
                "reference_type": "monster",
                "review_status": status,
                "review_flags": (
                    [OCR_REVIEW_FLAG]
                    if status == "verified"
                    else [OCR_REVIEW_FLAG, REPAIR_FLAG]
                ),
                "source_key": "Manuale_del_giocatore__1787259882002.pdf",
                "source_refs": [
                    {
                        "filename": "Manuale_del_giocatore__1787259882002.pdf",
                        "page": 304,
                    }
                ],
                "canonical_id": None,
            }
        )

    selected = select_players_handbook_blocked20_targets(records)

    assert len(selected) == EXPECTED_PLAYERS_HANDBOOK_BLOCKED20_COUNT == 20
    fingerprint = hashlib.md5(
        ",".join(sorted(str(row["id"]) for row in selected)).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()
    assert fingerprint == EXPECTED_PLAYERS_HANDBOOK_BLOCKED20_IDS_MD5
    assert "Aquila Gigante" not in {row["name"] for row in selected}
    assert "Coccodrillo" not in {row["name"] for row in selected}
    assert "Cavallo Da Galoppo" in {row["name"] for row in selected}
    assert "Topo" in {row["name"] for row in selected}


def test_players_handbook_blocked16_is_sealed_from_full_phb_batch():
    from scripts.repair_monsters_from_source import PLAYERS_HANDBOOK_TARGETS

    records = []
    for expected in PLAYERS_HANDBOOK_TARGETS:
        status = expected["status"]
        records.append(
            {
                "id": expected["id"],
                "name": expected["name"],
                "reference_type": "monster",
                "review_status": status,
                "review_flags": (
                    [OCR_REVIEW_FLAG]
                    if status == "verified"
                    else [OCR_REVIEW_FLAG, REPAIR_FLAG]
                ),
                "source_key": "Manuale_del_giocatore__1787259882002.pdf",
                "source_refs": [
                    {
                        "filename": "Manuale_del_giocatore__1787259882002.pdf",
                        "page": 304,
                    }
                ],
                "canonical_id": None,
            }
        )

    selected = select_players_handbook_blocked16_targets(records)

    assert len(selected) == EXPECTED_PLAYERS_HANDBOOK_BLOCKED16_COUNT == 16
    fingerprint = hashlib.md5(
        ",".join(sorted(str(row["id"]) for row in selected)).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()
    assert fingerprint == EXPECTED_PLAYERS_HANDBOOK_BLOCKED16_IDS_MD5
    assert "Cavallo Da Galoppo" not in {row["name"] for row in selected}
    assert "Gatto" not in {row["name"] for row in selected}
    assert "Ragno Gigante" not in {row["name"] for row in selected}
    assert "Serpente Stritolatore" not in {row["name"] for row in selected}
    assert "Cinghiale" in {row["name"] for row in selected}
    assert "Imp" in {row["name"] for row in selected}


def test_hp_micro_ocr_repeated_title_matches_can_converge_on_one_hp_line(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 300), False)
    image.clear_with(255)
    image.save(image_path)
    page_text = (
        "Mastino\n"
        "Mastino\n"
        "Bestia media\n"
        "Classe Armatura 12\n"
        "Punti Ferita 5 (1d8 + 1)\n"
        "Velocità 12 m\n"
    )

    with patch("scripts.repair_monsters_from_source.subprocess.run") as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            page_text,
            "Mastino",
        )

    assert result == page_text
    run.assert_not_called()


def test_players_handbook_blocked12_is_sealed_from_full_phb_batch():
    from scripts.repair_monsters_from_source import PLAYERS_HANDBOOK_TARGETS

    records = []
    for expected in PLAYERS_HANDBOOK_TARGETS:
        status = expected["status"]
        records.append(
            {
                "id": expected["id"],
                "name": expected["name"],
                "reference_type": "monster",
                "review_status": status,
                "review_flags": (
                    [OCR_REVIEW_FLAG]
                    if status == "verified"
                    else [OCR_REVIEW_FLAG, REPAIR_FLAG]
                ),
                "source_key": "Manuale_del_giocatore__1787259882002.pdf",
                "source_refs": [
                    {
                        "filename": "Manuale_del_giocatore__1787259882002.pdf",
                        "page": 304,
                    }
                ],
                "canonical_id": None,
            }
        )

    selected = select_players_handbook_blocked12_targets(records)

    assert len(selected) == EXPECTED_PLAYERS_HANDBOOK_BLOCKED12_COUNT == 12
    fingerprint = hashlib.md5(
        ",".join(sorted(str(row["id"]) for row in selected)).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()
    assert fingerprint == EXPECTED_PLAYERS_HANDBOOK_BLOCKED12_IDS_MD5
    selected_names = {row["name"] for row in selected}
    assert "Corvo" not in selected_names
    assert "Imp" not in selected_names
    assert "Mastino" not in selected_names
    assert "Topo" not in selected_names
    assert "Cavallo Da Guerra" in selected_names
    assert "Rana" in selected_names


def test_players_handbook_blocked11_is_sealed_after_quasit_passes():
    from scripts.repair_monsters_from_source import PLAYERS_HANDBOOK_TARGETS

    records = []
    for expected in PLAYERS_HANDBOOK_TARGETS:
        status = expected["status"]
        records.append(
            {
                "id": expected["id"],
                "name": expected["name"],
                "reference_type": "monster",
                "review_status": status,
                "review_flags": (
                    [OCR_REVIEW_FLAG]
                    if status == "verified"
                    else [OCR_REVIEW_FLAG, REPAIR_FLAG]
                ),
                "source_key": "Manuale_del_giocatore__1787259882002.pdf",
                "source_refs": [
                    {
                        "filename": "Manuale_del_giocatore__1787259882002.pdf",
                        "page": 304,
                    }
                ],
                "canonical_id": None,
            }
        )

    selected = select_players_handbook_blocked11_targets(records)

    assert len(selected) == EXPECTED_PLAYERS_HANDBOOK_BLOCKED11_COUNT == 11
    fingerprint = hashlib.md5(
        ",".join(sorted(str(row["id"]) for row in selected)).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()
    assert fingerprint == EXPECTED_PLAYERS_HANDBOOK_BLOCKED11_IDS_MD5
    selected_names = {row["name"] for row in selected}
    assert "Quasit" not in selected_names
    assert "Rana" in selected_names
    assert "Cinghiale" in selected_names
    assert "Orso Bruno" in selected_names


def test_players_handbook_blocked9_is_sealed_after_run107_passes():
    from scripts.repair_monsters_from_source import PLAYERS_HANDBOOK_TARGETS

    records = []
    for expected in PLAYERS_HANDBOOK_TARGETS:
        status = expected["status"]
        records.append(
            {
                "id": expected["id"],
                "name": expected["name"],
                "reference_type": "monster",
                "review_status": status,
                "review_flags": (
                    [OCR_REVIEW_FLAG]
                    if status == "verified"
                    else [OCR_REVIEW_FLAG, REPAIR_FLAG]
                ),
                "source_key": "Manuale_del_giocatore__1787259882002.pdf",
                "source_refs": [
                    {
                        "filename": "Manuale_del_giocatore__1787259882002.pdf",
                        "page": 304,
                    }
                ],
                "canonical_id": None,
            }
        )

    selected = select_players_handbook_blocked9_targets(records)

    assert len(selected) == EXPECTED_PLAYERS_HANDBOOK_BLOCKED9_COUNT == 9
    fingerprint = hashlib.md5(
        ",".join(sorted(str(row["id"]) for row in selected)).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()
    assert fingerprint == EXPECTED_PLAYERS_HANDBOOK_BLOCKED9_IDS_MD5
    selected_names = {row["name"] for row in selected}
    assert "Leone" not in selected_names
    assert "Tigre" not in selected_names
    assert "Cavallo Da Guerra" in selected_names
    assert "Cinghiale" in selected_names
    assert "Rana" in selected_names


def test_players_handbook_blocked8_is_sealed_after_mulo_passes():
    from scripts.repair_monsters_from_source import PLAYERS_HANDBOOK_TARGETS

    records = []
    for expected in PLAYERS_HANDBOOK_TARGETS:
        status = expected["status"]
        records.append(
            {
                "id": expected["id"],
                "name": expected["name"],
                "reference_type": "monster",
                "review_status": status,
                "review_flags": (
                    [OCR_REVIEW_FLAG]
                    if status == "verified"
                    else [OCR_REVIEW_FLAG, REPAIR_FLAG]
                ),
                "source_key": "Manuale_del_giocatore__1787259882002.pdf",
                "source_refs": [
                    {
                        "filename": "Manuale_del_giocatore__1787259882002.pdf",
                        "page": 304,
                    }
                ],
                "canonical_id": None,
            }
        )

    selected = select_players_handbook_blocked8_targets(records)

    assert len(selected) == EXPECTED_PLAYERS_HANDBOOK_BLOCKED8_COUNT == 8
    fingerprint = hashlib.md5(
        ",".join(sorted(str(row["id"]) for row in selected)).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()
    assert fingerprint == EXPECTED_PLAYERS_HANDBOOK_BLOCKED8_IDS_MD5
    selected_names = {row["name"] for row in selected}
    assert "Mulo" not in selected_names
    assert "Cavallo Da Guerra" in selected_names
    assert "Falco" in selected_names
    assert "Rana" in selected_names


def test_residual_batches_are_disjoint_complete_and_fingerprinted():
    ids_by_batch = {
        name: [target["id"] for target in targets]
        for name, targets in RESIDUAL_BATCH_TARGETS.items()
    }

    assert {name: len(ids) for name, ids in ids_by_batch.items()} == (
        EXPECTED_RESIDUAL_BATCH_COUNTS
    )
    assert sum(len(ids) for ids in ids_by_batch.values()) == 31
    assert len({record_id for ids in ids_by_batch.values() for record_id in ids}) == 31
    assert "ref_14406fab44dc5f57a4bb06187ba33465" in ids_by_batch["batch_alpha"]
    assert "ref_94dd0655e7fc518aaf9e3ad214e0dba7" in ids_by_batch["batch_alpha"]
    for name, ids in ids_by_batch.items():
        fingerprint = hashlib.md5(
            ",".join(sorted(ids)).encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()
        assert fingerprint == EXPECTED_RESIDUAL_BATCH_IDS_MD5[name]


def test_residual_batch_selector_fails_closed_on_identity_drift():
    failures = [
        {
            "id": target["id"],
            "name": target["name"],
            "review_status": "verified",
            "canonical_id": None,
        }
        for target in RESIDUAL_BATCH_TARGETS["batch_alpha"]
    ]

    selected = select_residual_batch_targets(failures, "batch_alpha")
    assert len(selected) == 10

    failures[0]["name"] = "drifted"
    try:
        select_residual_batch_targets(failures, "batch_alpha")
    except RuntimeError as exc:
        assert "name drift" in str(exc)
    else:
        raise AssertionError("sealed batch identity drift must fail closed")


def test_target_identity_accepts_bounded_edit_only_on_registered_page():
    candidate = {
        "name": "Bae1",
        "normalized_name": "bae1",
        "source_refs": [{"page": 61}],
        "attributes": {"ocr_independent_agreement": True},
    }

    assert _candidate_matches_target(candidate, "Bael", 61) is True
    assert _candidate_matches_target(candidate, "Bael", 62) is False


def test_target_page_plus_one_requires_multi_token_clean_agreement():
    candidate = {
        "name": "Progenie Stellare Hulk",
        "normalized_name": "progenie stellare hulk",
        "source_refs": [{"page": 20}],
        "attributes": {
            "ocr_independent_agreement": True,
            "ocr_clean_deterministic_core_agreement": True,
        },
    }

    assert _candidate_matches_target(candidate, "Progenie Stellare Hulk", 19) is True
    candidate["attributes"].pop("ocr_clean_deterministic_core_agreement")
    assert _candidate_matches_target(candidate, "Progenie Stellare Hulk", 19) is False


def test_zero_agreement_reports_candidate_counts_and_divergent_core_fields():
    primary = [
        {
            "name": "Mostro Prova",
            "normalized_name": "mostro prova",
            "start_page": 13,
            "source_refs": [{"page": 12}],
            "attributes": {
                "classe_armatura": "15",
                "punti_ferita": "20 (3d8 + 6)",
                "velocita": "9 m rapido",
            },
        }
    ]
    comparison = [
        {
            "name": "Mostro Prova",
            "normalized_name": "mostro prova",
            "start_page": 12,
            "source_refs": [{"page": 12}],
            "attributes": {
                "classe_armatura": "16",
                "punti_ferita": "20 (3d8 + 6)",
                "velocita": "9 m rapido rapido",
            },
        }
    ]

    with (
        patch(
            "scripts.repair_monsters_from_source.parse_monster_statblocks",
            side_effect=[primary, comparison],
        ),
        patch(
            "scripts.repair_monsters_from_source.agreed_monster_records",
            return_value=[],
        ),
    ):
        try:
            _agreed_target_candidate([], [], "manual.pdf", "it", "Mostro Prova", 12)
        except RepairBlocked as exc:
            assert exc.reason == "no_unique_independent_agreement"
            assert exc.diagnostics == {
                "comparison_candidates_found": 1,
                "comparison_name_candidates": 1,
                "comparison_target_candidates": 1,
                "containment_match_count": 0,
                "discarded_pairs": [
                    {
                        "comparison_start_page": 12,
                        "containment_match": False,
                        "deterministic_matches": {
                            "classe_armatura_deterministic_match": False,
                            "punti_ferita_deterministic_match": True,
                            "velocita_deterministic_match": False,
                        },
                        "exact_name_match": True,
                        "primary_start_page": 13,
                        "semantic_matches": {
                            "classe_armatura_semantic_match": False,
                            "punti_ferita_semantic_match": True,
                            "velocita_semantic_match": True,
                        },
                        "start_page_mismatch": True,
                        "velocita_duplicate_ambiguous": True,
                    }
                ],
                "divergent_core_fields": ["classe_armatura", "velocita"],
                "exact_name_match_count": 1,
                "primary_candidates_found": 1,
                "primary_name_candidates": 1,
                "primary_target_candidates": 1,
                "target_normalized_name": "mostro prova",
                "target_page": 12,
            }
        else:
            raise AssertionError("zero agreement must remain blocked")


def test_zero_agreement_counts_strict_name_containment_pairs():
    attributes = {
        "classe_armatura": "15",
        "punti_ferita": "20 (3d8 + 6)",
        "velocita": "9 m",
    }
    primary = [
        {
            "name": "Mostro",
            "normalized_name": "mostro",
            "start_page": 12,
            "source_refs": [{"page": 12}],
            "attributes": attributes,
        }
    ]
    comparison = [
        {
            "name": "Mostro Prova",
            "normalized_name": "mostro prova",
            "start_page": 12,
            "source_refs": [{"page": 12}],
            "attributes": attributes,
        }
    ]

    with (
        patch(
            "scripts.repair_monsters_from_source.parse_monster_statblocks",
            side_effect=[primary, comparison],
        ),
        patch(
            "scripts.repair_monsters_from_source.agreed_monster_records",
            return_value=[],
        ),
    ):
        try:
            _agreed_target_candidate([], [], "manual.pdf", "it", "Mostro", 12)
        except RepairBlocked as exc:
            assert exc.diagnostics is not None
            assert exc.diagnostics["exact_name_match_count"] == 0
            assert exc.diagnostics["containment_match_count"] == 1
            assert exc.diagnostics["discarded_pairs"][0]["containment_match"] is True
        else:
            raise AssertionError("zero agreement must remain blocked")


def test_local_adaptive_threshold_is_inverted_and_local():
    samples = bytes(
        [
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            40,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
            220,
        ]
    )

    result = _local_adaptive_inverted_samples(
        samples,
        5,
        5,
        window_size=3,
    )

    assert result[12] == 255
    assert result[0] == 0


def test_isolated_foreground_noise_removes_only_single_pixel_components():
    samples = bytes(
        [
            0,
            0,
            0,
            0,
            0,
            0,
            255,
            0,
            255,
            255,
            0,
            0,
            0,
            0,
            0,
        ]
    )

    result = _remove_isolated_foreground_noise(samples, 5, 3)

    assert result[6] == 0
    assert result[8] == 255
    assert result[9] == 255


def test_hp_micro_ocr_contrast_crop_and_character_whitelist(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t0\t1\t20\t20\t120\t20\t95\tFraz-Urb'Luu\n"
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
            "Fraz-Urb'Luu",
        )

    assert "Punti Ferita 127 (15d12 + 30)" in result
    assert len(run.call_args_list) == 2
    assert "tsv" in run.call_args_list[0].args[0]
    micro_command = run.call_args_list[1].args[0]
    assert "--psm" in micro_command
    assert "7" in micro_command
    assert "tessedit_char_whitelist=0123456789d+-() " in micro_command


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
            "Fraz-Urb'Luu",
        )

    assert result == "Classe Armatura 17\nVelocità 3 m"
    run.assert_not_called()


def test_hp_micro_ocr_skips_when_unique_local_hp_is_already_valid(tmp_path, capsys):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 300), False)
    image.clear_with(255)
    image.save(image_path)
    page_text = (
        "Quasit\n"
        "Minuscolo immondo, legale malvagio\n"
        "Classe Armatura 13\n"
        "Punti Ferita 7 (3d4)\n"
        "Velocità 6 m, volare 12 m\n"
    )

    with patch("scripts.repair_monsters_from_source.subprocess.run") as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            page_text,
            "Quasit",
        )

    assert result == page_text
    run.assert_not_called()
    assert "HP_MICRO_OCR_SKIPPED_VALID_LOCAL" in capsys.readouterr().out


def test_micro_target_line_matches_bounded_title_ocr_error():
    assert _micro_target_line_matches(
        "Cavallo Da Galopo",
        "Cavallo Da Galoppo",
    )
    assert not _micro_target_line_matches(
        "Cavallo Da Guerra",
        "Cavallo Da Galoppo",
    )


def test_verified_core_agreement_accepts_only_presentation_differences():
    raw, deterministic = _verified_core_agreement(
        {
            "classe_armatura": "14 (armatura naturale)",
            "punti_ferita": "26 (4d10 + 4)",
            "velocita": "12 m, scalare 9 m",
        },
        {
            "classe_armatura": "14 (armatura naturale}",
            "punti_ferita": "26 (4d10+4)",
            "velocita": "12 m, scalare 9m",
        },
    )

    assert raw == {
        "classe_armatura": False,
        "punti_ferita": False,
        "velocita": False,
    }
    assert deterministic == {
        "classe_armatura": True,
        "punti_ferita": True,
        "velocita": True,
    }

    _raw, deterministic = _verified_core_agreement(
        {
            "classe_armatura": "13",
            "punti_ferita": "10 (3d4 + 3)",
            "velocita": "6 m, volare 12 m; 6 m, scalare 6 m",
        },
        {
            "classe_armatura": "13",
            "punti_ferita": "10 (3d4 + 3)",
            "velocita": "6 m, volare 12 m",
        },
    )
    assert deterministic["velocita"] is False


def test_hp_micro_ocr_replaces_target_local_hp_after_bounded_name_match(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 300), False)
    image.clear_with(255)
    image.save(image_path)
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    rows = [
        "5\t1\t1\t1\t1\t1\t20\t20\t170\t20\t95\tCavallo Da Galopo",
        "5\t1\t1\t1\t2\t1\t20\t50\t45\t20\t95\tPunti",
        "5\t1\t1\t1\t2\t2\t72\t50\t50\t20\t95\tFerita",
    ]
    page_text = (
        "Altro Mostro\n"
        "Punti Ferita 99 (9d10 + 45)\n"
        "Cavallo Da Galopo\n"
        "Punti Ferita 13 (2d1O + 2)\n"
        "Velocità 18 m\n"
    )
    responses = [
        CompletedProcess([], 0, stdout=header + "\n".join(rows) + "\n", stderr=""),
        CompletedProcess([], 0, stdout="13 (2d10 + 2)\n", stderr=""),
    ]

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        side_effect=responses,
    ):
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            page_text,
            "Cavallo Da Galoppo",
        )

    assert "Altro Mostro\nPunti Ferita 99 (9d10 + 45)" in result
    assert "Cavallo Da Galopo\nPunti Ferita 13 (2d10 + 2)" in result


def test_hp_micro_ocr_uses_target_name_as_upper_anchor(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 300), False)
    image.clear_with(255)
    image.save(image_path)
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    rows = [
        "5\t1\t1\t1\t1\t1\t20\t20\t100\t20\t95\tAltro Mostro",
        "5\t1\t1\t1\t2\t1\t20\t50\t45\t20\t95\tPunti",
        "5\t1\t1\t1\t2\t2\t72\t50\t50\t20\t95\tFerita",
        "5\t1\t2\t1\t1\t1\t20\t120\t120\t20\t95\tQuetzalcoatlus",
        "5\t1\t2\t1\t2\t1\t20\t150\t45\t20\t95\tPunti",
        "5\t1\t2\t1\t2\t2\t72\t150\t50\t20\t95\tFerita",
    ]
    responses = [
        CompletedProcess([], 0, stdout=header + "\n".join(rows) + "\n", stderr=""),
        CompletedProcess([], 0, stdout="30 (4d10 + 8)\n", stderr=""),
    ]

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run", side_effect=responses
    ):
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Quetzalcoatlus\nPunti Ferita\n",
            "Quetzalcoatlus",
        )

    assert result == "Quetzalcoatlus\nPunti Ferita 30 (4d10 + 8)\n"


def test_hp_micro_ocr_finds_hp_label_within_five_tsv_lines_of_name(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 300), False)
    image.clear_with(255)
    image.save(image_path)
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    rows = [
        "5\t1\t1\t1\t1\t1\t20\t20\t120\t10\t95\tQuetzalcoatlus",
        "5\t1\t1\t1\t2\t1\t20\t30\t80\t10\t95\tEnorme",
        "5\t1\t1\t1\t3\t1\t20\t40\t80\t10\t95\tBestia",
        "5\t1\t1\t1\t4\t1\t20\t50\t80\t10\t95\tSenza",
        "5\t1\t1\t1\t5\t1\t20\t60\t80\t10\t95\tAllineamento",
        "5\t1\t1\t1\t6\t1\t20\t70\t45\t10\t95\tPunti",
        "5\t1\t1\t1\t7\t1\t72\t75\t50\t10\t95\tFerita",
    ]
    responses = [
        CompletedProcess([], 0, stdout=header + "\n".join(rows) + "\n", stderr=""),
        CompletedProcess([], 0, stdout="30 (4d12 + 4)\n", stderr=""),
        CompletedProcess([], 0, stdout="30 (4d12 + 4)\n", stderr=""),
    ]

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run", side_effect=responses
    ):
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Quetzalcoatlus\nPunti Ferita 30 (4d1 2 + 4)\n",
            "Quetzalcoatlus",
        )

    assert result == "Quetzalcoatlus\nPunti Ferita 30 (4d12 + 4)\n"


def test_hp_micro_ocr_page_wide_fallback_requires_unique_text_and_tsv_label(
    tmp_path, capsys
):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 240), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t2\t1\t1\t1\t20\t100\t45\t12\t95\tPunti\n"
        "5\t1\t2\t1\t1\t2\t72\t100\t50\t12\t95\tFerita\n"
    )
    responses = [
        CompletedProcess([], 0, stdout=tsv, stderr=""),
        CompletedProcess([], 0, stdout="30 (4d12 + 4)\n", stderr=""),
    ]

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run", side_effect=responses
    ):
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Quetzalcoatlus\nEnorme bestia\nPunti Ferita 30 (4d1 2 + 4)\n",
            "Quetzalcoatlus",
        )

    assert result.endswith("Punti Ferita 30 (4d12 + 4)\n")
    assert "HP_PAGE_WIDE_FALLBACK" in capsys.readouterr().out


def test_hp_micro_ocr_page_wide_fallback_rejects_ambiguous_hp_labels(tmp_path, capsys):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 240), False)
    image.clear_with(255)
    image.save(image_path)
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    rows = [
        "5\t1\t2\t1\t1\t1\t20\t80\t45\t12\t95\tPunti",
        "5\t1\t2\t1\t1\t2\t72\t80\t50\t12\t95\tFerita",
        "5\t1\t3\t1\t1\t1\t20\t160\t45\t12\t95\tPunti",
        "5\t1\t3\t1\t1\t2\t72\t160\t50\t12\t95\tFerita",
    ]
    page_text = (
        "Quetzalcoatlus\nPunti Ferita 30 (4d1 2 + 4)\n"
        "Altro Mostro\nPunti Ferita 20 (3d8 + 6)\n"
    )

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        return_value=CompletedProcess(
            [], 0, stdout=header + "\n".join(rows) + "\n", stderr=""
        ),
    ) as run:
        result = _micro_ocr_hit_points_line(
            image_path, "ita", 3, page_text, "Quetzalcoatlus"
        )

    assert result == page_text
    assert run.call_count == 1
    output = capsys.readouterr().out
    assert "HP_ANCHOR_DIAGNOSTIC" in output
    payload = json.loads(output.split("HP_ANCHOR_DIAGNOSTIC ", 1)[1])
    assert payload == {
        "name": "Quetzalcoatlus",
        "page_text_local_hp_count": 2,
        "page_text_target_count": 1,
        "reason": "no_unique_structural_hp_anchor",
        "tsv_local_label_found": False,
        "tsv_name_anchor_found": False,
        "tsv_page_wide_hp_label_count": 2,
    }


def test_hp_micro_ocr_collapses_identical_duplicate_hp_lines(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 240), False)
    image.clear_with(255)
    image.save(image_path)
    page_text = (
        "Rana\nPunti Ferita 1 (1d4 - 1)\n"
        "Rana\nPunti Ferita 1 (1d4 - 1)\n"
    )

    with patch("scripts.repair_monsters_from_source.subprocess.run") as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            page_text,
            "Rana",
        )

    assert result == page_text
    run.assert_not_called()


def test_hp_micro_ocr_unique_geometry_can_repair_duplicate_target_copies(tmp_path, capsys):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 240), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t20\t20\t80\t15\t95\tRana\n"
        "5\t1\t1\t1\t2\t1\t20\t50\t45\t15\t95\tPunti\n"
        "5\t1\t1\t1\t2\t2\t72\t50\t50\t15\t95\tFerita\n"
    )
    page_text = (
        "Rana\nPunti Ferita 1 (1dA - 1)\nVelocità 6 m\n"
        "Rana\nPunti Ferita 1 (1d 4 - 1)\nVelocità 6 m\n"
    )
    responses = [
        CompletedProcess([], 0, stdout=tsv, stderr=""),
        CompletedProcess([], 0, stdout="1 (1d4 - 1)\n", stderr=""),
    ]

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        side_effect=responses,
    ):
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            page_text,
            "Rana",
            single_target_geometry=True,
        )

    assert result.count("Punti Ferita 1 (1d4 - 1)") == 2
    assert "HP_UNIQUE_GEOMETRY_DUPLICATE_REPLACEMENT" in capsys.readouterr().out


def test_hit_points_whitelist_preserves_negative_modifier_sign():
    assert "-" in HIT_POINTS_WHITELIST


def test_numeric_dice_separator_confusion_repairs_only_unique_math_valid_candidate():
    assert (
        _repair_numeric_dice_separator_confusion("11 (248 + 2)")
        == "11 (2d8 + 2)"
    )
    assert (
        _repair_numeric_dice_separator_confusion("1 (144 - 1)")
        == "1 (1d4 - 1)"
    )


def test_numeric_dice_separator_confusion_fails_closed_on_bad_math_or_valid_input():
    assert _repair_numeric_dice_separator_confusion("12 (248 + 2)") is None
    assert _repair_numeric_dice_separator_confusion("11 (2d8 + 2)") is None
    assert _repair_numeric_dice_separator_confusion("11 (245 + 2)") is None


def test_phb_blocked7_source_guided_segments_are_right_column():
    assert PLAYERS_HANDBOOK_TIMEOUT4_NAMES == {
        "Falco",
        "Gufo",
        "Lupo",
        "Pipistrello",
    }
    assert {
        name: TARGET_SEGMENT_BY_NAME[name]
        for name in (
            "Cavallo Da Guerra",
            "Cinghiale",
            "Falco",
            "Gufo",
            "Lupo",
            "Orso Bruno",
            "Pipistrello",
        )
    } == {
        "Cavallo Da Guerra": "right",
        "Cinghiale": "right",
        "Falco": "right",
        "Gufo": "right",
        "Lupo": "right",
        "Orso Bruno": "right",
        "Pipistrello": "right",
    }


def test_phb_timeout4_full_spectrum_starts_with_x4_no_morphology(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t20\t20\t100\t20\t95\tFalco\n"
        "5\t1\t1\t1\t2\t1\t20\t50\t45\t20\t95\tPunti\n"
        "5\t1\t1\t1\t2\t2\t72\t50\t50\t20\t95\tFerita\n"
    )
    responses = [
        CompletedProcess([], 0, stdout=tsv, stderr=""),
        CompletedProcess([], 0, stdout="1 (1dA - 1)\n", stderr=""),
        CompletedProcess([], 0, stdout="1 (1dA - 1)\n", stderr=""),
        CompletedProcess([], 0, stdout="1 (1dA - 1)\n", stderr=""),
        CompletedProcess([], 0, stdout="1 (1dA - 1)\n", stderr=""),
        CompletedProcess([], 0, stdout="1 (1d4 - 1)\n", stderr=""),
    ]

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        side_effect=responses,
    ) as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Falco\nPunti Ferita 1 (1dA - 1)\nVelocità 3 m, volare 18 m\n",
            "Falco",
        )

    assert "Punti Ferita 1 (1d4 - 1)" in result
    first_spectrum_path = run.call_args_list[5].args[0][1]
    assert "upscaled-x4" in first_spectrum_path
    assert "dark-eroded" not in first_spectrum_path
    assert "dark-dilated" not in first_spectrum_path


def test_phb_full_spectrum_uses_native_morphology_only(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t20\t20\t100\t20\t95\tMulo\n"
        "5\t1\t1\t1\t2\t1\t20\t50\t45\t20\t95\tPunti\n"
        "5\t1\t1\t1\t2\t2\t72\t50\t50\t20\t95\tFerita\n"
    )
    responses = [
        CompletedProcess([], 0, stdout=tsv, stderr=""),
        CompletedProcess([], 0, stdout="11 (248+ 2)\n", stderr=""),
        CompletedProcess([], 0, stdout="11 (248+ 2)\n", stderr=""),
        CompletedProcess([], 0, stdout="11 (248+ 2)\n", stderr=""),
        CompletedProcess([], 0, stdout="11 (248+ 2)\n", stderr=""),
        CompletedProcess([], 0, stdout="11 (2d8 + 2)\n", stderr=""),
    ]

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        side_effect=responses,
    ) as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Mulo\nPunti Ferita 11 (248+ 2)\nVelocità 12 m\n",
            "Mulo",
        )

    assert "Punti Ferita 11 (2d8 + 2)" in result
    first_spectrum_path = run.call_args_list[5].args[0][1]
    assert "upscaled-x4" in first_spectrum_path
    assert "dark-dilated" not in first_spectrum_path
    assert "dark-eroded" not in first_spectrum_path
    assert "threshold-140" in first_spectrum_path


def test_hp_micro_ocr_reports_page_text_identity_ambiguity(tmp_path, capsys):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 240), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t2\t1\t1\t1\t20\t100\t45\t12\t95\tPunti\n"
        "5\t1\t2\t1\t1\t2\t72\t100\t50\t12\t95\tFerita\n"
    )
    page_text = (
        "Quetzalcoatlus\nPunti Ferita 30 (4d12 + 4)\n"
        "Quetzalcoatlus\nPunti Ferita 31 (4d12 + 5)\n"
    )

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=tsv, stderr=""),
    ):
        result = _micro_ocr_hit_points_line(
            image_path, "ita", 3, page_text, "Quetzalcoatlus"
        )

    assert result == page_text
    payload = json.loads(capsys.readouterr().out.split("HP_ANCHOR_DIAGNOSTIC ", 1)[1])
    assert payload["page_text_target_count"] == 2
    assert payload["page_text_local_hp_count"] == 2
    assert payload["tsv_page_wide_hp_label_count"] == 1
    assert payload["tsv_name_anchor_found"] is False
    assert payload["tsv_local_label_found"] is False


def test_hp_micro_ocr_subprocess_crash_fails_closed_without_aborting(tmp_path, capsys):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t20\t20\t120\t20\t95\tLarvico\n"
        "5\t1\t1\t1\t2\t1\t20\t50\t45\t20\t95\tPunti\n"
        "5\t1\t1\t1\t2\t2\t72\t50\t50\t20\t95\tFerita\n"
    )
    calls = 0

    def run_tesseract(command, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return CompletedProcess([], 0, stdout=tsv, stderr="")
        raise subprocess.CalledProcessError(-8, command, stderr="SIGFPE")

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run", side_effect=run_tesseract
    ):
        result = _micro_ocr_hit_points_line(
            image_path, "ita", 3, "Larvico\nPunti Ferita ???\n", "Larvico"
        )

    assert result == "Larvico\nPunti Ferita ???\n"
    assert "HP_MICRO_OCR_SUBPROCESS_FAILURE" in capsys.readouterr().out


def test_hp_micro_ocr_retries_corrupted_die_at_lower_contrast(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t20\t20\t120\t20\t95\tFraz-Urb'Luu\n"
        "5\t1\t1\t1\t2\t1\t20\t50\t45\t20\t95\tPunti\n"
        "5\t1\t1\t1\t2\t2\t72\t50\t50\t20\t95\tFerita\n"
    )
    responses = [
        CompletedProcess([], 0, stdout=tsv, stderr=""),
        CompletedProcess([], 0, stdout="149 (22410 + 28)\n", stderr=""),
        CompletedProcess([], 0, stdout="149 (22410 + 28)\n", stderr=""),
        CompletedProcess([], 0, stdout="149 (22410 + 28)\n", stderr=""),
        CompletedProcess([], 0, stdout="149 (22d10 + 28)\n", stderr=""),
    ]
    crop_sizes = []

    def run_tesseract(command, **_kwargs):
        response = responses.pop(0)
        if "hit-points-" in command[1]:
            crop = fitz.Pixmap(command[1])
            crop_sizes.append((crop.width, crop.height))
        return response

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run", side_effect=run_tesseract
    ) as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Fraz-Urb'Luu\nPunti Ferita 149 (22410 + 28)\n",
            "Fraz-Urb'Luu",
        )

    assert result == "Fraz-Urb'Luu\nPunti Ferita 149 (22d10 + 28)\n"
    assert len(run.call_args_list) == 5
    assert run.call_args_list[1].args[0][1].endswith("hit-points-2.0.png")
    assert run.call_args_list[2].args[0][1].endswith("hit-points-1.2-otsu-inverted.png")
    assert (
        run.call_args_list[3]
        .args[0][1]
        .endswith("hit-points-1.2-upscaled-x2-otsu-inverted.png")
    )
    assert crop_sizes[2] == (crop_sizes[1][0] * 2, crop_sizes[1][1] * 2)
    assert "upscaled-x4" in run.call_args_list[4].args[0][1]
    assert "threshold-100" in run.call_args_list[4].args[0][1]
    assert "dark-dilated" not in run.call_args_list[4].args[0][1]
    assert crop_sizes[3] == (crop_sizes[1][0] * 4, crop_sizes[1][1] * 4)


def test_dark_pixel_dilation_expands_only_into_immediate_neighborhood():
    source = bytes(
        [
            255,
            255,
            255,
            255,
            0,
            255,
            255,
            255,
            255,
        ]
    )

    assert _dilate_dark_pixels(source, 3, 3) == bytes([0] * 9)


def test_dark_pixel_erosion_thins_only_into_immediate_neighborhood():
    source = bytes(
        [
            0,
            0,
            0,
            0,
            255,
            0,
            0,
            0,
            0,
        ]
    )

    assert _erode_dark_pixels(source, 3, 3) == bytes([255] * 9)


def test_full_spectrum_contrast_range_and_background_variance_are_bounded():
    assert HIT_POINTS_FULL_SPECTRUM_CONTRASTS == (1.0, 2.0)
    assert _sample_variance(bytes([255, 255, 255])) == 0.0
    assert _sample_variance(bytes([0, 255])) > 36.0


def test_quetzalcoatlus_fourth_hp_retry_uses_dark_dilation(tmp_path):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t20\t20\t140\t20\t95\tQuetzalcoatlus\n"
        "5\t1\t1\t1\t2\t1\t20\t50\t45\t20\t95\tPunti\n"
        "5\t1\t1\t1\t2\t2\t72\t50\t50\t20\t95\tFerita\n"
    )
    responses = [
        CompletedProcess([], 0, stdout=tsv, stderr=""),
        CompletedProcess([], 0, stdout="19 (341043) 8\n", stderr=""),
        CompletedProcess([], 0, stdout="19 (341043) 8\n", stderr=""),
        CompletedProcess([], 0, stdout="19 (341043) 0\n", stderr=""),
        CompletedProcess([], 0, stdout="30 (4d10 + 8)\n", stderr=""),
    ]

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run", side_effect=responses
    ) as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Quetzalcoatlus\nPunti Ferita 19 (341043) 8\n",
            "Quetzalcoatlus",
        )

    assert result == "Quetzalcoatlus\nPunti Ferita 30 (4d10 + 8)\n"
    assert "upscaled-x4" in run.call_args_list[4].args[0][1]
    assert "threshold-100" in run.call_args_list[4].args[0][1]
    assert "dark-dilated" not in run.call_args_list[4].args[0][1]


def test_hp_micro_ocr_retries_modellaghiaccio_nonstandard_die_faces(tmp_path, capsys):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t20\t20\t140\t20\t95\tModellaghiaccio\n"
        "5\t1\t1\t1\t2\t1\t20\t50\t45\t20\t95\tPunti\n"
        "5\t1\t1\t1\t2\t2\t72\t50\t50\t20\t95\tFerita\n"
    )
    responses = [
        CompletedProcess([], 0, stdout=tsv, stderr=""),
        CompletedProcess([], 0, stdout="310 (27d412 + 135)\n", stderr=""),
        CompletedProcess([], 0, stdout="310 (27d12 + 135)\n", stderr=""),
    ]
    with patch(
        "scripts.repair_monsters_from_source.subprocess.run", side_effect=responses
    ) as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Modellaghiaccio\nPunti Ferita 310 (27d412 + 135)\n",
            "Modellaghiaccio",
        )

    assert result == "Modellaghiaccio\nPunti Ferita 310 (27d12 + 135)\n"
    assert len(run.call_args_list) == 3
    assert run.call_args_list[1].args[0][1].endswith("hit-points-2.0.png")
    assert run.call_args_list[2].args[0][1].endswith("hit-points-1.2-otsu-inverted.png")
    diagnostic = capsys.readouterr().out
    assert "HP_MICRO_OCR_DIAGNOSTIC" in diagnostic
    payload = json.loads(diagnostic.split("HP_MICRO_OCR_DIAGNOSTIC ", 1)[1])
    assert payload["initial_raw"] == "310 (27d412 + 135)\n"
    assert payload["otsu_inverted_raw"] == "310 (27d12 + 135)\n"
    assert payload["otsu_hp_format_error"] is False
    assert payload["upscaled_otsu_inverted_raw"] is None


def test_hp_micro_ocr_uses_otsu_when_initial_result_fails_math_gate(tmp_path, capsys):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t20\t20\t120\t20\t95\tMostro Prova\n"
        "5\t1\t1\t1\t2\t1\t20\t50\t45\t20\t95\tPunti\n"
        "5\t1\t1\t1\t2\t2\t72\t50\t50\t20\t95\tFerita\n"
    )
    responses = [
        CompletedProcess([], 0, stdout=tsv, stderr=""),
        CompletedProcess([], 0, stdout="30 (4d12 + 3)\n", stderr=""),
        CompletedProcess([], 0, stdout="30 (4d12 + 3)\n", stderr=""),
        CompletedProcess([], 0, stdout="30 (4d12 + 3)\n", stderr=""),
        CompletedProcess([], 0, stdout="30 (4d12 + 3)\n", stderr=""),
        CompletedProcess([], 0, stdout="30 (4d10 + 8)\n", stderr=""),
    ]

    with patch(
        "scripts.repair_monsters_from_source.subprocess.run", side_effect=responses
    ) as run:
        result = _micro_ocr_hit_points_line(
            image_path,
            "ita",
            3,
            "Mostro Prova\nPunti Ferita 30 (4d12 + 3)\n",
            "Mostro Prova",
        )

    assert result == "Mostro Prova\nPunti Ferita 30 (4d10 + 8)\n"
    assert (
        run.call_args_list[3]
        .args[0][1]
        .endswith("hit-points-1.2-upscaled-x2-otsu-inverted.png")
    )
    assert "upscaled-x4" in run.call_args_list[4].args[0][1]
    assert "threshold-100" in run.call_args_list[4].args[0][1]
    assert "upscaled-x4" in run.call_args_list[5].args[0][1]
    assert "threshold-140" in run.call_args_list[5].args[0][1]
    diagnostic = capsys.readouterr().out
    assert '"otsu_hp_format_error": true' in diagnostic
    assert '"upscaled_otsu_hp_format_error": true' in diagnostic
    assert '"superscaled_otsu_hp_format_error": null' in diagnostic
    assert '"full_spectrum_attempt_count": 2' in diagnostic
    assert '"morphology": "none"' in diagnostic
    assert '"threshold": 140' in diagnostic


def test_otsu_inversion_makes_dark_text_white_and_light_background_black():
    samples = bytes([10, 12, 14, 240, 245, 250])

    result = _otsu_inverted_samples(samples)

    assert result == bytes([255, 255, 255, 0, 0, 0])


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
        _monster(
            "Yuan-Ti Guardia Della Stirpe", "14", "45 (7d8 + 14)", record_id="good"
        ),
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
    active_sources = [
        {
            "physical_filename": "Mostri del multiverso 201-294.pdf",
            "logical_source_id": "mpmm_2022_it",
            "source_role": "authority",
            "source_status": "active",
            "physical_pages": 94,
        }
    ]

    source, ref = resolve_source(record, active_sources)
    assert source["source_role"] == "authority"
    assert ref["page"] == 85


def test_resolve_source_blocks_extraction_aid_alias():
    record = {
        **_monster("Legacy Spanish Monster", "1", "20 (3d8 + 6)"),
        "source_refs": [
            {
                "filename": "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf",
                "page": 915,
            }
        ],
    }
    active_sources = [
        {
            "physical_filename": "731764731-D-D-Manual-Del-Jugador-5e(1).pdf",
            "source_role": "extraction_aid",
            "source_status": "active",
            "physical_pages": 1018,
        }
    ]

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
        ("left", (0.0, 0.0, 0.52, 1.0)),
        ("right", (0.48, 0.0, 1.0, 1.0)),
    )
    assert _layout_segments(source, overlap_fraction=0.05) == (
        ("left", (0.0, 0.0, 0.55, 1.0)),
        ("right", (0.45, 0.0, 1.0, 1.0)),
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
        ("left", (0.0, 0.0, 0.52, 1.0)),
        ("right", (0.48, 0.0, 1.0, 1.0)),
    )
    assert _layout_ocr_settings(
        source,
        dpi=220,
        psm=6,
        comparison_psm=4,
    ) == (300, 3, 4)


def test_players_handbook_layout_profile_splits_columns():
    source = {"logical_source_id": "phb_2014_it"}

    assert _layout_profile(source) == "two_column_vertical"
    assert _layout_segments(source) == (
        ("left", (0.0, 0.0, 0.52, 1.0)),
        ("right", (0.48, 0.0, 1.0, 1.0)),
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
    assert _layout_segments(source) == (("full", (0.0, 0.0, 1.0, 1.0)),)
    assert _layout_ocr_settings(
        source,
        dpi=220,
        psm=6,
        comparison_psm=4,
    ) == (220, 6, 4)


def test_dynamic_layout_retry_requires_missing_identity_in_two_column_source():
    source = {"logical_source_id": "mpmm_2022_it"}
    missing = RepairBlocked(
        "no_unique_independent_agreement",
        diagnostics={
            "primary_name_candidates": 0,
            "comparison_name_candidates": 1,
        },
    )
    disagreement = RepairBlocked(
        "no_unique_independent_agreement",
        diagnostics={
            "primary_name_candidates": 1,
            "comparison_name_candidates": 1,
        },
    )

    assert _should_retry_dynamic_layout(missing, source) is True
    assert _should_retry_dynamic_layout(disagreement, source) is False
    assert (
        _should_retry_dynamic_layout(missing, {"logical_source_id": "tce_2020_it"})
        is False
    )


def test_sparse_page_anchor_requires_title_like_identity():
    assert _sparse_anchor_matches("RAK   TULKHESH", "Rak Tulkhesh")
    assert _sparse_anchor_matches("RAK   TULKHESH X", "Rak Tulkhesh")
    assert _sparse_anchor_matches("CINGHIAIE", "Cinghiale")
    assert _sparse_anchor_matches("CING HIALE", "Cinghiale")
    assert _sparse_anchor_matches("MUIO", "Mulo")
    assert not _sparse_anchor_matches(
        "RAK TULKHESH Classe Armatura",
        "Rak Tulkhesh",
    )
    assert not _sparse_anchor_matches(
        "Il Rak Tulkhesh attacca",
        "Rak Tulkhesh",
    )


def test_sparse_page_anchor_rejects_empty_target():
    assert not _sparse_anchor_matches("Rak Tulkhesh", "")


def test_targeted_ocr_budget_token_extends_only_the_total_budget():
    with patch(
        "scripts.repair_monsters_from_source.time.monotonic",
        return_value=70.0,
    ):
        assert _remaining_global_ocr_budget((0.0, 75.0)) == 5.0
        with pytest.raises(RepairBlocked) as exc:
            _remaining_global_ocr_budget((0.0, 60.0))

    assert exc.value.reason == "ocr_global_timeout"
    assert exc.value.diagnostics["budget_seconds"] == 60.0


def test_source_pdf_cache_resolves_registered_r2_alias_and_verifies_sha(tmp_path):
    payload = b"registered PHB bytes"
    source = {
        "physical_filename": "Manuale del giocatore .pdf",
        "physical_sha256": hashlib.sha256(payload).hexdigest(),
    }

    class FakeClient:
        def download_file(self, bucket, key, target):
            assert bucket == "tomoforge-manuals"
            assert key == "uploads/Manuale del Giocatore .pdf"
            Path(target).write_bytes(payload)

    with (
        patch(
            "scripts.import_manuals_from_r2._r2_client",
            return_value=FakeClient(),
        ),
        patch(
            "scripts.import_manuals_from_r2._list_pdf_objects",
            return_value={
                "Manuale del Giocatore .pdf": {
                    "key": "uploads/Manuale del Giocatore .pdf"
                }
            },
        ),
    ):
        cache = SourcePdfCache(str(tmp_path), allow_r2_download=True)
        try:
            resolved = cache.get(source)
            assert resolved.read_bytes() == payload
            assert resolved.name == "Manuale del Giocatore .pdf"
        finally:
            cache.close()


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


def test_approved1_sealed_target_set_contains_only_numerically_valid_identity():
    records = []
    for expected in APPROVED1_TARGETS:
        row = _monster(
            expected["name"],
            "1",
            "20 (3d8 + 6)",
            record_id=expected["id"],
        )
        row["source_text_checksum"] = f"checksum-{expected['id']}"
        records.append(row)

    selected = select_approved1_targets(records)

    assert len(selected) == EXPECTED_APPROVED1_COUNT == 1
    assert {row["name"] for row in selected} == {"Abishai Rosso"}
    assert {row["name"] for row in selected}.isdisjoint(
        {"Colline", "Di Fuoco", "Mietitore", "Modellaghiaccio"}
    )


def test_approved5_sealed_target_set_resolves_only_gate_clean_batch():
    records = []
    for expected in APPROVED5_TARGETS:
        row = _monster(
            expected["name"],
            "1",
            "20 (3d8 + 6)",
            record_id=expected["id"],
        )
        row["source_text_checksum"] = f"checksum-{expected['id']}"
        records.append(row)

    selected = select_approved5_targets(records)

    assert len(selected) == EXPECTED_APPROVED5_COUNT == 5
    assert {row["name"] for row in selected} == {
        "Colosso Di Carne",
        "Di Terra",
        "Fraz-Urb'Luu",
        "Lavamandra Warlock Di Imix",
        "Modellaghiaccio",
    }


def test_approved5_sealed_target_set_rejects_live_state_drift():
    records = []
    for expected in APPROVED5_TARGETS:
        row = _monster(
            expected["name"],
            "1",
            "20 (3d8 + 6)",
            record_id=expected["id"],
        )
        row["source_text_checksum"] = f"checksum-{expected['id']}"
        records.append(row)
    records[0]["review_flags"] = ["unexpected"]

    try:
        select_approved5_targets(records)
    except RuntimeError as exc:
        assert "review flag drift" in str(exc)
    else:
        raise AssertionError("sealed approved5 batch must reject live-state drift")


def test_oblex1_sealed_target_set_resolves_only_reviewed_identity():
    expected = OBLEX1_TARGETS[0]
    record = _monster(
        expected["name"],
        "1",
        "20 (3d8 + 6)",
        record_id=expected["id"],
    )
    record["source_text_checksum"] = "checksum-oblex"

    selected = select_oblex1_targets([record])

    assert len(selected) == EXPECTED_OBLEX1_COUNT == 1
    assert selected[0]["name"] == "0Blex Antico"


def test_oblex1_sealed_target_set_rejects_status_drift():
    expected = OBLEX1_TARGETS[0]
    record = _monster(
        expected["name"],
        "1",
        "20 (3d8 + 6)",
        record_id=expected["id"],
    )
    record["source_text_checksum"] = "checksum-oblex"
    record["review_status"] = "pending"

    try:
        select_oblex1_targets([record])
    except RuntimeError as exc:
        assert "status drift" in str(exc)
    else:
        raise AssertionError("sealed oblex1 batch must reject status drift")


def test_ready6_sealed_target_set_resolves_exact_newly_clean_batch():
    records = []
    for expected in READY6_TARGETS:
        row = _monster(
            expected["name"],
            "1",
            "20 (3d8 + 6)",
            record_id=expected["id"],
        )
        row["source_text_checksum"] = f"checksum-{expected['id']}"
        records.append(row)

    selected = select_ready6_targets(records)

    assert len(selected) == EXPECTED_READY6_COUNT == 6
    assert {row["name"] for row in selected} == {
        "Mirmidone Elementale Dacqua",
        "Progenie Stellare Hulk",
        "Riportato Re",
        "T'Erra Malvagia",
        "T'Lincalli",
        "Thstencefalo",
    }


def test_ready6_sealed_target_set_rejects_missing_or_drifted_row():
    records = []
    for expected in READY6_TARGETS:
        row = _monster(
            expected["name"],
            "1",
            "20 (3d8 + 6)",
            record_id=expected["id"],
        )
        row["source_text_checksum"] = f"checksum-{expected['id']}"
        records.append(row)
    records[0]["review_flags"] = ["unexpected"]

    try:
        select_ready6_targets(records)
    except RuntimeError as exc:
        assert "review flag drift" in str(exc)
    else:
        raise AssertionError("sealed ready6 batch must reject live-state drift")


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


def test_background_luminance_stats_detects_nonwhite_frame():
    width = 10
    height = 10
    white = bytes([255] * (width * height))
    tinted = bytes([220] * (width * height))

    white_mean, white_variance = _background_luminance_stats(
        white,
        width,
        height,
    )
    tinted_mean, tinted_variance = _background_luminance_stats(
        tinted,
        width,
        height,
    )

    assert white_mean == 255
    assert white_variance == 0
    assert tinted_mean == 220
    assert tinted_variance == 0


def test_phb_quality_pre_otsu_clip_preserves_source_anchor_geometry():
    source = fitz.Rect(100, 50, 500, 450)

    orso = _phb_quality_pre_otsu_clip(source, "Orso Bruno")
    cavallo = _phb_quality_pre_otsu_clip(source, "Cavallo Da Guerra")

    assert orso == source
    assert cavallo == source


def test_orso_bruno_sparse_retry_preserves_source_raster():
    assert _phb_sparse_uses_quality_pre_otsu("Orso Bruno") is False
    assert _phb_sparse_uses_quality_pre_otsu("Cavallo Da Guerra") is False
    assert _phb_sparse_uses_quality_pre_otsu("Gufo") is True


def test_cavallo_sparse_comparison_uses_scoped_adaptive_source():
    assert _phb_sparse_comparison_uses_adaptive_source("Cavallo Da Guerra") is True
    assert _phb_sparse_comparison_uses_adaptive_source("Cinghiale") is False
    assert _phb_sparse_comparison_uses_adaptive_source("Gufo") is False
    assert _phb_sparse_comparison_uses_adaptive_source("Orso Bruno") is False


def test_phb_quality_gate_pre_otsu_targets_are_exactly_the_three_residuals():
    assert PHB_QUALITY_GATE_PRE_OTSU_TARGETS == {
        "Cavallo Da Guerra",
        "Gufo",
        "Orso Bruno",
    }


def test_phb_sparse_continuation_clips_are_source_reviewed_and_bounded():
    assert PHB_SPARSE_CONTINUATION_CLIPS == {
        "Gufo": (1, (0.06, 0.0, 0.49, 0.12)),
        "Lupo": (1, (0.06, 0.0, 0.49, 0.22)),
    }
    for page_offset, fractions in PHB_SPARSE_CONTINUATION_CLIPS.values():
        assert page_offset == 1
        x0, y0, x1, y1 = fractions
        assert 0.0 <= x0 < x1 <= 0.5
        assert y0 == 0.0
        assert 0.0 < y1 < 0.25


def test_phb_sparse_bottom_fractions_stop_before_neighboring_blocks():
    assert PHB_SPARSE_BOTTOM_FRACTION_BY_NAME == {
        "Cavallo Da Guerra": 0.455,
        "Falco": 0.35,
        "Orso Bruno": 0.84,
        "Pipistrello": 0.38,
    }
    assert all(
        0.3 < fraction < 0.9
        for fraction in PHB_SPARSE_BOTTOM_FRACTION_BY_NAME.values()
    )


def test_phb_sparse_quality_context_is_scoped_to_short_isolated_blocks():
    assert PHB_SPARSE_QUALITY_CONTEXT_TARGETS == {"Falco", "Pipistrello"}


def test_local_otsu_inversion_handles_distinct_local_backgrounds():
    width = 64
    height = 32
    samples = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            samples[y * width + x] = 220 if x < 32 else 250

    for y in range(6, 26):
        for x in range(10, 13):
            samples[y * width + x] = 30
        for x in range(43, 46):
            samples[y * width + x] = 80

    result = _local_otsu_inverted_samples(
        bytes(samples),
        width,
        height,
        tile_size=32,
    )

    assert result[10 * width + 11] == 255
    assert result[10 * width + 44] == 255
    assert result[2 * width + 2] == 0
    assert result[2 * width + 50] == 0


def test_sparse_anchor_crop_recenters_unique_right_column_target(tmp_path):
    image_path = tmp_path / "page.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 1000, 1200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t650\t200\t60\t30\t95\tRAK\n"
        "5\t1\t1\t1\t1\t2\t720\t200\t120\t30\t95\tTULKHESH\n"
    )
    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=tsv, stderr=""),
    ) as run:
        crop = _sparse_anchor_crop_fractions(
            image_path,
            "ita",
            "Rak Tulkhesh",
        )

    assert crop is not None
    assert crop[0] == 0.42
    assert crop[2] == 1.0
    assert 0.0 <= crop[1] < 0.2
    assert crop[3] == 1.0
    command = run.call_args.args[0]
    assert "--psm" in command
    assert "11" in command
    assert "tsv" in command


def test_sparse_anchor_crop_can_use_distinct_psm12(tmp_path):
    image_path = tmp_path / "page.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 1000, 1200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t650\t200\t120\t30\t95\tCINGHIALE\n"
    )
    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=tsv, stderr=""),
    ) as run:
        crop = _sparse_anchor_crop_fractions(
            image_path,
            "ita",
            "Cinghiale",
            psm=12,
        )

    assert crop is not None
    command = run.call_args.args[0]
    psm_index = command.index("--psm")
    assert command[psm_index + 1] == "12"


def test_phb_residual_retry_sets_keep_rana_and_bounded_budgets():
    assert "ref_66cc59680c4e58fa93a99656f8a07887" in (
        PLAYERS_HANDBOOK_HP_SPARSE_RETRY_IDS
    )
    assert all(0 < budget <= 150.0 for budget in OCR_GLOBAL_TIMEOUT_BY_RECORD_ID.values())
    phb_ids = {
        "ref_85a4eadb862758fbb682e93ab19f1065",
        "ref_f28940a5239a54f696cb524805e29cc2",
        "ref_38273488414b57489e9d7e57a6c0a360",
        "ref_87ee4ffeff7c5b7bb65e12def234a3be",
        "ref_019562bded0b320ac918f4b2514c65e4",
        "ref_0626a11ef12ec092e8c13f94d1b03cd8",
    }
    assert {record_id: OCR_GLOBAL_TIMEOUT_BY_RECORD_ID[record_id] for record_id in phb_ids} == {
        "ref_85a4eadb862758fbb682e93ab19f1065": 150.0,
        "ref_f28940a5239a54f696cb524805e29cc2": 150.0,
        "ref_38273488414b57489e9d7e57a6c0a360": 150.0,
        "ref_87ee4ffeff7c5b7bb65e12def234a3be": 150.0,
        "ref_019562bded0b320ac918f4b2514c65e4": 150.0,
        "ref_0626a11ef12ec092e8c13f94d1b03cd8": 150.0,
    }


def test_phb_sparse_comparison_psm_stays_independent_and_scoped():
    assert _phb_sparse_comparison_psm("Cinghiale", 4) == 12
    assert _phb_sparse_comparison_psm("Rana", 4) == 12
    assert _phb_sparse_comparison_psm("Cavallo Da Guerra", 4) == 4
    assert _phb_sparse_comparison_psm("Gufo", 4) == 4
    assert _phb_sparse_comparison_psm("Orso Bruno", 4) == 4
    assert _phb_sparse_comparison_psm("Falco", 4) == 12


def test_cavallo_sparse_title_restore_requires_unique_anchor_and_ordered_core():
    comparison = """Bestia Grande, senza allineamento
pie Classe Armatura 11
Le Punti Ferita 19 (3d10 + 3)
Ja delle Velocità 18 m
FOR DES COS INT SAG CAR
"""

    restored = _restore_cavallo_sparse_title_from_anchor(
        comparison,
        "Cavallo Da Guerra",
        unique_anchor_found=True,
    )
    assert restored.startswith("CAVALLO DA GUERRA\n")
    assert "\nClasse Armatura 11\n" in restored
    assert "\nPunti Ferita 19 (3d10 + 3)\n" in restored
    assert "\nVelocità 18 m\n" in restored

    assert (
        _restore_cavallo_sparse_title_from_anchor(
            comparison,
            "Cavallo Da Guerra",
            unique_anchor_found=False,
        )
        == comparison
    )
    assert (
        _restore_cavallo_sparse_title_from_anchor(
            "Bestia Grande\nPunti Ferita 19 (3d10 + 3)\nVelocità 18 m\n",
            "Cavallo Da Guerra",
            unique_anchor_found=True,
        )
        .startswith("CAVALLO DA GUERRA")
        is False
    )


def test_sparse_anchor_crop_rejects_ambiguous_duplicate_title(tmp_path):
    image_path = tmp_path / "page.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 1000, 1200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t100\t200\t80\t30\t95\tBAEL\n"
        "5\t1\t2\t1\t1\t1\t650\t700\t80\t30\t95\tBAEL\n"
    )
    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=tsv, stderr=""),
    ):
        assert _sparse_anchor_crop_fractions(image_path, "ita", "Bael") is None


def test_target_agreement_is_symmetric_when_only_comparison_keeps_target_name():
    attributes = {
        "classe_armatura": "17",
        "punti_ferita": "120 (16d10 + 32)",
        "velocita": "9 m",
    }
    primary = [
        {
            "name": "XQZ SIGNAL",
            "normalized_name": "xqz signal",
            "start_page": 61,
            "source_refs": [{"page": 61}],
            "attributes": dict(attributes),
            "review_flags": ["ocr_da_verificare"],
        }
    ]
    comparison = [
        {
            "name": "Rak Tulkhesh",
            "normalized_name": "rak tulkhesh",
            "start_page": 61,
            "source_refs": [{"page": 61}],
            "attributes": dict(attributes),
            "review_flags": ["ocr_da_verificare"],
        }
    ]

    with patch(
        "scripts.repair_monsters_from_source.parse_monster_statblocks",
        side_effect=[primary, comparison],
    ):
        candidate = _agreed_target_candidate(
            [],
            [],
            "manual.pdf",
            "it",
            "Rak Tulkhesh",
            61,
        )

    assert candidate["name"] == "Rak Tulkhesh"
    assert candidate["attributes"]["ocr_independent_agreement"] is True
    assert candidate["attributes"]["ocr_core_only_same_page_agreement"] is True


@pytest.mark.parametrize(
    ("extra_block", "missing_speed", "expected_anchor"),
    [(False, False, True), (True, False, False), (False, True, False)],
)
def test_adrosauro_duplicate_titles_require_one_ordered_local_statblock(
    tmp_path, extra_block, missing_speed, expected_anchor
):
    image_path = tmp_path / "adrosauro.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 1000, 1200), False)
    image.clear_with(255)
    image.save(image_path)
    lines = [(100, "ADROSAURO"), (600, "ADROSAURO")]
    for title_top in ([100, 600] if extra_block else [600]):
        lines.extend(
            [
                (title_top + 60, "Bestia Grande (Dinosauro), senza allineamento"),
                (title_top + 120, "Classe Armatura 11"),
                (title_top + 180, "Punti Ferita 19 (3d10 + 3)"),
            ]
        )
        if not missing_speed:
            lines.append((title_top + 240, "Velocità 12 m"))
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        + "".join(
            f"5\t1\t{index}\t1\t1\t1\t80\t{top}\t220\t30\t95\t{text}\n"
            for index, (top, text) in enumerate(lines, 1)
        )
    )
    with patch(
        "scripts.repair_monsters_from_source.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=tsv, stderr=""),
    ):
        crop = _sparse_anchor_crop_fractions(image_path, "ita", "Adrosauro")
    if expected_anchor:
        assert crop is not None
        assert crop[0] == 0.0
        assert crop[2] == 0.5
        assert 0.45 < crop[1] < 0.55
    else:
        assert crop is None


@pytest.mark.parametrize(
    ("mutation", "accepted"),
    [("none", True), ("duplicate_hp", False), ("missing_eye", False), ("wrong_ca", False)],
)
def test_arciere_action_identity_restore_requires_unique_local_evidence(mutation, accepted):
    from scripts.repair_monsters_from_source import _restore_arciere_title_from_local_actions

    text = (
        "OCR title debris\n"
        "Umanoide Medio, qualsiasi allineamento\n"
        "Classe Armatura 16 (cuoio borchiato)\n"
        "Punti Ferita 75 (10d8 + 30)\n"
        "Velocità 9 m\n"
        "AZIONI\n"
        "Multiattacco. L'arciere effettua attacchi.\n"
        "AZIONI BONUS\n"
        "Occhio dell'arciere. Test sintetico.\n"
    )
    if mutation == "duplicate_hp":
        text += "Punti Ferita 75 (10d8 + 30)\n"
    elif mutation == "missing_eye":
        text = text.replace("Occhio dell'arciere. Test sintetico.\n", "")
    elif mutation == "wrong_ca":
        text = text.replace("Armatura 16", "Armatura 17")
    result = _restore_arciere_title_from_local_actions(text, "Arciere")
    if accepted:
        assert result.replace("ARCIERE\n", "", 1) == text
        assert result.index("ARCIERE") < result.index("Umanoide")
    else:
        assert result == text
    assert _restore_arciere_title_from_local_actions(text, "Babau") == text


@pytest.mark.parametrize("missing_identity", [False, True])
def test_bael_title_restore_preserves_unresolved_dice(missing_identity):
    from scripts.repair_monsters_from_source import _restore_bael_title_from_local_actions

    text = (
        "OCR debris\n"
        "Immondo Grande (Diavolo), legale malvagio\n"
        "Classe Armatura 18 (piastre)\n"
        "Punti Ferita 189 (18410 + 90)\n"
        "Velocità 9 m\n"
        "Resistenza leggendaria. Se Bael fallisce, test.\n"
        "Multiattacco. Bael effettua attacchi.\n"
    )
    if missing_identity:
        text = text.replace("Resistenza leggendaria. Se Bael fallisce, test.\n", "")
    result = _restore_bael_title_from_local_actions(text, "Bael")
    if missing_identity:
        assert result == text
    else:
        assert result.replace("BAEL\n", "", 1) == text
        assert "18410" in result


@pytest.mark.parametrize("duplicate_hp", [False, True])
def test_bael_micro_ocr_uses_unique_ordered_core_row(tmp_path, duplicate_hp):
    from scripts.repair_monsters_from_source import _micro_ocr_hit_points_line

    image_path = tmp_path / "bael.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 500), False)
    image.clear_with(255)
    image.save(image_path)
    text = (
        "BAEL\n"
        "Immondo Grande (Diavolo), legale malvagio\n"
        "Classe Armatura 18 (piastre)\n"
        "Punti Ferita 189 (18410 + 90)\n"
        "Velocità 9 m\n"
        "Rigenerazione. Bael recupera 20 punti ferita.\n"
        "Se Bael inizia con 0 punti ferita, test.\n"
    )
    rows = [
        (30, ["BAEL"]),
        (60, ["Classe", "Armatura", "18", "(piastre)"]),
        (90, ["Punti", "Ferita", "189", "(18410", "+", "90)"]),
        (120, ["Velocità", "9", "m"]),
        (160, ["Rigenerazione.", "Bael", "recupera", "20", "punti", "ferita."]),
    ]
    if duplicate_hp:
        rows.insert(3, (105, ["Punti", "Ferita", "189", "(18410", "+", "90)"]))
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        + "".join(
            f"5\t1\t{block}\t1\t1\t{word}\t{10 + 45 * word}\t{top}\t40\t15\t95\t{value}\n"
            for block, (top, words) in enumerate(rows, 1)
            for word, value in enumerate(words, 1)
        )
    )

    def source_reading(command, *args, **kwargs):
        return tsv if "tsv" in command else "189 (18d10 + 90)\n"

    with patch(
        "scripts.repair_monsters_from_source._run_tesseract_bounded",
        side_effect=source_reading,
    ):
        result = _micro_ocr_hit_points_line(image_path, "ita", 3, text, "Bael")
    if duplicate_hp:
        assert result == text
    else:
        assert result == text.replace("189 (18410 + 90)", "189 (18d10 + 90)")

@pytest.mark.parametrize("mutation", ["none", "missing_type", "duplicate_hp", "missing_trait"])
def test_bodak_identity_requires_complete_independent_local_evidence(mutation):
    from scripts.repair_monsters_from_source import _restore_bodak_title_from_local_traits

    text = (
        "OCR debris\n"
        ". Non morto Medio, generalmente caotico malvagio\n"
        "Classe Armatura 15 (armatura naturale)\n"
        "Punti Ferita 58 (9d8 + 18)\n"
        "Velocità 9 m\n"
        "Ipersensibilità al sole. Il bodak subisce danni, test.\n"
        "Natura insolita. Il bodak non necessita di respirare, test.\n"
    )
    if mutation == "missing_type":
        text = text.replace("Non morto", "on morto")
    elif mutation == "duplicate_hp":
        text += "Punti Ferita 58 (9d8 + 18)\n"
    elif mutation == "missing_trait":
        text = text.replace(
            "Natura insolita. Il bodak non necessita di respirare, test.\n", ""
        )
    result = _restore_bodak_title_from_local_traits(text, "Bodak")
    if mutation == "none":
        assert result.replace("BODAK\n", "", 1) == text.replace(". Non", "Non", 1)
    else:
        assert result == text
    assert _restore_bodak_title_from_local_traits(text, "Babau") == text

@pytest.mark.parametrize("mutation", ["none", "disagreement", "duplicate_geometry"])
def test_bodak_descriptor_micro_requires_two_source_reads(tmp_path, mutation):
    from scripts.repair_monsters_from_source import _micro_ocr_bodak_descriptor

    image_path = tmp_path / "bodak.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 300), False)
    image.clear_with(255)
    image.save(image_path)
    descriptor = "Non morto Medio, generalmente caotico malvagio"
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        + "".join(
            f"5\t1\t{block}\t1\t1\t{word}\t{10 + 70 * word}\t{top}\t60\t15\t95\t{value}\n"
            for block, top in (
                [(1, 40), (2, 70)] if mutation == "duplicate_geometry" else [(1, 40)]
            )
            for word, value in enumerate(descriptor.split(), 1)
        )
    )
    primary = (
        ". Non morto Medio, generalmente caotico malvagio\n"
        "Classe Armatura 15 (armatura naturale)\n"
        "Punti Ferita 58 (9d8 + 18)\n"
        "Velocità 9 m\n"
    )
    comparison = primary.replace(". Non morto", "on morto").replace("9d8", "948")

    def source_reading(command, *args, **kwargs):
        if "tsv" in command:
            return tsv
        if mutation == "disagreement" and command[command.index("--psm") + 1] == "7":
            return "on morto Medio, generalmente caotico malvagio"
        return descriptor

    with patch(
        "scripts.repair_monsters_from_source._run_tesseract_bounded",
        side_effect=source_reading,
    ):
        result = _micro_ocr_bodak_descriptor(image_path, "ita", primary, comparison)
    if mutation == "none":
        assert result[0] == primary.replace(". Non morto", "Non morto")
        assert result[1] == comparison.replace("on morto", "Non morto")
        assert "948" in result[1]
    else:
        assert result == (primary, comparison)

def test_brontosauro_comparison_hp_keeps_independent_geometry_and_numeric_modes(tmp_path):
    from scripts.repair_monsters_from_source import _micro_ocr_hit_points_line

    image_path = tmp_path / "brontosauro.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 300), False)
    image.clear_with(255)
    image.save(image_path)
    text = (
        "BRONTOSAURO\n"
        "Bestia Mastodontica (Dinosauro), senza allineamento\n"
        "Classe Armatura 15 (armatura naturale)\n"
        "Punti Ferita 121 (9420 + 27)\n"
        "Velocità 9 m\n"
    )
    rows = [
        (30, ["BRONTOSAURO"]),
        (60, ["Classe", "Armatura", "15"]),
        (90, ["Punti", "Ferita", "121", "(9420", "+", "27)"]),
        (120, ["Velocità", "9", "m"]),
    ]
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        + "".join(
            f"5\t1\t{block}\t1\t1\t{word}\t{10 + 45 * word}\t{top}\t40\t15\t95\t{value}\n"
            for block, (top, words) in enumerate(rows, 1)
            for word, value in enumerate(words, 1)
        )
    )
    commands = []

    def source_reading(command, *args, **kwargs):
        commands.append(command)
        return tsv if "tsv" in command else "121 (9d20 + 27)\n"

    with patch(
        "scripts.repair_monsters_from_source._run_tesseract_bounded",
        side_effect=source_reading,
    ):
        result = _micro_ocr_hit_points_line(image_path, "ita", 4, text, "Brontosauro")
    assert result == text.replace("9420", "9d20")
    assert commands[0][commands[0].index("--psm") + 1] == "11"
    assert all(
        command[command.index("--psm") + 1] == "6" for command in commands[1:]
    )

@pytest.mark.parametrize("mutation", ["none", "missing_identity", "duplicate_core", "existing_title"])
def test_bulezau_title_restore_requires_observed_heading_and_local_trait(mutation):
    from scripts.repair_monsters_from_source import _restore_bulezau_title_from_local_trait

    text = (
        "BULEZAU\n"
        "Test sintetico di prosa introduttiva.\n"
        "Altra riga sintetica.\n"
        "Altra riga sintetica.\n"
        "Altra riga sintetica.\n"
        "Altra riga sintetica.\n"
        "Immondo Medio (Demone), generalmente caotico malvagio\n"
        "Classe Armatura 14 (armatura naturale)\n"
        "Punti Ferita 52 (7d8 + 21)\n"
        "Velocità 12 m\n"
        "Presenza putrescente. Una creatura che non sia un\n"
        "demone inizia il suo turno entro 9 metri dal bulezau, test.\n"
    )
    if mutation == "missing_identity":
        text = text.replace("dal bulezau", "dal demone")
    elif mutation == "duplicate_core":
        text += "Classe Armatura 14 (armatura naturale)\n"
    elif mutation == "existing_title":
        text = text.replace("Immondo Medio", "BULEZAU\nImmondo Medio")
    result = _restore_bulezau_title_from_local_trait(text, "Bulezau")
    if mutation == "none":
        assert result.replace("BULEZAU\nImmondo", "Immondo", 1) == text
    else:
        assert result == text
    assert _restore_bulezau_title_from_local_trait(text, "Babau") == text

@pytest.mark.parametrize("mutation", ["none", "duplicate_hp", "wrong_type", "non_border_prefix"])
def test_celeresto_core_prefix_cleanup_is_scoped_and_preserves_values(mutation):
    from scripts.repair_monsters_from_source import _clean_celeresto_core_prefixes

    text = (
        "CELERESTO\n"
        "Folletto Minuscolo, generalmente caotico malvagio\n"
        "Classe Armatura 16\n"
        "i Punti Ferita 10 (3d4 + 3)\n"
        "i Velocità 36 m\n"
    )
    if mutation == "duplicate_hp":
        text += "Punti Ferita 10 (3d4 + 3)\n"
    elif mutation == "wrong_type":
        text = text.replace("Folletto", "Bestia")
    elif mutation == "non_border_prefix":
        text = text.replace("i Punti", "test Punti")
    result = _clean_celeresto_core_prefixes(text, "Celeresto")
    if mutation == "none":
        assert result == text.replace("i Punti", "Punti").replace("i Velocità", "Velocità")
    else:
        assert result == text
    assert _clean_celeresto_core_prefixes(text, "Babau") == text

@pytest.mark.parametrize("duplicate_target_hp", [False, True])
@pytest.mark.parametrize("nearby_speed", [False, True])
def test_delfino_hp_crop_does_not_use_sollazzatore(tmp_path, duplicate_target_hp, nearby_speed):
    from scripts.repair_monsters_from_source import _micro_ocr_hit_points_line

    image_path = tmp_path / "delfino.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 700, 500), False)
    image.clear_with(255)
    image.save(image_path)
    text = (
        "DELFINO\nBestia Media, senza allineamento\n"
        "Classe Armatura 12 (armatura naturale)\n"
        "Punti Ferita 11 (248 + 2)\nVelocità 0 m, nuotare 18 m\n"
        "Apnea. Il delfino può trattenere il respiro, test.\n"
        "DELFINO SOLLAZZATORE\nFolletto Medio, generalmente caotico buono\n"
        "Classe Armatura 14 (armatura naturale)\n"
        "Punti Ferita 27 (5d8 + 5)\nVelocità 0 m, nuotare 18 m\n"
    )
    rows = [
        (30, ["DELFINO"]),
        (60, ["Classe", "Armatura", "12"]),
        (90, ["Punti", "Ferita", "11", "(248", "+", "2)"]),
        (120, ["Velocità", "0", "m"]),
        (160, ["Apnea.", "Il", "delfino", "test."]),
        (190, ["DELFINO", "SOLLAZZATORE"]),
        (220, ["Classe", "Armatura", "14"]),
        (250, ["Punti", "Ferita", "27", "(5d8", "+", "5)"]),
        (280, ["Velocità", "0", "m"]),
    ]
    if not nearby_speed:
        rows.insert(6, (205, ["Folletto", "Medio,", "caotico", "buono"]))
    if duplicate_target_hp:
        rows.insert(3, (105, ["Punti", "Ferita", "11", "(248", "+", "2)"]))
        text = text.replace("Velocità 0 m", "Punti Ferita 11 (248 + 2)\nVelocità 0 m", 1)
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        + "".join(
            f"5\t1\t{block}\t1\t1\t{word}\t{10 + 45 * word}\t{top}\t40\t15\t95\t{value}\n"
            for block, (top, words) in enumerate(rows, 1)
            for word, value in enumerate(words, 1)
        )
    )
    commands = []

    def source_reading(command, *args, **kwargs):
        commands.append(command)
        return tsv if "tsv" in command else "11 (2d8 + 2)\n"

    with patch(
        "scripts.repair_monsters_from_source._run_tesseract_bounded",
        side_effect=source_reading,
    ):
        result = _micro_ocr_hit_points_line(image_path, "ita", 4, text, "Delfino")
    if duplicate_target_hp or nearby_speed:
        assert result == text
    else:
        assert result == text.replace("11 (248 + 2)", "11 (2d8 + 2)")
        assert "27 (5d8 + 5)" in result
        assert commands[0][commands[0].index("--psm") + 1] == "11"
        assert commands[1][commands[1].index("--psm") + 1] == "6"

@pytest.mark.parametrize("mutation", ["none", "missing_trait", "ambiguous_type"])
def test_delfino_title_identity_ignores_sollazzatore_shared_speed(mutation):
    from scripts.repair_monsters_from_source import _restore_delfino_title_from_local_traits

    text = (
        "Dario\nBestia Media, senza allineamento\n"
        "Classe Armatura 12 (armatura naturale)\n"
        "Punti Ferita 11 (248 + 2)\nVelocità 0 m, nuotare 18 m\n"
        "Apnea. Il delfino può trattenere il respiro, test.\n"
        "Se, prima del colpo, il delfino ha nuotato per metri, test.\n"
        "DELFINO SOLLAZZATORE\nFolletto Medio, generalmente caotico buono\n"
        "Classe Armatura 14 (armatura naturale)\n"
        "Punti Ferita 27 (5d8 + 5)\nVelocità 0 m, nuotare 18 m\n"
    )
    if mutation == "missing_trait":
        text = text.replace("il delfino ha nuotato", "ha nuotato")
    elif mutation == "ambiguous_type":
        text += "Bestia Media, senza allineamento\n"
    result = _restore_delfino_title_from_local_traits(text, "Delfino")
    if mutation == "none":
        assert result.replace("DELFINO\nBestia", "Bestia", 1) == text
        assert "248" in result
        assert "DELFINO SOLLAZZATORE" in result
    else:
        assert result == text
    assert _restore_delfino_title_from_local_traits(text, "Babau") == text

@pytest.mark.parametrize("mutation", ["none", "sapiente_type", "sapiente_hp", "missing_trait"])
def test_derro_title_restore_does_not_accept_sapiente(mutation):
    from scripts.repair_monsters_from_source import _restore_derro_title_from_local_traits

    text = (
        "DERR\nOCR debris\n"
        "Aberrazione Piccola, generalmente caotica malvagia\n"
        "Classe Armatura 13 (armatura di cuoio)\n"
        "Punti Ferita 13 (3d6 + 3)\nVelocità 9 m\n"
        "Resistenza alla magia. Il derro dispone di vantaggio, test.\n"
        "i Sensibilità al sole. Al sole, il derro ha svantaggio, test.\n"
    )
    if mutation == "sapiente_type":
        text = text.replace("Aberrazione Piccola,", "Aberrazione Piccola (Stregone),")
    elif mutation == "sapiente_hp":
        text = text.replace("13 (3d6 + 3)", "36 (8d6 + 8)")
    elif mutation == "missing_trait":
        text = text.replace("Il derro dispone", "Dispone")
    result = _restore_derro_title_from_local_traits(text, "Derro")
    if mutation == "none":
        assert result.replace("DERRO\nAberrazione", "Aberrazione", 1) == text
    else:
        assert result == text
    assert _restore_derro_title_from_local_traits(text, "Babau") == text

@pytest.mark.parametrize("mutation", ["none", "missing_trait", "duplicate_hp", "wrong_type"])
def test_divoratore_identity_requires_unique_local_traits(mutation):
    from scripts.repair_monsters_from_source import _restore_divoratore_title_from_local_traits

    text = (
        "OCR debris\n"
        "Non morto Grande, generalmente caotico malvagio\n"
        "Classe Armatura 16 (armatura naturale)\n"
        "Punti Ferita 189 (18410 + 90)\nVelocità 9 m\n"
        "Natura insolita. Un divoratore non necessita di respirare, test.\n"
        "Multiattacco. Il divoratore effettua attacchi, test.\n"
    )
    if mutation == "missing_trait":
        text = text.replace("Un divoratore", "La creatura")
    elif mutation == "duplicate_hp":
        text += "Punti Ferita 189 (18410 + 90)\n"
    elif mutation == "wrong_type":
        text = text.replace("Non morto", "Immondo")
    result = _restore_divoratore_title_from_local_traits(text, "Divoratore")
    if mutation == "none":
        assert result.replace("DIVORATORE\n", "", 1) == text
        assert "18410" in result
    else:
        assert result == text
    assert _restore_divoratore_title_from_local_traits(text, "Babau") == text


@pytest.mark.parametrize("duplicate_hp", [False, True])
def test_divoratore_micro_ocr_uses_unique_core_not_body_hp(tmp_path, duplicate_hp):
    from scripts.repair_monsters_from_source import _micro_ocr_hit_points_line

    image_path = tmp_path / "divoratore.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 500), False)
    image.clear_with(255)
    image.save(image_path)
    text = (
        "DIVORATORE\nNon morto Grande, generalmente caotico malvagio\n"
        "Classe Armatura 16 (armatura naturale)\n"
        "Punti Ferita 189 (18410 + 90)\nVelocità 9 m\n"
        "Il divoratore recupera punti ferita, test.\n"
    )
    rows = [
        (30, ["DIVORATORE"]),
        (60, ["Classe", "Armatura", "16"]),
        (90, ["Punti", "Ferita", "189", "(18410", "+", "90)"]),
        (120, ["Velocità", "9", "m"]),
        (160, ["Il", "divoratore", "recupera", "punti", "ferita."]),
    ]
    if duplicate_hp:
        rows.insert(3, (105, ["Punti", "Ferita", "189", "(18410", "+", "90)"]))
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        + "".join(
            f"5\t1\t{block}\t1\t1\t{word}\t{10 + 45 * word}\t{top}\t40\t15\t95\t{value}\n"
            for block, (top, words) in enumerate(rows, 1)
            for word, value in enumerate(words, 1)
        )
    )
    commands = []

    def source_reading(command, *args, **kwargs):
        commands.append(command)
        return tsv if "tsv" in command else "189 (18d10 + 90)\n"

    with patch(
        "scripts.repair_monsters_from_source._run_tesseract_bounded",
        side_effect=source_reading,
    ):
        result = _micro_ocr_hit_points_line(image_path, "ita", 4, text, "Divoratore")
    if duplicate_hp:
        assert result == text
    else:
        assert result == text.replace("18410", "18d10")
        assert commands[0][commands[0].index("--psm") + 1] == "11"
        assert commands[1][commands[1].index("--psm") + 1] == "6"

@pytest.mark.parametrize("mutation", ["none", "disagreement", "duplicate_geometry"])
def test_draegloth_descriptor_micro_requires_two_source_reads(tmp_path, mutation):
    from scripts.repair_monsters_from_source import _micro_ocr_draegloth_descriptor

    image_path = tmp_path / "draegloth.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 300), False)
    image.clear_with(255)
    image.save(image_path)
    descriptor = "Immondo Grande (Demone), generalmente caotico malvagio"
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        + "".join(
            f"5\t1\t{block}\t1\t1\t{word}\t{10 + 70 * word}\t{top}\t60\t15\t95\t{value}\n"
            for block, top in (
                [(1, 40), (2, 70)] if mutation == "duplicate_geometry" else [(1, 40)]
            )
            for word, value in enumerate(descriptor.split(), 1)
        )
    )
    primary = (
        ". Immondo Grande (Demone), generalmente caotico malvagio\n"
        "Classe Armatura 15 (armatura naturale)\n"
        "Punti Ferita 123 (13d10 + 52)\n"
        "Velocità 9 m\n"
    )
    comparison = primary.replace(". Immondo", "lmmondo").replace("13d10", "13410")

    def source_reading(command, *args, **kwargs):
        if "tsv" in command:
            return tsv
        if mutation == "disagreement" and command[command.index("--psm") + 1] == "7":
            return "lmmondo Grande (Demone), generalmente caotico malvagio"
        return descriptor

    with patch(
        "scripts.repair_monsters_from_source._run_tesseract_bounded",
        side_effect=source_reading,
    ):
        result = _micro_ocr_draegloth_descriptor(image_path, "ita", primary, comparison)
    if mutation == "none":
        assert result[0] == primary.replace(". Immondo", "Immondo")
        assert result[1] == comparison.replace("lmmondo", "Immondo")
        assert "13410" in result[1]
    else:
        assert result == (primary, comparison)


def test_deforme_suffix_cleanup_preserves_source_attributes_and_inputs():
    attributes = {
        "classe_armatura": "15 (armatura naturale)",
        "punti_ferita": "10 (4d6 - 4)",
        "velocita": "12 m",
        "synthetic_provenance": "independent primary source",
    }
    primary = {
        "name": "Addolorato Deforme",
        "normalized_name": "addolorato deforme",
        "start_page": 46,
        "source_refs": [{"page": 46}],
        "attributes": attributes,
    }
    comparison = {
        **primary,
        "name": "ADDOLORATO DEFORME hi",
        "normalized_name": "addolorato deforme hi",
        "attributes": {**attributes, "classe_armatura": "15 (armatura naturale) V"},
    }
    before = json.dumps([primary, comparison], sort_keys=True)
    with patch(
        "scripts.repair_monsters_from_source.parse_monster_statblocks",
        side_effect=[[primary], [comparison]],
    ):
        candidate = _agreed_target_candidate(
            [], [], "synthetic.pdf", "it", "Addolorato Deforme", 45
        )
    assert candidate["attributes"] == attributes
    assert json.dumps([primary, comparison], sort_keys=True) == before


def test_deforme_ambiguous_identity_cannot_inject_expected_core():
    attributes = {
        "classe_armatura": "16 (armatura naturale)",
        "punti_ferita": "14 (4d6)",
        "velocita": "9 m",
    }
    primary = {
        "name": "Addolorato Deforme",
        "normalized_name": "addolorato deforme",
        "start_page": 46,
        "source_refs": [{"page": 46}],
        "attributes": attributes,
    }
    comparison = {
        **primary,
        "name": "ADDOLORATO DEFORME hi",
        "normalized_name": "addolorato deforme hi",
        "attributes": {**attributes, "classe_armatura": "16 (armatura naturale) V"},
    }
    before = json.dumps([primary, comparison], sort_keys=True)
    with (
        patch(
            "scripts.repair_monsters_from_source.parse_monster_statblocks",
            side_effect=[[primary], [comparison]],
        ),
        patch(
            "scripts.repair_monsters_from_source.agreed_monster_records",
            return_value=[],
        ),
        pytest.raises(RepairBlocked) as caught,
    ):
        _agreed_target_candidate(
            [], [], "synthetic.pdf", "it", "Addolorato Deforme", 45
        )
    assert caught.value.reason == "no_unique_independent_agreement"
    assert json.dumps([primary, comparison], sort_keys=True) == before


@pytest.mark.parametrize(
    "record_overrides,logical_source,expected_calls",
    [
        ({}, "mpmm_2022_it", 2),
        ({"id": "ref_25a60967a5b8526fbb235e29d243c019"}, "mpmm_2022_it", 1),
        ({"name": "Another Monster"}, "mpmm_2022_it", 1),
        ({"review_status": "verified"}, "mpmm_2022_it", 1),
        ({}, "another_source", 1),
    ],
)
def test_korred_invalid_agreement_retries_sparse_without_bypassing_hp_gate(
    record_overrides, logical_source, expected_calls
):
    record = {
        "id": "ref_4b2e9b5984dd506d89caf10b4f15c3fd",
        "name": "Korred",
        "review_status": "pending",
        **record_overrides,
    }
    source = {
        "logical_source_id": logical_source,
        "physical_filename": "synthetic.pdf",
        "physical_pages": 100,
    }
    candidate = {
        "name": "Korred",
        "attributes": {
            "classe_armatura": "17",
            "punti_ferita": "unreadable",
            "velocita": "9 m",
        },
    }
    args = SimpleNamespace(
        dpi=220, languages="ita", psm=6, comparison_psm=4,
        target_set="batch_mpmm_pending_131",
    )
    with (
        patch.object(repair, "resolve_source", return_value=(source, {"page": 10})),
        patch.object(repair.SourcePdfCache, "get", return_value=Path("synthetic.pdf")),
        patch.object(
            repair, "_ocr_source_window", return_value=([], [], {10: {}})
        ) as ocr,
        patch.object(repair, "_agreed_target_candidate", return_value=candidate),
        pytest.raises(repair.RepairBlocked) as caught,
    ):
        asyncio.run(
            repair._repair_one(None, record, [], repair.SourcePdfCache("", False), args)
        )
    assert caught.value.reason == "repaired_candidate_failed_gates"
    assert "HP_format_error" in caught.value.detail
    assert ocr.call_count == expected_calls
    budget = ocr.call_args_list[0].kwargs["ocr_budget_started_at"]
    assert budget[1] == 60.0
    if expected_calls == 2:
        assert ocr.call_args_list[1].kwargs["sparse_full_page"] is True
        assert ocr.call_args_list[1].kwargs["ocr_budget_started_at"] is budget


def test_bheur_corrupted_candidate_reports_evidence_and_still_blocks():
    candidate = {
        "name": "Megera Bheur |",
        "start_page": 84,
        "source_refs": [{"filename": "synthetic.pdf", "page": 84}],
        "attributes": {
            "classe_armatura": "17 (armatura naturale)",
            "punti_ferita": "91 (14d8 + 28)",
            "velocita": "9 m",
        },
    }
    with pytest.raises(RepairBlocked) as caught:
        build_repair_proposal({"id": "ref_f2cee258e0c45f8d96d22bb9f71c9e7a"}, candidate)
    assert caught.value.reason == "repaired_candidate_corrupted_name"
    assert caught.value.diagnostics["candidate_name"] == candidate["name"]
    assert caught.value.diagnostics["candidate_core"] == candidate["attributes"]
    assert caught.value.diagnostics["candidate_source_refs"] == candidate["source_refs"]


@pytest.mark.parametrize(
    "text",
    [
        "MEGERA | BHEUR\n", "| MEGERA BHEUR altro\n", "|| MEGERA BHEUR\n",
        "| MEGERA BHEUR\n| MEGERA BHEUR\n",
    ],
)
def test_bheur_rule_isolation_refuses_other_noise_and_duplicate_titles(text):
    assert repair._isolate_bheur_title_rule(text) == text


def test_bheur_rule_isolation_retains_debris_and_all_numeric_source_text():
    text = "| MEGERA BHEUR\nClasse Armatura 17\nPunti Ferita 91 (14d8 + 28)\n"
    assert repair._isolate_bheur_title_rule(text) == text.replace(
        "| MEGERA BHEUR", "|\nMEGERA BHEUR"
    )


@pytest.mark.parametrize("comparison_ca", ["17", "18"])
def test_bheur_isolated_rule_still_requires_independent_core_agreement(comparison_ca):
    text = (
        "| MEGERA BHEUR\nFolletto Medio, caotico malvagio\n"
        "Classe Armatura 17 (armatura naturale)\nPunti Ferita 91 (14d8 + 28)\n"
        "Velocità 9 m, volare 15 m\nFor Des Cos Int Sag Car\n"
        "13 (+1) 16 (+3) 14 (+2) 12 (+1) 13 (+1) 16 (+3)\n"
        "Sensi scurovisione 18 m\nLinguaggi Comune\nSfida 7\nAzioni\nArtiglio.\n"
    )
    before = [(84, text)]
    comparison = [(84, text.replace("Armatura 17", f"Armatura {comparison_ca}"))]
    if comparison_ca != "17":
        with pytest.raises(RepairBlocked):
            _agreed_target_candidate(
                before, comparison, "synthetic.pdf", "it", "Megera Bheur", 84,
                isolate_bheur_title_rule=True,
            )
    else:
        candidate = _agreed_target_candidate(
            before, comparison, "synthetic.pdf", "it", "Megera Bheur", 84,
            isolate_bheur_title_rule=True,
        )
        assert candidate["name"] == "MEGERA BHEUR"
        assert candidate["attributes"]["punti_ferita"] == "91 (14d8 + 28)"
        assert candidate["source_refs"][0]["page"] == 84
        raw_candidate = _agreed_target_candidate(
            before, comparison, "synthetic.pdf", "it", "Megera Bheur", 84
        )
        with pytest.raises(RepairBlocked, match="repaired_candidate_corrupted_name"):
            build_repair_proposal(
                {"id": "ref_f2cee258e0c45f8d96d22bb9f71c9e7a"}, raw_candidate
            )
    assert before == [(84, text)]


def test_korred_hp_anchor_ignores_narrative_mentions_and_prose_hp():
    lines = [
        "KORRED", "Il korred usa i suoi capelli.", "Punti Ferita nella descrizione.",
        "KORRED", "Folletto Piccolo, caotico neutrale", "Classe Armatura 17",
        "Punti Ferita 93 (11d6 + 55)", "Velocità 9 m, scavare 9 m",
        "Il korred recupera Punti Ferita.", "Punti Ferita nella capacità del korred.",
    ]
    assert repair._korred_structural_hp_anchors(lines) == ([3], [6])


@pytest.mark.parametrize("damage", ["duplicate_hp", "missing_speed", "duplicate_block", "other_title"])
def test_korred_structural_hp_anchor_fails_closed_on_missing_or_ambiguous_block(damage):
    lines = ["KORRED", "Folletto Piccolo", "Classe Armatura 17", "Punti Ferita unreadable", "Velocità 9 m"]
    if damage == "duplicate_hp":
        lines.insert(4, "Punti Ferita 14 (4d6)")
    elif damage == "missing_speed":
        lines.pop()
    elif damage == "other_title":
        lines[0] = "ALTRO MOSTRO"
    else:
        # Keep independent ambiguous blocks; do not collapse equal HP values.
        lines = lines + ["Azioni"] * 9 + lines
        titles, hp = repair._korred_structural_hp_anchors(lines)
        assert len(titles) == len(hp) == 2
        return
    assert repair._korred_structural_hp_anchors(lines) == ([], [])


def test_korred_duplicate_ca_anchor_is_not_collapsed():
    lines = ["KORRED", "Folletto Piccolo", "Classe Armatura 17", "Classe Armatura 18", "Punti Ferita 93 (11d6 + 55)", "Velocità 9 m"]
    assert repair._korred_structural_hp_anchors(lines) == ([0, 0], [4, 4])


def test_korred_micro_crop_replaces_only_unique_structural_hp(tmp_path):
    lines = [
        "KORRED", "Il korred usa i capelli.", "Punti Ferita nella descrizione.",
        "KORRED", "Folletto Piccolo", "Classe Armatura 17",
        "Punti Ferita unreadable", "Velocità 9 m, scavare 9 m",
        "Il korred recupera Punti Ferita.", "Punti Ferita nella capacità del korred.",
    ]
    image_path = tmp_path / "synthetic-korred.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 900, 400), False)
    image.clear_with(255)
    image.save(image_path)
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    rows = [
        f"5\t1\t1\t1\t{index + 1}\t{word_index + 1}\t{20 + word_index * 90}\t{15 + index * 25}\t80\t12\t95\t{word}"
        for index, line in enumerate(lines)
        for word_index, word in enumerate(line.split())
    ]
    page_text = "\n".join(lines) + "\n"
    with patch.object(
        repair.subprocess, "run", side_effect=[
            CompletedProcess([], 0, stdout=header + "\n".join(rows) + "\n", stderr=""),
            CompletedProcess([], 0, stdout="93 (11d6 + 55)\n", stderr=""),
        ],
    ):
        result = _micro_ocr_hit_points_line(image_path, "ita", 3, page_text, "Korred")
    assert result == page_text.replace("Punti Ferita unreadable", "Punti Ferita 93 (11d6 + 55)")


def test_mpmm_core_diagnostics_preserve_failed_agreement_and_exclude_page_text():
    primary = {
        "name": "Mostro Prova", "normalized_name": "mostro prova",
        "start_page": 12, "source_refs": [{"page": 12}],
        "full_text": "PRIVATE_PAGE_TEXT_MUST_NOT_BE_EMITTED",
        "attributes": {"classe_armatura": "17", "punti_ferita": "93 (11d6 + 55)", "velocita": "9 m"},
    }
    comparison = {**primary, "attributes": {**primary["attributes"], "classe_armatura": "18"}}
    with (
        patch.object(repair, "parse_monster_statblocks", side_effect=[[primary], [comparison]]),
        pytest.raises(RepairBlocked) as caught,
    ):
        _agreed_target_candidate(
            [], [], "synthetic.pdf", "it", "Mostro Prova", 12,
            include_core_diagnostics=True,
        )
    assert caught.value.reason == "no_unique_independent_agreement"
    diagnostic = caught.value.diagnostics
    assert diagnostic["primary_core_candidates"][0]["core"] == primary["attributes"]
    assert diagnostic["comparison_core_candidates"][0]["core"] == comparison["attributes"]
    assert "PRIVATE_PAGE_TEXT_MUST_NOT_BE_EMITTED" not in json.dumps(diagnostic)


@pytest.mark.parametrize("refs", [[44, 45], [44], [44, 45, 45]])
def test_grung_brado_audit_uses_only_the_unique_registered_variant_page(refs):
    record = {
        "id": "ref_dfcfc30092385b9d9facc6af40035fd4", "name": "Grung Brado",
        "review_status": "pending",
        "source_refs": [{"filename": "synthetic.pdf", "page": page} for page in refs],
    }
    source = {"physical_filename": "synthetic.pdf", "physical_pages": 100, "logical_source_id": "mpmm_2022_it"}
    args = SimpleNamespace(dpi=220, languages="ita", psm=6, comparison_psm=4, target_set="batch_mpmm_pending_131")
    before = json.dumps(record, sort_keys=True)
    with (
        patch.object(repair, "resolve_source", return_value=(source, record["source_refs"][0])),
        patch.object(repair.SourcePdfCache, "get", return_value=Path("synthetic.pdf")),
        patch.object(repair, "_ocr_source_window", side_effect=RepairBlocked("pilot_stop")) as ocr,
        pytest.raises(RepairBlocked) as caught,
    ):
        asyncio.run(repair._repair_one(None, record, [], repair.SourcePdfCache("", False), args))
    if refs == [44, 45]:
        assert caught.value.reason == "pilot_stop"
        assert ocr.call_args.args[1] == 45
        assert ocr.call_args.kwargs["target_page_only"] is True
        assert ocr.call_args.kwargs["ocr_budget_started_at"][1] == 60.0
    else:
        assert caught.value.reason == "source_page_override_ref_drift"
        ocr.assert_not_called()
    assert json.dumps(record, sort_keys=True) == before


@pytest.mark.parametrize("identifier,name,page", [
    ("ref_09eb88310e015ab6aa41d9dc35874f48", "Grung Guerriero D'Élite", 45),
    ("ref_25a60967a5b8526fbb235e29d243c019", "Capo Vegepigmeo", 65),
])
def test_pending_variant_audit_excludes_unregistered_neighbor_pages(identifier, name, page):
    record = {
        "id": identifier, "name": name,
        "review_status": "pending",
        "source_refs": [{"filename": "synthetic.pdf", "page": page}],
    }
    source = {"physical_filename": "synthetic.pdf", "physical_pages": 100, "logical_source_id": "mpmm_2022_it"}
    args = SimpleNamespace(dpi=220, languages="ita", psm=6, comparison_psm=4, target_set="batch_mpmm_pending_131")
    before = json.dumps(record, sort_keys=True)
    with (
        patch.object(repair, "resolve_source", return_value=(source, record["source_refs"][0])),
        patch.object(repair.SourcePdfCache, "get", return_value=Path("synthetic.pdf")),
        patch.object(repair, "_ocr_source_window", side_effect=RepairBlocked("pilot_stop")) as ocr,
        pytest.raises(RepairBlocked) as caught,
    ):
        asyncio.run(repair._repair_one(None, record, [], repair.SourcePdfCache("", False), args))
    assert caught.value.reason == "pilot_stop"
    assert ocr.call_args.args[1] == page
    assert ocr.call_args.kwargs["target_page_only"] is True
    assert ocr.call_args.kwargs["ocr_budget_started_at"][1] == 60.0
    assert json.dumps(record, sort_keys=True) == before


@pytest.mark.parametrize("suffix", ["Ù", "i"])
def test_kithrak_isolation_preserves_numeric_text_and_raw_glyph(suffix):
    text = f"GITHYANKI KITH'RAK {suffix}\nClasse Armatura 18 (piastre) (\nPunti Ferita 180 (24d8 + 72)\nVelocità 9 m 3\n"
    assert repair._isolate_kithrak_title_debris(text) == text.replace(
        f"GITHYANKI KITH'RAK {suffix}", f"{suffix}\nGITHYANKI KITH'RAK"
    )


@pytest.mark.parametrize("title", [
    "GITHYANKI KITH'RAK altro", "GITHYANKI KITH'RAK ii",
    "GITHYANKI KITH'RAK I", "GITHYANKI KITH'RAK Ù\nGITHYANKI KITH'RAK i",
])
def test_kithrak_isolation_rejects_unobserved_or_duplicate_titles(title):
    assert repair._isolate_kithrak_title_debris(title) == title


@pytest.mark.parametrize("comparison_ca", ["18", "19"])
def test_kithrak_isolated_title_keeps_independent_numeric_gate(comparison_ca):
    text = (
        "GITHYANKI KITH'RAK Ù\nUmanoide Medio, legale malvagio\n"
        "Classe Armatura 18 (piastre)\nPunti Ferita 180 (24d8 + 72)\n"
        "Velocità 9 m\nFor Des Cos Int Sag Car\n"
        "18 (+4) 16 (+3) 16 (+3) 16 (+3) 15 (+2) 17 (+3)\n"
        "Sensi percezione passiva 12\nLinguaggi Gith\nSfida 12\nAzioni\nSpada.\n"
    )
    primary = [(36, text)]
    comparison = [(36, text.replace("RAK Ù", "RAK i").replace("Armatura 18", f"Armatura {comparison_ca}"))]
    if comparison_ca == "18":
        candidate = _agreed_target_candidate(
            primary, comparison, "synthetic.pdf", "it", "Githyanki Kith'Rak", 36,
            isolate_kithrak_title_debris=True,
        )
        assert candidate["name"] == "GITHYANKI KITH'RAK"
        assert candidate["attributes"]["punti_ferita"] == "180 (24d8 + 72)"
    else:
        with pytest.raises(RepairBlocked):
            _agreed_target_candidate(
                primary, comparison, "synthetic.pdf", "it", "Githyanki Kith'Rak", 36,
                isolate_kithrak_title_debris=True,
            )
    assert primary == [(36, text)]


@pytest.mark.parametrize("ca,speed", [
    ("18 (piastre) (", "9 m"), ("18 (piastre)", "9 m 3"),
    ("18 (piastre) (", "9 m 3"),
])
def test_pending_kithrak_agreed_core_debris_still_blocks(ca, speed):
    legacy = {
        "id": "ref_e4ce5aac88725918a98e4f1dacc8cd1a", "name": "Githyanki Kith'Rak",
        "review_status": "pending", "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "attributes": {},
    }
    candidate = {
        "name": legacy["name"], "start_page": 36, "source_refs": [{"page": 36}],
        "attributes": {"classe_armatura": ca, "punti_ferita": "180 (24d8 + 72)", "velocita": speed},
    }
    before = json.dumps([legacy, candidate], sort_keys=True)
    with pytest.raises(RepairBlocked) as caught:
        build_repair_proposal(legacy, candidate)
    assert caught.value.reason == "repaired_candidate_core_debris"
    assert json.dumps([legacy, candidate], sort_keys=True) == before


def test_pending_kithrak_clean_core_gate_does_not_assume_expected_values():
    legacy = {
        "id": "ref_e4ce5aac88725918a98e4f1dacc8cd1a", "name": "Githyanki Kith'Rak",
        "review_status": "pending", "review_flags": ["ocr_da_verificare", "source_guided_repair"],
        "attributes": {},
    }
    candidate = {
        "name": legacy["name"], "start_page": 36, "source_refs": [{"page": 36}],
        "attributes": {"classe_armatura": "17 (armatura naturale)", "punti_ferita": "93 (11d6 + 55)", "velocita": "12 m"},
    }
    assert build_repair_proposal(legacy, candidate)["attributes"] == candidate["attributes"]


@pytest.mark.parametrize("target", ["Oscuride", "Oscuride Anziano"])
@pytest.mark.parametrize("mutation", ["none", "ca_disagreement", "duplicate", "missing_exact"])
def test_oscuride_exact_identity_separates_variant_without_bypassing_core(mutation, target):
    base = {
        "name": "OSCURIDE", "normalized_name": "oscuride", "start_page": 13,
        "source_refs": [{"page": 13}],
        "attributes": {"classe_armatura": "14 (armatura di cuoio)", "punti_ferita": "13 (3d6 + 3)", "velocita": "9 m"},
    }
    variant = {
        **base, "name": "OSCURIDE ANZIANO", "normalized_name": "oscuride anziano",
        "attributes": {"classe_armatura": "15 (armatura di cuoio borchiato)", "punti_ferita": "27 (5d8 + 5)", "velocita": "9 m"},
    }
    primary = [base, variant]
    comparison = [base, variant]
    selected = base if target == "Oscuride" else variant
    other = variant if target == "Oscuride" else base
    if mutation == "ca_disagreement":
        comparison = [{**selected, "attributes": {**selected["attributes"], "classe_armatura": "16"}}, other]
    elif mutation == "duplicate":
        primary = [selected, selected, other]
    elif mutation == "missing_exact":
        comparison = [other]
    before = json.dumps([primary, comparison], sort_keys=True)
    with patch.object(repair, "parse_monster_statblocks", side_effect=[primary, comparison]):
        if mutation == "none":
            candidate = _agreed_target_candidate(
                [], [], "synthetic.pdf", "it", target, 13,
                require_exact_target_identity=True,
            )
            assert candidate["name"] == selected["name"]
            assert candidate["attributes"]["punti_ferita"] == selected["attributes"]["punti_ferita"]
        else:
            with pytest.raises(RepairBlocked):
                _agreed_target_candidate(
                    [], [], "synthetic.pdf", "it", target, 13,
                    require_exact_target_identity=True,
                )
    assert json.dumps([primary, comparison], sort_keys=True) == before

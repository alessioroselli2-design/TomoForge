import asyncio
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import fitz

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
    HIT_POINTS_FULL_SPECTRUM_CONTRASTS,
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
    _remove_isolated_foreground_noise,
    _micro_ocr_hit_points_line,
    _otsu_inverted_samples,
    _sample_variance,
    _should_retry_dynamic_layout,
    _sparse_anchor_crop_fractions,
    _sparse_anchor_matches,
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
)


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
            "Fraz-Urb'Luu",
        )

    assert result == "Classe Armatura 17\nVelocità 3 m"
    run.assert_not_called()


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
        "Quetzalcoatlus\nPunti Ferita 30 (4d12 + 4)\n"
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
    assert payload["page_text_local_hp_count"] == 0
    assert payload["tsv_page_wide_hp_label_count"] == 1
    assert payload["tsv_name_anchor_found"] is False
    assert payload["tsv_local_label_found"] is False


def test_hp_micro_ocr_subprocess_crash_fails_closed_without_aborting(tmp_path, capsys):
    image_path = tmp_path / "column.png"
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 200), False)
    image.clear_with(255)
    image.save(image_path)
    tsv = (
        "level\\tpage_num\\tblock_num\\tpar_num\\tline_num\\tword_num\\tleft\\ttop\\twidth\\theight\\tconf\\ttext\\n"
        "5\\t1\\t1\\t1\\t1\\t1\\t20\\t20\\t120\\t20\\t95\\tLarvico\\n"
        "5\\t1\\t1\\t1\\t2\\t1\\t20\\t50\\t45\\t20\\t95\\tPunti\\n"
        "5\\t1\\t1\\t1\\t2\\t2\\t72\\t50\\t50\\t20\\t95\\tFerita\\n"
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
            image_path, "ita", 3, "Larvico\\nPunti Ferita ???\\n", "Larvico"
        )

    assert result == "Larvico\\nPunti Ferita ???\\n"
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
    assert (
        run.call_args_list[4]
        .args[0][1]
        .endswith("hit-points-1.2-dark-dilated-upscaled-x4-otsu-inverted.png")
    )
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
    assert HIT_POINTS_FULL_SPECTRUM_CONTRASTS == (
        0.8,
        1.1,
        1.4,
        1.7,
        2.0,
        2.3,
        2.6,
        2.9,
        3.2,
        3.5,
    )
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
    assert (
        run.call_args_list[4]
        .args[0][1]
        .endswith("hit-points-1.2-dark-dilated-upscaled-x4-otsu-inverted.png")
    )


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
    assert '"initial_raw": "310 (27d412 + 135)\\n"' in diagnostic
    assert '"otsu_inverted_raw": "310 (27d12 + 135)\\n"' in diagnostic
    assert '"otsu_hp_format_error": false' in diagnostic
    assert '"upscaled_otsu_inverted_raw": null' in diagnostic


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
    assert (
        run.call_args_list[4]
        .args[0][1]
        .endswith("hit-points-1.2-dark-dilated-upscaled-x4-otsu-inverted.png")
    )
    diagnostic = capsys.readouterr().out
    assert '"otsu_hp_format_error": true' in diagnostic
    assert '"upscaled_otsu_hp_format_error": true' in diagnostic
    assert '"superscaled_otsu_hp_format_error": true' in diagnostic
    assert '"full_spectrum_attempt_count": 1' in diagnostic
    assert '"morphology": "erosion"' in diagnostic
    assert '"threshold": 80' in diagnostic


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


def test_sparse_page_anchor_compacts_layout_whitespace_but_requires_identity():
    assert _sparse_anchor_matches("RAK   TULKHESH\nClasse Armatura", "Rak Tulkhesh")
    assert not _sparse_anchor_matches("Altro Mostro\nClasse Armatura", "Rak Tulkhesh")


def test_sparse_page_anchor_rejects_empty_target():
    assert not _sparse_anchor_matches("Rak Tulkhesh", "")


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

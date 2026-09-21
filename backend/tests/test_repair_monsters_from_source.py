import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import fitz

from scripts.repair_monsters_from_source import (
    BIGBY19_TARGETS,
    BIGBY4_TARGETS,
    APPROVED5_TARGETS,
    EXPECTED_BIGBY19_COUNT,
    EXPECTED_BIGBY4_COUNT,
    EXPECTED_HEALTHY22_COUNT,
    EXPECTED_APPROVED1_COUNT,
    EXPECTED_APPROVED5_COUNT,
    HEALTHY22_TARGETS,
    APPROVED1_TARGETS,
    OCR_REVIEW_FLAG,
    REPAIR_FLAG,
    RepairBlocked,
    SourcePdfCache,
    _agreed_target_candidate,
    _apply_update,
    _dilate_dark_pixels,
    _layout_ocr_settings,
    _layout_profile,
    _layout_segments,
    _micro_ocr_hit_points_line,
    _otsu_inverted_samples,
    build_repair_proposal,
    resolve_source,
    select_bigby19_targets,
    select_bigby4_targets,
    select_corrupted_name_monsters,
    select_failed_monsters,
    select_healthy22_targets,
    select_approved1_targets,
    select_approved5_targets,
)


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
        CompletedProcess([], 0, stdout="149 (27410)\n", stderr=""),
        CompletedProcess([], 0, stdout="149 (27410)\n", stderr=""),
        CompletedProcess([], 0, stdout="149 (27410)\n", stderr=""),
        CompletedProcess([], 0, stdout="149 (27d10)\n", stderr=""),
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
            "Fraz-Urb'Luu\nPunti Ferita 149 (27410)\n",
            "Fraz-Urb'Luu",
        )

    assert result == "Fraz-Urb'Luu\nPunti Ferita 149 (27d10)\n"
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

    assert result == "Mostro Prova\nPunti Ferita 30 (4d12 + 3)\n"
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


def test_source_pdf_cache_resolves_registered_r2_alias_and_verifies_sha(tmp_path):
    payload = b"registered PHB bytes"
    source = {
        "physical_filename": "Manuale del giocatore .pdf",
        "physical_sha256": hashlib.sha256(payload).hexdigest(),
    }

    class FakeClient:
        def download_file(self, bucket, key, target):
            assert bucket == "tomoforge-manuals"
            assert key == "uploads/Manuale del giocatore.pdf"
            Path(target).write_bytes(payload)

    with (
        patch(
            "scripts.import_manuals_from_r2._r2_client",
            return_value=FakeClient(),
        ),
        patch(
            "scripts.import_manuals_from_r2._list_pdf_objects",
            return_value={
                "Manuale del giocatore.pdf": {
                    "key": "uploads/Manuale del giocatore.pdf"
                }
            },
        ),
    ):
        cache = SourcePdfCache(str(tmp_path), allow_r2_download=True)
        try:
            resolved = cache.get(source)
            assert resolved.read_bytes() == payload
            assert resolved.name == "Manuale del giocatore.pdf"
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

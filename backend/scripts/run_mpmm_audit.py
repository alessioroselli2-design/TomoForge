#!/usr/bin/env python3
"""Keep private OCR output in the worker and publish only audit metadata."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
CORE_FIELDS = ("classe_armatura", "punti_ferita", "velocita")
PUBLIC_COMPATIBLE_GATE_FLAGS = frozenset(
    {
        "CA_out_of_bounds",
        "CA_format_error",
        "HP_format_error",
    }
)

PUBLIC_HP_ANCHOR_REASONS = frozenset(
    {
        "bael_structural_hp_anchor_ambiguous",
        "drow_sparse_missing_hp_reconstruction_ambiguous",
        "drow_structural_hp_anchor_ambiguous",
        "drow_text_core_order_ambiguous",
        "drow_text_identity_anchor_ambiguous",
        "delfino_core_order_ambiguous",
        "delfino_structural_hp_anchor_ambiguous",
        "divoratore_structural_hp_anchor_ambiguous",
        "ferita_token_missing_from_label",
        "hp_crop_invalid",
        "hp_crop_raster_mismatch",
        "micro_ocr_numeric_value_missing",
        "micro_ocr_reconstruction_missing_anchor",
        "micro_ocr_reconstruction_speed_anchor_missing",
        "micro_ocr_replacement_target_ambiguous",
        "micro_ocr_target_hp_line_unparseable",
        "no_unique_structural_hp_anchor",
        "normalized_target_name_empty",
    }
)

PUBLIC_REASONS = frozenset(
    {
        "ocr_global_timeout",
        "no_unique_independent_agreement",
        "no_unique_exact_target_identity",
        "target_page_quality_fail",
        "dynamic_layout_exhausted",
        "ocr_subprocess_timeout",
        "ocr_subprocess_failed",
        "repaired_candidate_core_debris",
        "repaired_candidate_failed_gates",
        "repaired_candidate_missing_speed",
        "repaired_candidate_invalid_title",
        "repaired_candidate_corrupted_name",
        "post_merge_gate_failure",
        "residual_review_flags",
        "verification_gate_failure",
        "write_apply_failed",
    }
)


def _count(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("invalid audit count")
    return value


def _digest(value: Any) -> str | None:
    return (
        value
        if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        else None
    )


def _public_hp_anchor_event(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    reason = payload.get("reason")
    result: dict[str, Any] = {
        "reason": reason if reason in PUBLIC_HP_ANCHOR_REASONS else "blocked",
    }
    for key in (
        "page_text_target_count",
        "page_text_local_hp_count",
        "tsv_page_wide_hp_label_count",
        "drow_tsv_hp_between_count",
    ):
        value = payload.get(key)
        if type(value) is int and value >= 0:
            result[key] = value
    for key in (
        "tsv_name_anchor_found",
        "tsv_local_label_found",
        "drow_local_tsv_structure",
        "drow_tsv_target_unique",
        "drow_tsv_ca_local_unique",
        "drow_tsv_speed_within_12_unique",
        "drow_tsv_hp_between_unique",
        "drow_hp_geometry_band_used",
        "drow_micro_value_valid",
        "drow_text_plain_ca_unique",
        "drow_text_permissive_ca_unique",
        "drow_text_speed_unique",
        "drow_text_page_speed_unique",
        "drow_text_page_speed_after_ca",
        "drow_text_page_speed_gap_le_12",
        "drow_text_page_speed_gap_le_16",
        "drow_text_page_speed_gap_le_24",
        "drow_text_bounded_speed_unique",
        "drow_text_permissive_ordered",
        "drow_text_gap_within_bound",
    ):
        value = payload.get(key)
        if type(value) is bool:
            result[key] = value
    return result


def _public_hp_micro_event(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    result: dict[str, Any] = {}
    for key in (
        "otsu_hp_format_error",
        "upscaled_otsu_hp_format_error",
        "superscaled_otsu_hp_format_error",
    ):
        value = payload.get(key)
        if type(value) is bool:
            result[key] = value
        elif value is None:
            result[key] = None
    for key in (
        "martellatore_psm7_hp_format_error",
        "martellatore_psm13_hp_format_error",
        "martellatore_psm6_hp_format_error",
        "martellatore_alt_psm_accepted",
    ):
        value = payload.get(key)
        if type(value) is bool:
            result[key] = value
    attempts = payload.get("full_spectrum_attempt_count")
    if type(attempts) is int and attempts >= 0:
        result["full_spectrum_attempt_count"] = attempts
    result["full_spectrum_accepted"] = isinstance(
        payload.get("full_spectrum_accepted"),
        dict,
    )
    return result


def _public_martellatore_segment_event(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    segment = payload.get("segment")
    if segment not in {"left", "right", "full", "sparse-full"}:
        return None
    result: dict[str, Any] = {"segment": segment}
    page_offset = payload.get("page_offset")
    if type(page_offset) is int and page_offset in {-1, 0, 1}:
        result["page_offset"] = page_offset
    for key in (
        "primary_target_anchor",
        "comparison_target_anchor",
        "primary_ca_label",
        "comparison_ca_label",
        "primary_hp_label",
        "comparison_hp_label",
        "primary_speed_label",
        "comparison_speed_label",
        "primary_class_token",
        "primary_armor_token",
        "primary_points_token",
        "primary_wound_token",
        "comparison_class_token",
        "comparison_armor_token",
        "comparison_points_token",
        "comparison_wound_token",
        "quality_pass",
    ):
        value = payload.get(key)
        if type(value) is bool:
            result[key] = value
    return result


def _public_esploratore_tsv_event(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    psm = payload.get("psm")
    if type(psm) is not int or psm not in {11, 12}:
        return None
    result: dict[str, Any] = {"psm": psm}
    for key in (
        "target_unique",
        "ca_unique",
        "hp_unique",
        "speed_unique",
        "target_left_half",
        "ca_left_half",
        "hp_left_half",
        "speed_left_half",
        "target_ca_same_half",
        "target_hp_same_half",
        "ca_after_target",
        "hp_after_ca",
        "speed_after_hp",
    ):
        value = payload.get(key)
        if type(value) is bool:
            result[key] = value
    return result


def _public_esploratore_registered_core_probe(
    payload: Any,
) -> dict[str, bool] | None:
    if not isinstance(payload, dict):
        return None
    keys = (
        "registered_page_ref_unique",
        "primary_any_core_match",
        "comparison_any_core_match",
        "primary_unique_core_match",
        "comparison_unique_core_match",
        "independent_core_match_agreement",
    )
    result: dict[str, bool] = {}
    for key in keys:
        value = payload.get(key)
        if type(value) is bool:
            result[key] = value
    return result if result else None


def _public_ki_rin_core_profile(payload: Any) -> dict[str, bool]:
    if not isinstance(payload, dict):
        return {}
    keys = (
        "primary_gate_clean",
        "comparison_gate_clean",
        "ca_semantic_match",
        "speed_semantic_match",
        "ca_deterministic_match",
        "speed_deterministic_match",
        "ca_residual_single_edit",
        "speed_residual_single_edit",
        "ca_residual_non_alphanumeric",
        "speed_residual_non_alphanumeric",
        "speed_extra_short_suffix",
        "speed_extra_single_token",
        "both_from_same_page",
        "ca_primary_reviewed_exact",
        "ca_comparison_reviewed_exact",
        "hp_primary_reviewed_exact",
        "hp_comparison_reviewed_exact",
        "speed_primary_reviewed_exact",
        "speed_comparison_reviewed_exact",
    )
    return {
        key: payload[key]
        for key in keys
        if type(payload.get(key)) is bool
    }


def _record_metadata(item: dict[str, Any]) -> dict[str, Any]:
    identifier = item.get("record_id")
    return {
        "record_id": identifier
        if isinstance(identifier, str) and re.fullmatch(r"ref_[0-9a-f]{32}", identifier)
        else None,
        "record_snapshot_sha256": _digest(item.get("record_snapshot_sha256")),
        "executed": item.get("executed") is True,
    }


def public_report(private: dict[str, Any]) -> dict[str, Any]:
    # These helpers evaluate evidence in the worker; no source values are copied.
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from reference_library import normalize_reference_name
    from scripts.repair_monsters_from_source import _verified_core_agreement
    from services.ocr_semantic_gates import monster_semantic_numeric_flags

    result = {
        key: _count(private[key])
        for key in (
            "initial_pending",
            "initial_verified",
            "initial_global_verified",
            "targets",
            "repairable",
            "blocked",
            "updates_performed",
            "final_pending",
            "final_verified",
            "global_monsters",
        )
    }
    result.update(
        dry_run=private.get("dry_run") is True,
        logical_source_id="mpmm_2022_it",
        protected_verified_fingerprint_sha256=_digest(
            private.get("protected_verified_fingerprint_sha256")
        ),
        target_fingerprint_sha256=_digest(private.get("target_fingerprint_sha256")),
        public_metadata_only=True,
    )
    result["batches"] = [
        {
            key: _count(batch[key])
            for key in ("batch", "target", "repairable", "blocked", "updates_performed")
        }
        for batch in private["batches"]
    ]
    result["blocked_records"] = []
    for item in private["blocked_records"]:
        reason = item.get("reason")
        diagnostics = item.get("diagnostics") or {}
        result["blocked_records"].append(
            {
                **_record_metadata(item),
                "reason": reason if reason in PUBLIC_REASONS else "blocked",
                "core_disagreement": {
                    field: field in diagnostics.get("divergent_core_fields", [])
                    for field in CORE_FIELDS
                },
                "hp_anchor": _public_hp_anchor_event(
                    {"reason": reason, **diagnostics}
                )
                or {},
                "ki_rin_core_profile": _public_ki_rin_core_profile(
                    diagnostics.get("ki_rin_core_profile")
                ),
                "exact_identity_candidates": {
                    path: _count(diagnostics[key])
                    for path, key in (
                        ("primary", "primary_exact_candidates"),
                        ("comparison", "comparison_exact_candidates"),
                    )
                    if key in diagnostics
                },
                "compatible_identity_candidates": {
                    path: _count(diagnostics[key])
                    for path, key in (
                        ("primary", "primary_compatible_candidates"),
                        ("comparison", "comparison_compatible_candidates"),
                    )
                    if key in diagnostics
                },
                "target_page_quality": (
                    {
                        "segments": {
                            segment: {
                                key: bool(value)
                                for key, value in values.items()
                                if key
                                in {
                                    "quality_pass",
                                    "sparse_anchor_found",
                                    "primary_chars_ok",
                                    "comparison_chars_ok",
                                    "primary_letter_ratio_ok",
                                    "comparison_letter_ratio_ok",
                                    "primary_printable_ratio_ok",
                                    "comparison_printable_ratio_ok",
                                    "primary_word_count_ok",
                                    "comparison_word_count_ok",
                                    "token_dice_ok",
                                    "unique_jaccard_ok",
                                    "length_ratio_ok",
                                }
                            }
                            for segment in ("left", "right", "full", "sparse-full")
                            if isinstance(
                                values := quality.get("segments", {}).get(segment),
                                dict,
                            )
                        }
                    }
                    if isinstance(
                        quality := diagnostics.get("target_page_quality"), dict
                    )
                    else {}
                ),
                "compatible_fallback": (
                    {
                        "eligible_name": fallback.get("eligible_name") is True,
                        "primary_exact_title_lines": _count(
                            fallback.get("primary_exact_title_lines", 0)
                        ),
                        "comparison_exact_title_lines": _count(
                            fallback.get("comparison_exact_title_lines", 0)
                        ),
                        "primary_gate_flags": sorted(
                            {
                                flag
                                for flag in fallback.get("primary_gate_flags", [])
                                if flag in PUBLIC_COMPATIBLE_GATE_FLAGS
                            }
                        ),
                        "comparison_gate_flags": sorted(
                            {
                                flag
                                for flag in fallback.get("comparison_gate_flags", [])
                                if flag in PUBLIC_COMPATIBLE_GATE_FLAGS
                            }
                        ),
                        "primary_gate_flag_count": _count(
                            len(fallback.get("primary_gate_flags", []))
                        ),
                        "comparison_gate_flag_count": _count(
                            len(fallback.get("comparison_gate_flags", []))
                        ),
                        "core_match": {
                            field: (fallback.get("core_match") or {}).get(field) is True
                            for field in CORE_FIELDS
                        },
                        "semantic_core_match": {
                            field: (fallback.get("semantic_core_match") or {}).get(field)
                            is True
                            for field in CORE_FIELDS
                        },
                        "speed_single_extra_token": {
                            key: (fallback.get("speed_single_extra_token") or {}).get(key)
                            is True
                            for key in (
                                "velocita_residual_single_extra_alpha_token_len_3_to_6",
                                "velocita_residual_single_extra_alpha_token_len_gt6",
                                "velocita_residual_single_extra_alpha_token_internal",
                            )
                        },
                        "speed_multi_extra_token": {
                            key: (fallback.get("speed_multi_extra_token") or {}).get(key)
                            is True
                            for key in (
                                "velocita_residual_extra_alpha_tokens_exactly_2",
                                "velocita_residual_extra_alpha_tokens_3_or_more",
                                "velocita_residual_duplicate_ambiguous",
                            )
                        },
                        **(
                            {
                                "speed_residual_single_edit": fallback.get(
                                    "speed_residual_single_edit"
                                )
                                is True
                            }
                            if "speed_residual_single_edit" in fallback
                            else {}
                        ),
                        **(
                            {
                                "speed_residual_shape": {
                                    key: (
                                        fallback.get("speed_residual_shape") or {}
                                    ).get(key)
                                    is True
                                    for key in (
                                        "edit_distance_2_match",
                                        "edit_distance_3_match",
                                        "extra_alpha_tokens",
                                        "word_order_variation",
                                        "known_manual_label_extra_alpha_tokens",
                                        "parenthetical_extra_alpha_tokens",
                                        "single_extra_alpha_token_short_lt3",
                                        "single_extra_alpha_token_prefix",
                                        "single_extra_alpha_token_suffix",
                                    )
                                }
                            }
                            if isinstance(fallback.get("speed_residual_shape"), dict)
                            else {}
                        ),
                        "hp_ocr_confusion_repaired": (
                            fallback.get("hp_ocr_confusion_repaired") is True
                        ),
                        "hp_repair_attempted": (
                            fallback.get("hp_repair_attempted") is True
                        ),
                        "hp_repair_has_letter_confusion": (
                            fallback.get("hp_repair_has_letter_confusion") is True
                        ),
                        "hp_repair_has_spaced_digits": (
                            fallback.get("hp_repair_has_spaced_digits") is True
                        ),
                        "hp_repair_shape": {
                            key: (fallback.get("hp_repair_shape") or {}).get(key) is True
                            for key in (
                                "has_open_paren",
                                "has_close_paren",
                                "ends_close_paren",
                                "has_d_separator",
                                "has_modifier_sign",
                            )
                        },
                        "hp_repair_candidate_valid": (
                            fallback.get("hp_repair_candidate_valid") is True
                        ),
                        "hp_repair_matches_peer": (
                            fallback.get("hp_repair_matches_peer") is True
                        ),
                        "hp_prefix_peer_repaired": (
                            fallback.get("hp_prefix_peer_repaired") is True
                        ),
                        "hp_digit_skeleton_repaired": (
                            fallback.get("hp_digit_skeleton_repaired") is True
                        ),
                        "hp_digit_skeleton_diagnostics": {
                            key: (
                                fallback.get("hp_digit_skeleton_diagnostics") or {}
                            ).get(key)
                            is True
                            for key in (
                                "peer_shape_valid",
                                "peer_gate_clean",
                                "paren_shape",
                                "spaced_digits",
                                "missing_d",
                                "missing_sign",
                                "chars_allowed",
                                "digit_skeleton_match",
                                "same_length",
                                "one_substitution",
                                "one_extra_observed",
                                "one_missing_observed",
                                "one_adjacent_transposition",
                            )
                        },
                        "hp_repair_diagnostics": {
                            key: (fallback.get("hp_repair_diagnostics") or {}).get(key)
                            is True
                            for key in (
                                "shape_match",
                                "trailing_present",
                                "trailing_has_numeric_syntax",
                                "digits_valid",
                                "die_standard",
                                "candidate_valid",
                                "prefix_numericish",
                                "inner_chars_allowed",
                                "single_d_separator",
                                "single_modifier_sign",
                                "suffix_present",
                                "suffix_has_numeric_syntax",
                            )
                        },
                    }
                    if isinstance(
                        fallback := diagnostics.get("compatible_fallback"), dict
                    )
                    else {}
                ),
                "identity_source_counts": {
                    path: {
                        metric: _count(values[metric])
                        for metric in (
                            "swarm_descriptor_lines",
                            "swarm_descriptor_after_exact_title",
                            "known_title_suffix_lines",
                            "parser_known_title_suffix_headers",
                            "parser_valid_headers",
                            "parser_exact_headers",
                            "parser_armor_fields",
                            "parser_hp_fields",
                            "parser_speed_fields",
                            "wrapped_title_pairs",
                            "wrapped_title_descriptor_pairs",
                            "wrapped_title_core_headers",
                            "exact_title_lines",
                            "reversed_title_lines",
                            "all_name_tokens_lines",
                            "reversed_exact_candidates",
                            "reversed_core_candidates",
                            "candidates_on_page",
                            "core_anchors",
                            "armor_label_mentions",
                            "hp_label_lines",
                            "hp_label_only_lines",
                            "hp_label_only_next_has_digit",
                            "hp_parser_label_regex_lines",
                            "hp_parser_value_has_digit",
                            "speed_label_lines",
                            "speed_label_only_lines",
                            "speed_label_only_next_has_digit",
                            "speed_parser_label_regex_lines",
                            "speed_parser_value_has_digit",
                            "descriptor_lines",
                            "split_descriptor_pairs",
                            "anchors_with_hp",
                            "anchors_with_speed",
                            "anchors_with_descriptor",
                            "valid_headers",
                            "exact_headers",
                            "plant_synonym_descriptor_lines",
                            "plant_synonym_after_exact_title",
                            "split_descriptor_after_exact_title",
                        )
                        if metric in values
                    }
                    for path in ("primary", "comparison")
                    if isinstance(
                        values := diagnostics.get(f"{path}_identity_source_counts"),
                        dict,
                    )
                },
            }
        )
    result["reports"] = []
    for item in private["reports"]:
        before = item["before"]["attributes"]
        after = item["after"]["attributes"]
        _, agreement = _verified_core_agreement(before, after)
        identity = item["source_candidate_identity"]
        exact_identity = normalize_reference_name(identity.get("name") or "") == (
            normalize_reference_name(item["before"].get("name") or "")
        )
        result["reports"].append(
            {
                **_record_metadata(item),
                "source_physical_sha256": _digest(
                    item["source"].get("physical_sha256")
                ),
                "source_physical_page": _count(item["source"]["physical_page"]),
                "candidate_start_page": _count(identity["start_page"]),
                "source_identity_exact": exact_identity,
                "gate_failure_count_after": len(item["gate_failures_after"]),
                "source_reviewed_status_only": (
                    item.get("source_reviewed_status_only") is True
                ),
                "existing_attributes_supported": exact_identity
                and all(agreement.values())
                and not monster_semantic_numeric_flags(before),
                "existing_core_whitespace_equal": all(
                    bool(before.get(field))
                    and bool(after.get(field))
                    and str(before[field]).split() == str(after[field]).split()
                    for field in CORE_FIELDS
                ),
                "changed_core_fields": [
                    field
                    for field in CORE_FIELDS
                    if before.get(field) != after.get(field)
                ],
            }
        )
    return result


def main() -> int:
    # Capture both file descriptors at the subprocess boundary, including
    # logging and tracebacks. Private diagnostics never reach Actions stdout.
    try:
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as runtime_output:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(BACKEND_DIR / "scripts/process_mpmm_pending.py"),
                    *sys.argv[1:],
                ],
                stdout=runtime_output,
                stderr=runtime_output,
                check=False,
            )
            if completed.returncode not in (0, 2):
                raise RuntimeError("private audit failed")
            runtime_output.seek(0)
            private = None
            hp_anchor_diagnostics: list[dict[str, Any]] = []
            hp_micro_ocr_diagnostics: list[dict[str, Any]] = []
            martellatore_segment_diagnostics: list[dict[str, Any]] = []
            esploratore_segment_diagnostics: list[dict[str, Any]] = []
            esploratore_tsv_diagnostics: list[dict[str, Any]] = []
            esploratore_registered_core_probe: dict[str, bool] | None = None
            for line in runtime_output:
                stripped = line.strip()
                if stripped.startswith("HP_ANCHOR_DIAGNOSTIC "):
                    try:
                        payload = json.loads(stripped.split(" ", 1)[1])
                    except (json.JSONDecodeError, IndexError):
                        continue
                    event = _public_hp_anchor_event(payload)
                    if event is not None and len(hp_anchor_diagnostics) < 32:
                        hp_anchor_diagnostics.append(event)
                elif stripped.startswith("HP_MICRO_OCR_DIAGNOSTIC "):
                    try:
                        payload = json.loads(stripped.split(" ", 1)[1])
                    except (json.JSONDecodeError, IndexError):
                        continue
                    event = _public_hp_micro_event(payload)
                    if event is not None and len(hp_micro_ocr_diagnostics) < 32:
                        hp_micro_ocr_diagnostics.append(event)
                elif stripped.startswith("MPMM_MARTELLATORE_SEGMENT_DIAGNOSTIC "):
                    try:
                        payload = json.loads(stripped.split(" ", 1)[1])
                    except (json.JSONDecodeError, IndexError):
                        continue
                    event = _public_martellatore_segment_event(payload)
                    if (
                        event is not None
                        and len(martellatore_segment_diagnostics) < 16
                    ):
                        martellatore_segment_diagnostics.append(event)
                elif stripped.startswith("MPMM_ESPLORATORE_SEGMENT_DIAGNOSTIC "):
                    try:
                        payload = json.loads(stripped.split(" ", 1)[1])
                    except (json.JSONDecodeError, IndexError):
                        continue
                    event = _public_martellatore_segment_event(payload)
                    if event is not None and len(esploratore_segment_diagnostics) < 16:
                        esploratore_segment_diagnostics.append(event)
                elif stripped.startswith("MPMM_ESPLORATORE_TSV_CORE_DIAGNOSTIC "):
                    try:
                        payload = json.loads(stripped.split(" ", 1)[1])
                    except (json.JSONDecodeError, IndexError):
                        continue
                    event = _public_esploratore_tsv_event(payload)
                    if event is not None and len(esploratore_tsv_diagnostics) < 8:
                        esploratore_tsv_diagnostics.append(event)
                elif stripped.startswith("MPMM_ESPLORATORE_REGISTERED_CORE_PROBE "):
                    try:
                        payload = json.loads(stripped.split(" ", 1)[1])
                    except (json.JSONDecodeError, IndexError):
                        continue
                    esploratore_registered_core_probe = (
                        _public_esploratore_registered_core_probe(payload)
                    )
                if stripped == "FINAL_REPORT":
                    private = json.loads(next(runtime_output))
            if private is None:
                raise RuntimeError("missing final report")
            public = public_report(private)
            public["hp_anchor_diagnostics"] = hp_anchor_diagnostics
            public["hp_micro_ocr_diagnostics"] = hp_micro_ocr_diagnostics
            public["martellatore_segment_diagnostics"] = (
                martellatore_segment_diagnostics
            )
            public["esploratore_segment_diagnostics"] = (
                esploratore_segment_diagnostics
            )
            public["esploratore_tsv_diagnostics"] = (
                esploratore_tsv_diagnostics
            )
            public["esploratore_registered_core_probe"] = (
                esploratore_registered_core_probe or {}
            )
        print("FINAL_REPORT")
        print(json.dumps(public, sort_keys=True))
        return completed.returncode
    except Exception:
        print(
            "MPMM_AUDIT_FAILED: private diagnostics retained only during worker execution"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

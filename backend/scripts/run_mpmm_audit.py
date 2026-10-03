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
                "identity_source_counts": {
                    path: {
                        metric: _count(values[metric])
                        for metric in (
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
                            "speed_label_lines",
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
                "existing_attributes_supported": exact_identity
                and all(agreement.values())
                and not monster_semantic_numeric_flags(before),
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
            for line in runtime_output:
                if line.strip() == "FINAL_REPORT":
                    private = json.loads(next(runtime_output))
            if private is None:
                raise RuntimeError("missing final report")
            public = public_report(private)
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

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts import run_mpmm_audit as runner

IDENTIFIER = "ref_" + "a" * 32
PRIVATE = "PRIVATE_SOURCE_SENTINEL"


def _report():
    attributes = {
        "classe_armatura": "15",
        "punti_ferita": "45 (6d10 + 12)",
        "velocita": "9 m",
    }
    return {
        "dry_run": True,
        "initial_pending": 40,
        "initial_verified": 155,
        "initial_global_verified": 204,
        "targets": 1,
        "repairable": 1,
        "blocked": 0,
        "updates_performed": 0,
        "final_pending": 40,
        "final_verified": 155,
        "global_monsters": 327,
        "batches": [
            {
                "batch": 1,
                "target": 1,
                "repairable": 1,
                "blocked": 0,
                "updates_performed": 0,
                "private": PRIVATE,
            }
        ],
        "blocked_records": [],
        "reports": [
            {
                "record_id": IDENTIFIER,
                "name": PRIVATE,
                "record_snapshot_sha256": "b" * 64,
                "executed": False,
                "source_candidate_identity": {"name": PRIVATE, "start_page": 1},
                "before": {
                    "name": PRIVATE,
                    "attributes": {**attributes, "private": PRIVATE},
                },
                "after": {"attributes": {**attributes, "private": PRIVATE}},
                "source": {
                    "physical_sha256": "c" * 64,
                    "physical_page": 1,
                    "private": PRIVATE,
                },
                "gate_failures_after": [],
                "diagnostics": {"text": PRIVATE},
            }
        ],
        "unexpected": {"private": PRIVATE},
    }


def test_public_report_excludes_source_values_and_arbitrary_nested_data():
    private = _report()
    private["blocked_records"] = [
        {
            "record_id": IDENTIFIER,
            "record_snapshot_sha256": "b" * 64,
            "reason": "no_unique_independent_agreement",
            "detail": PRIVATE,
            "diagnostics": {
                "primary_context": [PRIVATE],
                "divergent_core_fields": ["punti_ferita"],
            },
        }
    ]
    public = runner.public_report(private)
    encoded = json.dumps(public)
    assert PRIVATE not in encoded
    assert "45 (6d10 + 12)" not in encoded
    assert "attributes" not in public["reports"][0]
    assert public["reports"][0]["existing_attributes_supported"] is True
    assert public["blocked_records"][0]["core_disagreement"]["punti_ferita"] is True


@pytest.mark.parametrize("speed,expected", [
    (" 9 m ", True),
    ("9  m", True),
    ("9\nm", True),
    ("9 m 3", False),
    ("9 m, volare 9 m", False),
    ("12 m", False),
])
def test_core_whitespace_equality_keeps_every_non_whitespace_token(speed, expected):
    private = _report()
    private["reports"][0]["after"]["attributes"]["velocita"] = speed
    public = runner.public_report(private)
    assert public["reports"][0]["existing_core_whitespace_equal"] is expected
    assert public["reports"][0]["changed_core_fields"] == ["velocita"]
    assert PRIVATE not in json.dumps(public)


@pytest.mark.parametrize("mutation", ["identity", "core", "gate"])
def test_original_attributes_are_supported_only_with_identity_agreement_and_gates(
    mutation,
):
    private = _report()
    item = private["reports"][0]
    if mutation == "identity":
        item["source_candidate_identity"]["name"] = "Other Entity"
    elif mutation == "core":
        item["after"]["attributes"]["classe_armatura"] = "16"
    else:
        item["before"]["attributes"]["punti_ferita"] = "46 (6d10 + 12)"
        item["after"]["attributes"]["punti_ferita"] = "46 (6d10 + 12)"
    assert (
        runner.public_report(private)["reports"][0]["existing_attributes_supported"]
        is False
    )


def test_unrecognized_block_reason_and_malformed_metadata_cannot_export_text():
    private = _report()
    private["blocked_records"] = [
        {"record_id": PRIVATE, "record_snapshot_sha256": PRIVATE, "reason": PRIVATE}
    ]
    public = runner.public_report(private)
    assert PRIVATE not in json.dumps(public)
    assert public["blocked_records"][0]["reason"] == "blocked"
    private["targets"] = PRIVATE
    with pytest.raises(ValueError, match="invalid audit count"):
        runner.public_report(private)


def test_exact_identity_failure_publishes_only_counts():
    private = _report()
    private["blocked_records"] = [
        {
            "record_id": IDENTIFIER,
            "reason": "no_unique_exact_target_identity",
            "detail": PRIVATE,
            "diagnostics": {
                "primary_exact_candidates": 0,
                "comparison_exact_candidates": 1,
                "private": PRIVATE,
            },
        }
    ]
    public = runner.public_report(private)
    assert PRIVATE not in json.dumps(public)
    assert public["blocked_records"][0]["reason"] == "no_unique_exact_target_identity"
    assert public["blocked_records"][0]["exact_identity_candidates"] == {
        "primary": 0,
        "comparison": 1,
    }


def test_target_quality_diagnostics_export_only_boolean_gate_results():
    private = _report()
    private["blocked_records"] = [
        {
            "record_id": IDENTIFIER,
            "reason": "target_page_quality_fail",
            "diagnostics": {
                "target_page_quality": {
                    "segments": {
                        "sparse-full": {
                            "quality_pass": False,
                            "sparse_anchor_found": True,
                            "primary_chars_ok": True,
                            "comparison_chars_ok": False,
                            "token_dice_ok": False,
                            "unique_jaccard_ok": True,
                            "length_ratio_ok": True,
                            "private": PRIVATE,
                        },
                        PRIVATE: {"quality_pass": True},
                    },
                    "private": PRIVATE,
                }
            },
        }
    ]
    public = runner.public_report(private)
    encoded = json.dumps(public)
    assert PRIVATE not in encoded
    assert public["blocked_records"][0]["target_page_quality"] == {
        "segments": {
            "sparse-full": {
                "quality_pass": False,
                "sparse_anchor_found": True,
                "primary_chars_ok": True,
                "comparison_chars_ok": False,
                "token_dice_ok": False,
                "unique_jaccard_ok": True,
                "length_ratio_ok": True,
            }
        }
    }


def test_compatible_fallback_exports_only_allowlisted_gate_metadata():
    private = _report()
    private["blocked_records"] = [
        {
            "record_id": IDENTIFIER,
            "reason": "no_unique_exact_target_identity",
            "diagnostics": {
                "compatible_fallback": {
                    "eligible_name": True,
                    "primary_exact_title_lines": 1,
                    "comparison_exact_title_lines": 1,
                    "primary_gate_flags": ["HP_format_error", PRIVATE],
                    "comparison_gate_flags": ["CA_format_error"],
                    "core_match": {
                        "classe_armatura": True,
                        "punti_ferita": True,
                        "velocita": True,
                        "private": PRIVATE,
                    },
                    "private": PRIVATE,
                }
            },
        }
    ]
    public = runner.public_report(private)
    encoded = json.dumps(public)
    assert PRIVATE not in encoded
    diagnostic = public["blocked_records"][0]["compatible_fallback"]
    assert diagnostic == {
        "eligible_name": True,
        "primary_exact_title_lines": 1,
        "comparison_exact_title_lines": 1,
        "primary_gate_flags": ["HP_format_error"],
        "comparison_gate_flags": ["CA_format_error"],
        "primary_gate_flag_count": 2,
        "comparison_gate_flag_count": 1,
        "core_match": {
            "classe_armatura": True,
            "punti_ferita": True,
            "velocita": True,
        },
    }


def test_identity_source_diagnostics_cannot_export_source_content():
    private = _report()
    private["blocked_records"] = [
        {
            "record_id": IDENTIFIER,
            "reason": "no_unique_exact_target_identity",
            "diagnostics": {
                "primary_identity_source_counts": {
                    "swarm_descriptor_lines": 1,
                    "swarm_descriptor_after_exact_title": 1,
                    "known_title_suffix_lines": 1,
                    "parser_known_title_suffix_headers": 1,
                    "reversed_title_lines": 1,
                    "valid_headers": 0,
                    "parser_valid_headers": 0,
                    "parser_exact_headers": 0,
                    "parser_armor_fields": 1,
                    "parser_hp_fields": 0,
                    "parser_speed_fields": 1,
                    "raw_title": PRIVATE,
                },
                "comparison_identity_source_counts": {
                    "reversed_exact_candidates": 1,
                    "candidate_core": PRIVATE,
                },
            },
        }
    ]
    public = runner.public_report(private)
    assert PRIVATE not in json.dumps(public)
    assert public["blocked_records"][0]["identity_source_counts"] == {
        "primary": {"swarm_descriptor_lines": 1, "swarm_descriptor_after_exact_title": 1, "known_title_suffix_lines": 1, "parser_known_title_suffix_headers": 1, "reversed_title_lines": 1, "valid_headers": 0, "parser_valid_headers": 0, "parser_exact_headers": 0, "parser_armor_fields": 1, "parser_hp_fields": 0, "parser_speed_fields": 1},
        "comparison": {"reversed_exact_candidates": 1},
    }
    private["blocked_records"][0]["diagnostics"]["primary_identity_source_counts"][
        "parser_known_title_suffix_headers"
    ] = PRIVATE
    with pytest.raises(ValueError, match="invalid audit count"):
        runner.public_report(private)


@pytest.mark.parametrize("status", [0, 2, 1])
def test_worker_stdout_stderr_and_crashes_never_reach_public_output(capsys, status):
    def worker(command, *, stdout, stderr, check):
        assert stdout is stderr
        stdout.write(PRIVATE + "\nTraceback: " + PRIVATE + "\nFINAL_REPORT\n")
        stdout.write(json.dumps(_report()) + "\n")
        stdout.flush()
        return SimpleNamespace(returncode=status)

    with (
        patch.object(runner.subprocess, "run", side_effect=worker),
        patch.object(runner.sys, "argv", ["runner", "--audit-record-id", IDENTIFIER]),
    ):
        assert runner.main() == status
    output = capsys.readouterr()
    assert PRIVATE not in output.out + output.err
    if status in (0, 2):
        report = json.loads(output.out.split("FINAL_REPORT\n")[1])
        assert report["public_metadata_only"] is True
    else:
        assert "MPMM_AUDIT_FAILED" in output.out


def test_native_subprocess_output_is_also_kept_private(tmp_path, capsys):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "process_mpmm_pending.py").write_text(
        "import os\n"
        f"os.write(1, {PRIVATE.encode()!r})\n"
        f"os.write(2, {PRIVATE.encode()!r})\n"
        "raise SystemExit(1)\n"
    )
    with (
        patch.object(runner, "BACKEND_DIR", tmp_path),
        patch.object(runner.sys, "argv", ["runner"]),
    ):
        assert runner.main() == 1
    output = capsys.readouterr()
    assert PRIVATE not in output.out + output.err
    assert "MPMM_AUDIT_FAILED" in output.out

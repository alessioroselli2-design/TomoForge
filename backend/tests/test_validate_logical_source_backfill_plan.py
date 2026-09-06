from scripts.build_logical_source_backfill_dry_run import build_backfill_plan
from scripts.validate_logical_source_backfill_plan import (
    candidate_fingerprint,
    validate_backfill_plan,
)


def _inputs():
    records = [
        {"id": "r-unique", "source_refs": [{"filename": "Bardo__1787233073462.pdf"}]},
        {"id": "r-ambiguous", "source_refs": [{"filename": "shared__1787233073462.pdf"}]},
        {
            "id": "r-existing",
            "source_refs": [{"logical_source_id": "already-set", "filename": "Bardo.pdf"}],
        },
    ]
    sources = [
        {"logical_source_id": "derived-bard", "physical_filename": "Bardo.pdf"},
        {"logical_source_id": "source-a", "physical_filename": "shared.pdf"},
        {"logical_source_id": "source-b", "physical_filename": "shared (1).pdf"},
    ]
    return records, sources


def _approval(saved):
    return {
        "schema_version": 1,
        "scope": "logical_source_provenance_backfill",
        "source_branch": "ai-canonical-library",
        "source_commit": "snapshot-sha",
        "candidate_count": saved["proposed_backfills"],
        "ambiguous_excluded_count": saved["excluded_ambiguous"],
        "candidate_sha256": candidate_fingerprint(saved["candidates"]),
        "approval_state": "preflight_only",
        "writes_authorized": False,
    }


def test_preflight_accepts_exact_reproducible_dry_run_with_approval_manifest():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)
    approval = _approval(saved)

    result = validate_backfill_plan(
        saved,
        records,
        sources,
        approval_manifest=approval,
    )

    expected = approval["candidate_sha256"]
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["writes_performed"] == 0
    assert result["saved_candidate_count"] == 1
    assert result["fresh_candidate_count"] == 1
    assert result["fresh_ambiguous_excluded_count"] == 1
    assert result["saved_plan_sha256"] == result["fresh_plan_sha256"] == expected
    assert result["approval_manifest_checked"] is True
    assert result["approval_manifest_valid"] is True
    assert result["approval_candidate_sha256"] == expected


def test_preflight_accepts_optional_additional_matching_fingerprint():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)
    approval = _approval(saved)

    result = validate_backfill_plan(
        saved,
        records,
        sources,
        approval_manifest=approval,
        expected_candidate_sha256=approval["candidate_sha256"],
    )

    assert result["valid"] is True
    assert result["expected_candidate_sha256"] == approval["candidate_sha256"]


def test_preflight_rejects_stale_or_tampered_candidate_set():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)
    expected = candidate_fingerprint(saved["candidates"])
    saved["candidates"] = [
        {"record_id": "r-ambiguous", "logical_source_id": "source-a"}
    ]

    result = validate_backfill_plan(
        saved,
        records,
        sources,
        expected_candidate_sha256=expected,
    )

    assert result["valid"] is False
    assert "saved candidate set is stale or differs from current live inputs" in result["errors"]
    assert result["writes_performed"] == 0


def test_preflight_rejects_non_dry_run_or_reported_writes():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)
    saved["mode"] = "apply"
    saved["writes_performed"] = 1

    result = validate_backfill_plan(saved, records, sources)

    assert result["valid"] is False
    assert "saved plan is not dry_run" in result["errors"]
    assert "saved plan reports writes" in result["errors"]
    assert result["writes_performed"] == 0


def test_preflight_rejects_duplicate_candidate_record_ids():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)
    candidate = dict(saved["candidates"][0])
    saved["candidates"] = [candidate, dict(candidate)]
    saved["proposed_backfills"] = 2

    result = validate_backfill_plan(saved, records, sources)

    assert result["valid"] is False
    assert "saved plan contains duplicate candidate record ids" in result["errors"]
    assert result["writes_performed"] == 0


def test_preflight_rejects_mismatched_pinned_fingerprint():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)

    result = validate_backfill_plan(
        saved,
        records,
        sources,
        expected_candidate_sha256="0" * 64,
    )

    assert result["valid"] is False
    assert "fresh candidate fingerprint does not match pinned SHA-256" in result["errors"]


def test_preflight_rejects_invalid_pinned_fingerprint():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)

    result = validate_backfill_plan(
        saved,
        records,
        sources,
        expected_candidate_sha256="not-a-sha256",
    )

    assert result["valid"] is False
    assert "expected candidate fingerprint is not a valid SHA-256" in result["errors"]


def test_preflight_rejects_manifest_that_authorizes_writes():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)
    approval = _approval(saved)
    approval["writes_authorized"] = True

    result = validate_backfill_plan(saved, records, sources, approval_manifest=approval)

    assert result["valid"] is False
    assert "approval manifest must not authorize writes" in result["errors"]
    assert result["approval_manifest_valid"] is False
    assert result["writes_performed"] == 0


def test_preflight_rejects_manifest_candidate_count_drift():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)
    approval = _approval(saved)
    approval["candidate_count"] += 1

    result = validate_backfill_plan(saved, records, sources, approval_manifest=approval)

    assert result["valid"] is False
    assert "fresh candidate count does not match approval manifest" in result["errors"]


def test_preflight_rejects_manifest_ambiguous_count_drift():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)
    approval = _approval(saved)
    approval["ambiguous_excluded_count"] += 1

    result = validate_backfill_plan(saved, records, sources, approval_manifest=approval)

    assert result["valid"] is False
    assert "fresh ambiguous exclusion count does not match approval manifest" in result["errors"]


def test_preflight_rejects_manifest_fingerprint_drift():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)
    approval = _approval(saved)
    approval["candidate_sha256"] = "0" * 64

    result = validate_backfill_plan(saved, records, sources, approval_manifest=approval)

    assert result["valid"] is False
    assert "fresh candidate fingerprint does not match approval manifest" in result["errors"]


def test_preflight_rejects_manifest_contract_changes():
    records, sources = _inputs()
    saved = build_backfill_plan(records, sources)
    approval = _approval(saved)
    approval.update(
        {
            "schema_version": 2,
            "scope": "other_scope",
            "approval_state": "approved_for_write",
        }
    )

    result = validate_backfill_plan(saved, records, sources, approval_manifest=approval)

    assert result["valid"] is False
    assert "approval manifest schema_version is unsupported" in result["errors"]
    assert "approval manifest scope is invalid" in result["errors"]
    assert "approval manifest is not preflight_only" in result["errors"]


def test_candidate_fingerprint_is_stable_and_order_sensitive():
    candidates = [
        {"record_id": "r-a", "logical_source_id": "source-a"},
        {"record_id": "r-b", "logical_source_id": "source-b"},
    ]

    first = candidate_fingerprint(candidates)
    second = candidate_fingerprint([dict(row) for row in candidates])
    reversed_digest = candidate_fingerprint(list(reversed(candidates)))

    assert first == second
    assert first != reversed_digest
    assert len(first) == 64

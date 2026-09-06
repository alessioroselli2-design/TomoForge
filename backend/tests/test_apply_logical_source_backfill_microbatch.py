from scripts.apply_logical_source_backfill_microbatch import (
    MAX_MICROBATCH_WRITES,
    enrich_source_refs,
    validate_batch_authorization,
)


def _fresh_plan():
    return {
        "candidates": [
            {"record_id": "ref_a", "logical_source_id": "src_a"},
            {"record_id": "ref_b", "logical_source_id": "src_b"},
        ]
    }


def _authorization(**overrides):
    value = {
        "schema_version": 1,
        "scope": "logical_source_provenance_microbatch",
        "approval_state": "microbatch_write",
        "writes_authorized": True,
        "candidate_sha256": "a" * 64,
        "candidates": [{"record_id": "ref_a", "logical_source_id": "src_a"}],
    }
    value.update(overrides)
    return value


def test_accepts_exact_single_live_candidate():
    errors, rows = validate_batch_authorization(_authorization(), _fresh_plan(), "a" * 64)
    assert errors == []
    assert rows == [{"record_id": "ref_a", "logical_source_id": "src_a"}]


def test_rejects_write_without_explicit_authorization():
    errors, _ = validate_batch_authorization(
        _authorization(writes_authorized=False), _fresh_plan(), "a" * 64
    )
    assert "batch authorization does not authorize writes" in errors


def test_rejects_stale_global_fingerprint():
    errors, _ = validate_batch_authorization(_authorization(), _fresh_plan(), "b" * 64)
    assert "batch authorization candidate fingerprint is stale" in errors


def test_rejects_candidate_not_in_fresh_deterministic_plan():
    errors, _ = validate_batch_authorization(
        _authorization(candidates=[{"record_id": "ref_x", "logical_source_id": "src_x"}]),
        _fresh_plan(),
        "a" * 64,
    )
    assert any("not present in fresh deterministic plan" in error for error in errors)


def test_rejects_duplicate_record_ids():
    errors, _ = validate_batch_authorization(
        _authorization(
            candidates=[
                {"record_id": "ref_a", "logical_source_id": "src_a"},
                {"record_id": "ref_a", "logical_source_id": "src_a"},
            ]
        ),
        _fresh_plan(),
        "a" * 64,
    )
    assert "batch contains duplicate record ids" in errors


def test_rejects_batch_larger_than_hard_cap():
    candidates = [
        {"record_id": f"ref_{index}", "logical_source_id": f"src_{index}"}
        for index in range(MAX_MICROBATCH_WRITES + 1)
    ]
    errors, _ = validate_batch_authorization(
        _authorization(candidates=candidates), {"candidates": candidates}, "a" * 64
    )
    assert f"batch must contain between 1 and {MAX_MICROBATCH_WRITES} candidates" in errors


def test_enrich_source_refs_preserves_existing_fields_and_adds_catalog_metadata():
    refs = [{"page": 67, "filename": "Mago__1787233073462.pdf", "language": "it"}]
    source = {
        "title": "Mago",
        "ruleset": "2014",
        "authority_class": "derived_reference",
        "source_role": "supplemental",
        "source_status": "active",
    }
    result = enrich_source_refs(refs, "derived_class_mago", source)
    assert result == [
        {
            "page": 67,
            "filename": "Mago__1787233073462.pdf",
            "language": "it",
            "logical_source_id": "derived_class_mago",
            "source_title": "Mago",
            "ruleset": "2014",
            "authority_class": "derived_reference",
            "source_role": "supplemental",
            "source_status": "active",
        }
    ]
    assert "logical_source_id" not in refs[0]


def test_enrich_source_refs_does_not_overwrite_existing_metadata():
    refs = [
        {
            "page": 67,
            "filename": "Mago__1787233073462.pdf",
            "source_title": "Titolo conservato",
            "ruleset": "legacy-ruleset",
            "authority_class": "historical",
            "source_role": "historical_reference",
            "source_status": "archived",
        }
    ]
    source = {
        "title": "Mago",
        "ruleset": "2014",
        "authority_class": "derived_reference",
        "source_role": "supplemental",
        "source_status": "active",
    }

    result = enrich_source_refs(refs, "derived_class_mago", source)

    assert result == [
        {
            "page": 67,
            "filename": "Mago__1787233073462.pdf",
            "logical_source_id": "derived_class_mago",
            "source_title": "Titolo conservato",
            "ruleset": "legacy-ruleset",
            "authority_class": "historical",
            "source_role": "historical_reference",
            "source_status": "archived",
        }
    ]
    assert "logical_source_id" not in refs[0]


def test_enrich_source_refs_rejects_incompatible_existing_provenance():
    refs = [{"filename": "x.pdf", "logical_source_id": "other"}]
    try:
        enrich_source_refs(refs, "expected", {})
    except ValueError as exc:
        assert "incompatible logical_source_id" in str(exc)
    else:
        raise AssertionError("expected incompatible provenance to be rejected")

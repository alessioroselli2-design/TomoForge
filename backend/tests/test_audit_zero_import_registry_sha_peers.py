from scripts.audit_zero_import_registry_sha_peers import (
    summarize_zero_import_registry_sha_peers,
)


def _source(source_id, sha, logical_id, *, status="active", import_state="catalogued", records=0, start=1, end=10, pages=10, size=1000, text_mode="vision_required"):
    return {
        "id": source_id,
        "physical_filename": f"{source_id}.pdf",
        "physical_sha256": sha,
        "physical_size_bytes": size,
        "physical_pages": pages,
        "logical_source_id": logical_id,
        "source_status": status,
        "import_state": import_state,
        "imported_record_count": records,
        "page_start": start,
        "page_end": end,
        "text_mode": text_mode,
    }


def test_exact_excluded_duplicate_peer_is_diagnostic_and_narrows_residual():
    active = _source("active", "sha-a", "phb")
    duplicate = _source(
        "duplicate",
        "sha-a",
        "phb",
        status="duplicate",
        import_state="excluded",
    )
    no_peer = _source("no-peer", "sha-b", "mm")

    result = summarize_zero_import_registry_sha_peers([active, duplicate, no_peer])

    assert result["zero_import_vision_sources_total"] == 2
    assert result["residual_zero_import_sources_after_shared_slices"] == 2
    assert result["residual_sources_with_exact_registry_sha_peer"] == 1
    assert result["residual_sources_with_imported_registry_sha_peer"] == 0
    assert result["residual_sources_with_exact_excluded_duplicate_peer"] == 1
    assert result["source_ids_with_exact_excluded_duplicate_peer"] == ["active"]
    assert result["residual_sources_still_unexplained_after_duplicate_peer_evidence"] == 1
    assert result["source_ids_still_unexplained_after_duplicate_peer_evidence"] == ["no-peer"]
    assert result["excluded_duplicate_peer_does_not_prove_usable_text"] is True
    assert result["automatic_import_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_peer_must_match_full_range_size_and_logical_identity():
    active = _source("active", "sha-a", "phb")
    wrong_logical = _source(
        "wrong-logical",
        "sha-a",
        "other",
        status="duplicate",
        import_state="excluded",
    )
    partial = _source(
        "partial",
        "sha-a",
        "phb",
        status="duplicate",
        import_state="excluded",
        start=2,
    )
    wrong_size = _source(
        "wrong-size",
        "sha-a",
        "phb",
        status="duplicate",
        import_state="excluded",
        size=999,
    )

    result = summarize_zero_import_registry_sha_peers(
        [active, wrong_logical, partial, wrong_size]
    )

    assert result["residual_sources_with_exact_registry_sha_peer"] == 1
    assert result["residual_sources_with_exact_excluded_duplicate_peer"] == 0
    assert result["source_ids_still_unexplained_after_duplicate_peer_evidence"] == ["active"]


def test_imported_sha_peer_is_reported_but_never_authorizes_import():
    active = _source("active", "sha-a", "phb")
    imported_peer = _source(
        "imported-peer",
        "sha-a",
        "phb",
        status="superseded",
        import_state="imported",
        records=12,
    )

    result = summarize_zero_import_registry_sha_peers([active, imported_peer])

    assert result["residual_sources_with_imported_registry_sha_peer"] == 1
    assert result["source_ids_with_imported_registry_sha_peer"] == ["active"]
    assert result["automatic_import_authorized"] is False
    assert result["review_state_mutation_authorized"] is False


def test_shared_slice_group_is_excluded_before_sha_peer_triage():
    slice_a = _source("slice-a", "sha-shared", "part-a", start=1, end=5, pages=10)
    slice_b = _source("slice-b", "sha-shared", "part-b", start=6, end=10, pages=10)
    # Shared-slice detection groups by filename, so these two intentionally share it.
    slice_b["physical_filename"] = slice_a["physical_filename"]

    result = summarize_zero_import_registry_sha_peers([slice_a, slice_b])

    assert result["zero_import_vision_sources_total"] == 2
    assert result["sources_excluded_as_verified_shared_slices"] == 2
    assert result["residual_zero_import_sources_after_shared_slices"] == 0
    assert result["residual_sources_with_exact_registry_sha_peer"] == 0

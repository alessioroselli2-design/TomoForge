from scripts.audit_shared_physical_source_slices import (
    summarize_shared_physical_source_slices,
)


def _source(source_id: str, logical_id: str, start: int, end: int, *, sha: str = "abc") -> dict:
    return {
        "id": source_id,
        "source_status": "active",
        "import_state": "catalogued",
        "text_mode": "vision_required",
        "imported_record_count": 0,
        "physical_filename": "Compilation.pdf",
        "physical_sha256": sha,
        "physical_size_bytes": 123456,
        "physical_pages": 75,
        "logical_source_id": logical_id,
        "page_start": start,
        "page_end": end,
    }


def test_disjoint_logical_slices_explain_repeated_physical_filename_without_resolving_provenance():
    sources = [
        _source("a", "volume-a", 3, 13),
        _source("b", "volume-b", 14, 27),
        _source("c", "volume-c", 28, 33),
    ]

    result = summarize_shared_physical_source_slices(sources)

    assert result["zero_import_vision_sources_total"] == 3
    assert result["repeated_physical_filename_group_count"] == 1
    assert result["repeated_physical_filename_source_count"] == 3
    assert result["shared_physical_artifact_disjoint_slice_group_count"] == 1
    assert result["shared_physical_artifact_disjoint_slice_source_count"] == 3
    assert result["unresolved_repeated_physical_identity_group_count"] == 0
    assert result["source_ids_in_shared_physical_artifact_disjoint_slices"] == ["a", "b", "c"]
    assert result["shared_physical_slices_are_diagnostic_only"] is True
    assert result["shared_physical_slices_do_not_authorize_import"] is True
    assert result["shared_physical_slices_do_not_resolve_logical_provenance"] is True
    assert result["ocr_authorized"] is False
    assert result["external_processing_authorized"] is False
    assert result["automatic_import_authorized"] is False
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_overlapping_or_different_sha_groups_remain_unresolved():
    overlapping = [
        _source("overlap-a", "one", 3, 20),
        _source("overlap-b", "two", 20, 30),
    ]
    different_sha = [
        _source("sha-a", "three", 31, 40, sha="abc"),
        _source("sha-b", "four", 41, 50, sha="def"),
    ]
    for source in different_sha:
        source["physical_filename"] = "Collision.pdf"

    result = summarize_shared_physical_source_slices(overlapping + different_sha)

    assert result["repeated_physical_filename_group_count"] == 2
    assert result["shared_physical_artifact_disjoint_slice_group_count"] == 0
    assert result["shared_physical_artifact_disjoint_slice_source_count"] == 0
    assert result["unresolved_repeated_physical_identity_group_count"] == 2
    assert result["unresolved_repeated_physical_identity_source_count"] == 4
    assert result["source_ids_with_unresolved_repeated_physical_identity"] == [
        "overlap-a",
        "overlap-b",
        "sha-a",
        "sha-b",
    ]

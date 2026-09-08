from scripts.audit_zero_import_logical_source_peers import (
    summarize_zero_import_logical_source_peers,
)


def _source(
    source_id,
    sha,
    logical_id,
    *,
    status="active",
    import_state="catalogued",
    records=0,
    start=1,
    end=10,
    pages=10,
    size=1000,
    text_mode="vision_required",
    filename=None,
    title="Book",
    language="en",
    ruleset="2014",
    authority_class="official_supplement",
    source_role="authority",
):
    return {
        "id": source_id,
        "physical_filename": filename or f"{source_id}.pdf",
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
        "title": title,
        "language": language,
        "ruleset": ruleset,
        "authority_class": authority_class,
        "source_role": source_role,
    }


def test_text_mode_logical_peer_is_structurally_gated_and_never_authorizes_import():
    blocked = _source(
        "vision",
        "sha-vision",
        "ggtr",
        title="Guildmasters' Guide to Ravnica",
        pages=258,
        end=258,
        source_role="visual_aid",
    )
    text_peer = _source(
        "text",
        "sha-text",
        "ggtr",
        text_mode="text",
        title="Guildmasters' Guide to Ravnica",
        pages=258,
        end=258,
        source_role="authority",
    )

    result = summarize_zero_import_logical_source_peers([blocked, text_peer])

    assert result["residual_sources_entering_logical_peer_triage"] == 1
    assert result["residual_sources_with_same_logical_source_peer"] == 1
    assert result["residual_sources_with_text_mode_logical_peer"] == 1
    assert result["residual_sources_with_structurally_concordant_text_peer"] == 1
    assert result["residual_sources_with_only_incompatible_text_peer"] == 0
    assert result["source_ids_with_text_mode_logical_peer"] == ["vision"]
    assert result["structurally_concordant_text_peer_ids_by_source"] == {
        "vision": ["text"]
    }
    assert result["incompatible_text_peer_reasons_by_source"] == {}
    assert result["structural_concordance_is_review_candidate_only"] is True
    assert result["text_mode_peer_requires_provenance_review"] is True
    assert result["automatic_import_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_language_page_and_authority_mismatch_blocks_text_peer_concordance():
    blocked = _source(
        "vision",
        "sha-vision",
        "vgtm_2016_en",
        title="Volo's Guide to Monsters",
        language="en",
        pages=226,
        end=226,
        authority_class="official_supplement",
        source_role="visual_authority",
    )
    text_peer = _source(
        "text-ru",
        "sha-text",
        "vgtm_2016_en",
        text_mode="text",
        title="Volo's Guide to Monsters",
        language="ru",
        pages=231,
        end=231,
        authority_class="extraction_aid",
        source_role="extraction_aid",
    )

    result = summarize_zero_import_logical_source_peers([blocked, text_peer])

    assert result["residual_sources_with_text_mode_logical_peer"] == 1
    assert result["residual_sources_with_structurally_concordant_text_peer"] == 0
    assert result["residual_sources_with_only_incompatible_text_peer"] == 1
    reasons = result["incompatible_text_peer_reasons_by_source"]["vision"]["text-ru"]
    assert "language_mismatch" in reasons
    assert "authority_class_mismatch" in reasons
    assert "page_end_mismatch" in reasons
    assert "physical_pages_mismatch" in reasons
    assert "peer_source_role_is_extraction_aid" in reasons
    assert result["automatic_import_authorized"] is False


def test_missing_required_metadata_blocks_structural_concordance():
    blocked = _source("vision", "sha-vision", "book")
    text_peer = _source("text", "sha-text", "book", text_mode="text", language=None)

    result = summarize_zero_import_logical_source_peers([blocked, text_peer])

    assert result["residual_sources_with_structurally_concordant_text_peer"] == 0
    assert result["residual_sources_with_only_incompatible_text_peer"] == 1
    assert result["incompatible_text_peer_reasons_by_source"]["vision"]["text"] == [
        "language_missing"
    ]


def test_duplicate_or_excluded_text_peer_is_not_a_text_candidate():
    blocked = _source("vision", "sha-vision", "book")
    excluded = _source(
        "excluded",
        "sha-other",
        "book",
        status="duplicate",
        import_state="excluded",
        text_mode="text",
    )

    result = summarize_zero_import_logical_source_peers([blocked, excluded])

    assert result["residual_sources_with_same_logical_source_peer"] == 1
    assert result["residual_sources_with_text_mode_logical_peer"] == 0
    assert result["source_ids_with_text_mode_logical_peer"] == []


def test_imported_logical_peer_is_diagnostic_only():
    blocked = _source("vision", "sha-vision", "book")
    imported = _source(
        "imported",
        "sha-imported",
        "book",
        status="superseded",
        import_state="imported",
        records=42,
        text_mode="text",
    )

    result = summarize_zero_import_logical_source_peers([blocked, imported])

    assert result["residual_sources_with_imported_logical_peer"] == 1
    assert result["source_ids_with_imported_logical_peer"] == ["vision"]
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False


def test_prior_sha_duplicate_evidence_is_removed_before_logical_triage():
    active = _source("active", "sha-a", "phb")
    duplicate = _source(
        "duplicate",
        "sha-a",
        "phb",
        status="duplicate",
        import_state="excluded",
    )
    no_peer = _source("no-peer", "sha-b", "mm")

    result = summarize_zero_import_logical_source_peers([active, duplicate, no_peer])

    assert result["sources_explained_by_exact_excluded_duplicate_peer"] == 1
    assert result["residual_sources_entering_logical_peer_triage"] == 1
    assert result["source_ids_without_same_logical_source_peer"] == ["no-peer"]


def test_shared_physical_slices_are_removed_before_logical_triage():
    slice_a = _source(
        "slice-a",
        "sha-shared",
        "part-a",
        start=1,
        end=5,
        pages=10,
        filename="compilation.pdf",
    )
    slice_b = _source(
        "slice-b",
        "sha-shared",
        "part-b",
        start=6,
        end=10,
        pages=10,
        filename="compilation.pdf",
    )
    residual = _source("residual", "sha-r", "other")

    result = summarize_zero_import_logical_source_peers([slice_a, slice_b, residual])

    assert result["sources_excluded_as_verified_shared_slices"] == 2
    assert result["residual_sources_entering_logical_peer_triage"] == 1
    assert result["source_ids_without_same_logical_source_peer"] == ["residual"]

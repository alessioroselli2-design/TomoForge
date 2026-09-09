from scripts.audit_native_text_probe_preflight import summarize_native_text_probe_preflight


def _source(
    source_id,
    logical_id,
    language,
    *,
    text_mode="vision_required",
    source_role="authority",
    source_status="active",
    import_state="catalogued",
    imported_record_count=0,
    ruleset="2014",
):
    return {
        "id": source_id,
        "logical_source_id": logical_id,
        "language": language,
        "ruleset": ruleset,
        "text_mode": text_mode,
        "source_role": source_role,
        "source_status": source_status,
        "import_state": import_state,
        "imported_record_count": imported_record_count,
    }


def test_spanish_extraction_aid_passes_metadata_preflight_only():
    italian = _source("phb-it", "phb_2014_it", "it")
    spanish = _source(
        "phb-es",
        "phb_2014_es",
        "es",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_native_text_probe_preflight([italian, spanish])

    assert result["native_text_probe_preflight_ready_pairs"] == ["phb-it->phb-es"]
    assert result["native_text_probe_preflight_ready_count"] == 1
    assert result["native_text_probe_preflight_blocked_count"] == 0
    assert result["preflight_reads_pdf_bytes"] is False
    assert result["specific_pdf_parse_verified"] is False
    assert result["bounded_native_text_parser_probe_executed"] is False
    assert result["ocr_authorized"] is False
    assert result["translation_authorized"] is False
    assert result["automatic_import_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_non_active_aid_is_blocked():
    italian = _source("phb-it", "phb_2014_it", "it")
    spanish = _source(
        "phb-es",
        "phb_2014_es",
        "es",
        text_mode="text",
        source_role="extraction_aid",
        source_status="superseded",
    )

    result = summarize_native_text_probe_preflight([italian, spanish])

    assert result["native_text_probe_preflight_ready_count"] == 0
    assert result["native_text_probe_preflight_blocked_pairs"] == {
        "phb-it->phb-es": ["aid_not_active"]
    }


def test_existing_records_block_probe_candidate():
    italian = _source("phb-it", "phb_2014_it", "it", imported_record_count=4)
    spanish = _source(
        "phb-es",
        "phb_2014_es",
        "es",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_native_text_probe_preflight([italian, spanish])

    assert result["native_text_probe_preflight_ready_count"] == 0
    assert result["native_text_probe_preflight_blocked_pairs"] == {
        "phb-it->phb-es": ["target_already_has_imported_records"]
    }


def test_unsupported_language_never_enters_preflight_candidate_set():
    italian = _source("vgtm-it", "vgtm-2016", "it")
    russian = _source(
        "vgtm-ru",
        "vgtm-2016",
        "ru",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_native_text_probe_preflight([italian, russian])

    assert result["native_text_probe_preflight_pairs_checked"] == 0
    assert result["native_text_probe_preflight_ready_pairs"] == []
    assert result["native_text_probe_preflight_blocked_pairs"] == {}

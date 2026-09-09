from scripts.audit_multilingual_parser_support import summarize_multilingual_parser_support


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


def test_spanish_text_aid_is_only_a_bounded_parser_probe_candidate():
    italian = _source("phb-it", "phb_2014_it", "it")
    spanish = _source(
        "phb-es",
        "phb_2014_es",
        "es",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_multilingual_parser_support([italian, spanish])

    assert result["text_only_multilingual_aid_pairs_checked"] == 1
    assert result[
        "text_only_multilingual_aid_pairs_with_explicit_parser_language_support"
    ] == 1
    assert result[
        "text_only_multilingual_aid_pair_ids_with_explicit_parser_language_support"
    ] == ["phb-it->phb-es"]
    assert result["parser_language_support_state_by_pair"] == {
        "phb-it->phb-es": "explicit_language_heuristics"
    }
    assert result[
        "zero_import_difficult_sources_with_text_only_aid_and_explicit_parser_language_support"
    ] == ["phb-it"]
    assert result["compatibility_claim_is_language_heuristics_only"] is True
    assert result["specific_pdf_parse_verified"] is False
    assert result["bounded_native_text_parser_probe_authorized"] is False
    assert result["ocr_authorized"] is False
    assert result["translation_authorized"] is False
    assert result["automatic_import_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_text_aid_without_explicit_language_heuristics_stays_blocked():
    italian = _source("vgtm-it", "vgtm-2016", "it")
    russian = _source(
        "vgtm-ru",
        "vgtm-2016",
        "ru",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_multilingual_parser_support([italian, russian])

    assert result[
        "text_only_multilingual_aid_pairs_without_explicit_parser_language_support"
    ] == 1
    assert result[
        "text_only_multilingual_aid_pair_ids_without_explicit_parser_language_support"
    ] == ["vgtm-it->vgtm-ru"]
    assert result["parser_language_support_state_by_pair"] == {
        "vgtm-it->vgtm-ru": "no_explicit_language_heuristics"
    }
    assert result[
        "zero_import_difficult_sources_with_text_only_aid_without_explicit_parser_language_support"
    ] == ["vgtm-it"]
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False


def test_structured_peer_is_not_reclassified_as_text_only_parser_candidate():
    italian = _source("book-it", "book", "it")
    spanish = _source(
        "book-es",
        "book",
        "es",
        text_mode="text",
        source_role="extraction_aid",
        import_state="imported",
        imported_record_count=12,
    )

    result = summarize_multilingual_parser_support([italian, spanish])

    assert result["text_only_multilingual_aid_pairs_checked"] == 0
    assert result[
        "text_only_multilingual_aid_pairs_with_explicit_parser_language_support"
    ] == 0
    assert result["parser_language_support_state_by_pair"] == {}


def test_supported_languages_are_explicit_and_testable():
    italian = _source("book-it", "book", "it")
    french = _source(
        "book-fr",
        "book",
        "fr",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_multilingual_parser_support(
        [italian, french], explicit_parser_languages={"fr"}
    )

    assert result["explicit_parser_languages"] == ["fr"]
    assert result["parser_language_support_state_by_pair"] == {
        "book-it->book-fr": "explicit_language_heuristics"
    }

from scripts.audit_multilingual_extraction_aids import summarize_multilingual_extraction_aids


def _source(
    source_id,
    logical_id,
    language,
    *,
    ruleset="2014",
    text_mode="vision_required",
    source_role="authority",
    source_status="active",
    import_state="catalogued",
    imported_record_count=0,
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


def test_cross_language_extraction_aid_is_reported_without_authorizing_translation_or_import():
    italian = _source("phb-it", "phb-2014", "it")
    spanish_aid = _source(
        "phb-es",
        "phb-2014",
        "es",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_multilingual_extraction_aids([italian, spanish_aid])

    assert result["multilingual_extraction_aid_pairs"] == 1
    assert result["logical_sources_with_multilingual_extraction_aid"] == 1
    assert result["multilingual_extraction_aid_pair_ids"] == ["phb-it->phb-es"]
    assert result["multilingual_extraction_aid_pair_match_types"] == {
        "phb-it->phb-es": "exact_logical_source_id"
    }
    assert result["multilingual_extraction_aid_peer_ids_by_source"] == {
        "phb-it": ["phb-es"]
    }
    assert result["structured_multilingual_extraction_aid_peer_ids_by_source"] == {}
    assert result["text_only_multilingual_extraction_aid_peer_ids_by_source"] == {
        "phb-it": ["phb-es"]
    }
    assert result["zero_import_difficult_sources_with_multilingual_extraction_aid"] == [
        "phb-it"
    ]
    assert result[
        "zero_import_difficult_sources_with_structured_multilingual_extraction_aid"
    ] == []
    assert result[
        "zero_import_difficult_sources_with_text_only_multilingual_extraction_aid"
    ] == ["phb-it"]
    assert result["zero_import_difficult_sources_without_multilingual_extraction_aid"] == []
    assert result["text_only_extraction_aid_requires_structured_parse_before_record_reuse"] is True
    assert result["cross_language_peer_is_intentional_extraction_evidence_only"] is True
    assert result["cross_language_peer_does_not_prove_translation_equivalence"] is True
    assert result["cross_language_peer_does_not_replace_authoritative_language_source"] is True
    assert result["translation_authorized"] is False
    assert result["automatic_import_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_imported_extraction_aid_is_separated_from_text_only_peer():
    italian = _source("book-it", "book-2014", "it")
    english_aid = _source(
        "book-en",
        "book-2014",
        "en",
        text_mode="text",
        source_role="extraction_aid",
        import_state="imported",
        imported_record_count=12,
    )

    result = summarize_multilingual_extraction_aids([italian, english_aid])

    assert result["structured_multilingual_extraction_aid_peer_ids_by_source"] == {
        "book-it": ["book-en"]
    }
    assert result["text_only_multilingual_extraction_aid_peer_ids_by_source"] == {}
    assert result[
        "zero_import_difficult_sources_with_structured_multilingual_extraction_aid"
    ] == ["book-it"]
    assert result[
        "zero_import_difficult_sources_with_text_only_multilingual_extraction_aid"
    ] == []
    assert result["structured_peer_records_are_cross_language_evidence_only"] is True
    assert result["automatic_import_authorized"] is False
    assert result["translation_authorized"] is False


def test_language_suffixed_ids_link_only_with_matching_metadata_and_ruleset():
    italian = _source("phb-it", "phb_2014_it", "it")
    spanish_aid = _source(
        "phb-es",
        "phb_2014_es",
        "es",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_multilingual_extraction_aids([italian, spanish_aid])

    assert result["multilingual_extraction_aid_pair_ids"] == ["phb-it->phb-es"]
    assert result["multilingual_extraction_aid_pair_match_types"] == {
        "phb-it->phb-es": "language_suffixed_family"
    }
    assert result["zero_import_difficult_sources_with_multilingual_extraction_aid"] == [
        "phb-it"
    ]
    assert result["title_or_filename_matching_used"] is False


def test_language_suffixed_family_rejects_language_metadata_mismatch():
    italian = _source("book-it", "book_2014_it", "it")
    mislabeled_aid = _source(
        "book-ru",
        "book_2014_en",
        "ru",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_multilingual_extraction_aids([italian, mislabeled_aid])

    assert result["multilingual_extraction_aid_pairs"] == 0
    assert result["zero_import_difficult_sources_without_multilingual_extraction_aid"] == [
        "book-it"
    ]


def test_language_suffixed_family_rejects_different_rulesets():
    italian = _source("book-it", "book_2014_it", "it", ruleset="2014")
    spanish_aid = _source(
        "book-es",
        "book_2014_es",
        "es",
        ruleset="2024",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_multilingual_extraction_aids([italian, spanish_aid])

    assert result["multilingual_extraction_aid_pairs"] == 0
    assert result["zero_import_difficult_sources_without_multilingual_extraction_aid"] == [
        "book-it"
    ]


def test_same_language_copy_is_not_classified_as_multilingual_extraction_aid():
    authority = _source("book-a", "book", "it")
    same_language_aid = _source(
        "book-b",
        "book",
        "it",
        text_mode="text",
        source_role="extraction_aid",
    )

    result = summarize_multilingual_extraction_aids([authority, same_language_aid])

    assert result["multilingual_extraction_aid_pairs"] == 0
    assert result["multilingual_extraction_aid_peer_ids_by_source"] == {}
    assert result["zero_import_difficult_sources_with_multilingual_extraction_aid"] == []
    assert result["zero_import_difficult_sources_without_multilingual_extraction_aid"] == [
        "book-a"
    ]
    assert result["duplicate_deletion_authorized"] is False


def test_cross_language_authority_peer_is_not_implicitly_treated_as_extraction_aid():
    italian = _source("book-it", "book", "it")
    english_authority = _source("book-en", "book", "en", text_mode="text")

    result = summarize_multilingual_extraction_aids([italian, english_authority])

    assert result["multilingual_extraction_aid_pairs"] == 0
    assert result["zero_import_difficult_sources_without_multilingual_extraction_aid"] == [
        "book-it"
    ]
    assert result["translation_authorized"] is False


def test_excluded_or_non_text_extraction_aid_is_not_eligible():
    authority = _source("book-it", "book", "it")
    excluded = _source(
        "book-es",
        "book",
        "es",
        text_mode="text",
        source_role="extraction_aid",
        source_status="duplicate",
        import_state="excluded",
    )
    vision_only = _source(
        "book-fr",
        "book",
        "fr",
        text_mode="vision_required",
        source_role="extraction_aid",
    )

    result = summarize_multilingual_extraction_aids([authority, excluded, vision_only])

    assert result["multilingual_extraction_aid_pairs"] == 0
    assert result["zero_import_difficult_sources_without_multilingual_extraction_aid"] == [
        "book-it"
    ]
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False


def test_only_catalogued_zero_import_difficult_sources_are_triaged():
    already_imported = _source(
        "imported-it",
        "imported-book",
        "it",
        imported_record_count=4,
    )
    text_source = _source(
        "text-it",
        "text-book",
        "it",
        text_mode="text",
    )
    excluded = _source(
        "excluded-it",
        "excluded-book",
        "it",
        import_state="excluded",
        source_status="duplicate",
    )

    result = summarize_multilingual_extraction_aids([already_imported, text_source, excluded])

    assert result["zero_import_difficult_sources_with_multilingual_extraction_aid"] == []
    assert result["zero_import_difficult_sources_without_multilingual_extraction_aid"] == []

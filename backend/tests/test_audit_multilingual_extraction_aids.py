from scripts.audit_multilingual_extraction_aids import summarize_multilingual_extraction_aids


def _source(
    source_id,
    logical_id,
    language,
    *,
    text_mode="vision_required",
    source_role="authority",
    source_status="active",
    import_state="catalogued",
):
    return {
        "id": source_id,
        "logical_source_id": logical_id,
        "language": language,
        "text_mode": text_mode,
        "source_role": source_role,
        "source_status": source_status,
        "import_state": import_state,
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
    assert result["multilingual_extraction_aid_peer_ids_by_source"] == {
        "phb-it": ["phb-es"]
    }
    assert result["cross_language_peer_is_intentional_extraction_evidence_only"] is True
    assert result["cross_language_peer_does_not_prove_translation_equivalence"] is True
    assert result["cross_language_peer_does_not_replace_authoritative_language_source"] is True
    assert result["translation_authorized"] is False
    assert result["automatic_import_authorized"] is False
    assert result["canonicalization_authorized"] is False


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
    assert result["duplicate_deletion_authorized"] is False


def test_cross_language_authority_peer_is_not_implicitly_treated_as_extraction_aid():
    italian = _source("book-it", "book", "it")
    english_authority = _source("book-en", "book", "en", text_mode="text")

    result = summarize_multilingual_extraction_aids([italian, english_authority])

    assert result["multilingual_extraction_aid_pairs"] == 0
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
    assert result["database_write_authorized"] is False
    assert result["review_state_mutation_authorized"] is False

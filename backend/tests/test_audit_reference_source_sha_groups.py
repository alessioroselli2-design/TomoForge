from scripts.audit_reference_source_sha_groups import summarize_reference_source_sha_groups


def test_classifies_duplicates_and_split_compilations_conservatively():
    sources = [
        {
            "id": "dup-active",
            "physical_sha256": "a" * 64,
            "logical_source_id": "book_a",
            "page_start": 1,
            "page_end": 10,
        },
        {
            "id": "dup-copy",
            "physical_sha256": "a" * 64,
            "logical_source_id": "book_a",
            "page_start": 1,
            "page_end": 10,
        },
        {
            "id": "part-1",
            "physical_sha256": "b" * 64,
            "logical_source_id": "part_one",
            "page_start": 1,
            "page_end": 20,
        },
        {
            "id": "part-2",
            "physical_sha256": "b" * 64,
            "logical_source_id": "part_two",
            "page_start": 21,
            "page_end": 40,
        },
        {
            "id": "single",
            "physical_sha256": "c" * 64,
            "logical_source_id": "single",
            "page_start": 1,
            "page_end": 5,
        },
    ]

    result = summarize_reference_source_sha_groups(sources)

    assert result["shared_sha_groups_total"] == 2
    assert result["same_logical_source_duplicates"] == 1
    assert result["split_compilations_non_overlapping"] == 1
    assert result["shared_sha_needs_review"] == 0
    assert [group["classification"] for group in result["groups"]] == [
        "same_logical_source_duplicate",
        "split_compilation_non_overlapping",
    ]
    assert result["database_write_authorized"] is False
    assert result["source_deletion_authorized"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["ocr_generation_authorized"] is False
    assert result["canonicalization_authorized"] is False


def test_overlapping_or_incomplete_split_needs_review():
    sources = [
        {
            "id": "overlap-1",
            "physical_sha256": "d" * 64,
            "logical_source_id": "one",
            "page_start": 1,
            "page_end": 20,
        },
        {
            "id": "overlap-2",
            "physical_sha256": "d" * 64,
            "logical_source_id": "two",
            "page_start": 20,
            "page_end": 30,
        },
        {
            "id": "missing-range-1",
            "physical_sha256": "e" * 64,
            "logical_source_id": "three",
            "page_start": None,
            "page_end": None,
        },
        {
            "id": "missing-range-2",
            "physical_sha256": "e" * 64,
            "logical_source_id": "four",
            "page_start": 1,
            "page_end": 10,
        },
    ]

    result = summarize_reference_source_sha_groups(sources)

    assert result["shared_sha_groups_total"] == 2
    assert result["shared_sha_needs_review"] == 2
    assert result["same_logical_source_duplicates"] == 0
    assert result["split_compilations_non_overlapping"] == 0

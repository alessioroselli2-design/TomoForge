import asyncio

from scripts.audit_logical_source_coverage import (
    fetch_all,
    summarize_logical_source_coverage,
)


class FakeCollection:
    def __init__(self, rows):
        self.rows = rows
        self.offsets = []

    def find(self, query):
        assert query == {}
        return self

    async def to_list(self, limit, offset=0):
        self.offsets.append(offset)
        return self.rows[offset:offset + limit]


def test_fetch_all_reads_every_page_without_duplication():
    collection = FakeCollection([{"id": index} for index in range(5)])

    result = asyncio.run(fetch_all(collection, page_size=2))

    assert [row["id"] for row in result] == list(range(5))
    assert collection.offsets == [0, 2, 4]


def test_summarize_reports_aggregate_logical_source_coverage_only():
    records = [
        {"source_refs": [{"logical_source_id": "source-alpha", "filename": "private-a.pdf"}]},
        {"source_refs": [{"logical_source_id": "source-alpha"}, {"logical_source_id": "source-beta"}]},
        {"source_refs": [{"logical_source_id": "source-missing", "text": "private source text"}]},
        {"source_refs": [{"filename": "legacy.pdf"}]},
        {"source_refs": None},
    ]
    sources = [
        {"logical_source_id": "source-alpha", "physical_filename": "private-a.pdf"},
        {"logical_source_id": "source-beta", "physical_filename": "private-b.pdf"},
    ]

    result = summarize_logical_source_coverage(records, sources)

    assert result == {
        "records_total": 5,
        "records_with_logical_source_id": 3,
        "records_without_logical_source_id": 2,
        "records_with_multiple_logical_source_ids": 1,
        "records_with_only_catalogued_logical_source_ids": 2,
        "records_with_unknown_logical_source_ids": 1,
        "records_without_id_with_filename_hint": 1,
        "records_without_id_without_filename_hint": 1,
        "records_without_id_with_unique_filename_match": 0,
        "records_without_id_with_ambiguous_filename_match": 0,
        "records_without_id_with_unmatched_filename": 1,
        "logical_source_record_coverage_ratio": 0.6,
        "catalog_logical_source_ids": 2,
        "referenced_logical_source_ids": 3,
        "unknown_referenced_logical_source_ids": 1,
        "logical_source_references_resolve": False,
    }
    rendered = str(result)
    assert "source-alpha" not in rendered
    assert "source-beta" not in rendered
    assert "source-missing" not in rendered
    assert "private-a.pdf" not in rendered
    assert "private source text" not in rendered


def test_summarize_classifies_legacy_filename_matches_without_exposing_names():
    records = [
        {"source_refs": [{"filename": "unique.pdf"}]},
        {"source_refs": [{"filename": "ambiguous.pdf"}]},
        {"source_refs": [{"filename": "missing.pdf"}]},
        {"source_refs": [{"filename": "first.pdf"}, {"filename": "second.pdf"}]},
        {"source_refs": []},
    ]
    sources = [
        {"logical_source_id": "source-unique", "physical_filename": "unique.pdf"},
        {"logical_source_id": "source-a", "physical_filename": "ambiguous.pdf"},
        {"logical_source_id": "source-b", "filename": "ambiguous.pdf"},
        {"logical_source_id": "source-shared", "physical_filename": "first.pdf"},
        {"logical_source_id": "source-shared", "physical_filename": "second.pdf"},
    ]

    result = summarize_logical_source_coverage(records, sources)

    assert result["records_without_logical_source_id"] == 5
    assert result["records_without_id_with_filename_hint"] == 4
    assert result["records_without_id_without_filename_hint"] == 1
    assert result["records_without_id_with_unique_filename_match"] == 2
    assert result["records_without_id_with_ambiguous_filename_match"] == 1
    assert result["records_without_id_with_unmatched_filename"] == 1
    rendered = str(result)
    assert "unique.pdf" not in rendered
    assert "ambiguous.pdf" not in rendered
    assert "source-unique" not in rendered


def test_summarize_deduplicates_repeated_ids_and_ignores_malformed_refs():
    records = [
        {
            "source_refs": [
                {"logical_source_id": " source-alpha "},
                {"logical_source_id": "source-alpha"},
                {"logical_source_id": ""},
                None,
                "not-a-dict",
            ]
        }
    ]
    sources = [
        {"logical_source_id": "source-alpha"},
        {"logical_source_id": "source-alpha"},
        {"logical_source_id": None},
    ]

    result = summarize_logical_source_coverage(records, sources)

    assert result["records_with_logical_source_id"] == 1
    assert result["records_with_multiple_logical_source_ids"] == 0
    assert result["catalog_logical_source_ids"] == 1
    assert result["referenced_logical_source_ids"] == 1
    assert result["logical_source_references_resolve"] is True


def test_summarize_handles_empty_catalogue():
    result = summarize_logical_source_coverage([], [])

    assert result == {
        "records_total": 0,
        "records_with_logical_source_id": 0,
        "records_without_logical_source_id": 0,
        "records_with_multiple_logical_source_ids": 0,
        "records_with_only_catalogued_logical_source_ids": 0,
        "records_with_unknown_logical_source_ids": 0,
        "records_without_id_with_filename_hint": 0,
        "records_without_id_without_filename_hint": 0,
        "records_without_id_with_unique_filename_match": 0,
        "records_without_id_with_ambiguous_filename_match": 0,
        "records_without_id_with_unmatched_filename": 0,
        "logical_source_record_coverage_ratio": 0.0,
        "catalog_logical_source_ids": 0,
        "referenced_logical_source_ids": 0,
        "unknown_referenced_logical_source_ids": 0,
        "logical_source_references_resolve": True,
    }

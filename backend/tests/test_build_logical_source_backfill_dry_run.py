from scripts.build_logical_source_backfill_dry_run import build_backfill_plan


def test_dry_run_proposes_only_unique_normalized_matches():
    records = [
        {"id": "r-unique", "source_refs": [{"filename": "Bardo__1787233073462.pdf"}]},
        {"id": "r-ambiguous", "source_refs": [{"filename": "shared__1787233073462.pdf"}]},
        {"id": "r-unmatched", "source_refs": [{"filename": "missing.pdf"}]},
        {"id": "r-existing", "source_refs": [{"logical_source_id": "already-set", "filename": "Bardo.pdf"}]},
        {"id": "r-no-file", "source_refs": []},
    ]
    sources = [
        {"logical_source_id": "derived-bard", "physical_filename": "Bardo.pdf"},
        {"logical_source_id": "source-a", "physical_filename": "shared.pdf"},
        {"logical_source_id": "source-b", "physical_filename": "shared (1).pdf"},
    ]

    result = build_backfill_plan(records, sources)

    assert result["mode"] == "dry_run"
    assert result["writes_performed"] == 0
    assert result["proposed_backfills"] == 1
    assert result["candidates"] == [
        {"record_id": "r-unique", "logical_source_id": "derived-bard"}
    ]
    assert result["excluded_existing_provenance"] == 1
    assert result["excluded_no_filename"] == 1
    assert result["excluded_ambiguous"] == 1
    assert result["excluded_unmatched"] == 1
    assert result["candidate_record_ids_unique"] is True


def test_dry_run_excludes_missing_record_ids_instead_of_guessing():
    records = [
        {"source_refs": [{"filename": "Bardo.pdf"}]},
        {"id": "  ", "source_refs": [{"filename": "Bardo.pdf"}]},
    ]
    sources = [{"logical_source_id": "derived-bard", "physical_filename": "Bardo.pdf"}]

    result = build_backfill_plan(records, sources)

    assert result["proposed_backfills"] == 0
    assert result["excluded_missing_record_id"] == 2
    assert result["writes_performed"] == 0


def test_dry_run_is_deterministic_and_does_not_mutate_inputs():
    records = [
        {"id": "r-b", "source_refs": [{"filename": "Second__1787233073462.pdf"}]},
        {"id": "r-a", "source_refs": [{"filename": "First__1787233073462.pdf"}]},
    ]
    sources = [
        {"logical_source_id": "source-second", "physical_filename": "Second.pdf"},
        {"logical_source_id": "source-first", "physical_filename": "First.pdf"},
    ]
    original_records = [dict(row, source_refs=[dict(ref) for ref in row["source_refs"]]) for row in records]
    original_sources = [dict(row) for row in sources]

    first = build_backfill_plan(records, sources)
    second = build_backfill_plan(list(reversed(records)), list(reversed(sources)))

    assert first == second
    assert first["candidates"] == [
        {"record_id": "r-a", "logical_source_id": "source-first"},
        {"record_id": "r-b", "logical_source_id": "source-second"},
    ]
    assert records == original_records
    assert sources == original_sources
    assert first["writes_performed"] == 0


def test_dry_run_requires_one_logical_id_across_all_filename_hints():
    records = [
        {
            "id": "r-conflict",
            "source_refs": [{"filename": "first.pdf"}, {"filename": "second.pdf"}],
        },
        {
            "id": "r-same-source",
            "source_refs": [{"filename": "copy-a.pdf"}, {"filename": "copy-b.pdf"}],
        },
    ]
    sources = [
        {"logical_source_id": "source-a", "physical_filename": "first.pdf"},
        {"logical_source_id": "source-b", "physical_filename": "second.pdf"},
        {"logical_source_id": "source-c", "physical_filename": "copy-a.pdf"},
        {"logical_source_id": "source-c", "physical_filename": "copy-b.pdf"},
    ]

    result = build_backfill_plan(records, sources)

    assert result["proposed_backfills"] == 1
    assert result["excluded_ambiguous"] == 1
    assert result["candidates"] == [
        {"record_id": "r-same-source", "logical_source_id": "source-c"}
    ]
    assert result["writes_performed"] == 0

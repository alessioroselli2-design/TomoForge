from scripts.audit_schema_cache_source_links import summarize_schema_cache_source_links


def test_schema_cache_source_linkage_is_aggregate_and_read_only():
    private_error = "PGRST204 schema cache private payload"
    private_fingerprint = "secret-fingerprint"
    jobs = [
        {
            "status": "failed",
            "filename": "private-a.pdf",
            "last_error": private_error,
            "source_fingerprint": private_fingerprint,
            "records_imported": 4,
        },
        {
            "status": "failed",
            "filename": "private-b.pdf",
            "last_error": private_error,
            "source_fingerprint": "missing-fingerprint",
            "records_flagged": 2,
        },
        {"status": "completed", "source_fingerprint": private_fingerprint, "records_imported": 9},
    ]
    sources = [
        {
            "physical_filename": "registered-private.pdf",
            "physical_sha256": private_fingerprint,
            "logical_source_id": "logical-a",
            "source_status": "active",
        }
    ]

    result = summarize_schema_cache_source_links(jobs, sources)

    assert result == {
        "failed_schema_cache_jobs": 2,
        "failed_schema_cache_jobs_with_record_activity": 2,
        "with_exact_registered_source_fingerprint": 1,
        "with_exact_active_single_logical_source": 1,
        "without_exact_registered_source_fingerprint": 1,
        "fingerprint_reconciliation_complete": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
    }
    rendered = str(result)
    assert "private-a.pdf" not in rendered
    assert "private-b.pdf" not in rendered
    assert "registered-private.pdf" not in rendered
    assert private_error not in rendered
    assert private_fingerprint not in rendered


def test_schema_cache_source_linkage_requires_record_activity():
    result = summarize_schema_cache_source_links(
        [
            {
                "status": "failed",
                "last_error": "PGRST204 missing field in schema cache",
                "source_fingerprint": "sha-a",
                "records_imported": 0,
            }
        ],
        [{"physical_sha256": "sha-a", "logical_source_id": "logical-a", "source_status": "active"}],
    )

    assert result["failed_schema_cache_jobs"] == 1
    assert result["failed_schema_cache_jobs_with_record_activity"] == 0
    assert result["with_exact_registered_source_fingerprint"] == 0
    assert result["without_exact_registered_source_fingerprint"] == 0
    assert result["fingerprint_reconciliation_complete"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False

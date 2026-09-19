from scripts.audit_schema_cache_logical_provenance import (
    summarize_schema_cache_logical_provenance,
)


def test_logical_provenance_reconciles_only_exact_record_key_and_single_active_identity():
    private_error = "PGRST204 schema cache private payload"
    private_job_name = "Manuale_del_giocatore__1787259882002.pdf"
    jobs = [
        {
            "status": "failed",
            "filename": private_job_name,
            "last_error": private_error,
            "records_imported": 10,
        }
    ]
    sources = [
        {
            "physical_filename": "Manuale del giocatore .pdf",
            "logical_source_id": "logical-private-a",
            "source_status": "active",
        },
        {
            "physical_filename": "Manuale del Giocatore (1).pdf",
            "logical_source_id": "logical-private-a",
            "source_status": "duplicate",
        },
    ]
    records = [{"source_key": private_job_name}, {"source_key": private_job_name}]

    result = summarize_schema_cache_logical_provenance(jobs, sources, records)

    assert result == {
        "schema_cache_failures_with_record_activity": 1,
        "with_exact_record_source_key_provenance": 1,
        "with_reconciled_active_logical_source_identity": 1,
        "with_ambiguous_registry_identity": 0,
        "without_registry_identity_match": 0,
        "logical_identity_reconciliation_complete": True,
        "record_set_completeness_confirmed": False,
        "automatic_retry_authorized": False,
        "database_write_authorized": False,
    }
    rendered = str(result)
    assert private_job_name not in rendered
    assert private_error not in rendered
    assert "logical-private-a" not in rendered


def test_logical_provenance_does_not_claim_reconciliation_without_exact_record_key():
    result = summarize_schema_cache_logical_provenance(
        [
            {
                "status": "failed",
                "filename": "Tasha_1787259976040.pdf",
                "last_error": "PGRST204 schema cache",
                "records_flagged": 2,
            }
        ],
        [
            {
                "physical_filename": "Tasha.pdf",
                "logical_source_id": "logical-a",
                "source_status": "active",
            }
        ],
        [{"source_key": "different-upload.pdf"}],
    )

    assert result["with_exact_record_source_key_provenance"] == 0
    assert result["with_reconciled_active_logical_source_identity"] == 0
    assert result["logical_identity_reconciliation_complete"] is False
    assert result["record_set_completeness_confirmed"] is False


def test_logical_provenance_rejects_ambiguous_logical_identity():
    filename = "Example_1787259976040.pdf"
    result = summarize_schema_cache_logical_provenance(
        [
            {
                "status": "failed",
                "filename": filename,
                "last_error": "PGRST204 schema cache",
                "records_updated": 3,
            }
        ],
        [
            {
                "physical_filename": "Example.pdf",
                "logical_source_id": "logical-a",
                "source_status": "active",
            },
            {
                "physical_filename": "Example.pdf",
                "logical_source_id": "logical-b",
                "source_status": "active",
            },
        ],
        [{"source_key": filename}],
    )

    assert result["with_exact_record_source_key_provenance"] == 1
    assert result["with_reconciled_active_logical_source_identity"] == 0
    assert result["with_ambiguous_registry_identity"] == 1
    assert result["logical_identity_reconciliation_complete"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["database_write_authorized"] is False

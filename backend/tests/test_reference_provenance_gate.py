from reference_library import reference_rule_source


def test_reference_rule_source_preserves_physical_and_canonical_provenance():
    record = {
        "id": "record-1",
        "name": "Example Rule",
        "reference_type": "spell",
        "source_refs": [
            {
                "filename": "manual.pdf",
                "page": 42,
                "logical_source_id": "source-1",
                "logical_page": 40,
            }
        ],
        "canonical_id": "canonical-1",
        "ai_review_status": "verified",
        "ai_confidence": 0.99,
        "ai_review_corrections": {
            "selected": True,
            "canonical_source_refs": [
                {
                    "logical_source_id": "source-1",
                    "logical_page": 40,
                }
            ],
        },
    }

    source = reference_rule_source(record)

    assert source["source_id"] == "record-1"
    assert source["source_refs"] == record["source_refs"]
    assert source["canonical_id"] == "canonical-1"
    assert source["canonical_verification_status"] == "verified"
    assert source["canonical_selected"] is True
    assert source["canonical_source_refs"] == record["ai_review_corrections"]["canonical_source_refs"]


def test_reference_rule_source_does_not_invent_canonical_provenance_when_unlinked():
    record = {
        "id": "record-2",
        "name": "Unlinked Rule",
        "reference_type": "feat",
        "source_refs": [{"filename": "manual.pdf", "page": 7}],
        "canonical_id": None,
        "ai_review_status": "pending",
        "ai_review_corrections": {},
    }

    source = reference_rule_source(record)

    assert source["source_refs"] == record["source_refs"]
    assert "canonical_id" not in source
    assert "canonical_source_refs" not in source
    assert "canonical_selected" not in source

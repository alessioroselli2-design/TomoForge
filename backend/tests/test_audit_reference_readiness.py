import asyncio

from scripts.audit_reference_readiness import fetch_all, summarize_readiness


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
    collection = FakeCollection([{"id": index} for index in range(7)])

    result = asyncio.run(fetch_all(collection, page_size=3))

    assert [row["id"] for row in result] == list(range(7))
    assert collection.offsets == [0, 3, 6]


def test_summarize_readiness_reports_only_aggregate_state():
    records = [
        {"review_status": "verified", "ai_review_status": "verified", "translation_status": "not_required", "canonical_id": None, "reference_type": "spell", "name": "Private rule text"},
        {"review_status": "needs_review", "ai_review_status": "pending", "translation_status": "failed", "canonical_id": "canon-1", "reference_type": "spell", "full_text": "Sensitive source text"},
        {"review_status": "pending", "ai_review_status": "low_confidence", "translation_status": "translated", "canonical_id": "", "reference_type": "feat"},
    ]
    sources = [
        {"source_status": "active", "text_mode": "text", "import_state": "catalogued", "physical_filename": "private.pdf"},
        {"source_status": "duplicate", "text_mode": "vision_required", "import_state": "excluded"},
        {"source_status": "superseded", "text_mode": "mixed", "import_state": "catalogued"},
    ]
    canonical = [
        {"verification_status": "verified", "full_text": "canonical private text"},
        {"verification_status": "manual_review"},
    ]

    result = summarize_readiness(records, sources, canonical)

    assert result == {
        "records_total": 3,
        "records_verified": 1,
        "records_needs_review": 1,
        "records_pending": 1,
        "review_status_breakdown": {"needs_review": 1, "pending": 1, "verified": 1},
        "ai_review_status_breakdown": {"low_confidence": 1, "pending": 1, "verified": 1},
        "records_ai_verified": 1,
        "records_ai_pending": 1,
        "records_ai_conflict": 0,
        "records_ai_low_confidence": 1,
        "review_queue_by_reference_type": {"feat": 1, "spell": 1},
        "review_queue_by_status_and_reference_type": {
            "needs_review": {"spell": 1},
            "pending": {"feat": 1},
        },
        "review_queue_by_language_translation_and_ai": {
            "unknown|failed|pending": 1,
            "unknown|translated|low_confidence": 1,
        },
        "no_translation_review_queue_by_reference_type": {},
        "translation_failed": 1,
        "translation_translated": 1,
        "records_linked_to_canonical": 1,
        "verified_ratio": 0.3333,
        "sources_total": 3,
        "source_status_breakdown": {"active": 1, "duplicate": 1, "superseded": 1},
        "source_text_mode_breakdown": {"mixed": 1, "text": 1, "vision_required": 1},
        "source_import_state_breakdown": {"catalogued": 2, "excluded": 1},
        "sources_active": 1,
        "sources_duplicate": 1,
        "sources_superseded": 1,
        "sources_catalogued": 2,
        "sources_excluded": 1,
        "sources_text": 1,
        "sources_mixed": 1,
        "sources_vision_required": 1,
        "canonical_total": 2,
        "canonical_status_breakdown": {"manual_review": 1, "verified": 1},
        "canonical_verified": 1,
        "canonical_ai_verified": 0,
        "canonical_manual_review": 1,
        "canonical_conflict": 0,
        "canonical_low_confidence": 0,
    }
    rendered = str(result)
    assert "Private rule text" not in rendered
    assert "Sensitive source text" not in rendered
    assert "private.pdf" not in rendered
    assert "canonical private text" not in rendered


def test_summarize_readiness_orders_review_queue_by_count_then_type():
    records = [
        {"review_status": "needs_review", "reference_type": "spell"},
        {"review_status": "pending", "reference_type": "spell"},
        {"review_status": "pending", "reference_type": "feat"},
        {"review_status": "needs_review", "reference_type": "race"},
        {"review_status": "verified", "reference_type": "spell"},
        {"review_status": "pending"},
    ]

    result = summarize_readiness(records, [], [])

    assert list(result["review_queue_by_reference_type"].items()) == [
        ("spell", 2),
        ("feat", 1),
        ("race", 1),
        ("unknown", 1),
    ]
    assert result["review_queue_by_status_and_reference_type"] == {
        "needs_review": {"race": 1, "spell": 1},
        "pending": {"feat": 1, "spell": 1, "unknown": 1},
    }
    assert result["review_queue_by_language_translation_and_ai"] == {
        "unknown|unknown|unknown": 5,
    }
    assert result["no_translation_review_queue_by_reference_type"] == {}


def test_summarize_readiness_groups_processing_state_without_content():
    records = [
        {"review_status": "needs_review", "source_language": "it", "translation_status": "not_required", "ai_review_status": "pending"},
        {"review_status": "pending", "source_language": "it", "translation_status": "not_required", "ai_review_status": "pending"},
        {"review_status": "needs_review", "source_language": "es", "translation_status": "failed", "ai_review_status": "pending"},
        {"review_status": "verified", "source_language": "es", "translation_status": "failed", "ai_review_status": "pending"},
    ]

    result = summarize_readiness(records, [], [])

    assert result["review_queue_by_language_translation_and_ai"] == {
        "it|not_required|pending": 2,
        "es|failed|pending": 1,
    }
    assert result["no_translation_review_queue_by_reference_type"] == {"unknown": 2}


def test_summarize_readiness_isolates_no_translation_review_queue_by_type():
    records = [
        {"review_status": "needs_review", "source_language": "it", "translation_status": "not_required", "reference_type": "weapon"},
        {"review_status": "pending", "source_language": "it", "translation_status": "not_required", "reference_type": "spell"},
        {"review_status": "needs_review", "source_language": "it", "translation_status": "not_required", "reference_type": "weapon"},
        {"review_status": "verified", "source_language": "it", "translation_status": "not_required", "reference_type": "weapon"},
        {"review_status": "needs_review", "source_language": "es", "translation_status": "not_required", "reference_type": "weapon"},
        {"review_status": "needs_review", "source_language": "it", "translation_status": "failed", "reference_type": "weapon"},
    ]

    result = summarize_readiness(records, [], [])

    assert result["no_translation_review_queue_by_reference_type"] == {
        "weapon": 2,
        "spell": 1,
    }


def test_summarize_readiness_reconciles_unexpected_source_states():
    sources = [
        {"source_status": "active", "text_mode": "text", "import_state": "catalogued"},
        {"source_status": "document", "text_mode": "document", "import_state": "catalogued"},
        {"source_status": "misidentified", "text_mode": None, "import_state": "excluded"},
    ]

    result = summarize_readiness([], sources, [])

    assert result["source_status_breakdown"] == {
        "active": 1,
        "document": 1,
        "misidentified": 1,
    }
    assert result["source_text_mode_breakdown"] == {
        "document": 1,
        "text": 1,
        "unknown": 1,
    }
    assert result["source_import_state_breakdown"] == {
        "catalogued": 2,
        "excluded": 1,
    }
    assert sum(result["source_status_breakdown"].values()) == result["sources_total"]
    assert sum(result["source_text_mode_breakdown"].values()) == result["sources_total"]
    assert sum(result["source_import_state_breakdown"].values()) == result["sources_total"]


def test_summarize_readiness_uses_only_live_canonical_schema_statuses():
    canonical = [
        {"verification_status": "pending"},
        {"verification_status": "ai_verified"},
        {"verification_status": "verified"},
        {"verification_status": "conflict"},
        {"verification_status": "low_confidence"},
        {"verification_status": "manual_review"},
        {"verification_status": "excluded"},
    ]

    result = summarize_readiness([], [], canonical)

    assert result["canonical_status_breakdown"] == {
        "ai_verified": 1,
        "conflict": 1,
        "excluded": 1,
        "low_confidence": 1,
        "manual_review": 1,
        "pending": 1,
        "verified": 1,
    }
    assert result["canonical_verified"] == 1
    assert result["canonical_ai_verified"] == 1
    assert result["canonical_manual_review"] == 1
    assert result["canonical_conflict"] == 1
    assert result["canonical_low_confidence"] == 1


def test_summarize_readiness_handles_empty_catalogue():
    result = summarize_readiness([], [], [])
    assert result["records_total"] == 0
    assert result["verified_ratio"] == 0.0
    assert result["canonical_total"] == 0
    assert result["review_status_breakdown"] == {}
    assert result["ai_review_status_breakdown"] == {}
    assert result["canonical_status_breakdown"] == {}
    assert result["review_queue_by_reference_type"] == {}
    assert result["review_queue_by_status_and_reference_type"] == {}
    assert result["review_queue_by_language_translation_and_ai"] == {}
    assert result["no_translation_review_queue_by_reference_type"] == {}
    assert result["source_status_breakdown"] == {}
    assert result["source_text_mode_breakdown"] == {}
    assert result["source_import_state_breakdown"] == {}

from scripts.isolate_legacy_foreign_monsters import (
    EXPECTED_TARGET_COUNT,
    EXPECTED_TARGET_IDS_MD5,
    EXPECTED_LOGICAL_SOURCE_ID,
    ISOLATION_FLAG,
    LEGACY_FILENAME,
    REGISTRY_FILENAME,
    TARGETS,
    _ids_md5,
    _preview,
    _resolve_foreign_source,
)


def _row():
    return {
        "id": TARGETS[0]["id"],
        "name": TARGETS[0]["name"],
        "reference_type": "monster",
        "source_text_checksum": TARGETS[0]["source_text_checksum"],
        "review_status": "verified",
        "review_flags": [],
        "canonical_id": None,
        "source_refs": [{"filename": LEGACY_FILENAME, "page": 1}],
    }


def _source(**overrides):
    source = {
        "physical_filename": REGISTRY_FILENAME,
        "source_role": "extraction_aid",
        "source_status": "active",
        "language": "es",
        "logical_source_id": EXPECTED_LOGICAL_SOURCE_ID,
    }
    source.update(overrides)
    return source


def test_foreign_target_set_is_sealed_to_29_exact_ids():
    assert len(TARGETS) == EXPECTED_TARGET_COUNT == 29
    assert _ids_md5(TARGETS) == EXPECTED_TARGET_IDS_MD5


def test_foreign_source_resolution_requires_spanish_extraction_aid():
    resolved = _resolve_foreign_source(_row(), [_source()])
    assert resolved["source_role"] == "extraction_aid"
    assert resolved["language"] == "es"

    try:
        _resolve_foreign_source(_row(), [_source(source_role="authority")])
    except RuntimeError as exc:
        assert "source_role" in str(exc)
    else:
        raise AssertionError("authority source must not pass foreign isolation preflight")


def test_foreign_preview_is_read_only_and_sets_only_review_isolation():
    report = _preview([_row()])
    assert report["dry_run"] is True
    assert report["writes_performed"] == 0
    assert report["would_set"] == {
        "review_status": "needs_review",
        "review_flags": [ISOLATION_FLAG],
    }

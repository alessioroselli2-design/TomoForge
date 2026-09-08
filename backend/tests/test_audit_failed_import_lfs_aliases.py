from pathlib import Path

from scripts.audit_failed_import_lfs_aliases import (
    parse_lfs_pointer,
    summarize_failed_import_lfs_aliases,
)


def _pointer(oid: str, size: int = 1234) -> str:
    return (
        "version https://git-lfs.github.com/spec/v1\n"
        f"oid sha256:{oid}\n"
        f"size {size}\n"
    )


def test_parse_lfs_pointer_requires_complete_pointer():
    oid = "a" * 64
    assert parse_lfs_pointer(_pointer(oid, 99)) == {"oid_sha256": oid, "size": 99}
    assert parse_lfs_pointer("not an lfs pointer") is None
    assert parse_lfs_pointer(
        "version https://git-lfs.github.com/spec/v1\nsize 99\n"
    ) is None


def test_audit_flags_shared_lfs_object_without_authorizing_retry(tmp_path: Path):
    shared_oid = "a" * 64
    unique_oid = "b" * 64
    (tmp_path / "Player.pdf").write_text(_pointer(shared_oid, 5000), encoding="utf-8")
    (tmp_path / "Monsters.pdf").write_text(_pointer(shared_oid, 5000), encoding="utf-8")
    (tmp_path / "Tasha.pdf").write_text(_pointer(unique_oid, 6000), encoding="utf-8")

    jobs = [
        {
            "id": "phb",
            "filename": "Player.pdf",
            "status": "failed",
            "page_count": 321,
            "last_error": "schema cache",
        },
        {
            "id": "mm",
            "filename": "Monsters.pdf",
            "status": "failed",
            "page_count": 321,
            "last_error": "manual_source_duplicate:Player.pdf",
        },
        {
            "id": "tasha",
            "filename": "Tasha.pdf",
            "status": "failed",
            "page_count": 194,
            "last_error": "schema cache",
        },
        {
            "id": "missing",
            "filename": "Missing.pdf",
            "status": "failed",
            "page_count": 10,
            "last_error": "manual_source_missing",
        },
        {
            "id": "complete",
            "filename": "Ignored.pdf",
            "status": "completed",
        },
    ]

    result = summarize_failed_import_lfs_aliases(jobs, tmp_path)

    assert result["failed_jobs_total"] == 4
    assert result["failed_jobs_with_lfs_pointer"] == 3
    assert result["failed_jobs_missing_exact_attached_asset"] == 1
    assert result["lfs_alias_collision_groups"] == 1
    assert result["failed_jobs_in_lfs_alias_collisions"] == 2
    collision = result["collisions"][0]
    assert collision["oid_sha256"] == shared_oid
    assert [job["job_id"] for job in collision["jobs"]] == ["mm", "phb"]
    assert result["evidence_is_diagnostic_only"] is True
    assert result["database_write_authorized"] is False
    assert result["registry_write_authorized"] is False
    assert result["automatic_retry_authorized"] is False
    assert result["ocr_generation_authorized"] is False
    assert result["canonicalization_authorized"] is False

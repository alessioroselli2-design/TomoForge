import json
from pathlib import Path


APPROVAL_PATH = Path(__file__).resolve().parents[1] / "provenance_backfill_approval.json"


def _approval():
    return json.loads(APPROVAL_PATH.read_text(encoding="utf-8"))


def test_provenance_backfill_approval_is_preflight_only_and_non_authorizing():
    approval = _approval()

    assert approval["schema_version"] == 1
    assert approval["scope"] == "logical_source_provenance_backfill"
    assert approval["source_branch"] == "ai-canonical-library"
    assert approval["approval_state"] == "preflight_only"
    assert approval["writes_authorized"] is False


def test_provenance_backfill_approval_pins_a_well_formed_candidate_set():
    approval = _approval()
    source_commit = approval["source_commit"]
    digest = approval["candidate_sha256"]

    assert approval["candidate_count"] == 3469
    assert approval["ambiguous_excluded_count"] == 196
    assert len(source_commit) == 40
    assert all(ch in "0123456789abcdef" for ch in source_commit)
    assert len(digest) == 64
    assert all(ch in "0123456789abcdef" for ch in digest)

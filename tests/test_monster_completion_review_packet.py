"""Regression tests for fail-closed reviewer handoff."""
from monster_completion_review_packet import build_review_packet


def test_review_packet_never_approves_or_writes():
    original = {
        "id": "monster-1", "source_name": "Example",
        "source_refs": [{"page": 37, "physical_sha256": "abc"}],
    }
    candidate = {
        "id": "monster-1", "name": "Esempio",
        "translation_status": "translated", "source_language": "en",
    }
    packet = build_review_packet(original, candidate)
    assert packet["independent_review"] is False
    assert packet["reviewer_verdict"] is None
    assert packet["approved"] is False
    assert packet["writes_performed"] == 0
    assert len(packet["candidate_fingerprint"]) == 64
    assert packet["source_refs"] == original["source_refs"]


def test_review_packet_does_not_infer_independence_from_candidate():
    original = {"id": "monster-2", "source_refs": [{"page": 45}]}
    candidate = {"id": "monster-2", "name": "Impostore",
                 "translation_status": "translated",
                 "independent_review": True, "approved": True}
    packet = build_review_packet(original, candidate)
    assert packet["independent_review"] is False
    assert packet["approved"] is False

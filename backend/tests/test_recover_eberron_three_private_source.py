"""Synthetic fail-closed recovery tests: no copied source pages."""

from scripts.recover_eberron_three_private_source import (
    SOURCE,
    TARGETS,
    _safe_row,
    gate,
    relevant_evidence,
)


def _fake_page(target):
    return (
        target["name"] + "\n"
        "Incremento dei Punteggi di Caratteristica.\n"
        + "\n".join(t + ". Fictional rule for an isolated test."
                    for t in target["labels"])
        + "\n"
        + ("Fictional test only " * 125)
    )


def test_three_explicit_one_page_windows():
    assert [t["page"] for t in TARGETS] == [41, 43, 51]
    assert len({t["id"] for t in TARGETS}) == 3


def test_all_label_agreement_required_even_for_long_source():
    target = TARGETS[0]
    full = _fake_page(target)
    assert gate(full, full, target)
    incomplete = full.replace("Più Grossi Sono", "A different fictional trait")
    assert not gate(full, incomplete, target)


def test_short_fragment_is_not_marked_as_recovered():
    target = TARGETS[1]
    sample = _fake_page(target)
    assert not gate("Marchio Della Guarigione", sample, target)
    assert not relevant_evidence("no matching rules", target)["heading"]


def test_exact_original_snapshot_and_role_required():
    target = TARGETS[2]
    row = {
        "id": target["id"], "name": target["name"],
        "source_key": SOURCE, "reference_type": "subrace",
        "review_status": "verified", "ai_review_status": "pending",
        "source_text_checksum": target["old_sha"],
        "source_full_text": "A short and incomplete synthetic source fragment.",
        "source_refs": [{"filename": SOURCE, "page": target["page"]}],
    }
    assert _safe_row(row, target)
    assert not _safe_row({**row, "source_key": "unrelated.pdf"}, target)
    assert not _safe_row({**row, "ai_review_status": "verified"}, target)
    assert not _safe_row({**row, "source_text_checksum": "changed"}, target)
    assert not _safe_row({**row, "source_refs": []}, target)


def test_raw_page_long_enough_and_short_enough():
    target = TARGETS[0]
    raw = _fake_page(target)
    assert gate(raw, raw, target)
    assert not gate(raw + ("x" * 25000), raw, target)

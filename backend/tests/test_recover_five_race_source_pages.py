"""Synthetic source tests, no licensed source excerpts."""

from scripts.recover_five_race_source_pages import (
    SOURCES, accepted, check_text, valid_old_record,
)


def _sample(target, names):
    return (
        target[2] + "\n" +
        "\n".join(f"{label}. Invented mechanical description."
                  for label in names) +
        "\n" + ("Fictional explanatory testing only. " * 30)
    )


def test_sources_have_five_unique_explicit_targets():
    targets = [t for source in SOURCES for t in source["targets"]]
    assert len(targets) == 5
    assert len({t[0] for t in targets}) == 5
    assert all(len(source["sha"]) == 64 for source in SOURCES)


def test_synthetic_dual_ocr_agreement():
    for source in SOURCES:
        for target in source["targets"]:
            example = _sample(target, target[4])
            assert accepted(example, example, target)
            assert check_text(example, target)["feature_matches"] == len(target[4])
            assert "Invented" not in str(check_text(example, target))


def test_evidence_needs_two_features_in_both_reads():
    target = SOURCES[0]["targets"][0]
    complete = _sample(target, target[4])
    incomplete = _sample(target, (target[4][0],))
    assert not accepted(complete, incomplete, target)
    assert not accepted(incomplete, complete, target)


def test_ai_verified_target_must_never_be_overwritten():
    config = SOURCES[2]
    target = config["targets"][0]
    proof = {"target": target, "source": config["filename"]}
    record = {
        "id": target[0], "name": target[1],
        "source_key": config["filename"],
        "reference_type": "race",
        "review_status": "verified", "ai_review_status": "pending",
        "source_full_text": "", "source_text_checksum": "",
        "source_refs": [{"filename": config["filename"], "page": target[3]}],
    }
    assert valid_old_record(record, proof)
    assert not valid_old_record({**record, "ai_review_status": "verified"}, proof)
    assert not valid_old_record({**record, "source_full_text": "prior text"}, proof)
    assert not valid_old_record({**record, "source_key": "wrong.pdf"}, proof)
    assert not valid_old_record({**record, "source_refs": []}, proof)

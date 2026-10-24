"""Synthetic, copyright-free source-location tests for original MToF 2018 races."""

from scripts.recover_mtof_original_race_pages import (
    SOURCE, TARGETS, WINDOW_MAX, page_score, valid_row,
)


def test_all_sixteen_records_have_unique_editions():
    assert len(TARGETS) == 16
    assert len({t[0] for t in TARGETS}) == 16
    assert WINDOW_MAX == 12
    assert all(23 <= t[1] <= 113 for t in TARGETS)


def test_famous_tiefling_disambiguation_requires_unique_legacy():
    src = "Baalzebul. Legacy of Maladomini. " + ("Synthetic test only. " * 70)
    assert page_score(src, TARGETS[0])["sufficient"]
    assert not page_score(src, TARGETS[1])["sufficient"]
    assert not page_score("Baalzebul name in contents " * 50, TARGETS[0])["sufficient"]


def test_gith_and_elf_headers_need_multiple_original_traits():
    for i in (8, 10, 11, 12, 13, 14, 15):
        target = TARGETS[i]
        fixture = target[2] + "\n" + "\n".join(target[3]) + "\n" + ("Synthetic example only. " * 45)
        assert page_score(fixture, target)["sufficient"]
        one = target[2] + "\n" + target[3][0] + "\n" + ("Synthetic example only. " * 45)
        assert not page_score(one, target)["sufficient"]


def test_never_mutate_already_ai_verified_original():
    target = TARGETS[0]
    fake = {
        "name": target[0], "source_key": SOURCE,
        "reference_type": "subrace", "review_status": "verified",
        "ai_review_status": "pending", "source_full_text": "",
        "source_text_checksum": "",
        "source_refs": [{"filename": SOURCE, "page": target[1]}],
    }
    assert valid_row(fake, {"target": target})
    assert not valid_row({**fake, "ai_review_status": "verified"}, {"target": target})
    assert not valid_row({**fake, "source_key": "another-manual.pdf"}, {"target": target})
    assert not valid_row({**fake, "source_text_checksum": "already-read"}, {"target": target})

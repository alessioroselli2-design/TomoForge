import asyncio
from types import SimpleNamespace

import pymupdf

from reference_library import (
    extract_reference_records,
    merge_reference_records,
    reference_is_trusted,
)
from schemas.library import ReferenceImportInput
from services import library
from core.db import MemoryCollection


def _page_text(title: str, language: str = "en") -> str:
    if language == "en":
        return f"{title}\nThis is original English rules text. " + "It remains in English and describes the rule exactly. " * 3
    return f"{title}\nTesto originale abbastanza lungo. " + "Descrive la regola senza omissioni. " * 4


def test_mixed_pdf_ocr_is_page_scoped_and_failure_does_not_abort(tmp_path):
    path = tmp_path / "mixed.pdf"
    document = pymupdf.open()
    native = document.new_page()
    native.insert_text((72, 72), _page_text("NATIVE RULE", "it"))
    document.new_page()
    document.new_page()
    document.save(path)
    document.close()

    calls = []

    def ocr_page(_page, page_number):
        calls.append(page_number)
        if page_number == 2:
            return _page_text("OCR RULE", "it")
        raise RuntimeError("temporary provider error")

    report = extract_reference_records(path, ocr_page=ocr_page, force_ocr=False)

    assert calls == [2, 3]
    assert report.pages_read == 2
    assert report.pages_needing_ocr == [3]
    assert any(record["name"] == "Ocr Rule" for record in report.records)
    assert all(
        "ocr_da_verificare" in record["review_flags"]
        for record in report.records if record["name"] == "Ocr Rule"
    )
    assert all(
        "ocr_da_verificare" not in record["review_flags"]
        for record in report.records if record["name"] == "Native Rule"
    )


def test_ocr_prompts_preserve_original_language(monkeypatch):
    captured = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": _page_text("ARCANE RECOVERY")}}]}

    class Page:
        def get_pixmap(self, **_kwargs):
            return SimpleNamespace(tobytes=lambda _format: b"png")

    monkeypatch.setattr(library, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(library.requests, "post", lambda _url, **kwargs: captured.append(kwargs) or Response())

    library.openai_ocr_manual_page(Page(), 4, source_language="en")

    prompt = captured[0]["json"]["messages"][0]["content"][0]["text"]
    assert "lingua originale" in prompt
    assert "non tradurre" in prompt
    assert "manuale di gioco in italiano" not in prompt
    assert " en." in prompt


def test_distinct_manuals_are_not_merged_even_with_identical_content():
    common = {
        "reference_type": "other",
        "name": "Same Rule",
        "normalized_name": "same rule",
        "description": "Same text",
        "full_text": "Same complete rule text",
        "attributes": {},
        "review_flags": [],
        "tags": [],
        "source_language": "en",
    }
    records = merge_reference_records([
        {**common, "id": "one", "source_key": "book-one.pdf", "source_refs": [{"filename": "book-one.pdf", "page": 1}]},
        {**common, "id": "two", "source_key": "book-two.pdf", "source_refs": [{"filename": "book-two.pdf", "page": 8}]},
    ])

    assert len(records) == 2
    assert {record["source_key"] for record in records} == {"book-one.pdf", "book-two.pdf"}
    assert all(len(record["source_refs"]) == 1 for record in records)


def test_ocr_and_unreviewed_translation_are_never_trusted_automatically():
    assert not reference_is_trusted({
        "review_status": "needs_review",
        "review_flags": ["ocr_da_verificare"],
        "translation_status": "not_required",
        "ai_review_status": "pending",
    })
    assert not reference_is_trusted({
        "review_status": "needs_review",
        "review_flags": ["traduzione_da_verificare"],
        "translation_status": "translated",
        "ai_review_status": "pending",
    })


def test_auto_accept_does_not_verify_ocr_record(monkeypatch, tmp_path):
    source = tmp_path / "scan.pdf"
    source.write_bytes(b"unused")
    extracted = {
        "id": "ocr-rule", "reference_type": "other", "name": "OCR Rule",
        "normalized_name": "ocr rule", "description": "OCR description",
        "full_text": "OCR complete source text", "attributes": {}, "tags": [],
        "source_refs": [{"filename": source.name, "page": 1}],
        "review_flags": ["ocr_da_verificare"], "parent_class": "",
        "parent_subclass": "", "level": "",
    }
    collection = MemoryCollection()
    db = SimpleNamespace(private_reference_records=collection)
    monkeypatch.setattr(library, "available_reference_manuals", lambda: {source.name: source})
    monkeypatch.setattr(library, "extract_reference_records", lambda *_args: SimpleNamespace(
        records=[extracted], pages_read=1, pages_needing_ocr=[]
    ))

    asyncio.run(library.import_private_reference_manuals(
        "owner",
        ReferenceImportInput(filenames=[source.name], auto_accept=True),
        db=db,
    ))

    assert collection.rows[0]["review_status"] == "needs_review"
    assert collection.rows[0]["ai_review_status"] == "pending"


def test_english_parser_keeps_uncertain_heading_as_other():
    path_text = _page_text("MYSTERIOUS OPTION")
    from reference_library import parse_reference_page

    records = parse_reference_page(path_text, "english.pdf", 1, "en")

    assert records
    assert records[0]["reference_type"] == "other"
    assert records[0]["full_text"].startswith("This is original English")

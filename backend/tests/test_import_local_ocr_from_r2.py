import pytest

from scripts.import_local_ocr_from_r2 import _MAX_PAGES, _OCR_REVISION, _validate_page_window


def test_local_ocr_live_import_is_hard_bounded_to_three_pages():
    assert _MAX_PAGES == 3
    assert _validate_page_window(12, 3) == (12, 14)


@pytest.mark.parametrize("start_page,page_count", [(0, 1), (1, 0), (1, 4)])
def test_local_ocr_live_import_rejects_unsafe_windows(start_page, page_count):
    with pytest.raises(ValueError):
        _validate_page_window(start_page, page_count)


def test_local_ocr_revision_is_explicit_and_local():
    assert _OCR_REVISION.startswith("local-tesseract-")

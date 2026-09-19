from scripts.audit_r2_ocr_artifacts import classify_artifact_key


def test_classifies_supported_ocr_artifacts_case_insensitively():
    assert classify_artifact_key("manuals/Tasha/page-001.OCR.TXT") == "ocr.txt"
    assert classify_artifact_key("manuals/PHB/page-002.ocr.json") == "ocr.json"


def test_rejects_rendered_pages_and_unrelated_text_files():
    assert classify_artifact_key("manuals/Tasha/page-001.png") is None
    assert classify_artifact_key("manuals/Tasha/page-001.txt") is None
    assert classify_artifact_key("manuals/Tasha/page-001.json") is None


def test_rejects_suffix_like_directory_names():
    assert classify_artifact_key("manuals/foo.ocr.txt/page-001.png") is None

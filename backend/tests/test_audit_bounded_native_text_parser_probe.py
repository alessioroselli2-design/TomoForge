from pathlib import Path

import pytest

from reference_library import ReferenceImportReport
from scripts.audit_bounded_native_text_parser_probe import (
    MAX_PROBE_PAGES,
    bounded_native_text_parser_probe,
    bounded_native_text_parser_probe_windows,
)


def _fake_extractor(pdf_path, ocr_page, start_page, end_page, force_ocr, source_language):
    assert ocr_page is None
    assert force_ocr is False
    assert source_language == "es"
    return ReferenceImportReport(
        source_filename=Path(pdf_path).name,
        pages_read=2,
        pages_needing_ocr=[3],
        records=[
            {"reference_type": "class", "name": "Bárbaro"},
            {"reference_type": "class_feature", "name": "Furia"},
        ],
    )


def _mixed_quality_extractor(pdf_path, ocr_page, start_page, end_page, force_ocr, source_language):
    assert ocr_page is None
    assert force_ocr is False
    assert source_language == "es"
    records = (
        [{"reference_type": "spell", "name": "Luz"}, {"reference_type": "spell", "name": ""}]
        if start_page == 1
        else []
    )
    return ReferenceImportReport(
        source_filename=Path(pdf_path).name,
        pages_read=end_page - start_page + 1,
        pages_needing_ocr=[],
        records=records,
    )


def test_probe_reports_parser_metrics_without_side_effects(tmp_path):
    pdf_path = tmp_path / "phb-es.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% bounded probe fixture\n")

    result = bounded_native_text_parser_probe(
        pdf_path,
        start_page=1,
        end_page=3,
        source_language="es",
        extractor=_fake_extractor,
    )

    assert result["requested_pages"] == 3
    assert result["pages_read"] == 2
    assert result["pages_needing_ocr"] == [3]
    assert result["records_detected"] == 2
    assert result["named_records_detected"] == 2
    assert result["unnamed_records_detected"] == 0
    assert result["record_types"] == {"class": 1, "class_feature": 1}
    assert result["sample_record_names"] == ["Bárbaro", "Furia"]
    assert result["pdf_bytes_read"] is True
    assert result["bounded_native_text_parser_probe_executed"] is True
    assert result["ocr_callback_supplied"] is False
    assert result["ocr_used"] is False
    assert result["translation_used"] is False
    assert result["external_processing_used"] is False
    assert result["database_read_used"] is False
    assert result["database_write_used"] is False
    assert result["records_persisted"] is False
    assert result["review_state_mutated"] is False
    assert result["canonicalization_performed"] is False
    assert result["automatic_import_authorized"] is False


def test_window_probe_reports_each_window_and_aggregate_without_side_effects(tmp_path):
    pdf_path = tmp_path / "phb-es.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% bounded window fixture\n")

    result = bounded_native_text_parser_probe_windows(
        pdf_path,
        windows=((1, 3), (20, 22)),
        source_language="es",
        extractor=_fake_extractor,
    )

    assert result["window_count"] == 2
    assert result["requested_pages_total"] == 6
    assert result["records_detected_total"] == 4
    assert result["named_records_detected_total"] == 4
    assert result["unnamed_records_detected_total"] == 0
    assert result["productive_windows"] == 2
    assert result["named_signal_windows"] == 2
    assert result["empty_windows"] == 0
    assert result["record_types_total"] == {"class": 2, "class_feature": 2}
    assert [(item["window_index"], item["start_page"], item["end_page"]) for item in result["windows"]] == [
        (1, 1, 3),
        (2, 20, 22),
    ]
    assert all(item["records_detected"] == 2 for item in result["windows"])
    assert all(item["named_records_detected"] == 2 for item in result["windows"])
    assert all(item["record_types"] == {"class": 1, "class_feature": 1} for item in result["windows"])
    assert result["ocr_used"] is False
    assert result["translation_used"] is False
    assert result["database_write_used"] is False
    assert result["records_persisted"] is False
    assert result["canonicalization_performed"] is False
    assert result["automatic_import_authorized"] is False


def test_window_probe_distinguishes_named_unnamed_and_empty_signals(tmp_path):
    pdf_path = tmp_path / "phb-es.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% bounded quality fixture\n")

    result = bounded_native_text_parser_probe_windows(
        pdf_path,
        windows=((1, 2), (20, 21)),
        source_language="es",
        extractor=_mixed_quality_extractor,
    )

    assert result["records_detected_total"] == 2
    assert result["named_records_detected_total"] == 1
    assert result["unnamed_records_detected_total"] == 1
    assert result["productive_windows"] == 1
    assert result["named_signal_windows"] == 1
    assert result["empty_windows"] == 1
    assert result["windows"][0]["named_records_detected"] == 1
    assert result["windows"][0]["unnamed_records_detected"] == 1
    assert result["windows"][1]["records_detected"] == 0


def test_window_probe_rejects_combined_budget_over_twelve_pages(tmp_path):
    pdf_path = tmp_path / "phb-es.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    with pytest.raises(ValueError, match=str(MAX_PROBE_PAGES)):
        bounded_native_text_parser_probe_windows(
            pdf_path,
            windows=((1, 7), (20, 25)),
            source_language="es",
            extractor=_fake_extractor,
        )


def test_probe_rejects_more_than_twelve_pages(tmp_path):
    pdf_path = tmp_path / "phb-es.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    with pytest.raises(ValueError, match=str(MAX_PROBE_PAGES)):
        bounded_native_text_parser_probe(
            pdf_path,
            start_page=1,
            end_page=MAX_PROBE_PAGES + 1,
            source_language="es",
            extractor=_fake_extractor,
        )


def test_probe_rejects_non_pdf_target(tmp_path):
    target = tmp_path / "manual.txt"
    target.write_text("not a pdf")

    with pytest.raises(ValueError, match="must be a PDF"):
        bounded_native_text_parser_probe(
            target,
            start_page=1,
            end_page=1,
            source_language="es",
            extractor=_fake_extractor,
        )

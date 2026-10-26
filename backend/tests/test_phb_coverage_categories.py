"""Regression: PHB equipment sections must be visible in coverage.

The PHB is a source of ordinary equipment, mounts, vehicles, trade goods and
services. Missing a category from the coverage configuration hides imported
records even when search supports the type.
"""

import services.library as library
from core.config import MANUAL_COVERAGE_CATEGORIES


PHB = "Manuale_del_giocatore__1787259882002.pdf"
EXTRA_EQUIPMENT_TYPES = ("vehicle", "mount", "trade_good", "service")


def test_phb_coverage_includes_specialized_equipment_types():
    categories = MANUAL_COVERAGE_CATEGORIES[PHB]
    for reference_type in ("equipment", *EXTRA_EQUIPMENT_TYPES):
        assert reference_type in categories
    assert len(categories) == len(set(categories))


def test_phb_coverage_counts_specialized_equipment(monkeypatch):
    monkeypatch.setattr(library, "available_reference_manuals", lambda: {PHB: None})
    records = [
        {
            "name": reference_type,
            "reference_type": reference_type,
            "source_refs": [{"filename": PHB, "page": 157}],
            "review_status": "verified",
            "review_flags": [],
            "source_language": "it",
            "translation_status": "not_required",
        }
        for reference_type in EXTRA_EQUIPMENT_TYPES
    ]
    coverage = library.manual_coverage_report(records)
    assert len(coverage) == 1
    by_type = {
        category["reference_type"]: category
        for category in coverage[0]["categories"]
    }
    for reference_type in EXTRA_EQUIPMENT_TYPES:
        assert by_type[reference_type]["records_total"] == 1
        assert by_type[reference_type]["missing"] == 0

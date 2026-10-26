"""Regression checks for the Player's Handbook coverage category registry.

The UI coverage report is driven by MANUAL_COVERAGE_CATEGORIES, not by
the union of record types in Supabase. Omitting a type hides otherwise
searchable records from the per-manual progress panel.
"""

from core.config import MANUAL_COVERAGE_CATEGORIES
from reference_library import REFERENCE_TYPES


PHB_SOURCE = "Manuale_del_giocatore__1787259882002.pdf"


def test_phb_coverage_includes_imported_equipment_categories():
    categories = MANUAL_COVERAGE_CATEGORIES[PHB_SOURCE]
    assert len(categories) == len(set(categories))
    assert set(categories) <= set(REFERENCE_TYPES)
    assert {"equipment", "vehicle", "trade_good", "service"} <= set(categories)


def test_phb_coverage_keeps_core_playable_categories():
    categories = MANUAL_COVERAGE_CATEGORIES[PHB_SOURCE]
    assert {
        "class",
        "subclass",
        "class_feature",
        "feat",
        "spell",
        "race",
        "subrace",
        "weapon",
        "armor",
        "shield",
        "tool",
    } <= set(categories)

import pytest

from scripts.repair_legacy_records import (
    _ReadOnlyCollection,
    _assert_source_is_read_only,
    analyze_verified_records,
)


def _monster(name: str, ac: str, hp: str) -> dict:
    return {
        "id": f"ref_{name.casefold().replace(' ', '_')}",
        "reference_type": "monster",
        "name": name,
        "review_status": "verified",
        "review_flags": [],
        "attributes": {
            "classe_armatura": ac,
            "punti_ferita": hp,
            "velocita": "9 m",
        },
    }


def test_zuggtmoy_style_legacy_record_is_real_repair_not_debris():
    report = analyze_verified_records(
        [
            _monster("Zuggtmoy", "1", "304 (32dl0 + 128)"),
        ]
    )

    assert report["dry_run"] is True
    assert report["database_writes_performed"] == 0
    assert report["verified_records_analyzed"] == 1
    assert report["ocr_debris_to_eliminate"] == 0
    assert report["real_records_to_repair"] == 1
    assert report["repair_records"] == [
        {
            "name": "Zuggtmoy",
            "reference_type": "monster",
            "flags": ["CA_out_of_bounds", "HP_format_error"],
            "would_review_status": "pending",
        }
    ]


def test_heading_with_bad_stats_is_classified_as_debris_not_repair():
    report = analyze_verified_records(
        [
            _monster("C A P I T O L O 6 I B E S T I A R I O", "1", "90 (12dl0 + 24)"),
        ]
    )

    assert report["ocr_debris_to_eliminate"] == 1
    assert report["real_records_to_repair"] == 0
    assert report["ocr_debris_records"][0]["flags"] == [
        "invalid_entity_title",
        "CA_out_of_bounds",
        "HP_format_error",
    ]


def test_healthy_verified_records_are_counted_without_auto_approval():
    records = [
        _monster("Goblin", "15 (armatura di cuoio)", "7 (2d6)"),
        {
            "id": "ref_spell",
            "reference_type": "spell",
            "name": "Incantesimo di prova",
            "review_status": "verified",
            "review_flags": [],
            "attributes": {"livello": "1"},
        },
    ]

    report = analyze_verified_records(records)

    assert report["verified_records_analyzed"] == 2
    assert report["verified_monsters_analyzed"] == 1
    assert report["healthy_records"] == 2
    assert report["ocr_debris_to_eliminate"] == 0
    assert report["real_records_to_repair"] == 0


def test_missing_monster_core_values_fail_closed_into_repair_queue():
    report = analyze_verified_records(
        [
            _monster("Mostro incompleto", "armatura naturale", "molti"),
        ]
    )

    assert report["real_records_to_repair"] == 1
    assert report["repair_records"][0]["flags"] == [
        "CA_format_error",
        "HP_format_error",
    ]


def test_script_source_contains_no_database_mutation_method_calls():
    _assert_source_is_read_only()


def test_read_only_collection_exposes_find_but_not_mutation_methods():
    class FakeCollection:
        def find(self, query):
            return ("find", query)

        def update_one(
            self, *_args, **_kwargs
        ):  # pragma: no cover - must stay inaccessible
            raise AssertionError("mutation must never be reachable")

    collection = _ReadOnlyCollection(FakeCollection())

    assert collection.find({"review_status": "verified"}) == (
        "find",
        {"review_status": "verified"},
    )
    with pytest.raises(AttributeError):
        collection.update_one({}, {})

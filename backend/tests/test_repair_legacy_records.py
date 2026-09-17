from scripts.repair_legacy_records import (
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


def test_zuggtmoy_style_legacy_record_is_reported_with_specific_flags():
    report = analyze_verified_records([
        _monster("Zuggtmoy", "1", "304 (32dl0 + 128)"),
    ])

    assert report["dry_run"] is True
    assert report["database_writes_performed"] == 0
    assert report["verified_records_analyzed"] == 1
    assert report["semantic_numeric_healthy"] == 0
    assert report["semantic_numeric_failed"] == 1
    assert report["failed_records"] == [
        {
            "name": "Zuggtmoy",
            "reference_type": "monster",
            "flags": ["CA_out_of_bounds", "HP_format_error"],
            "would_review_status": "pending",
        }
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
    assert report["semantic_numeric_healthy"] == 2
    assert report["semantic_numeric_failed"] == 0
    assert report["failed_records"] == []


def test_missing_monster_core_values_fail_closed():
    report = analyze_verified_records([
        _monster("Mostro incompleto", "armatura naturale", "molti"),
    ])

    assert report["semantic_numeric_failed"] == 1
    assert report["failed_records"][0]["flags"] == [
        "CA_format_error",
        "HP_format_error",
    ]


def test_script_source_contains_no_database_mutation_method_calls():
    # This check parses the real script source and raises if mutation methods
    # such as update/insert/delete/upsert have been introduced.
    _assert_source_is_read_only()

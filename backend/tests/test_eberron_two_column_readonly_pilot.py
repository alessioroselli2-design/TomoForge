"""Fail-closed scoping for the Eberron experimental two-column OCR profile."""

from argparse import Namespace

from scripts import repair_monsters_from_source as repair


QUORI_ID = "ref_70901222165b54fe8e2827d5a3968998"


def _record(record_id=QUORI_ID, status="pending"):
    return {"id": record_id, "review_status": status}


def _source(logical_source_id="erlw_2019_it"):
    return {"logical_source_id": logical_source_id}


def _args(execute=False, target_set="bigby_single_pending_readonly"):
    return Namespace(execute=execute, target_set=target_set)


def test_default_eberron_layout_remains_full_page():
    assert repair._layout_profile(_source()) == "full_page"
    assert repair._layout_profile({"logical_source_id": "bgg_2023_it"}) == (
        "two_column_vertical"
    )


def test_in_memory_audit_only_flag_enables_eberron_columns():
    source = {**_source(), "_audit_only_eberron_two_column": True}
    assert repair._layout_profile(source) == "two_column_vertical"
    assert repair._layout_profile(
        {"logical_source_id": "other", "_audit_only_eberron_two_column": True}
    ) == "full_page"


def test_eberron_pilot_requires_known_pending_record_and_read_only_selector():
    assert repair._eberron_two_column_audit_eligible(
        _record(), _source(), _args()
    )
    for record, source, args in [
        (_record("ref_00000000000000000000000000000000"), _source(), _args()),
        (_record(status="verified"), _source(), _args()),
        (_record(), _source("bgg_2023_it"), _args()),
        (_record(), _source(), _args(execute=True)),
        (_record(), _source(), _args(target_set="batch_mpmm_pending_131")),
        (_record(), _source(), Namespace()),
    ]:
        assert not repair._eberron_two_column_audit_eligible(
            record, source, args
        )

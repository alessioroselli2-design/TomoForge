from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

from scripts import process_mpmm_pending as process


def _record(identifier: str, name: str, *, flags=None) -> dict:
    return {
        "id": identifier,
        "user_id": "owner-1",
        "name": name,
        "reference_type": "monster",
        "review_status": "pending",
        "review_flags": flags or ["ocr_da_verificare", "source_guided_repair"],
        "source_text_checksum": f"checksum-{identifier}",
        "source_refs": [{"logical_source_id": "mpmm_2022_it", "page": 12}],
        "attributes": {
            "classe_armatura": "15",
            "punti_ferita": "45 (6d10 + 12)",
            "velocita": "9 m",
        },
        "canonical_id": None,
    }


def test_mpmm_selection_requires_monster_and_explicit_logical_provenance():
    record = _record("one", "Uno")
    assert process._is_mpmm(record)
    assert not process._is_mpmm({**record, "reference_type": "race"})
    assert not process._is_mpmm({**record, "source_refs": [{"page": 12}]})


def test_partition_is_deterministic_and_never_exceeds_25():
    records = [_record(str(index), f"Mostro {index:03}") for index in range(61, -1, -1)]
    batches = process._partition(records, 25)
    assert [len(batch) for batch in batches] == [25, 25, 12]
    assert [row["name"] for batch in batches for row in batch] == sorted(
        row["name"] for row in records
    )


@pytest.mark.parametrize("field,value", [("attributes", {"classe_armatura": "18"}), ("updated_at", "2026-10-02T01:00:00Z"), ("review_notes", "new review"), ("source_refs", []), ("canonical_id", "linked")])
def test_full_record_revalidation_blocks_drift_beyond_the_old_three_fields(field, value):
    original = _record("one", "Uno")
    collection = _Collection({**original, field: value})
    with pytest.raises(process.repair.RepairBlocked, match="one"):
        asyncio.run(process._revalidate_pending(collection, [original]))


def test_snapshot_fingerprint_is_order_independent_and_covers_all_columns():
    record = _record("one", "Uno")
    assert process._record_snapshot_sha256(record) == process._record_snapshot_sha256(dict(reversed(list(record.items()))))
    assert process._record_snapshot_sha256(record) != process._record_snapshot_sha256({**record, "ai_review_status": "changed"})


def test_verified_proposal_removes_only_the_two_authorized_review_flags():
    record = _record("one", "Uno")
    proposal = process._verified_proposal({"after": record})
    assert proposal == {
        "attributes": record["attributes"],
        "review_flags": [],
        "review_status": "verified",
    }


def test_verified_proposal_fails_closed_on_residual_review_flag():
    record = _record("one", "Uno", flags=["ocr_da_verificare", "table_isolation"])
    with pytest.raises(process.repair.RepairBlocked) as exc:
        process._verified_proposal({"after": record})
    assert exc.value.reason == "residual_review_flags"


class _Result:
    matched_count = 1


class _Collection:
    def __init__(self, row):
        self.row = dict(row)

    async def update_one(self, query, update):
        assert query["review_status"] == "pending"
        self.row.update(update["$set"])
        return _Result()

    async def find_one(self, query):
        return dict(self.row) if query["id"] == self.row["id"] else None


class _History:
    def __init__(self):
        self.rows = []

    async def insert_one(self, row):
        self.rows.append(dict(row))

    async def delete_one(self, query):
        self.rows = [row for row in self.rows if row["id"] != query["id"]]
        return _Result()


def test_apply_verified_preserves_provenance_and_records_review_history():
    original = _record("one", "Uno")
    collection = _Collection(original)
    history = _History()
    timestamp = "2026-10-01T08:57:00Z"
    proposal = process._verified_proposal({"after": original})

    asyncio.run(
        process._apply_verified(
            collection, history, original, proposal, updated_at=timestamp
        )
    )

    assert collection.row["review_status"] == "verified"
    assert collection.row["review_flags"] == []
    assert collection.row["source_refs"] == original["source_refs"]
    assert collection.row["canonical_id"] is None
    assert collection.row["updated_at"] == timestamp
    assert len(history.rows) == 1
    assert history.rows[0]["reference_id"] == "one"
    assert history.rows[0]["review_status"] == "verified"


def test_sealed_snapshot_counts_distinguish_mpmm_from_global_verified():
    assert process.EXPECTED_PENDING == 29
    assert process.EXPECTED_MPMM_VERIFIED == 166
    assert process.EXPECTED_GLOBAL_VERIFIED == 215
    assert process.CONFIRMATION_TOKEN == "VERIFY_MPMM_PENDING_29"
    assert process.EXPECTED_PENDING_FINGERPRINT == (
        "907ea2b93e1d3f134a50a0c25409d10b0a1541e69a1af141a5573dd47b50cc8e"
    )
    assert process.EXPECTED_VERIFIED_FINGERPRINT == (
        "6b0edb33bf66fc63ccf5115cb3c45c99e92575bc09f6f526a3c8811925b26c5a"
    )


def test_execute_write_failure_isolated_and_final_report_survives(capsys):
    first = _record("one", "Uno")
    second = _record("two", "Due")
    rows = [first, second]
    after = [
        {**first, "review_status": "verified", "review_flags": []},
        second,
    ]
    args = process._parser().parse_args(
        ["--execute", "--confirm", process.CONFIRMATION_TOKEN]
    )
    with (
        patch.object(type(process.db), "configured", PropertyMock(return_value=True)),
        patch.object(
            process.repair,
            "_fetch_all",
            AsyncMock(side_effect=[rows, [], after]),
        ),
        patch.object(
            process.repair,
            "_repair_one",
            AsyncMock(side_effect=[{"after": first}, {"after": second}]),
        ),
        patch.object(process, "_revalidate_pending", AsyncMock()),
        patch.object(
            process,
            "_apply_verified",
            AsyncMock(side_effect=[None, RuntimeError("synthetic write failure")]),
        ),
        patch.object(process, "EXPECTED_PENDING", 2),
        patch.object(process, "EXPECTED_MPMM_VERIFIED", 0),
        patch.object(process, "EXPECTED_GLOBAL_VERIFIED", 0),
        patch.object(process, "EXPECTED_PENDING_FINGERPRINT", process._fingerprint(rows)),
        patch.object(process, "EXPECTED_VERIFIED_FINGERPRINT", process._fingerprint([])),
        patch.object(
            process.db.private_reference_records,
            "find_one",
            AsyncMock(return_value=second),
        ),
    ):
        assert asyncio.run(process._run(args)) == 2

    report = json.loads(capsys.readouterr().out.split("FINAL_REPORT\n")[1])
    assert report["repairable"] == 2
    assert report["updates_performed"] == 1
    assert report["final_pending"] == 1
    assert report["final_verified"] == 1
    assert any(
        item["record_id"] == "two" and item["reason"] == "write_apply_failed"
        for item in report["blocked_records"]
    )


def test_execute_snapshot_fingerprint_drift_blocks_before_source_access():
    pending = [_record(f"pending-{index}", f"Pending {index}") for index in range(29)]
    verified = [
        {**_record(f"verified-{index}", f"Verified {index}"), "review_status": "verified"}
        for index in range(166)
    ]
    non_mpmm_verified = [
        {
            **_record(f"global-{index}", f"Global {index}"),
            "review_status": "verified",
            "source_refs": [{"logical_source_id": "other_source", "page": 1}],
        }
        for index in range(49)
    ]
    rows = [*pending, *verified, *non_mpmm_verified]
    args = process._parser().parse_args(
        ["--execute", "--confirm", process.CONFIRMATION_TOKEN]
    )
    with (
        patch.object(type(process.db), "configured", PropertyMock(return_value=True)),
        patch.object(process.repair, "_fetch_all", AsyncMock(return_value=rows)) as fetch,
        patch.object(process, "EXPECTED_PENDING_FINGERPRINT", "0" * 64),
        pytest.raises(RuntimeError, match="initial-state drift"),
    ):
        asyncio.run(process._run(args))
    assert fetch.await_count == 1


def test_focused_audit_preserves_global_counts_and_never_writes(capsys):
    rows = [_record("one", "Uno"), _record("two", "Due")]
    args = process._parser().parse_args(["--audit-record-id", "one"])
    with (
        patch.object(type(process.db), "configured", PropertyMock(return_value=True)),
        patch.object(
            process.repair, "_fetch_all", AsyncMock(side_effect=[rows, [], rows])
        ),
        patch.object(
            process.repair, "_repair_one", AsyncMock(return_value={"after": rows[0]})
        ) as repair,
        patch.object(process, "_apply_verified", AsyncMock()) as write,
    ):
        assert asyncio.run(process._run(args)) == 0
    report = json.loads(capsys.readouterr().out.split("FINAL_REPORT\n")[1])
    assert report["initial_pending"] == report["final_pending"] == 2
    assert report["targets"] == report["repairable"] == 1
    assert report["updates_performed"] == 0
    assert repair.await_args.args[1]["id"] == "one"
    write.assert_not_called()


def test_focused_audit_refuses_execute_even_with_confirmation():
    args = process._parser().parse_args(
        [
            "--audit-record-id",
            "one",
            "--execute",
            "--confirm",
            process.CONFIRMATION_TOKEN,
        ]
    )
    with (
        patch.object(type(process.db), "configured", PropertyMock(return_value=True)),
        pytest.raises(RuntimeError, match="focused audits are read-only"),
    ):
        asyncio.run(process._run(args))


@pytest.mark.parametrize(
    "row",
    [
        None,
        {**_record("one", "Uno"), "review_status": "verified"},
        {**_record("one", "Uno"), "source_refs": []},
    ],
)
def test_focused_audit_refuses_records_outside_pending_mpmm(row):
    args = process._parser().parse_args(["--audit-record-id", "one"])
    with (
        patch.object(type(process.db), "configured", PropertyMock(return_value=True)),
        patch.object(
            process.repair, "_fetch_all", AsyncMock(return_value=[row] if row else [])
        ),
        pytest.raises(RuntimeError, match="exactly one pending MPMM record"),
    ):
        asyncio.run(process._run(args))


@pytest.mark.parametrize(
    "record_id",
    [
        "ref_25a60967a5b8526fbb235e29d243c019",
        "ref_a6f22b9706e058a8bd3f4dcbbd24c985",
        "ref_fae2af9678e6572cb755708aab5c393d",
        "ref_75abc404d54c51a2a312cbc2cd894e4a",
        "ref_aadff2eb6eff59af9caddb92deee6614",
        "ref_744cb23cb7f95be7b5d7521316ce8e78",
        "ref_c41175075be5535ab3cfd37dbbd7e1e1",
        "ref_ed33758b9132587a91e04e31c4df0d7a",
        "ref_9b1196c7b5c85057bd4c60098313a271",
        "ref_e14604cbec0a5306918cca5f4e74d639",
        "ref_3986eba313495283bfe6b6f843891add",
        "ref_90b64fd6ac3057ee8ab373bb0be776a8",
        "ref_f0919b1e8ef955a19953d273054accaf",
        "ref_2d833b3db343531b8cbe0669197259bd",
        "ref_2ea09533213a54178032bc4c5b0b952d",
        "ref_43a10fe5cecc50f9a2112cbea5b5c839",
        "ref_b414135fe8fd5447a6aedfba2a419baa",
        "ref_1e187bb2bbc257439e399104067bf326",
        "ref_de503e430ad356ec98964fb1a65bd34a",
        "ref_b624eff23c3e543ba8b2c952761eb707",
        "ref_be2228ae9b615c7da3734fa7395b016d",
        "ref_6b0e1564d7325987a342097cebb39316",
        "ref_a6b5749652855247a3266f61817441fa",
    ],
)
def test_timeout_residuals_use_narrow_extended_aggregate_budget(record_id):
    assert process.repair.OCR_GLOBAL_TIMEOUT_BY_RECORD_ID[record_id] == 150.0

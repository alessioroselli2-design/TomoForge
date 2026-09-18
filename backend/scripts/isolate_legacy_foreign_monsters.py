#!/usr/bin/env python3
"""Guarded isolation plan for 29 legacy monsters tied to a Spanish extraction aid.

Default mode is preview-only. A live write requires --execute plus the exact
confirmation token. Mutation selection is sealed by exact ID, exact name,
source_text_checksum, count, and an MD5 fingerprint. Before any write, every
record must still be a verified, unflagged, non-canonical monster and its
legacy provenance must resolve uniquely to the active Spanish extraction_aid
source phb_2014_es.

The action is reversible: it changes only review_status, review_flags and
updated_at. It never repairs attributes, deletes rows, approves or canonicalizes.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

PAGE_SIZE = 1000
EXPECTED_TARGET_COUNT = 29
EXPECTED_TARGET_IDS_MD5 = "223ab533a712d0871982a7451da551ea"
ISOLATION_FLAG = "legacy_foreign_source_isolated"
CONFIRMATION_TOKEN = (
    "ISOLATE-LEGACY-FOREIGN-29-223ab533a712d0871982a7451da551ea"
)

LEGACY_FILENAME = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
REGISTRY_FILENAME = "731764731-D-D-Manual-Del-Jugador-5e(1).pdf"
EXPECTED_LOGICAL_SOURCE_ID = "phb_2014_es"

TARGETS: tuple[dict[str, str], ...] = (
    {"id": "ref_148e045bd1945d2a94b3aa9e39cf9c9b", "name": "Lupo", "source_text_checksum": "c3d15226b85097550b2f6f75d7f317d3f02f4f3f6ab36d76df9c2d8fcdf5ad2e"},
    {"id": "ref_261cf2767f9158e2ba46c9556ddbe800", "name": "Mastino", "source_text_checksum": "ebb620425a3c0b944087a98f73811f2dfc0a6a47bd95145d1525271e6e8c2f81"},
    {"id": "ref_3797df73011955d5aa90f071dda55a40", "name": "Coccodrillo", "source_text_checksum": "f27bf0f67a0757e0242a494f8c9640c4514378d716c5ab08a368c2afd9503429"},
    {"id": "ref_39cd9f3c3e3c5ce2854e84e023b43d6d", "name": "Falco", "source_text_checksum": "9ecb0830a7466c6f24a57fecdd37d997206fd5c1d98af9014a25be8f98fa2c2c"},
    {"id": "ref_4cce1908ad2c5f43ad76c2af12e53f83", "name": "Duende", "source_text_checksum": "67fafc3f8e51c2f31a5990ffea81409518411d8694ae81166a6839ecb9450c4c"},
    {"id": "ref_6bffc618ddef5e1fb9b53698c968bf6d", "name": "Cinghiale", "source_text_checksum": "88f6f933d4e817926ec4b15773532b91fbfd8b47a00041a9fa035da4f8f6c637"},
    {"id": "ref_713e2f97160c548ab6cfe071030414c9", "name": "Serpente Velenosa", "source_text_checksum": "18e93246ca641cd5fe72789ef95c9bcf29148beae272419a7c70c2e44ba4599d"},
    {"id": "ref_7165511ff99e5a09883405168520ee4d", "name": "Gatto", "source_text_checksum": "3859dcc6bf75ad9e703f990d0305c53b2b2d0c0930e2ae51d9dec28a156961ed"},
    {"id": "ref_73b5b673e731575bae53a1206f6e1723", "name": "Pipistrello", "source_text_checksum": "9e7adb30204fc45c0efcda2fe3d07a80e7015a3da974a1cf5ed9dfdc36ba0412"},
    {"id": "ref_7727aa275e2a58fa9a60e8e822f6d863", "name": "Corvo", "source_text_checksum": "c01597e9be6aae37ffe7be0772dd2585a86db5c55bb826c4d64351dff388645f"},
    {"id": "ref_7cfa30d87eb95e29a9308d1b99ea668b", "name": "Ragno Gigante", "source_text_checksum": "87f34da58956bb6d6263fcb18bb26f4a5e32475cd5aa7b199896569d7e3c74d0"},
    {"id": "ref_84008ea62eb65716bc2ac23a967d6494", "name": "Scheletro", "source_text_checksum": "7805c054c1f1c2840683a2991c39e76b0bb21c16d8c8a1ad9aeb1afd0b87c1ab"},
    {"id": "ref_843098a0ca7b56f0ad29fcc30c7f71c5", "name": "Zombi", "source_text_checksum": "48c52e74d7f1fa85e62657f745d3d7cbdb31ecdffc1167826376386b14deac8d"},
    {"id": "ref_86acb6c34bc551d394be69e1b150fb02", "name": "Rana", "source_text_checksum": "d08d5ec044be88a2b73d4424b4ed4ed41796f1265cd58de6fcb30f0fb3794a99"},
    {"id": "ref_a9eb95f7beba55419a8e936b6015a39a", "name": "Rata", "source_text_checksum": "2c7240d26f9ac6eeebe8a5f3dc93a008afff99d07db35676d0c78810532cb3b1"},
    {"id": "ref_ae65945d5ae95204b74ca133feffb441", "name": "Cavallo Da Guerra", "source_text_checksum": "b3a81d40398d8057c6b219e030a4127608ea4e6f4f927141e8eb9ab0f653ebdc"},
    {"id": "ref_b933ddb6ef1a56baa243e227f6e87c2b", "name": "Pseudodragone", "source_text_checksum": "67bab58e775bb5f3526ddcd0c88c6baff547040a1d741fb2f52513874d34ba55"},
    {"id": "ref_ba352470ea12549b8302ccc8ce53dbd3", "name": "Serpente Constrictora", "source_text_checksum": "0da22d76c0c9a6d0dc3b86ade1714319a7e9910fedb3bcd815a2a60e01dcb23c"},
    {"id": "ref_bb424efc0c055e6d898033d779f0bba3", "name": "Cavallo da Monta", "source_text_checksum": "3e704fd17307d5917bbb7dfa54cac7c7a2f7ae487d3d4fef7636f759b25eb3e3"},
    {"id": "ref_be2df526e7035ac8baf14c768ad6fc37", "name": "Tigre", "source_text_checksum": "33a31f927ba8687700c592c93453dd0ccd08351ff4f5f494a3fd25eb01663705"},
    {"id": "ref_c0a704ff46ac57dab1e2ef0e911b75af", "name": "Quasit", "source_text_checksum": "c928848929207a389a3253d0f33a98849928d0c86ba56890e9d2db64abdc3153"},
    {"id": "ref_c44cafcb7a6456858a100f40797fe2a5", "name": "Leone", "source_text_checksum": "19d411af227c52c1b199bbff84f68fa70f7c409c513288e55b931a98e4ff212e"},
    {"id": "ref_c797e508001b52c0a859b0d41488522f", "name": "Diavolo", "source_text_checksum": "10771b8d39b35b2f101c349da397f3f77004de55175bc958a3471d9f6671bfb9"},
    {"id": "ref_cf342ea131fa524f86ca09530e99abe5", "name": "Squalo di barriera", "source_text_checksum": "08b2cc267223dbf47489f7fe43e25ffe2ddc98e54557fa599c61b3bad25e6fb8"},
    {"id": "ref_e3b0a8e2744c5d85b9fba212d417f1e9", "name": "Aquila Gigante", "source_text_checksum": "677302fc0e78abb963d4083b88906711db946a6b5982233de76d07983ed913e4"},
    {"id": "ref_e43502ed415c5ac4a004ea4c50634570", "name": "Pantera", "source_text_checksum": "08b963c73f1d1d577350eaa29a7c2b756504fd244f68cec0e422c6d329491d43"},
    {"id": "ref_e5e1617193cf5493b22ce46293e1ad48", "name": "Mulo", "source_text_checksum": "10bcc4e9cce59ed409c1fe7a826be0918cfe6fa4ed712d0266acdd0527eec33b"},
    {"id": "ref_ee42d70e3491579c867700b6e46f3f28", "name": "Orso Bruno", "source_text_checksum": "a2273b555e8183ccf21155ae1d8ca9add7a2c89b14bfff17ddf7b711c9b77eab"},
    {"id": "ref_fd09c31c190156e6abac1f047b33f10c", "name": "Lupo Terribile", "source_text_checksum": "e015dd0867ebb4d641bac1c68d2bbf3b5cdadc94e9331836b302f0ea01f72135"},
)


def _ids_md5(rows: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> str:
    joined = ",".join(sorted(str(row["id"]) for row in rows))
    return hashlib.md5(joined.encode("utf-8"), usedforsecurity=False).hexdigest()


if len(TARGETS) != EXPECTED_TARGET_COUNT or _ids_md5(TARGETS) != EXPECTED_TARGET_IDS_MD5:
    raise RuntimeError("Sealed foreign-source target constants are inconsistent")


async def _fetch_all(collection: Any, query: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = await collection.find(query).to_list(PAGE_SIZE, offset=offset)
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += len(page)


def _first_source_filename(row: dict[str, Any]) -> str:
    refs = row.get("source_refs") or []
    if refs and isinstance(refs[0], dict):
        return str(refs[0].get("filename") or "")
    return ""


def _resolve_foreign_source(
    row: dict[str, Any],
    active_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    if _first_source_filename(row) != LEGACY_FILENAME:
        raise RuntimeError(f"Legacy source filename drift: {row['id']}")
    matches = [
        source
        for source in active_sources
        if str(source.get("physical_filename") or "") == REGISTRY_FILENAME
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one active extraction-aid source, got {len(matches)}"
        )
    source = matches[0]
    expected = {
        "source_role": "extraction_aid",
        "source_status": "active",
        "language": "es",
        "logical_source_id": EXPECTED_LOGICAL_SOURCE_ID,
    }
    for field, value in expected.items():
        if str(source.get(field) or "") != value:
            raise RuntimeError(
                f"Foreign source registry drift: {field}={source.get(field)!r}"
            )
    return source


async def _load_exact_targets(
    records_collection: Any,
    source_collection: Any,
) -> list[dict[str, Any]]:
    active_sources = await _fetch_all(source_collection, {"source_status": "active"})
    rows: list[dict[str, Any]] = []
    for expected in TARGETS:
        row = await records_collection.find_one({"id": expected["id"]})
        if row is None:
            raise RuntimeError(f"Target missing: {expected['id']}")
        if str(row.get("name") or "") != expected["name"]:
            raise RuntimeError(f"Target name drift: {expected['id']}")
        if str(row.get("reference_type") or "") != "monster":
            raise RuntimeError(f"Target no longer a monster: {expected['id']}")
        if str(row.get("source_text_checksum") or "") != expected["source_text_checksum"]:
            raise RuntimeError(f"Target checksum drift: {expected['id']}")
        if str(row.get("review_status") or "") != "verified":
            raise RuntimeError(f"Target review_status drift: {expected['id']}")
        if list(row.get("review_flags") or []):
            raise RuntimeError(f"Target already has review flags: {expected['id']}")
        if row.get("canonical_id"):
            raise RuntimeError(f"Target linked to canonical data: {expected['id']}")
        _resolve_foreign_source(row, active_sources)
        rows.append(row)

    if len(rows) != EXPECTED_TARGET_COUNT or _ids_md5(rows) != EXPECTED_TARGET_IDS_MD5:
        raise RuntimeError("Exact foreign target count/fingerprint drift")
    return rows


async def _isolate(collection: Any, rows: list[dict[str, Any]]) -> int:
    # Re-read all rows before the first write, so any pre-existing drift aborts
    # the batch before mutation begins.
    for snapshot in rows:
        current = await collection.find_one({"id": snapshot["id"]})
        if current is None:
            raise RuntimeError(f"Target disappeared: {snapshot['id']}")
        for field in (
            "name",
            "reference_type",
            "source_text_checksum",
            "review_status",
            "review_flags",
            "canonical_id",
            "source_refs",
        ):
            if current.get(field) != snapshot.get(field):
                raise RuntimeError(
                    f"Concurrent drift before isolation: {snapshot['id']} field={field}"
                )

    changed = 0
    for snapshot in rows:
        result = await collection.update_one(
            {
                "id": str(snapshot["id"]),
                "review_status": "verified",
                "source_text_checksum": str(snapshot["source_text_checksum"]),
            },
            {
                "$set": {
                    "review_status": "needs_review",
                    "review_flags": [ISOLATION_FLAG],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        if result.matched_count != 1:
            raise RuntimeError(
                f"Isolation affected {result.matched_count} rows for {snapshot['id']}"
            )
        changed += 1

    for snapshot in rows:
        verify = await collection.find_one({"id": snapshot["id"]})
        if verify is None:
            raise RuntimeError(f"Post-isolation target missing: {snapshot['id']}")
        if str(verify.get("review_status") or "") != "needs_review":
            raise RuntimeError(f"Post-isolation status mismatch: {snapshot['id']}")
        if list(verify.get("review_flags") or []) != [ISOLATION_FLAG]:
            raise RuntimeError(f"Post-isolation flags mismatch: {snapshot['id']}")
    return changed


def _preview(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "dry_run": True,
        "target_count": len(rows),
        "target_ids_md5": _ids_md5(rows),
        "source": {
            "legacy_filename": LEGACY_FILENAME,
            "registry_filename": REGISTRY_FILENAME,
            "logical_source_id": EXPECTED_LOGICAL_SOURCE_ID,
            "source_role": "extraction_aid",
            "language": "es",
        },
        "would_set": {
            "review_status": "needs_review",
            "review_flags": [ISOLATION_FLAG],
        },
        "writes_performed": 0,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Guarded isolation of 29 legacy foreign-source monsters"
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")
    rows = await _load_exact_targets(
        db.private_reference_records,
        db.private_reference_sources,
    )

    if not args.execute:
        report = _preview(rows)
    else:
        if args.confirm != CONFIRMATION_TOKEN:
            raise RuntimeError("Refusing isolation: confirmation token mismatch")
        changed = await _isolate(db.private_reference_records, rows)
        report = {
            "dry_run": False,
            "database_write_completed": True,
            "targets": EXPECTED_TARGET_COUNT,
            "isolated": changed,
            "review_status": "needs_review",
            "review_flags": [ISOLATION_FLAG],
        }

    print("FINAL_REPORT")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(_run(_parse_args()))
    except Exception as exc:
        print(f"Foreign-source isolation aborted: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

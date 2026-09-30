#!/usr/bin/env python3
"""Read-only source-guided audit for the first 53 MPMM legacy monsters."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.db import db
from scripts import repair_monsters_from_source as repair

SOURCE_KEY = "Mostri del multi verso 1-100.pdf"
EXPECTED_COUNT = 53
EXPECTED_IDS_MD5 = "54846d7694335f16a61a645970d3e21e"
TARGETS = [
    {
        "id": "ref_774152a7b21953f99d394f65a852c8ca",
        "name": "Abishai Bianco",
        "source_text_checksum": "53d7c69d77be68865f9c6db8fe6ad6d95094c2d9209a93841c299c9eceda30e1"
    },
    {
        "id": "ref_92aa00cd69a658578bc05c4de9d126ae",
        "name": "Abishai Blu",
        "source_text_checksum": "38c4c87abadab79c49b903a8e4ba34e2a7763c215e22711bcbb39d66b44bd682"
    },
    {
        "id": "ref_13c451b5c15a5014a05870c538c1027f",
        "name": "Abishai Nero",
        "source_text_checksum": "8b0f24b28b6b5c134abd1f043d4949d926ceb7dce9ce41f895f7da1ad47e33e0"
    },
    {
        "id": "ref_36a7ca03ed43517b8b036334ea6d61ec",
        "name": "Abishai Rosso",
        "source_text_checksum": "1a5e1be53072a007e52d28739e4eeb08edeb8560ee8510b0db53b24b5a7df858"
    },
    {
        "id": "ref_7b77784c85825bfdbf0ee87caa77685c",
        "name": "Abishai Verde",
        "source_text_checksum": "47127852a9f847f7b40eed01b98d3501f0d12ff16162716e6e02d70507ac5f31"
    },
    {
        "id": "ref_b8ecefd5b01e59eaa13cc3721d7b2ae1",
        "name": "Addolorato Affamato",
        "source_text_checksum": "465a207c341fa6ba8f53e7c5eb799f3e6f9e19e7336e8c863039830b65711350"
    },
    {
        "id": "ref_f1c3523767b9529492bffb1c248ae461",
        "name": "Addolorato Deforme",
        "source_text_checksum": "371620c9402c9b65c480c22b5e7c60222304d4929d4290edaca4a35c9b33490b"
    },
    {
        "id": "ref_a99ccaba6e535852ab3db93771e9335c",
        "name": "Addolorato Rabbioso",
        "source_text_checksum": "345f006c8b4f3e27d0de31effa001d13e6721886a436d5241e4a984adf701a61"
    },
    {
        "id": "ref_1d4ca5e97a5850ba870ee0d9219d2bc9",
        "name": "Addolorato Smarrito",
        "source_text_checksum": "a607a9811a2ad61cee77d4651e706618ccb5cd7d1bdea1501c93cd335b7b3995"
    },
    {
        "id": "ref_55f881bc0c4e5ea6ae90b26869321b71",
        "name": "Addolorato Solitario",
        "source_text_checksum": "80ce651c0ace05c8e4a16f65b5b8b5bce542b7684f9bc2e9a56a4f946cb1011b"
    },
    {
        "id": "ref_bd9eded730d55b87af0aaec2cdcd13c7",
        "name": "Adrosauro",
        "source_text_checksum": "f12fb28d6c657546dfc7f004289b8442a0c7bc908505aa851861c7fcba73989e"
    },
    {
        "id": "ref_57670ec3c4825c2ebab4061d47d5fd7c",
        "name": "Alhoon",
        "source_text_checksum": "fe5935f2ef2ec92b98d631cc16c224c89be4d373b524cbf3fae77cebbe8cfe8b"
    },
    {
        "id": "ref_10ca47ba29865314aefab982a9123350",
        "name": "Allip",
        "source_text_checksum": "92216f40cde606cf11a5ecc489c4780312dc88dd5e5e8b8ab3462ff8ecedfdd5"
    },
    {
        "id": "ref_c4c35f6cbb825c3aba63d01b20c1e82a",
        "name": "Arciere",
        "source_text_checksum": "da2f821df6706594ddde4a59bc94e3c1de113f98f283d81b5acfce9458a22131"
    },
    {
        "id": "ref_831f50a1ffc451409008b47588b9e675",
        "name": "Artiglio Osseo",
        "source_text_checksum": "0365f1387a4c570858399d358a7f9783939d7493593814e1d5d78662760a2eb1"
    },
    {
        "id": "ref_984cc4241b7c5acb992526f8e7e2567c",
        "name": "Babau",
        "source_text_checksum": "96c38c47eb75c00a57038a8bfd6198e29dfe7b524fc8597f2f1ed7c4b0adbfac"
    },
    {
        "id": "ref_14406fab44dc5f57a4bb06187ba33465",
        "name": "Bael",
        "source_text_checksum": "cd08c75deca8a3168226cd9561400f0ecef183e1bebee8de9938351ab9eff0b2"
    },
    {
        "id": "ref_327a3411d36d54b6a863007957cbe79d",
        "name": "Balhannoth",
        "source_text_checksum": "3bc78ea6442e1c0ba8cbaa6cb9c66a6000a1324cfdef99017d2329868b1044cf"
    },
    {
        "id": "ref_79c43d7528455aad9b566b0da200d784",
        "name": "Banderhobb",
        "source_text_checksum": "c4f98b5f14f6aefb7a0c80659904bdc5519d7a84d1884a95a66cd2a9a51cf79b"
    },
    {
        "id": "ref_39326e59e23d51c098d467286ac040a6",
        "name": "Baphomet",
        "source_text_checksum": "d18637d887a4a49b2d9b64c017469bfb11a68452bf4f0ddd000731805267ac54"
    },
    {
        "id": "ref_01d0ccd1219f54adb8499f6fde82181c",
        "name": "Barghest",
        "source_text_checksum": "5767db90a5882d4ac651b80f5bab205d12af08973d61747c5a21ac95ec0ab16b"
    },
    {
        "id": "ref_c3551ceba31958819b2379553c32fccb",
        "name": "Berbalang",
        "source_text_checksum": "90de76407d38b7f648fe815082b3738fc83e155096acc5f193ca4ea11f4a57c6"
    },
    {
        "id": "ref_50f157429a555107a918e7ba85c2fa39",
        "name": "Berretto Rosso",
        "source_text_checksum": "be9eae6a50faa4a4df3d45d757ba13dc38971d39635f58691ee0d7c8e742993c"
    },
    {
        "id": "ref_bed8d1bcca885801b62c8ae3f471f45c",
        "name": "Bocca Di Grolantor",
        "source_text_checksum": "73179f2f28592566c269f0877bb7d0ed5e592251935bc61930acc0d826355cbc"
    },
    {
        "id": "ref_63b48acb74315053a90845cd07b022bb",
        "name": "Bodak",
        "source_text_checksum": "fd0c1126a181831b772fbcbc1a63d857e4c81682983ce21aa3bcebcd5080bd2e"
    },
    {
        "id": "ref_bb40323f98c45bf89fdcddcefc53a31f",
        "name": "Bove Fetente",
        "source_text_checksum": "118184fa2ecda7437aed0e49dc18b8e30c12531cf75dd56c283a0a29a78a8351"
    },
    {
        "id": "ref_9b905e15da9751c09cf177cc8f68522f",
        "name": "Brontosauro",
        "source_text_checksum": "e2897e2d0a97eaf06d48fb62799979262fbb6c7080d6b131236506120f6bbe4c"
    },
    {
        "id": "ref_5327fa4109f654189a10d7568aff0fb6",
        "name": "Bue",
        "source_text_checksum": "49d6310c623adb28882672caf9fde54e2e0da0858f3760e79a9125af27d4052d"
    },
    {
        "id": "ref_8d48d375b778533fbe95ba07bd4ae054",
        "name": "Bulezau",
        "source_text_checksum": "ed84454ac4fe6f15304607c9c4138abf9204ef982fb8b8cdc4f930800daecf61"
    },
    {
        "id": "ref_bd44eb65e41a5771868c2990dc601737",
        "name": "Campione",
        "source_text_checksum": "ee8697f05177b12e13c057df76e8551cd30ffcae4985d54b3f2eb90770eea12f"
    },
    {
        "id": "ref_4673c35de39059c9ad3e9a603a3ae9b8",
        "name": "Canoloth",
        "source_text_checksum": "a72eb1a02ec311de96eca2a636b92447af524f2f82ec7b868eccff906963efcc"
    },
    {
        "id": "ref_70e4f5f6362a5dd79071b24b0b0cc1a2",
        "name": "Catoblepas",
        "source_text_checksum": "391c2f8d0f02b53df46339cb31a6cb339bad97485f48294d4653f1bcaeb0cc42"
    },
    {
        "id": "ref_b163e723e8dc549894ee8501f4f6152f",
        "name": "Celeresto",
        "source_text_checksum": "b7852947bf91cf7d503298b855679abae5a5e7362b94895833dfdad10c6f441c"
    },
    {
        "id": "ref_73328b58b96b57738c11d62b83f32c82",
        "name": "Cervello Antico",
        "source_text_checksum": "3dbe0a03e114a211e3aee9c674d74f098562fb23c1453f988dccf1df05e8859a"
    },
    {
        "id": "ref_0901f2c639d05ed694c9bf2cbcfc031d",
        "name": "Coboldo Inventore",
        "source_text_checksum": "53aa1c1345a2b2e8c1f54774156ce9ce8a6b0f81f54d525510c602ee041ecf4f"
    },
    {
        "id": "ref_a2996e4f64235368b2f419b83e1a1aa3",
        "name": "Coboldo Stregone A Scaglie",
        "source_text_checksum": "f91892a56c6554a856e1dc621f8e1960c744220fd2430a0c9b73190981380bfb"
    },
    {
        "id": "ref_900c8f9a4c74514684531df9b6ab0ccd",
        "name": "Collezionista Di Cadaveri",
        "source_text_checksum": "47b080aac807da80e9896b4e9fbe4dd73ffbe958d2bb53ac19b84c6f641d3465"
    },
    {
        "id": "ref_85f35a6dddec5d428462ff7cbbafc69a",
        "name": "Deinonychus",
        "source_text_checksum": "d9f9370f73a62e8bd1cb87bc074b6f6f5571490434aeb142054c340d72df90da"
    },
    {
        "id": "ref_d740777fcfbb52169d3621c8f57f5e3f",
        "name": "Delfino",
        "source_text_checksum": "ecf442284b6d2aaef7cce5bb68eb1a00b959334a0ed74689d6bc25f2421dfe37"
    },
    {
        "id": "ref_6a8221d51cae525db1f6db8caad0018f",
        "name": "Delfino Sollazzatore",
        "source_text_checksum": "a1cc797716a42ae9dbe222a0987d477086fca835226dd569b63532d9ef3134b0"
    },
    {
        "id": "ref_81c7b2ca71995b949986286c05274312",
        "name": "Demogorgon",
        "source_text_checksum": "3eba97d3782284a929d844f9887fd7b3fc7241da1316eb35fce6fe0d04af161b"
    },
    {
        "id": "ref_76c239ada48d59f6b651f3d647fbd715",
        "name": "Demone Fauci",
        "source_text_checksum": "74068e94bb59f46663e97d1c0d5eba208b395894254877768ccd6a4d5879d03f"
    },
    {
        "id": "ref_14098ccddd9358e28b83fe7d17bb0734",
        "name": "Derro",
        "source_text_checksum": "bf9033a3aa31b6e877de4b5b86e597759ff437759cb4e0581e3c28de165dd256"
    },
    {
        "id": "ref_c6e57ca5531f568b890aa0f99bf2aff2",
        "name": "Dhergoloth",
        "source_text_checksum": "502746f5275926398ed4acb8c3e3011e4e1c81ed2cbb822e09162ed224870e35"
    },
    {
        "id": "ref_bccdf665b4e05ba1bd9d7f1710103779",
        "name": "Dimetrodonte",
        "source_text_checksum": "2519595b8c5ef1bc8b79543792b792f7d4f12dd5be69a63eb0ab674ddef2bf7a"
    },
    {
        "id": "ref_823f8b15d62359458189ca8d4384152a",
        "name": "Divoratore",
        "source_text_checksum": "2dd2bf5ffc591454c637c2933ea436f4a15b93ad4217df4e213003d027ce267a"
    },
    {
        "id": "ref_bd546d49bc7e523eba3a719c3762a928",
        "name": "Draegloth",
        "source_text_checksum": "af78f5b56f02e30599d0a208fdb693736373497e5f1fe7dd4ebaa6efd32aed57"
    },
    {
        "id": "ref_874afcf3b5ba58f992b317269ffb9b26",
        "name": "Drago Sorvegliante",
        "source_text_checksum": "bfa7dcbe160699757d80f7c77822e9c3ef817bdbb5faae51d236cee0dd2b6f87"
    },
    {
        "id": "ref_94dd0655e7fc518aaf9e3ad214e0dba7",
        "name": "Quetzalcoatlus",
        "source_text_checksum": "7b7b7a04f73f31e4057d03c3d9cf15715c350eaaedfd2bc2062c39dc31c79a25"
    },
    {
        "id": "ref_35ca599ba1ec5c00a8fbdd144f9a99f3",
        "name": "Rothé Delle Profondità",
        "source_text_checksum": "70e7f2d4652d9a7a2ae498888fee16289f7b69fcaa023208774f128fd6cc0daf"
    },
    {
        "id": "ref_5eefc25e9c9b5e22aa061386c84628f6",
        "name": "Stegosauro",
        "source_text_checksum": "e8030574406b8962c3d717cd585f8552d922161c00e5f63008a812bd4d32b087"
    },
    {
        "id": "ref_81f0825741ca50978cb36fc95f7eaebf",
        "name": "Uro",
        "source_text_checksum": "0e735223fbc57ad0da82aa5ed66011fac4e7dbb8e5fd38d7b0ee0f4e9ed4fba6"
    },
    {
        "id": "ref_ae7d3851315e5d1e8ec09fed56397623",
        "name": "Velociraptor",
        "source_text_checksum": "5922fa7e67654a57db1cefdce677df458ddaea471b0271cf65c4696ec9e0d015"
    }
]


def _ids_md5(records: list[dict[str, Any]]) -> str:
    joined = ",".join(sorted(str(record["id"]) for record in records))
    return hashlib.md5(joined.encode("utf-8"), usedforsecurity=False).hexdigest()


def _select_targets(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected_by_id = {str(item["id"]): item for item in TARGETS}
    selected: list[dict[str, Any]] = []
    for record in records:
        record_id = str(record.get("id") or "")
        expected = expected_by_id.get(record_id)
        if expected is None:
            continue
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"MPMM 1-100 name drift: {record_id}")
        if str(record.get("source_text_checksum") or "") != expected["source_text_checksum"]:
            raise RuntimeError(f"MPMM 1-100 checksum drift: {record_id}")
        if str(record.get("source_key") or "") != SOURCE_KEY:
            raise RuntimeError(f"MPMM 1-100 source drift: {record_id}")
        if str(record.get("review_status") or "") != "pending":
            raise RuntimeError(f"MPMM 1-100 status drift: {record_id}")
        if record.get("canonical_id"):
            raise RuntimeError(f"MPMM 1-100 canonical link detected: {record_id}")
        selected.append(record)

    fingerprint = _ids_md5(selected)
    if len(selected) != EXPECTED_COUNT or fingerprint != EXPECTED_IDS_MD5:
        raise RuntimeError(
            f"MPMM 1-100 count/fingerprint drift: count={len(selected)} md5={fingerprint}"
        )
    return sorted(selected, key=repair._record_sort_key)


async def _run(args: argparse.Namespace) -> int:
    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records = await repair._fetch_all(
        db.private_reference_records,
        {"reference_type": "monster", "source_key": SOURCE_KEY},
    )
    targets = _select_targets(records)
    if args.name:
        wanted = args.name.casefold()
        targets = [
            record
            for record in targets
            if str(record.get("name") or "").casefold() == wanted
        ]
        if len(targets) != 1:
            raise RuntimeError(
                f"Expected one sealed MPMM 1-100 target named {args.name!r}; "
                f"found {len(targets)}"
            )
    active_sources = await repair._fetch_all(
        db.private_reference_sources,
        {"source_status": "active"},
    )

    stage_args = argparse.Namespace(
        execute=False,
        target_set="batch_mpmm_1_100",
        pdf_root=args.pdf_root,
        allow_r2_download=args.allow_r2_download,
        dpi=args.dpi,
        languages=args.languages,
        psm=args.psm,
        comparison_psm=args.comparison_psm,
    )

    reports: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    pdf_cache = repair.SourcePdfCache(args.pdf_root, args.allow_r2_download)
    try:
        for record in targets:
            try:
                reports.append(
                    await repair._repair_one(
                        db.private_reference_records,
                        record,
                        active_sources,
                        pdf_cache,
                        stage_args,
                    )
                )
            except repair.RepairBlocked as exc:
                blocked.append(
                    {
                        "record_id": record.get("id"),
                        "name": record.get("name"),
                        "reason": exc.reason,
                        "detail": exc.detail,
                        "executed": False,
                        **(
                            {"diagnostics": exc.diagnostics}
                            if exc.diagnostics is not None
                            else {}
                        ),
                    }
                )
            except Exception as exc:
                blocked.append(
                    {
                        "record_id": record.get("id"),
                        "name": record.get("name"),
                        "reason": "crash_eccezione_raw",
                        "detail": str(exc),
                        "executed": False,
                    }
                )
    finally:
        pdf_cache.close()

    final = {
        "dry_run": True,
        "source_key": SOURCE_KEY,
        "focused_name": args.name or "",
        "targets": len(targets),
        "repairable": len(reports),
        "blocked": len(blocked),
        "updates_performed": 0,
        "failed_monsters_total": len(blocked),
        "reports": reports,
        "blocked_records": blocked,
    }
    print("FINAL_REPORT")
    print(json.dumps(final, ensure_ascii=False, sort_keys=True))
    expected_run_count = 1 if args.name else EXPECTED_COUNT
    return 0 if len(reports) + len(blocked) == expected_run_count else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only MPMM 1-100 audit")
    parser.add_argument("--pdf-root", default="")
    parser.add_argument("--allow-r2-download", action="store_true")
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--languages", default="ita")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--comparison-psm", type=int, default=4)
    parser.add_argument("--name", default="")
    return parser


def main() -> int:
    return asyncio.run(_run(_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())

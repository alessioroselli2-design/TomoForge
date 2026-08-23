"""Verify that the private reference catalogue is populated in Supabase.

This is an operational check, not an application endpoint. It reads only the
record metadata required to confirm that a specific account can search the
equipment library; it never reads, uploads, or exposes source PDFs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from supabase import create_client
from reference_library import CARD_TYPE_BY_REFERENCE_TYPE, reference_review_state


PROBES = {
    "feat": "acechador",
    "race": "enano",
    "subrace": "enano de las colinas",
    "spell": "bola de fuego",
    "weapon": "adamantio",
    "armor": "fumigante",
    "shield": "espressione",
    "tool": "fabbro",
    "magic_item": "perla",
}
REQUIRED_CHARACTER_CREATION_TYPES = frozenset({
    "class", "subclass", "class_feature", "race", "subrace",
    "feat", "spell", "weapon", "armor", "shield", "equipment", "tool",
})
REQUIRED_SOURCE_FILENAMES = (
    "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf",
)
PLAYER_HANDBOOK_FILENAME = "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"
PLAYER_HANDBOOK_PROBE_TYPES = frozenset({"feat", "race", "subrace", "spell"})


def verify_card_payload(
    user_id: str,
    records: list[dict[str, Any]],
    api_url: str,
) -> dict[str, Any]:
    """Confirm one trusted library record can drive the authenticated card flow.

    This invokes the same owner-scoped endpoint used by the application but
    does not create or modify a card. Response details that could contain rule
    text are intentionally not returned in the operational report.
    """
    trusted_records = (
        candidate for candidate in records if reference_review_state(candidate) == "valid"
    )
    record = next(
        (
            candidate for candidate in trusted_records
            if candidate.get("reference_type") in PROBES
        ),
        None,
    )
    if not record or not record.get("id"):
        raise RuntimeError(
            "Nessun record affidabile è disponibile per verificare il flusso carta."
        )
    jwt_secret = os.getenv("JWT_SECRET") or os.getenv("SESSION_SECRET")
    if not jwt_secret:
        raise RuntimeError(
            "JWT_SECRET o SESSION_SECRET è richiesto per verificare il flusso carta."
        )

    token = jwt.encode(
        {"user_id": user_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=2)},
        jwt_secret,
        algorithm="HS256",
    )
    endpoint = f"{api_url.rstrip('/')}/library/{record['id']}/apply"
    request = urllib.request.Request(
        endpoint,
        data=b"",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Il flusso carta ha risposto con stato HTTP {response.status}."
                )
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Il flusso carta autenticato ha risposto con stato HTTP {exc.code}."
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Il backend non è raggiungibile per verificare il flusso carta."
        ) from exc

    if payload.get("reference_id") != record["id"]:
        raise RuntimeError("Il payload carta non conserva il riferimento verificato.")
    if payload.get("reference_ids") != [record["id"]]:
        raise RuntimeError("Il payload carta non conserva il collegamento al riferimento.")
    expected_card_type = CARD_TYPE_BY_REFERENCE_TYPE.get(
        record.get("reference_type", "other"),
        "custom",
    )
    if payload.get("card_type") != expected_card_type:
        raise RuntimeError("Il payload carta non conserva il tipo della regola selezionata.")
    rule_source = payload.get("rule_source")
    if not isinstance(rule_source, dict):
        raise RuntimeError("Il payload carta non conserva la provenienza della regola.")
    if rule_source.get("source_kind") != "reference":
        raise RuntimeError("Il payload carta non indica una provenienza da riferimento.")
    if rule_source.get("source_id") != record["id"]:
        raise RuntimeError("Il payload carta punta a una provenienza diversa dal riferimento selezionato.")

    return {
        "status": "ok",
        "reference_type": record.get("reference_type", ""),
        "reference_link_retained": True,
        "provenance_retained": True,
        "card_persisted": False,
    }


def verify_library(user_id: str) -> dict[str, Any]:
    """Return a compact, read-only catalogue health report or raise clearly."""
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY sono richieste")

    client = create_client(url, service_key)
    records: list[dict[str, Any]] = []
    page_size = 1000
    offset = 0
    try:
        while True:
            response = (
                client
                .table("private_reference_records")
                .select("id,reference_type,name,normalized_name,source_normalized_name,review_flags,review_status,translation_status,source_refs")
                .eq("user_id", user_id)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            batch = response.data or []
            records.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
    except Exception as exc:
        raise RuntimeError(
            "La tabella private_reference_records non è disponibile: applica prima backend/supabase_schema.sql"
        ) from exc
    by_type = Counter(record.get("reference_type", "") for record in records)
    by_state = Counter(reference_review_state(record) for record in records)
    reviewed_by_type: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        reviewed_by_type[record.get("reference_type", "")][reference_review_state(record)] += 1
    source_counts = Counter(
        reference.get("filename")
        for record in records
        for reference in record.get("source_refs", [])
        if reference.get("filename")
    )
    missing_sources = [
        filename for filename in REQUIRED_SOURCE_FILENAMES if source_counts[filename] == 0
    ]
    # DMG absence is reported in required_manual_records but does not block
    # the PHB category checks (feat/race/subrace/spell), which are independent.
    if source_counts[PLAYER_HANDBOOK_FILENAME] == 0:
        raise RuntimeError(
            "Manca la provenienza richiesta dal Manuale del Giocatore spagnolo: "
            + PLAYER_HANDBOOK_FILENAME
        )
    probes: dict[str, dict[str, Any]] = {}
    for reference_type, needle in PROBES.items():
        matches = [
            record
            for record in records
            if record.get("reference_type") == reference_type
            and (
                needle in (record.get("normalized_name") or "").casefold()
                or needle in (record.get("source_normalized_name") or "").casefold()
            )
        ]
        if not matches:
            raise RuntimeError(f"Manca il controllo di ricerca per {reference_type}: {needle}")
        valid_matches = [
            record for record in matches
            if reference_review_state(record) == "valid"
        ]
        if not valid_matches:
            raise RuntimeError(
                f"Manca un controllo affidabile per {reference_type}: {needle}"
            )
        if reference_type in PLAYER_HANDBOOK_PROBE_TYPES:
            player_handbook_matches = [
                record for record in valid_matches
                if any(
                    reference.get("filename") == PLAYER_HANDBOOK_FILENAME
                    for reference in record.get("source_refs", [])
                )
            ]
            if not player_handbook_matches:
                raise RuntimeError(
                    "Manca la provenienza dal Manuale del Giocatore spagnolo "
                    f"per {reference_type}: {needle}"
                )
            valid_matches = player_handbook_matches
        probes[reference_type] = {
            "count": by_type[reference_type],
            "match": valid_matches[0]["name"],
            "needs_review": bool(valid_matches[0].get("review_flags")),
        }

    return {
        "status": "ok",
        "records_total": len(records),
        "flagged_for_review": by_state["review"],
        "coverage_by_category": {
            reference_type: {
                "valid": reviewed_by_type[reference_type]["valid"],
                "to_review": reviewed_by_type[reference_type]["review"],
                "missing": int(reviewed_by_type[reference_type]["valid"] == 0),
            }
            for reference_type in sorted(REQUIRED_CHARACTER_CREATION_TYPES)
        },
        "required_manual_records": {
            filename: source_counts[filename] for filename in REQUIRED_SOURCE_FILENAMES
        } | {PLAYER_HANDBOOK_FILENAME: source_counts[PLAYER_HANDBOOK_FILENAME]},
        "probes": probes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica la biblioteca privata in Supabase")
    parser.add_argument("--user-id", required=True, help="ID dell'account proprietario della biblioteca")
    parser.add_argument(
        "--check-card-payload",
        action="store_true",
        help="Verifica il flusso autenticato record affidabile → payload carta senza salvare carte.",
    )
    parser.add_argument(
        "--api-url",
        help="Base URL dell'API, incluso il prefisso /api, richiesta con --check-card-payload.",
    )
    args = parser.parse_args()
    if args.check_card_payload and not args.api_url:
        parser.error("--api-url è richiesto con --check-card-payload")
    try:
        report = verify_library(args.user_id)
        if args.check_card_payload:
            url = str(args.api_url)
            report["card_payload_probe"] = verify_card_payload(
                args.user_id,
                # Query only safe metadata above; no source text is sent here.
                (
                    create_client(
                        os.environ["SUPABASE_URL"],
                        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
                    )
                    .table("private_reference_records")
                    .select("id,reference_type,review_flags,review_status,translation_status")
                    .eq("user_id", args.user_id)
                    .limit(8000)
                    .execute()
                    .data
                    or []
                ),
                url,
            )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except RuntimeError as exc:
        print(f"Errore di verifica: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
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
from collections import Counter, defaultdict
from typing import Any

from supabase import create_client
from reference_library import reference_review_state


PROBES = {
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


def verify_library(user_id: str) -> dict[str, Any]:
    """Return a compact, read-only catalogue health report or raise clearly."""
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY sono richieste")

    try:
        response = (
            create_client(url, service_key)
            .table("private_reference_records")
            .select("reference_type,name,normalized_name,review_flags,review_status,translation_status,source_refs")
            .eq("user_id", user_id)
            .limit(8000)
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "La tabella private_reference_records non è disponibile: applica prima backend/supabase_schema.sql"
        ) from exc

    records = response.data or []
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
    if missing_sources:
        raise RuntimeError(
            "Manca la provenienza richiesta dal Manuale del Dungeon Master: "
            + ", ".join(missing_sources)
        )
    probes: dict[str, dict[str, Any]] = {}
    for reference_type, needle in PROBES.items():
        matches = [
            record
            for record in records
            if record.get("reference_type") == reference_type
            and needle in (record.get("normalized_name") or "").casefold()
        ]
        if not matches:
            raise RuntimeError(f"Manca il controllo di ricerca per {reference_type}: {needle}")
        probes[reference_type] = {
            "count": by_type[reference_type],
            "match": matches[0]["name"],
            "needs_review": bool(matches[0].get("review_flags")),
        }

    return {
        "status": "ok",
        "records_total": len(records),
        "flagged_for_review": by_state["review"],
        "coverage_by_category": {
            reference_type: {
                "valid": reviewed_by_type[reference_type]["valid"],
                "to_review": reviewed_by_type[reference_type]["review"],
                "missing": int(by_type[reference_type] == 0),
            }
            for reference_type in sorted(REQUIRED_CHARACTER_CREATION_TYPES)
        },
        "required_manual_records": {
            filename: source_counts[filename] for filename in REQUIRED_SOURCE_FILENAMES
        },
        "probes": probes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica la biblioteca privata in Supabase")
    parser.add_argument("--user-id", required=True, help="ID dell'account proprietario della biblioteca")
    args = parser.parse_args()
    try:
        print(json.dumps(verify_library(args.user_id), ensure_ascii=False, indent=2))
    except RuntimeError as exc:
        print(f"Errore di verifica: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
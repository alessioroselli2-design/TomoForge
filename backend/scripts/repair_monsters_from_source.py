#!/usr/bin/env python3
"""Source-guided repair for legacy monster OCR records.

Default mode is a read-only single-record dry-run (Zuggtmoy). The script:
1. selects legacy verified monsters that fail current semantic/numeric gates;
2. removes manual headings and structurally corrupted OCR names from repair;
3. resolves provenance against the live active source registry;
4. materializes the exact source PDF locally and verifies its SHA-256;
5. OCRs at most a 3-page window (target page +/- 1) with two independent
   Tesseract layout modes;
6. applies a source-specific layout profile when a manual is known to use
   two-column stat blocks, OCRing each column independently before parsing;
7. requires an independently-agreed monster candidate matching the known name;
8. requires the repaired core attributes to pass ocr_semantic_gates;
9. prints BEFORE/AFTER JSON plus a separate corrupt-name bucket; and
10. performs no UPDATE unless --execute is explicitly supplied.

The script never auto-approves or canonicalizes. Even a successful repair is
written as review_status='pending' with review flag 'ocr_da_verificare'.
Hosted LLM providers are intentionally disabled in this implementation.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from datetime import datetime, timezone
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from reference_library import normalize_reference_name
from scripts.pilot_local_ocr_from_r2 import (
    _agreement_metrics,
    _run_tesseract,
    _sha256_file,
)
from services.monster_name_diagnostics import compact_name_containment_match
from services.monster_statblock_ocr import agreed_monster_records, parse_monster_statblocks
from services.ocr_semantic_gates import (
    CA_FORMAT_ERROR_FLAG,
    CA_OUT_OF_BOUNDS_FLAG,
    CORRUPTED_ENTITY_NAME_FLAG,
    HP_FORMAT_ERROR_FLAG,
    INVALID_ENTITY_TITLE_FLAG,
    OCR_REVIEW_FLAG,
    apply_ocr_review_gates,
    entity_name_semantic_flags,
    monster_identity_sanity_flags,
    monster_semantic_numeric_flags,
)

PAGE_SIZE = 1000
EXPECTED_INITIAL_FAILURES = 109
REPAIR_FLAG = "source_guided_repair"
ELIGIBLE_SOURCE_ROLES = {"authority", "ingest_copy"}
CRITICAL_GATE_FLAGS = {
    CA_FORMAT_ERROR_FLAG,
    CA_OUT_OF_BOUNDS_FLAG,
    CORRUPTED_ENTITY_NAME_FLAG,
    HP_FORMAT_ERROR_FLAG,
    INVALID_ENTITY_TITLE_FLAG,
}

EXPECTED_HEALTHY22_COUNT = 22
EXPECTED_HEALTHY22_IDS_MD5 = "3c1f0be4ba3b7429694fe1a797c50870"
HEALTHY22_CONFIRMATION_TOKEN = (
    "REPAIR-HEALTHY22-22-3c1f0be4ba3b7429694fe1a797c50870"
)
HEALTHY22_TARGETS: tuple[dict[str, str], ...] = (
    {"id": "ref_09eb88310e015ab6aa41d9dc35874f48", "name": "Grung Guerriero D'Élite", "source_text_checksum": "3b83895b29020edb44eee6a37161661d6fb2833041b5e4b46efea0e66f565790"},
    {"id": "ref_13c451b5c15a5014a05870c538c1027f", "name": "Abishai Nero", "source_text_checksum": "8b0f24b28b6b5c134abd1f043d4949d926ceb7dce9ce41f895f7da1ad47e33e0"},
    {"id": "ref_1f9f9e07e45c598aabfbf96b74f6da5c", "name": "Supremo", "source_text_checksum": "d4c1ff1ebf2e2517e5ffb03059cb0d0582a52a5e0a1e54d7ba82fbf302b0daf7"},
    {"id": "ref_4f37ea01e1385ebaa14bd94e9927c3fb", "name": "Di Tenebre", "source_text_checksum": "a5fe712f86535281be78a8fdc54a7cf3cd5b4581b7a2fd56ea36bcb44b9fc9b4"},
    {"id": "ref_4fc3bf9cf15f5e109f9a305789da3396", "name": "Di Bronzo", "source_text_checksum": "ff8f58d6047f2fd38b18326e414e9120cdafdc7dd48458813c2fb4b0331abd73"},
    {"id": "ref_774152a7b21953f99d394f65a852c8ca", "name": "Abishai Bianco", "source_text_checksum": "53d7c69d77be68865f9c6db8fe6ad6d95094c2d9209a93841c299c9eceda30e1"},
    {"id": "ref_7b77784c85825bfdbf0ee87caa77685c", "name": "Abishai Verde", "source_text_checksum": "47127852a9f847f7b40eed01b98d3501f0d12ff16162716e6e02d70507ac5f31"},
    {"id": "ref_86e7c81f54295e38bf97d70b8dd37f74", "name": "Idroloth", "source_text_checksum": "761338350331d83b7710b3fbc10812827dfb2480e2227b97b24edf9af586cb42"},
    {"id": "ref_872a575e21a65e0e9ef677227c7aee61", "name": "Petron", "source_text_checksum": "53a51b79e011cab1bf2a33bcfeb417f63da9f000a848546efaf3593b86e6cd23"},
    {"id": "ref_8be52d9c63b0507fb8a1ee943dfef4a7", "name": "Predatore D'Acciaio", "source_text_checksum": "dbb31095d0be61ee7176b349b0049c58fa2c2886a4e6f92bd7944ba8d2301d73"},
    {"id": "ref_92e3b080e4fe5ba58c7bf439251876a2", "name": "Mente", "source_text_checksum": "4ea538392992e57c9dc0224f46f40b51aaf78ebe1a029f67bfbe48b28f893b5b"},
    {"id": "ref_95407fdd26ae57e88fc3943545bd5cc4", "name": "Mago Trasmutatore", "source_text_checksum": "38c12e6bac483312455092a88e43c99107ac8eef1bb57c566e2957b7380cb862"},
    {"id": "ref_9675b27dfcf2508895f60fa16f372c25", "name": "Graz'Zt", "source_text_checksum": "09ab11db46773be1ea31bfd4e74bd90a2a9f79fcd0443e1f6cd6ef9afe66ffbe"},
    {"id": "ref_a2996e4f64235368b2f419b83e1a1aa3", "name": "Coboldo Stregone A Scaglie", "source_text_checksum": "f91892a56c6554a856e1dc621f8e1960c744220fd2430a0c9b73190981380bfb"},
    {"id": "ref_ab32494230d3599c84042660933cecf1", "name": "Dell'Ombra", "source_text_checksum": "b264b48ea1969c59a59bf4147a8a92d7dfc3dd64c534f04dd1095a30d865e1f6"},
    {"id": "ref_abaf4a8fe2395260991a96729a200351", "name": "Cacciatore Di Baphomet", "source_text_checksum": "94e2b86aa7bbd78a46dc484cf7e9b36b4290e38afea7d7ab7a8ac7dd152e93d1"},
    {"id": "ref_bb4edf45dab45e2a849aead637d922f7", "name": "Duergar Kavalracni", "source_text_checksum": "4c46e8046628ec6513bd94ce6e39db47b8785b3aebf8fc9af84dcb8378e9752a"},
    {"id": "ref_e0ed42b772a1564d8208dbee3557dae2", "name": "Mirmidone Elementale D'Aria", "source_text_checksum": "6a066bac120437f27ae5e6552ea6226a796e9dd8f9741f11f45b181a889581c3"},
    {"id": "ref_e35ab09f132e526292e86469507b55b0", "name": "Di Quercia", "source_text_checksum": "6b4bebe3fbc20186debbbc7cda213ef1754a05175af27d6e704f1f32304fe5f1"},
    {"id": "ref_e4ce5aac88725918a98e4f1dacc8cd1a", "name": "Githyanki Kith'Rak", "source_text_checksum": "15154d968982915f1aa1342e7f53ed67bd707e9c8c110b38dadfd64874217fbb"},
    {"id": "ref_f42275a1fc7956a88a2449eb3fc6d22d", "name": "Dell'Oscurità", "source_text_checksum": "933e922d521771cf049231668f6d4264875f3fba6e7de7110159087e17bc19f5"},
    {"id": "ref_fc9b6c580dc85c0a9ca6ec918192c216", "name": "Statua Sacra", "source_text_checksum": "194a9e65755a7efab06c3192afa0a1b606032a676a6fda9e495ab072d5304be2"},
)

# Known source families whose stat blocks are laid out in two vertical columns.
# Keep this explicit and source-guided: do not guess a layout from OCR output.
TWO_COLUMN_LOGICAL_SOURCE_IDS = {
    "mpmm_2022_it",  # Mordenkainen Presenta: Mostri del Multiverso
}
TWO_COLUMN_MIN_DPI = 300
TWO_COLUMN_PRIMARY_PSM = 3
TWO_COLUMN_COMPARISON_PSM = 4

# Explicitly reviewed legacy upload aliases. Resolution is still accepted only
# if the destination registry row is active and authority/ingest_copy.
LEGACY_FILENAME_ALIASES = {
    "Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf":
        "Calderone-Omnicomprensivo-di-TASHA.pdf",
    "724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf":
        "724962906-D-D-5e-Manuale-Del-Dungeon-Master.pdf",
    "Manuale_del_giocatore__1787259882002.pdf":
        "Manuale del giocatore .pdf",
    # Diagnostics only: the registry currently classifies this extraction_aid,
    # therefore repair is blocked by the source-role gate.
    "731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf":
        "731764731-D-D-Manual-Del-Jugador-5e(1).pdf",
}


class RepairBlocked(RuntimeError):
    """Expected fail-closed outcome for a record that is unsafe to repair."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail or reason


async def _fetch_all(collection: Any, query: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = await collection.find(query).to_list(PAGE_SIZE, offset=offset)
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += len(page)


def _legacy_failure_flags(record: dict[str, Any]) -> set[str]:
    """Return current failure flags, including identity only for numeric failures."""
    if str(record.get("reference_type") or "") != "monster":
        return set()
    title_flags = entity_name_semantic_flags(record.get("name"))
    if title_flags:
        return title_flags
    numeric_flags = monster_semantic_numeric_flags(record.get("attributes") or {})
    if not numeric_flags:
        return set()
    return numeric_flags | monster_identity_sanity_flags(record.get("name"))


def _record_sort_key(record: dict[str, Any]) -> tuple[str, str]:
    return (
        str(record.get("name") or "").casefold(),
        str(record.get("id") or ""),
    )


def select_failed_monsters(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select failed monsters whose identity is safe enough for source repair."""
    selected = []
    for record in records:
        flags = _legacy_failure_flags(record)
        if not flags:
            continue
        if INVALID_ENTITY_TITLE_FLAG in flags:
            continue
        if CORRUPTED_ENTITY_NAME_FLAG in flags:
            continue
        selected.append(record)
    return sorted(selected, key=_record_sort_key)


def select_corrupted_name_monsters(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Isolate numerically failed monsters whose names look like OCR debris."""
    selected = []
    for record in records:
        flags = _legacy_failure_flags(record)
        if (
            CORRUPTED_ENTITY_NAME_FLAG in flags
            and INVALID_ENTITY_TITLE_FLAG not in flags
        ):
            selected.append(record)
    return sorted(selected, key=_record_sort_key)


def _ids_md5(records: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> str:
    joined = ",".join(sorted(str(record["id"]) for record in records))
    return hashlib.md5(
        joined.encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()


def select_healthy22_targets(
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve the reviewed 22-row batch by exact sealed identity."""
    by_id = {str(record.get("id") or ""): record for record in failures}
    targets: list[dict[str, Any]] = []
    for expected in HEALTHY22_TARGETS:
        record = by_id.get(expected["id"])
        if record is None:
            raise RuntimeError(
                f"Sealed healthy22 target missing from current failures: {expected['id']}"
            )
        if str(record.get("name") or "") != expected["name"]:
            raise RuntimeError(f"Healthy22 name drift: {expected['id']}")
        if str(record.get("source_text_checksum") or "") != expected["source_text_checksum"]:
            raise RuntimeError(f"Healthy22 checksum drift: {expected['id']}")
        if str(record.get("review_status") or "") != "verified":
            raise RuntimeError(f"Healthy22 status drift: {expected['id']}")
        if record.get("canonical_id"):
            raise RuntimeError(f"Healthy22 canonical link detected: {expected['id']}")
        if list(record.get("review_flags") or []):
            raise RuntimeError(f"Healthy22 unexpected pre-existing review flags: {expected['id']}")
        if monster_identity_sanity_flags(record.get("name")):
            raise RuntimeError(f"Healthy22 identity gate failure: {expected['id']}")
        targets.append(record)

    if (
        len(targets) != EXPECTED_HEALTHY22_COUNT
        or _ids_md5(targets) != EXPECTED_HEALTHY22_IDS_MD5
    ):
        raise RuntimeError("Healthy22 target count/fingerprint drift")
    return targets


async def _revalidate_target_snapshots(
    collection: Any,
    originals: list[dict[str, Any]],
) -> None:
    """Abort the batch if any reviewed target changed while OCR was running."""
    protected_fields = (
        "name",
        "reference_type",
        "attributes",
        "review_flags",
        "review_status",
        "source_refs",
        "source_text_checksum",
        "canonical_id",
        "updated_at",
    )
    for original in originals:
        current = await collection.find_one({"id": str(original["id"])})
        if current is None:
            raise RuntimeError(f"Healthy22 target disappeared: {original['id']}")
        for field in protected_fields:
            if current.get(field) != original.get(field):
                raise RuntimeError(
                    f"Healthy22 concurrent drift for {original['id']}: {field}"
                )


def _first_source_ref(record: dict[str, Any]) -> dict[str, Any]:
    refs = record.get("source_refs") or []
    for ref in refs:
        if isinstance(ref, dict) and ref.get("page") is not None:
            return ref
    raise RepairBlocked(
        "missing_source_ref",
        "Record has no source_ref with a physical page",
    )


def _legacy_filename(record: dict[str, Any], ref: dict[str, Any]) -> str:
    return str(ref.get("filename") or record.get("source_key") or "").strip()


def resolve_source(
    record: dict[str, Any],
    active_sources: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve legacy provenance to one active registry row, fail-closed."""
    ref = _first_source_ref(record)
    legacy_filename = _legacy_filename(record, ref)
    if not legacy_filename:
        raise RepairBlocked("missing_source_filename")

    candidate_filename = LEGACY_FILENAME_ALIASES.get(
        legacy_filename,
        legacy_filename,
    )
    candidates = [
        source
        for source in active_sources
        if str(source.get("physical_filename") or "") == candidate_filename
    ]
    if len(candidates) != 1:
        raise RepairBlocked(
            "source_resolution_required",
            f"Expected one active registry source for "
            f"{candidate_filename!r}; got {len(candidates)}",
        )

    source = candidates[0]
    role = str(source.get("source_role") or "")
    if role not in ELIGIBLE_SOURCE_ROLES:
        raise RepairBlocked(
            "source_ineligible_role",
            f"Resolved source_role={role!r}",
        )
    if str(source.get("source_status") or "") != "active":
        raise RepairBlocked("source_not_active")

    page = int(ref.get("page") or 0)
    page_total = int(source.get("physical_pages") or 0)
    if page < 1 or page_total < 1 or page > page_total:
        raise RepairBlocked(
            "source_page_out_of_bounds",
            f"page={page}, physical_pages={page_total}",
        )
    return source, ref


def _layout_profile(source: dict[str, Any]) -> str:
    logical_source_id = str(source.get("logical_source_id") or "").strip()
    if logical_source_id in TWO_COLUMN_LOGICAL_SOURCE_IDS:
        return "two_column_vertical"
    return "full_page"


def _layout_segments(
    source: dict[str, Any],
) -> tuple[tuple[str, tuple[float, float, float, float]], ...]:
    """Return normalized page clips; values are fractions of width/height."""
    if _layout_profile(source) == "two_column_vertical":
        # Exact half-page split: no cross-column pixels can enter the other OCR.
        # This intentionally favors omission over bleed across the center gutter.
        return (
            ("left", (0.0, 0.0, 0.5, 1.0)),
            ("right", (0.5, 0.0, 1.0, 1.0)),
        )
    return (("full", (0.0, 0.0, 1.0, 1.0)),)


def _layout_ocr_settings(
    source: dict[str, Any],
    *,
    dpi: int,
    psm: int,
    comparison_psm: int,
) -> tuple[int, int, int]:
    """Return (dpi, primary_psm, comparison_psm) for the resolved source."""
    if _layout_profile(source) == "two_column_vertical":
        # At 300 DPI PSM 3 and PSM 4 independently preserve compact dice tokens
        # in the MP:MM stat-block font while still using distinct page analysis.
        return (
            max(dpi, TWO_COLUMN_MIN_DPI),
            TWO_COLUMN_PRIMARY_PSM,
            TWO_COLUMN_COMPARISON_PSM,
        )
    return dpi, psm, comparison_psm


class SourcePdfCache:
    """Resolve exact registry PDFs locally; optional R2 fallback is explicit."""

    def __init__(self, pdf_root: str, allow_r2_download: bool) -> None:
        self.pdf_root = Path(pdf_root).expanduser() if pdf_root else None
        self.allow_r2_download = allow_r2_download
        self._tmp = tempfile.TemporaryDirectory(
            prefix="tomoforge-source-repair-"
        )
        self._cache: dict[str, Path] = {}

    def close(self) -> None:
        self._tmp.cleanup()

    def _verify(self, path: Path, source: dict[str, Any]) -> Path:
        expected = str(
            source.get("physical_sha256") or ""
        ).strip().casefold()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise RepairBlocked("missing_registry_sha256")
        actual = _sha256_file(path)
        if actual != expected:
            raise RepairBlocked(
                "source_sha256_mismatch",
                f"expected={expected} actual={actual}",
            )
        return path

    def get(self, source: dict[str, Any]) -> Path:
        filename = str(source.get("physical_filename") or "")
        if not filename:
            raise RepairBlocked("missing_registry_filename")
        if filename in self._cache:
            return self._cache[filename]

        if self.pdf_root is not None:
            local = self.pdf_root / filename
            if local.is_file():
                self._cache[filename] = self._verify(local, source)
                return self._cache[filename]

        if not self.allow_r2_download:
            raise RepairBlocked(
                "source_pdf_not_local",
                f"{filename!r} not found under --pdf-root "
                "and R2 fallback is disabled",
            )

        from scripts import import_manuals_from_r2 as r2_worker

        client = r2_worker._r2_client()
        bucket = (
            os.getenv("R2_BUCKET", "tomoforge-manuals").strip()
            or "tomoforge-manuals"
        )
        objects = r2_worker._list_pdf_objects(client, bucket)
        safe_name = r2_worker._safe_pdf_name(filename)
        metadata = objects.get(safe_name)
        if metadata is None:
            raise RepairBlocked("source_pdf_missing_r2", safe_name)

        target = Path(self._tmp.name) / safe_name
        client.download_file(bucket, metadata["key"], str(target))
        self._cache[filename] = self._verify(target, source)
        return self._cache[filename]


def _clip_rect(
    page_rect: Any,
    fractions: tuple[float, float, float, float],
) -> Any:
    """Convert normalized clip fractions to a fitz.Rect."""
    import fitz

    x0, y0, x1, y1 = fractions
    return fitz.Rect(
        page_rect.x0 + page_rect.width * x0,
        page_rect.y0 + page_rect.height * y0,
        page_rect.x0 + page_rect.width * x1,
        page_rect.y0 + page_rect.height * y1,
    )


def _ocr_source_window(
    pdf_path: Path,
    target_page: int,
    page_total: int,
    source: dict[str, Any],
    *,
    dpi: int,
    languages: str,
    psm: int,
    comparison_psm: int,
) -> tuple[
    list[tuple[int, str]],
    list[tuple[int, str]],
    dict[int, dict[str, Any]],
]:
    """OCR <=3 pages, isolating columns and any quality-fail segment."""
    import fitz

    start_page = max(1, target_page - 1)
    end_page = min(page_total, target_page + 1)
    if end_page - start_page + 1 > 3:
        raise AssertionError(
            "source-guided repair window unexpectedly exceeded 3 pages"
        )

    effective_dpi, primary_psm, secondary_psm = _layout_ocr_settings(
        source,
        dpi=dpi,
        psm=psm,
        comparison_psm=comparison_psm,
    )
    if primary_psm == secondary_psm:
        raise RepairBlocked("ocr_layout_modes_not_independent")

    primary_pages: list[tuple[int, str]] = []
    comparison_pages: list[tuple[int, str]] = []
    metrics: dict[int, dict[str, Any]] = {}
    matrix = fitz.Matrix(effective_dpi / 72.0, effective_dpi / 72.0)
    segments = _layout_segments(source)

    document = fitz.open(pdf_path)
    try:
        with tempfile.TemporaryDirectory(
            prefix="tomoforge-source-repair-ocr-"
        ) as image_tmp:
            image_root = Path(image_tmp)
            for page_number in range(start_page, end_page + 1):
                page = document.load_page(page_number - 1)
                primary_parts: list[str] = []
                comparison_parts: list[str] = []
                segment_metrics: dict[str, dict[str, Any]] = {}

                for segment_name, fractions in segments:
                    clip = _clip_rect(page.rect, fractions)
                    image_path = (
                        image_root
                        / f"page-{page_number:04d}-{segment_name}.png"
                    )
                    page.get_pixmap(
                        matrix=matrix,
                        clip=clip,
                        alpha=False,
                        colorspace=fitz.csGRAY,
                    ).save(image_path)

                    primary = _run_tesseract(
                        image_path,
                        languages,
                        primary_psm,
                    )
                    comparison = _run_tesseract(
                        image_path,
                        languages,
                        secondary_psm,
                    )
                    agreement = _agreement_metrics(
                        primary,
                        comparison,
                    )
                    segment_metrics[segment_name] = agreement

                    # Fail closed per segment. A bad neighboring column is
                    # isolated and cannot poison a clean target column.
                    if agreement["quality_pass"]:
                        primary_parts.append(primary)
                        comparison_parts.append(comparison)

                page_quality_pass = bool(primary_parts)
                metrics[page_number] = {
                    "quality_pass": page_quality_pass,
                    "layout_profile": _layout_profile(source),
                    "effective_dpi": effective_dpi,
                    "primary_psm": primary_psm,
                    "comparison_psm": secondary_psm,
                    "segments": segment_metrics,
                }
                if page_quality_pass:
                    # Column outputs are concatenated only after independent
                    # OCR/quality checks; no pixels or same-line text can bleed.
                    primary_pages.append(
                        (page_number, "\n\n".join(primary_parts))
                    )
                    comparison_pages.append(
                        (page_number, "\n\n".join(comparison_parts))
                    )
    finally:
        document.close()

    if target_page not in {page for page, _ in primary_pages}:
        raise RepairBlocked("target_page_quality_fail")
    return primary_pages, comparison_pages, metrics


def _candidate_matches_target(
    candidate: dict[str, Any],
    target_name: str,
    target_page: int,
) -> bool:
    candidate_name = str(
        candidate.get("normalized_name")
        or candidate.get("name")
        or ""
    )
    target_normalized = normalize_reference_name(target_name)
    pages = {
        int(ref.get("page"))
        for ref in (candidate.get("source_refs") or [])
        if isinstance(ref, dict) and ref.get("page") is not None
    }
    name_match = (
        candidate_name == target_normalized
        or compact_name_containment_match(
            candidate_name,
            target_normalized,
        )
    )
    return target_page in pages and name_match


def _agreed_target_candidate(
    primary_pages: list[tuple[int, str]],
    comparison_pages: list[tuple[int, str]],
    source_filename: str,
    source_language: str,
    target_name: str,
    target_page: int,
) -> dict[str, Any]:
    primary = parse_monster_statblocks(
        primary_pages,
        source_filename,
        source_language,
    )
    comparison = parse_monster_statblocks(
        comparison_pages,
        source_filename,
        source_language,
    )
    agreed = agreed_monster_records(primary, comparison)
    matches = [
        candidate
        for candidate in agreed
        if _candidate_matches_target(
            candidate,
            target_name,
            target_page,
        )
    ]
    if len(matches) != 1:
        raise RepairBlocked(
            "no_unique_independent_agreement",
            f"matching independently-agreed candidates={len(matches)}",
        )
    return matches[0]


def build_repair_proposal(
    legacy: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Build a minimal core-field repair and run all OCR gates in memory."""
    candidate_attributes = dict(candidate.get("attributes") or {})
    gate_failures = monster_semantic_numeric_flags(candidate_attributes)
    if gate_failures:
        raise RepairBlocked(
            "repaired_candidate_failed_gates",
            ",".join(sorted(gate_failures)),
        )
    if not str(candidate_attributes.get("velocita") or "").strip():
        raise RepairBlocked("repaired_candidate_missing_speed")
    if entity_name_semantic_flags(candidate.get("name")):
        raise RepairBlocked("repaired_candidate_invalid_title")
    if monster_identity_sanity_flags(candidate.get("name")):
        raise RepairBlocked("repaired_candidate_corrupted_name")

    merged_attributes = dict(legacy.get("attributes") or {})
    for field in ("classe_armatura", "punti_ferita", "velocita"):
        merged_attributes[field] = candidate_attributes[field]

    existing_flags = {
        str(flag)
        for flag in (legacy.get("review_flags") or [])
        if str(flag) not in CRITICAL_GATE_FLAGS
    }
    existing_flags.add(REPAIR_FLAG)

    gated = apply_ocr_review_gates({
        **legacy,
        "attributes": merged_attributes,
        "review_flags": sorted(existing_flags),
        "review_status": "pending",
    })

    post_flags = monster_semantic_numeric_flags(
        gated.get("attributes") or {}
    )
    if post_flags:
        raise RepairBlocked(
            "post_merge_gate_failure",
            ",".join(sorted(post_flags)),
        )
    gated_flags = set(gated.get("review_flags") or [])
    if INVALID_ENTITY_TITLE_FLAG in gated_flags:
        raise RepairBlocked("post_merge_invalid_title")
    if CORRUPTED_ENTITY_NAME_FLAG in gated_flags:
        raise RepairBlocked("post_merge_corrupted_name")
    if (
        gated.get("review_status") != "pending"
        or OCR_REVIEW_FLAG not in gated_flags
    ):
        raise AssertionError(
            "OCR repair proposal lost mandatory review state"
        )

    return {
        "attributes": gated["attributes"],
        "review_flags": gated["review_flags"],
        "review_status": "pending",
    }


async def _apply_update(
    collection: Any,
    legacy: dict[str, Any],
    proposal: dict[str, Any],
) -> None:
    if legacy.get("canonical_id"):
        raise RepairBlocked(
            "canonical_record_linked",
            "Refusing to mutate a record already linked to canonical data",
        )
    if monster_identity_sanity_flags(legacy.get("name")):
        raise RepairBlocked(
            "corrupted_entity_name",
            "Refusing to mutate a monster with a structurally corrupt legacy name",
        )

    query: dict[str, Any] = {
        "id": str(legacy["id"]),
        "review_status": "verified",
    }
    checksum = str(legacy.get("source_text_checksum") or "")
    if checksum:
        query["source_text_checksum"] = checksum

    write_payload = {
        **proposal,
        "updated_at": datetime.now(timezone.utc),
    }
    result = await collection.update_one(
        query,
        {"$set": write_payload},
    )
    if result.matched_count != 1:
        raise RepairBlocked(
            "concurrent_record_drift",
            f"matched_count={result.matched_count}",
        )

    verify = await collection.find_one(
        {"id": str(legacy["id"])}
    )
    if not verify or verify.get("review_status") != "pending":
        raise RuntimeError("post-update verification failed")
    verify_flags = {
        str(flag)
        for flag in (verify.get("review_flags") or [])
    }
    if (
        OCR_REVIEW_FLAG not in verify_flags
        or REPAIR_FLAG not in verify_flags
    ):
        raise RuntimeError(
            "post-update review flags verification failed"
        )
    if CORRUPTED_ENTITY_NAME_FLAG in verify_flags:
        raise RuntimeError("post-update corrupted name verification failed")
    if monster_semantic_numeric_flags(
        verify.get("attributes") or {}
    ):
        raise RuntimeError(
            "post-update semantic/numeric verification failed"
        )
    if str(verify.get("updated_at") or "") == str(
        legacy.get("updated_at") or ""
    ):
        raise RuntimeError("post-update updated_at verification failed")


def _json_view(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "name": record.get("name"),
        "attributes": record.get("attributes") or {},
        "review_flags": record.get("review_flags") or [],
        "review_status": record.get("review_status"),
        "source_refs": record.get("source_refs") or [],
    }


def _corrupted_name_report(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record.get("id"),
        "name": record.get("name"),
        "review_flags": [CORRUPTED_ENTITY_NAME_FLAG],
        "classification": "Record con Nome Corrotto (Scorie OCR)",
        "executed": False,
    }


async def _repair_one(
    collection: Any,
    record: dict[str, Any],
    active_sources: list[dict[str, Any]],
    pdf_cache: SourcePdfCache,
    args: argparse.Namespace,
) -> dict[str, Any]:
    source, source_ref = resolve_source(
        record,
        active_sources,
    )
    physical_page = int(source_ref["page"])
    pdf_path = pdf_cache.get(source)

    primary_pages, comparison_pages, quality = _ocr_source_window(
        pdf_path,
        physical_page,
        int(source["physical_pages"]),
        source,
        dpi=args.dpi,
        languages=args.languages,
        psm=args.psm,
        comparison_psm=args.comparison_psm,
    )
    candidate = _agreed_target_candidate(
        primary_pages,
        comparison_pages,
        str(source["physical_filename"]),
        str(source.get("language") or "it"),
        str(record.get("name") or ""),
        physical_page,
    )
    proposal = build_repair_proposal(
        record,
        candidate,
    )

    target_metrics = quality[physical_page]
    report = {
        "name": record.get("name"),
        "record_id": record.get("id"),
        "source": {
            "physical_filename": source.get(
                "physical_filename"
            ),
            "logical_source_id": source.get(
                "logical_source_id"
            ),
            "source_role": source.get("source_role"),
            "source_status": source.get("source_status"),
            "physical_page": physical_page,
            "logical_page": source_ref.get("logical_page"),
        },
        "layout": {
            "profile": target_metrics["layout_profile"],
            "effective_dpi": target_metrics["effective_dpi"],
            "primary_psm": target_metrics["primary_psm"],
            "comparison_psm": target_metrics[
                "comparison_psm"
            ],
            "segments": sorted(
                target_metrics["segments"].keys()
            ),
        },
        "ocr_pages": sorted(quality),
        "quality_fail_pages": sorted(
            page
            for page, page_metrics in quality.items()
            if not page_metrics["quality_pass"]
        ),
        "before": _json_view(record),
        "after": {
            **_json_view(record),
            **proposal,
        },
        "gate_failures_before": sorted(
            monster_semantic_numeric_flags(
                record.get("attributes") or {}
            )
        ),
        "gate_failures_after": [],
        "would_update": True,
        "executed": False,
    }

    if args.execute:
        await _apply_update(
            collection,
            record,
            proposal,
        )
        report["executed"] = True
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Source-guided legacy monster repair"
    )
    parser.add_argument(
        "--name",
        default="Zuggtmoy",
        help="Single monster name; default dry-run sample",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every currently failed legacy monster with a sane name",
    )
    parser.add_argument(
        "--target-set",
        choices=("healthy22",),
        default=None,
        help="Process only an exact reviewed sealed target set",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply validated repairs; default is dry-run",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help="Exact confirmation token required for sealed batch execution",
    )
    parser.add_argument(
        "--pdf-root",
        default=os.getenv("TOMOFORGE_PDF_ROOT", ""),
    )
    parser.add_argument(
        "--allow-r2-download",
        action="store_true",
        help="Download exact registry PDF to a temporary local path",
    )
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--languages", default="ita")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--comparison-psm", type=int, default=4)
    return parser


async def _run(args: argparse.Namespace) -> int:
    if args.psm == args.comparison_psm:
        raise RuntimeError("OCR layout modes must differ")
    if not 120 <= args.dpi <= 300:
        raise RuntimeError("dpi must be between 120 and 300")
    if args.all and args.target_set:
        raise RuntimeError("--all and --target-set are mutually exclusive")
    if args.execute and not args.all and not args.target_set and not args.name:
        raise RuntimeError(
            "execution requires an explicit --name, --all, or --target-set"
        )
    if (
        args.execute
        and args.target_set == "healthy22"
        and args.confirm != HEALTHY22_CONFIRMATION_TOKEN
    ):
        raise RuntimeError("Healthy22 confirmation token mismatch")

    # Defense in depth: this repair path must never call hosted AI.
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)

    from core.db import db

    if not db.configured:
        raise RuntimeError("Supabase is not configured")

    records_collection = db.private_reference_records
    source_collection = db.private_reference_sources
    verified = await _fetch_all(
        records_collection,
        {
            "review_status": "verified",
            "reference_type": "monster",
        },
    )
    failures = select_failed_monsters(verified)
    corrupted_names = select_corrupted_name_monsters(verified)
    active_sources = await _fetch_all(
        source_collection,
        {"source_status": "active"},
    )

    summary = {
        "verified_monsters": len(verified),
        "failed_monsters_total": len(failures) + len(corrupted_names),
        "failed_monsters_selected": len(failures),
        "corrupted_entity_names": len(corrupted_names),
        "expected_initial_failures": EXPECTED_INITIAL_FAILURES,
        "dry_run": not args.execute,
    }
    print("SOURCE_GUIDED_REPAIR_SUMMARY")
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    if not failures and not corrupted_names:
        return 0

    sealed_batch = args.target_set == "healthy22"
    if sealed_batch:
        targets = select_healthy22_targets(failures)
    elif args.all:
        targets = failures
    else:
        wanted = str(args.name or "").casefold()
        corrupt_wanted = [
            record
            for record in corrupted_names
            if str(record.get("name") or "").casefold() == wanted
        ]
        if corrupt_wanted:
            raise RuntimeError(
                f"Monster {args.name!r} is isolated by "
                f"{CORRUPTED_ENTITY_NAME_FLAG} and cannot enter repair"
            )
        targets = [
            record
            for record in failures
            if str(record.get("name") or "").casefold()
            == wanted
        ]
        if len(targets) != 1:
            raise RuntimeError(
                f"Expected one failed monster named "
                f"{args.name!r}; found {len(targets)}"
            )

    pdf_cache = SourcePdfCache(
        args.pdf_root,
        args.allow_r2_download,
    )
    reports = []
    blocked = []
    stage_args = argparse.Namespace(**vars(args))
    if sealed_batch:
        # No live write is allowed until every one of the 22 proposals has
        # completed OCR, independent agreement and semantic/numeric gates.
        stage_args.execute = False
    try:
        for record in targets:
            try:
                reports.append(
                    await _repair_one(
                        records_collection,
                        record,
                        active_sources,
                        pdf_cache,
                        stage_args,
                    )
                )
            except RepairBlocked as exc:
                blocked.append({
                    "record_id": record.get("id"),
                    "name": record.get("name"),
                    "reason": exc.reason,
                    "detail": exc.detail,
                    "executed": False,
                })
    finally:
        pdf_cache.close()

    if sealed_batch and args.execute:
        if blocked or len(reports) != EXPECTED_HEALTHY22_COUNT:
            raise RuntimeError(
                "Healthy22 batch refused: all 22 proposals must be repairable before any UPDATE"
            )
        await _revalidate_target_snapshots(records_collection, targets)
        originals = {str(record["id"]): record for record in targets}
        for report in reports:
            expected_flags = sorted([OCR_REVIEW_FLAG, REPAIR_FLAG])
            actual_flags = sorted(str(flag) for flag in report["after"]["review_flags"])
            if actual_flags != expected_flags:
                raise RuntimeError(
                    f"Healthy22 unexpected proposal flags for {report['record_id']}: {actual_flags!r}"
                )
            proposal = {
                "attributes": report["after"]["attributes"],
                "review_flags": report["after"]["review_flags"],
                "review_status": "pending",
            }
            await _apply_update(
                records_collection,
                originals[str(report["record_id"])],
                proposal,
            )
            report["executed"] = True

    name_corruption_bucket = {
        "label": "Record con Nome Corrotto (Scorie OCR)",
        "count": len(corrupted_names),
        "records": [
            _corrupted_name_report(record)
            for record in corrupted_names
        ],
    }
    final = {
        "dry_run": not args.execute,
        "failed_monsters_total": len(failures) + len(corrupted_names),
        "targets": len(targets),
        "repairable": len(reports),
        "blocked": len(blocked),
        "corrupted_entity_names": len(corrupted_names),
        "name_corruption_bucket": name_corruption_bucket,
        "updates_performed": sum(
            1
            for report in reports
            if report["executed"]
        ),
        "reports": reports,
        "blocked_records": blocked,
    }
    print("FINAL_REPORT")
    print(
        json.dumps(
            final,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if reports or blocked or corrupted_names else 1


def main() -> int:
    try:
        return asyncio.run(
            _run(_parser().parse_args())
        )
    except Exception as exc:
        print(
            f"Source-guided monster repair aborted: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

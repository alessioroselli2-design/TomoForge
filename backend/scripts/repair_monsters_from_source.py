#!/usr/bin/env python3
"""Source-guided repair for legacy monster OCR records.

Default mode is a read-only single-record dry-run (Zuggtmoy). The script:
1. selects legacy verified monsters that fail current semantic/numeric gates;
2. resolves provenance against the live active source registry;
3. materializes the exact source PDF locally and verifies its SHA-256;
4. OCRs at most a 3-page window (target page +/- 1) with two independent
   Tesseract layout modes;
5. applies a source-specific layout profile when a manual is known to use
   two-column stat blocks, OCRing each column independently before parsing;
6. requires an independently-agreed monster candidate matching the known name;
7. requires the repaired core attributes to pass ocr_semantic_gates;
8. prints BEFORE/AFTER JSON; and
9. performs no UPDATE unless --execute is explicitly supplied.

The script never auto-approves or canonicalizes. Even a successful repair is
written as review_status='pending' with review flag 'ocr_da_verificare'.
Hosted LLM providers are intentionally disabled in this implementation.
"""

from __future__ import annotations

import argparse
import asyncio
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
    HP_FORMAT_ERROR_FLAG,
    INVALID_ENTITY_TITLE_FLAG,
    OCR_REVIEW_FLAG,
    apply_ocr_review_gates,
    entity_name_semantic_flags,
    monster_semantic_numeric_flags,
)

PAGE_SIZE = 1000
EXPECTED_INITIAL_FAILURES = 109
REPAIR_FLAG = "source_guided_repair"
ELIGIBLE_SOURCE_ROLES = {"authority", "ingest_copy"}
CRITICAL_GATE_FLAGS = {
    CA_FORMAT_ERROR_FLAG,
    CA_OUT_OF_BOUNDS_FLAG,
    HP_FORMAT_ERROR_FLAG,
    INVALID_ENTITY_TITLE_FLAG,
}

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
    if str(record.get("reference_type") or "") != "monster":
        return set()
    if entity_name_semantic_flags(record.get("name")):
        return {INVALID_ENTITY_TITLE_FLAG}
    return monster_semantic_numeric_flags(record.get("attributes") or {})


def select_failed_monsters(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select genuine verified monsters failing CA/HP gates, excluding headings."""
    selected = []
    for record in records:
        flags = _legacy_failure_flags(record)
        if flags and INVALID_ENTITY_TITLE_FLAG not in flags:
            selected.append(record)
    return sorted(
        selected,
        key=lambda row: (
            str(row.get("name") or "").casefold(),
            str(row.get("id") or ""),
        ),
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
    if INVALID_ENTITY_TITLE_FLAG in set(
        gated.get("review_flags") or []
    ):
        raise RepairBlocked("post_merge_invalid_title")
    if (
        gated.get("review_status") != "pending"
        or OCR_REVIEW_FLAG
        not in set(gated.get("review_flags") or [])
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

    query: dict[str, Any] = {
        "id": str(legacy["id"]),
        "review_status": "verified",
    }
    checksum = str(legacy.get("source_text_checksum") or "")
    if checksum:
        query["source_text_checksum"] = checksum

    result = await collection.update_one(
        query,
        {"$set": proposal},
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
    if monster_semantic_numeric_flags(
        verify.get("attributes") or {}
    ):
        raise RuntimeError(
            "post-update semantic/numeric verification failed"
        )


def _json_view(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "name": record.get("name"),
        "attributes": record.get("attributes") or {},
        "review_flags": record.get("review_flags") or [],
        "review_status": record.get("review_status"),
        "source_refs": record.get("source_refs") or [],
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
        help="Process every currently failed legacy monster",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply validated repairs; default is dry-run",
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
    if args.execute and not args.all and not args.name:
        raise RuntimeError(
            "execution requires an explicit --name or --all"
        )

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
    active_sources = await _fetch_all(
        source_collection,
        {"source_status": "active"},
    )

    summary = {
        "verified_monsters": len(verified),
        "failed_monsters_selected": len(failures),
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

    if not failures:
        return 0

    if args.all:
        targets = failures
    else:
        wanted = str(args.name or "").casefold()
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
    try:
        for record in targets:
            try:
                reports.append(
                    await _repair_one(
                        records_collection,
                        record,
                        active_sources,
                        pdf_cache,
                        args,
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

    final = {
        "dry_run": not args.execute,
        "targets": len(targets),
        "repairable": len(reports),
        "blocked": len(blocked),
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
    return 0 if reports or blocked else 1


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

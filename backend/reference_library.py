"""Compatibility wrapper around the stable reference-library parser.

The historical implementation is kept byte-for-byte in
``_reference_library_base.py``.  This wrapper executes that module in the
current namespace, then adds one narrow OCR-only bridge: an English record that
the generic parser classified as ``other`` may be promoted to ``monster`` only
when the conservative monster parser independently finds the same normalized
name on the same page with all core stat-block fields present.

Promotion never clears OCR/manual-review flags and never marks a record trusted.
"""

from pathlib import Path as _BootstrapPath

_base_path = _BootstrapPath(__file__).with_name("_reference_library_base.py")
_base_source = _base_path.read_text(encoding="utf-8")
exec(compile(_base_source, str(_base_path), "exec"), globals(), globals())
del _base_source


def _promote_ocr_english_monsters(
    records: list[dict],
    raw_page_text: str,
    source_filename: str,
    source_page: int,
    source_language: str,
) -> list[dict]:
    """Promote exact same-page English OCR matches from ``other`` to ``monster``.

    This is deliberately fail-closed:
    - English OCR pages only.
    - Existing generic records only; no new record is invented here.
    - Exact normalized-name and page agreement is required.
    - The conservative monster parser must already have accepted a complete
      Armor Class / Hit Points / Speed stat block.
    - Existing provenance is preserved.
    - ``ocr_da_verificare`` remains mandatory, so Supabase review is still
      required before the record can become trusted.
    """
    if source_language != "en" or not raw_page_text.strip():
        return records

    # Local import avoids a module cycle: monster_statblock_ocr imports the
    # normalization helpers exposed by this module.
    from services.monster_statblock_ocr import parse_monster_statblocks

    candidates = parse_monster_statblocks(
        [(int(source_page), raw_page_text)],
        source_filename,
        source_language,
    )
    candidates_by_name: dict[str, list[dict]] = {}
    for candidate in candidates:
        if int(candidate.get("start_page") or 0) != int(source_page):
            continue
        normalized_name = str(candidate.get("normalized_name") or "")
        if normalized_name:
            candidates_by_name.setdefault(normalized_name, []).append(candidate)

    promoted: list[dict] = []
    for record in records:
        current = record
        if record.get("reference_type") == "other":
            normalized_name = str(record.get("normalized_name") or "")
            exact = candidates_by_name.get(normalized_name, [])
            if len(exact) == 1:
                candidate = exact[0]
                attributes = dict(candidate.get("attributes") or {})
                if all(
                    attributes.get(field)
                    for field in ("classe_armatura", "punti_ferita", "velocita")
                ):
                    # Preserve the richer registry-aware provenance produced by
                    # the generic parser.  Only classification and structured
                    # stat-block facts come from the conservative parser.
                    current = {
                        **record,
                        "id": candidate.get("id") or record.get("id"),
                        "reference_type": "monster",
                        "description": candidate.get("description")
                        or record.get("description", ""),
                        "full_text": candidate.get("full_text")
                        or record.get("full_text", ""),
                        "attributes": attributes,
                        "tags": sorted(set(record.get("tags") or []) | {"monster"}),
                        "review_flags": sorted(
                            set(record.get("review_flags") or [])
                            | set(candidate.get("review_flags") or [])
                            | {"ocr_da_verificare"}
                        ),
                    }
        promoted.append(current)
    return promoted


def extract_reference_records(
    pdf_path: Path,
    ocr_page: Optional[Callable[[object, int], str]] = None,
    start_page: int = 1,
    end_page: Optional[int] = None,
    force_ocr: bool = False,
    source_language: str = "it",
) -> ReferenceImportReport:
    """Read source pages and bridge accepted English OCR monsters into import."""
    try:
        import pymupdf as fitz
    except ImportError as exc:  # pragma: no cover - deployment setup
        raise RuntimeError(
            "PyMuPDF non è installato: aggiungi PyMuPDF alle dipendenze backend."
        ) from exc

    document = fitz.open(pdf_path)
    report = ReferenceImportReport(source_filename=pdf_path.name)
    pending_spanish_feat: Optional[tuple[str, int]] = None
    current_class = ""
    current_subclass = ""
    try:
        first = max(start_page, 1)
        last = min(end_page or len(document), len(document))
        for page_number in range(first, last + 1):
            page = document[page_number - 1]
            text = "" if force_ocr else page.get_text("text")
            extracted_with_ocr = force_ocr
            if not text_is_usable(text):
                if ocr_page is None:
                    report.pages_needing_ocr.append(page_number)
                    continue
                try:
                    text = ocr_page(page, page_number)
                except Exception as exc:
                    logger.warning("OCR pagina %s non riuscito: %s", page_number, exc)
                    report.pages_needing_ocr.append(page_number)
                    continue
                extracted_with_ocr = True
                if not text_is_usable(text):
                    stripped = text.strip() if text else ""
                    if not stripped:
                        report.pages_needing_ocr.append(page_number)
                        continue
                    logger.warning(
                        "OCR pagina %s: testo sotto soglia qualità (len=%s) — accettato con flag review",
                        page_number,
                        len(stripped),
                    )

            report.pages_read += 1
            lines = [line.strip() for line in text.splitlines()]
            if pending_spanish_feat:
                title, title_page = pending_spanish_feat
                next_heading = next(
                    (
                        index
                        for index, line in enumerate(lines)
                        if _title_from_line(line)
                    ),
                    len(lines),
                )
                continuation = "\n".join(lines[:next_heading])
                continued_records = parse_reference_page(
                    f"{title}\n{continuation}",
                    pdf_path.name,
                    title_page,
                    source_language,
                    current_class,
                    current_subclass,
                )
                continued = next(
                    (
                        record
                        for record in continued_records
                        if record["normalized_name"] == normalize_reference_name(title)
                    ),
                    None,
                )
                if continued:
                    continued["review_flags"] = [
                        flag
                        for flag in continued.get("review_flags", [])
                        if flag != "sezione_potenzialmente_continua"
                    ]
                    report.records.append(continued)
                pending_spanish_feat = None

            records = parse_reference_page(
                text,
                pdf_path.name,
                page_number,
                source_language,
                current_class,
                current_subclass,
            )

            if extracted_with_ocr and source_language == "en":
                records = _promote_ocr_english_monsters(
                    records,
                    text,
                    pdf_path.name,
                    page_number,
                    source_language,
                )

            for record in records:
                if record.get("reference_type") == "class":
                    current_class = record.get("name", "")
                    current_subclass = ""
                elif record.get("reference_type") == "subclass":
                    current_subclass = record.get("name", "")

            if extracted_with_ocr:
                # Apply the same fail-closed gate to every OCR-derived record
                # before it can reach the ingestion service. The gate never
                # repairs source text or removes provenance.
                from services.ocr_semantic_gates import apply_ocr_review_gates

                records = [apply_ocr_review_gates(record) for record in records]

            report.records.extend(records)
            if source_language == "es" and not _is_sparse_index_page(
                lines, source_language
            ):
                parsed_names = {record["normalized_name"] for record in records}
                for line in reversed(lines):
                    title = _title_from_line(line)
                    if not title:
                        continue
                    if (
                        normalize_reference_name(title) in SPANISH_FEAT_TITLES
                        and normalize_reference_name(title) not in parsed_names
                    ):
                        pending_spanish_feat = (title, page_number)
                    break
        return report
    finally:
        document.close()

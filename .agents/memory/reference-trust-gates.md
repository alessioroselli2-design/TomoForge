---
name: Reference trust gates
description: The trust policy for extracted manual records and every deterministic use of them.
---

Records created by the automatic supplied-manual queue are accepted as usable source-backed records once their processing succeeds. Failed translations remain unavailable.

**Why:** The project owner explicitly wants requests such as a class, ancestry, and subclass to produce a card from the prepared library without any manual review gate.

**How to apply:** Keep source/page provenance and failure states, but do not reintroduce a review-only filter for successful automatic preload records. Direct card and character materialization must be able to use them.

Card provenance must remain server-derived per linked rule, including spells, rather than as only a shared list of manuals. Snapshot and history responses may expose that rule name, source identifier, manual, and page, but never extracted source text.

**Why:** An aggregate source list cannot establish which page supports a given applied rule, while raw snapshots can disclose private manual extracts through card history and update flows.

**How to apply:** Rebuild per-rule provenance whenever links change, include it in undo/redo state, and use an explicit public snapshot projection for every card-shaped response.

When the Spanish Manual del Jugador and the Italian edition cover the same 5e player rules, treat the Spanish source as the preferred canonical input: it has native readable text, while the Italian source may require OCR. Keep the Spanish original beside the Italian translation; use the Italian edition as supplementary validation rather than allowing it to replace the preferred source.

**Why:** The project owner explicitly selected the Spanish edition as the most reliable and practical base, and the current file-quality metadata confirms that it is native text while the Italian player manual is OCR-gated.

**How to apply:** Automatic indexing should prioritize the Spanish manual for overlapping rules, retain all page-level provenance, and report Italian-only or Spanish-missing coverage separately.
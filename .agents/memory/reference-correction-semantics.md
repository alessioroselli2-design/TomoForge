---
name: Reference correction semantics
description: Trust and persistence rules for owner corrections to extracted or translated manual records.
---

Review notes describe verification context and must never be parsed or applied as content edits. Content corrections must be entered explicitly, preserve the original extract for comparison, and remain untrusted until the owner confirms them.

**Why:** Free-form notes are ambiguous. Treating them as executable instructions could silently turn an inferred correction into an authoritative rule, while discarding them on re-import would lose deliberate owner work.

**How to apply:** Keep notes in the append-only review trail. Store explicit corrected fields separately from the immutable source snapshot, preserve them when the same source is automatically reprocessed, and invalidate or reassess them when the source itself changes.
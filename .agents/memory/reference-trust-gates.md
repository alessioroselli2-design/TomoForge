---
name: Reference trust gates
description: The trust policy for extracted manual records and every deterministic use of them.
---

Records sourced through OCR, automatic translation, or extraction warnings must remain non-authoritative until a reviewer explicitly marks them verified. This requirement applies both to search/auto-completion and to direct APIs that attach or materialize rules on cards.

**Why:** A filter only on search is bypassable by a client that submits a known reference identifier; OCR output can otherwise silently become a character fact despite being visibly uncertain.

**How to apply:** Preserve uncertainty at ingestion, classify it centrally, and enforce the classification at every route that turns a reference into a persisted card or character value. Reports should count these records as needing review rather than missing.
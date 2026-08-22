---
name: Private review comparisons
description: Rules for exposing source and translated text during manual record review.
---

Original manual text and generated translations may be returned together only from a dedicated, authenticated owner-review response. General library search, card APIs, public cards, snapshots, and history must continue to use summary/provenance projections without extracted source text.

**Why:** A reviewer needs a side-by-side comparison to make an informed approval, but returning the same text through routine browsing or card responses would unnecessarily widen access to private manual extracts.

**How to apply:** Keep review views account-scoped, show the associated manual and page with the comparison, and update trust only through the explicit review action. Any normal path that turns a reference into a card must still check the centralized trust state.
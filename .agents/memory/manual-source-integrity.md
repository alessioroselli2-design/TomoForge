---
name: Manual source integrity
description: Preventing a mislabeled or copied supplied PDF from being indexed as a different manual.
---

Validate supplied manuals that are expected to be distinct before indexing them. A duplicate or mislabeled PDF should be treated as an invalid source, rather than as a parser or OCR failure.

**Why:** Reprocessing the duplicate can mislabel records and inflate a manual’s coverage with rules from a different source.

**How to apply:** Validate before both direct imports and background preload; remove records tied to an invalid source, reset its visible counters, and keep the failure visible. A changed source fingerprint can then resume indexing after replacement.
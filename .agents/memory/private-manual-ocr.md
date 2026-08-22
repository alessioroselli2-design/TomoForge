---
name: Private manual OCR
description: Privacy and safety rules for extracting structured records from personal manual scans.
---

OCR of owner-supplied manuals runs automatically per account in small, resumable page batches; no per-manual acknowledgement is shown.

**Why:** The project owner explicitly wants the supplied manuals to be ready without any import, page-selection, or consent steps. Small batches still bound cost and make recovery possible.

**How to apply:** Keep PDF binaries and page images local to the import path, persist only structured records and page references, and let the automatic queue invoke OCR as needed. Do not restore consent panels or manual page-range controls.
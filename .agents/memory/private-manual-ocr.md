---
name: Private manual OCR
description: Privacy and safety rules for extracting structured records from personal manual scans.
---

OCR of owner-supplied manuals must remain per-account, require an explicit acknowledgement before external processing, and be limited to small, resumable page batches.

**Why:** The original manuals and their rendered pages are private source material. Sending a whole scanned manual to an external model without a clear acknowledgement creates an avoidable disclosure and cost risk, while large synchronous jobs are hard to verify or recover.

**How to apply:** Keep PDF binaries and page images local to the import path, persist only structured records and page references, and require one selected manual plus a bounded page range for external OCR. Surface uncertain extraction with review flags rather than silently treating it as canonical.
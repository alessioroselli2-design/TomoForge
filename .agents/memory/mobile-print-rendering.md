---
name: Mobile print rendering
description: Reliable A4 card export strategy for iOS and home printers.
---

For A4 card faces generated from mobile browsers, avoid relying on a DOM screenshot of the interactive flex layout. Dedicated canvas renderers with fixed dimensions, explicit text coordinates, and high-contrast colors are the reliable export path for both front and back.

**Why:** iOS browser capture paths can clip glyphs or alter line boxes inside flex/overflow layouts, and printer output makes low-contrast text on dark backgrounds unreadable.

**How to apply:** Keep the interactive card design independent from the print composition. For physical-card PDFs, draw every front and back element into a fixed-size canvas before placing it on the A4 PDF. Include artwork, QR, frame, emblem, wordmark, motto, type label, and all text regions; use high-contrast text and keep footer marks inside the fixed canvas bounds.

The fixed canvas path was confirmed to resolve the clipped-text issue in A4 printing and single-card PNG/PDF export.
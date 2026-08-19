---
name: Mobile print rendering
description: Reliable A4 card export strategy for iOS and home printers.
---

For A4 card fronts generated from mobile browsers, avoid relying on a DOM screenshot of the interactive flex layout. A dedicated canvas renderer with fixed dimensions, explicit text coordinates, and high-contrast colors is the reliable export path.

**Why:** iOS browser capture paths can clip glyphs or alter line boxes inside flex/overflow layouts, and printer output makes low-contrast text on dark backgrounds unreadable.

**How to apply:** Keep the interactive card design independent from the print composition. For physical-card PDF fronts, draw the frame, artwork, QR, and each text region into a fixed-size canvas before placing it on the A4 PDF. Use high-contrast text and keep footer marks inside the fixed canvas bounds.

The fixed canvas path was confirmed to resolve the clipped-text issue in both A4 printing and single-card PDF export.
# Bigby — recovery of five pre-existing misclassified monster records

## Scope
All five are **existing database records** whose original registered narrative source text is intact but `reference_type=other` and `attributes={}`. The "verified" state of four *other*-type records is **not proof they were previously verified as monsters**. The fifth, Gelovivente, is `needs_review`. No new records, bulk OCR, manual PDFs, image files, or copyrighted source pages are committed. The name, original prose, source hash, historical empty source_attributes and licensed PDF source keys remain immutable.

## Original Italian source statblocks, directly viewed and cross-checked with the text layer

| Source name | Registered narrative PDF page | **Actual named stat-block** PDF page | CA | PF | Velocità | Characteristic proof |
| --- | ---: | ---: | --- | --- | --- | --- |
| Furia Di Kostchtchie | 139 | 139 | 16 (armatura naturale) | 216 (16d12 + 112) | 12 m | CON25 (+7); 16×7=112 |
| Gelovivente | 144 | 144 | 13 (armatura naturale) | 195 (17d12 + 85) | 12 m | CON21 (+5); 17×5=85 |
| Infernale Del Fuoco | 165 | 165 | 18 (piastre) | 175 (14d12 + 84) | 9 m | CON23 (+6); 14×6=84 |
| Rampollo Di Surtur | 178 | **179** | 20 (armatura naturale) | 546 (28d20 + 252) | 18 m | CON28 (+9); 28×9=252 |
| Rampollo Di Thrym | 180 | **181** | 19 (armatura naturale) | 499 (27d20 + 216) | 18 m | CON27 (+8); 27×8=216 |

- For Surtur, original PDF p178 also contains `Culla del Rampollo del Fuoco` (CA20, 555 HP, 12 m), **not** Surtur's own CA20, 546 HP, 18 m. Never merge adjacent statblocks.
- For Thrym, original PDF p180 contains `Culla del Rampollo del Gelo` (CA20, 499 HP, 12 m/nuotare12 m), **not** Thrym's own CA19, 499 HP, 18 m. Coincidence in HP totals cannot establish identity.
- PDF page numbers refer to actual one-indexed physical PDF positions, not to the printed folio. The registered p178/p180 descriptive source refs must remain and additional p179/p181 **same-filename licensed authority** refs should be appended only after passing a strict separate write gate.

## Safety and promotion plan
The source-lock service pins the exact registered original record ID, source checksum, independent description-text SHA256, original typed status, source page, corrections, zero OCR source attributes, and unaltered raw description. For all five, exact stat-block numeric values pass the unmodified global monster semantic numeric gate and coherent D&D dice averages.

Protected GitHub live audit reads exactly five existing IDs with an unchanged before/after snapshot and zero writes. Required backend Ruff/pytest, frontend tests/build and Vercel must be green and PR squash-merged on `develop` before any change to live records. Afterwards, apply five **individually guarded CAS transactions** (fail closed on drift/duplication) that reclassify the same IDs to `monster`, fill only verified operational CA/PF/velocità, preserve original text/checksum/OCR fields, add provenance p179 and p181 only for the two cross-page monsters, and append `private_reference_review_history` for each.

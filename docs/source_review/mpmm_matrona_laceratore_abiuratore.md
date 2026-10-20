# Original Italian MPMM sources for three missing monster references

All three existing reference rows were erroneously classified `other/verified` without monster attrs or monster-specific reviewed history. Independently inspected licensed Italian `Mostri del multiverso 101-200.pdf` original page images:

| Monster | Original PDF prose page | Actual named boxed-statblock page | AC | HP | Speed |
| --- | --- | --- | --- | --- | --- |
| Drow Matrona Madre | 6 (logical106) | **7** (logical107) | 17 (mezza armatura) | 247 (33d8 + 99) | 9 m |
| Laceratore Grigio | 62 (logical162) | 62 | 19 (armatura naturale) | 189 (18d10 + 90) | 9 m |
| Mago Abiuratore | 68 (logical168) | 68 | 12 (15 con armatura magica) | 104 (16d8 + 32) | 9 m |

Drow Matrona Madre has original source_refs for biography only on p6, while full named statblock occurs p7. Preserve historical registered page and separately document actual statblock; NEVER quietly rewrite original OCR pages. All original raw SHA256/checksums, source references, source_name, empty source_attributes must remain unchanged. Math average and global semantic gates fail closed.

PR adds no-write live original source checks with same-book anti-duplicate gates, negative regression tests and provenance. Require live audit, full backend/frontend CI and Vercel green, squash merge into `develop`, followed by **three separate** exact original row-snapshot CAS updates to `monster/verified` and append-only verified histories. No new or duplicate records.

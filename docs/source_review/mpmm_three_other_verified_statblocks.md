# Three independently boxed encounter monsters misclassified `other/verified`

Licensed Italian `Mostri del multiverso 201-294.pdf`, independently visually inspected in the original PDF:

| Creature | PDF page / logical page | CA | PF | Speed |
|---|---|---|---|---|
| Signore della Guerra | 46 / 246 | 18 (piastre) | 229 (27d8 + 108) | 9 m |
| Strangolatore | 49 / 249 | 16 (armatura naturale) | 13 (3d6 + 3) | 9 m |
| Ululatore | 63 / 263 | 16 (armatura naturale) | 90 (12d10 + 24) | 12 m |

All three are existing `other/verified`, with **no prior verified monster history** and empty `attributes` / `source_attributes`. Historical `verified` refers only to their *nonmonster classification*; do not claim they were monster-verified already. Keep historical review and original source text/refs/checksum/reviewer metadata intact.

This PR provides strict source snapshot SHA256 + checksum + page check, mathematical and global semantic gates, no-duplicate live audit and negative tests. No database writes in PR. After live audit, full backend/frontend CI, exact-head Vercel green and squash merge into `develop`, perform one CAS reclassification per original ID from `other/verified` to `monster/verified`, with new append-only history. No new records, no manufactured OCR evidence and no forcing.

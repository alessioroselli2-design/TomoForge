# MPMM original source recovery — Nilbog and two trolls

All three are already in the database as `other / needs_review`; no new records should be inserted.

| Monster | Italian source physical PDF page | Logical page | AC | HP | Speed |
| --- | ---: | ---: | --- | --- | --- |
| Nilbog | 2 | 202 | 13 (armatura di cuoio) | 7 (2d6) | 9 m |
| Troll Putrefatto | 60 | 260 | 16 (armatura naturale) | 138 (12d10 + 72) | 9 m |
| Troll Velenoso | 61 | 261 | 15 (armatura naturale) | 94 (9d10 + 45) | 9 m |

Direct visual inspection of the **original Italian** stat blocks in registered `Mostri del multiverso 201-294.pdf`. These are separately named stat blocks; do not mix Troll Feroce on an adjacent page, or any two troll subtypes.

Every original registered row ID, source checksum, full narrative SHA256, Italian source page, source attributes `{}`, OCR correction flags and historical review status are independently sealed in the review service. Strict unchanged global numeric sanity checks and average-hit-dice arithmetic validate values.

This PR performs **read-only** live source checks with unchanged before/after snapshot and negative regressions, and does not write Supabase. Only after successful live audit, backend/frontend CI, Vercel green on exact commit and squash merge into develop may three **separate** exact-snapshot, no-duplicate CAS transactions change existing records to `monster / verified` and append separate review histories. Original OCR, raw text, source refs and checksums remain immutable.

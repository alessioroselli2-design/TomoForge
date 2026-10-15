# MPMM four existing encounter creatures: primary-source recovery

The Italian source PDF `Mostri del multiverso 101-200.pdf` was inspected visually at logical pages **102, 103, 105 and 131**. It contains a separate boxed stat block for each of the four creatures below; verified stats are not sourced from neighboring prose.

| Creature | Logical page | AC | HP | Speed |
| --- | ---: | --- | --- | --- |
| Drow Capitano di Casata | 102 | 16 (cotta di maglia) | 162 (25d8 + 50) | 9m |
| Drow Consorte Prediletto | 103 | 15 (18 con armatura magica) | 240 (32d8 + 96) | 9m |
| Drow Lama d'Ombra | 105 | 17 (cuoio borchiato) | 150 (20d8 + 60) | 9m |
| Giff | 131 | 16 (corazza) | 60 (8d8 + 24) | 9m |

All four were already imported from the same licensed Italian MPMM source but incorrectly tagged `reference_type=other` and `needs_review`. Do not insert duplicates. The original source description, SHA256, checksum, empty OCR source attrs and source refs are preserved; core attributes must be set from the independent original image inspection, never claimed to be auto-OCR output. Each record passes the original global math/semantic checks, including average hit dice.

After positive live no-write audit, green backend/frontend CI, READY exact-commit Vercel preview and squash merge into develop, perform four **separate, exact-snapshot compare-and-set transitions** to `monster/verified` with add-only verified review history. Do not touch any other record or silently normalize overlapping editions.

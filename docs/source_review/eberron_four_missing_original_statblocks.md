# Eberron — four already-registered monster statblocks misclassified as other

Each target has an original source narrative, exact registered SHA256 and filename, but `reference_type=other`, `attributes={}`, and `source_attributes={}`. The original text, registration checksum, audit flags, identity, reference pages and source key are immutable. Never create duplicates.

| Name | Existing PDF narrative page | Named statblock page | CA | HP | Speed | Source validation |
| --- | ---: | ---: | --- | --- | --- | --- |
| Corridore | 292 | 292 | 14 | 9 (2d8) | 15 m | Same-page boxed Medium beast, no ability modifier |
| Dolgaunt | 293 | 293 | 16 (Difesa Senza Armatura) | 33 (6d8 + 6) | 12 m | Boxed Medium aberration, CON12 (+1) |
| Mordakhesh | 306 | 306 | 18 (armatura completa) | 170 (20d8 + 80) | 12 m | Named Medium fiend, CON18 (+4) |
| Sul Khatesh | 314 | **315** | 22 (armatura naturale) | 475 (50d10 + 200) | 12 m, volare 12 m (fluttuare) | Named Large fiend, CON19 (+4) |

All numbers independently confirmed in the directly inspected licensed original Italian PDF page images and the PDF's native text layer. No neighboring stat block supplies values: p314 includes **Rak Tulkhesh**, not Sul Khatesh's own CA/PF. Preserve existing Sul Khatesh narrative reference p314 and append its independently observed named statblock authority p315, after separate gated review.

A source-locked, read-only live GitHub audit tests each of the four exact existing records, proves raw/source fields remain untouched and reruns global semantic numeric gates without weakening them. A CI/Vercel green squash merge to `develop` is mandatory before individually guarded per-record Supabase CAS reclassification of `reference_type` and operational stats, with one new review-history entry. Existing generic `other/verified` is never treated as verified monster.

**Destriero Valenar** is a **fifth, distinct Eberron bestiary stat block** on PDF p285 (AC13, HP22(3d10+6), speed18m) not currently represented by a matching source record. It must be handled by a separate *new-source insertion* flow with independent provenance, dedup and completeness gates; this PR does not fabricate an existing Destriero record.

# Recover two independent MPMM giants from truncated OCR source headings

Direct original visual page checks in licensed Italian Mostri del Multiverso:

| Full original monster name | Italian PDF / registered logical page | Original boxed statblock |
|---|---|---|
| Gigante delle Nuvole Sorridente | `Mostri del multiverso 101-200.pdf`, p32/logical132 | CA15 natural; HP250(20d12+120); speed12m, fly12m (hover) |
| Quintessenza di Gigante delle Tempeste | `Mostri del multiverso 201-294.pdf`, p24/logical224 | CA12; HP230(20d12+100); speed15m, fly15m (hover), swim15m |

The existing records are wrongly `other/needs_review` named **Sorridente** and **Delle Tempeste**. Original source narratives on the same page explicitly describe the corresponding named giants and their full original boxed statblocks. Preserve original `source_name`, registered original text/checksum/ref/SHA256, review flags and source_attributes, but propose correcting current `name` + `normalized_name` to the visually confirmed complete original title. Do not insert duplicate records, do not change a plain `Gigante` to a generic name, and do not confuse with similarly named Bigby creatures.

No-write live source audit requires exact original short-name record and checks no other same-source record already uses complete name; strict independent original hit dice and global semantic gates with negative regressions. Require positive live audit, full backend/frontend CI and exact-head Vercel READY/green, then squash merge to `develop`; only then perform two individually guarded original-record compare-and-set reclassifications with append-only review histories, preserving source_name and all other original provenance.

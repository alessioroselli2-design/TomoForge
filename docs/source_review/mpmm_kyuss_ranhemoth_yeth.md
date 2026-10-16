# Three missing MPMM named boxed statblocks, already in original reference table

The licensed Italian source `Mostri del multiverso 201-294.pdf` has been visually inspected at **physical pages 17, 27, and 36**, corresponding to registered logical pages 217, 227, 236:

| Existing creature | PDF page | AC | HP | Speed |
| --- | ---: | --- | --- | --- |
| Progenie di Kyuss | 17 | 10 | 76 (9d8 + 36) | 9 m |
| Ranhemoth | 27 | 14 (armatura naturale) | 161 (14d12 + 70) | 9 m, nuotare 9 m |
| Segugio Yeth | 36 | 14 (armatura naturale) | 51 (6d10 + 18) | 12 m, volare 12 m (fluttuare) |

All are separately named complete statblocks, distinct from spell descriptions and adjacent entities. Their exact original records are `other/needs_review`, with source checksum + SHA256 and source refs retained; Kyuss and Ranhemoth have a historical `sezione_potenzialmente_continua` OCR flag that must remain documented in the new audit history, but source CA/HP/speed boxes appear fully on the registered page.

User rule counts all independent boxed creature statistics, including summoned companions, as monster references. **No duplicate insert**. The PR contains only a no-write original-record source validator, negative tests, and GitHub live readonly audit. After positive audit, full backend/frontend CI and exact-head Vercel READY/success and squash merge to `develop`, perform **three separate guarded full-snapshot CAS transactions**, changing the original existing IDs to `monster/verified`, clearing only operational warnings supported by source evidence, adding append-only verified review histories while leaving raw original text/OCR/checksums/authority and historical source_name untouched. Never relax the HP mathematical/semantic gates.

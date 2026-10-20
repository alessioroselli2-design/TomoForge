# Three already verified MPMM monsters whose statistics belong to neighbors

The Italian licensed PDF `Mostri del multiverso 201-294.pdf` has been independently examined visually:

| Original creature | Physical pages (logical) | Incorrect current stats (other creature) | Correct own named statblock |
| --- | --- | --- | --- |
| Serramorte Stratega | 37–38 (237–238) | Base Serramorte: AC12/15 mage, HP36 (8d8), 9m | **AC13 (16 con armatura magica); HP110 (20d8 + 20); speed9m** |
| Serramorte Wight | 37–38 (237–238) | Base Serramorte: AC12/15 mage, HP36 (8d8), 9m | **AC12 (15 con armatura magica); HP37 (5d8+15); speed9m** |
| Danzatore dell'Ombra | 40 (240) | Shadar-Kai Tessitore di Tenebre: AC14/17 mage, HP104 (16d8+32), 9m | **AC15 (cuoio borchiato); HP71 (13d8+13); speed9m** |

These original record IDs are already `monster/verified`. Such a status does not prove source numeric correctness: do not create new records or change their statuses. Both Serramorte subtypes already have original narrative p37 and named statblock p38 authority refs; preserve both. Danzatore has its own source p40; keep name as imported pending any separate full-title normalization review.

Source SHA256, name, ID, original source raw/OCR attrs, audit flags, review_corrections, checksum, pages and prior review history must remain intact. The code checks exact existing erroneous attributes and the **correct distinct named-box stats** before proposing an attribute-only correction. PR audit reads database without writing, includes negative tests. After live source audit, backend/frontend CI and exact-head Vercel READY/success and merge into `develop`, apply three independent source-locked CAS attribute-only corrections and append an audit-history event per monster, preserving earlier verified history.

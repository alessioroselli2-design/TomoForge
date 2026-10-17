# Three distinct original Italian encounter statblocks, misclassified as other

Under the user's rule all separately named creature statblocks, whether encounter enemies, allies or summons, belong in `monster`, while class features/spells without independent statblocks remain their original type.

| Original creature | Source PDF, actual statblock page | Registered prose page | AC | HP | Speed |
| --- | --- | --- | --- | --- | --- |
| Bacio della Morte | `Mostri del multi verso 1-100.pdf` p59 | 59 | 15 natural | 142 (15d10 + 60) | 0m, fly9m (hover) |
| Sacerdote di Guerra | `Mostri del multiverso 201-294.pdf` p32 (logical232) | 32 | 18 plate | 117 (18d8 + 36) | 9m |
| Titivilus | `Mostri del multiverso 201-294.pdf` p56 (logical256) | **55 (logical255)** | 20 natural | 150 (20d8 + 60) | 12m, fly18m |

The originally registered Titivilus row refers to his biography on p55, while the complete named boxed statblock is on adjoining p56. Record source refs must be preserved as historical evidence; the actual statblock page must be documented separately, not misrepresented as a page already referenced by OCR.

All three rows currently `other/verified`, with empty attrs; there are no corresponding existing monster records from those sources. `Sacerdote di Guerra` also names a PHB class ability in another source; retain that unrelated class ability, as it is not a duplicate of the MPMM monster.

Read-only registered original checksum, raw SHA256, authority, reference/page and math gates plus negative tests are required. No database writes within PR. Only after live audit, CI backend/frontend and exact-head Vercel green and merge into `develop`, do three independently guarded CAS transitions to `monster/verified`, preserving original text, provenance, checksums and the historical other classification in appended review notes.

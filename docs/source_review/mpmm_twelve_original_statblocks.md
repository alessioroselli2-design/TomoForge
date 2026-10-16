# Twelve independent Italian MPMM source-locked monster statblocks

Original `Mostri del multiverso 101-200.pdf`, visually inspected page by page. Each creature has its **own boxed AC/HP/speed statblock** and an already imported original record under `other` or `weapon` rather than `monster`. Preserve original `source_name`, names, IDs, full text and source attributes; do **not** duplicate them.

| Creature | Physical / logical page | AC | HP | Speed |
| --- | --- | --- | --- | --- |
| Duergar Maestro Della Mente | 13 / 113 | 14 (cuoio) | 39 (6d8+12) | 7,5 m |
| Evanescente | 22 / 122 | 14 | 18 (4d8) | 9 m |
| Githzerai Illuminato | 38 / 138 | 18 (difesa psichica) | 112 (15d8+45) | 12 m |
| Glasto Ligneo | 39 / 139 | 18 (naturale, scudo) | 75 (10d8+30) | 9 m, scalare 9 m |
| Gnoll Scarnito | 41 / 141 | 12 (naturale) | 11 (2d8+2) | 9 m |
| Guardia Nera | 46 / 146 | 18 (piastre) | 119 (14d8+56) | 9 m |
| Inseguitore Strisciante | 53 / 153 | 14 | 39 (6d8+12) | 9 m, scalare 9 m |
| Kruthik Adulto | 61 / 161 | 18 (naturale) | 39 (6d8+12) | 12 m, scavare 6 m, scalare 12 m |
| Lavamandra Guerriera | 64 / 164 | 13 (scudo) | 27 (5d8+5) | 9 m |
| Mastino D'Ombra | 76 / 176 | 12 | 33 (6d8+6) | 12 m |
| Maurezhi | 77 / 177 | 15 (naturale) | 88 (16d8+16) | 9 m |
| Nagpa | 96 / 196 | 19 (naturale) | 203 (37d8+37) | 9 m |

Some previously carried `other/verified` or `weapon/verified`; **verification of the previous category alone is insufficient to certify the monster statblock**. Every entry must obtain a new independent licensed-original-source stat audit and append-only verified history entry when reclassified. Some `needs_review` sources carried a historical `sezione_potenzialmente_continua` flag; original boxed CA/PF/speed are nonetheless visibly present on the identified PDF page. Preserve the old state/flags in a new review-history note when clearing only stale operational flags.

This PR contains no DB writes. Live exact identity/page/SHA256/source attribute/categorical/history preflight with zero writes and negative tests are required. CI backend/frontend, exact-head Vercel READY/success and squash merge into `develop` are mandatory before **twelve separate full-snapshot CAS mutations**. No forced verification, no hidden invented statistics, no substitution of a spell/class ability for its independent monster.

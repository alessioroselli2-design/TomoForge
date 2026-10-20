# Cacciatore Di Baphomet — Bigby Italian registered-source review

- Registered IT record: ref_abaf4a8fe2395260991a96729a200351, Bigby bgg_2023_it p124; original checksum 94e2b86aa7bbd78a46dc484cf7e9b36b4290e38afea7d7ab7a8ac7dd152e93d1.
- Original Italian OCR reports "Classe Armatura 1 7", "Punti Ferita 200 (l 6dl 2 + 96)", "Velocità 12 m". The OCR is preserved byte-for-byte as evidence; these substrings are never normalized in the source field.
- Original operational attributes before this review: CA17 natural, HP200 (16d12+96), speed12m.
- The English **Stalker of Baphomet**, *Bigby Presents: Glory of the Giants* p178, independently corroborates AC17 natural, HP200 (16d12+96), speed40ft (12m). Corroboration: https://www.aidedd.org/dnd/monstres.php?vo=stalker-of-baphomet and https://www.thievesguild.cc/harvest/creature.php?id=682 . 16 dice × Constitution +6 =96, average 16d12=104, total 200.
- The old OCR PR #404 remains an inconclusive *different* OCR path. This source adjudication never claims the old paired-OCR passed. It rejects changes to exact id/status/raw text/checksum/source attributes/operational attributes/manual provenance/page, rejects duplicate authorities, and retains the global numeric gate. Code audit reads twice and writes 0 rows.
- Merge only with **positive live registered-source audit**, green backend/frontend CI and Vercel. Only after merge may a separately guarded Supabase transaction change status/flags/review notes and append review history. No raw/source/operational values may be rewritten.

# Eberron: Non Morto Karrnathi — one-record source adjudication

- Exact sealed ID: `ref_b6af0f71247d5a4a8804486807d83776`, source `erlw_2019_it`, registered PDF `618795464-Eberron.pdf`, physical page 316. SHA-256 source text `fa517173161dacd7b164b24e15871a98d0e96bfc11a952e43acc8ce377a12657`.
- Original saved Italian text remains byte-for-byte: **Non morto Medio, legale malvagio Classe Armatura 17 (mezza armatura) Punti Ferita 52 (7d8 + 21) Velocità 9 m**.
- English *Eberron: Rising from the Last War*, Karrnathi Undead Soldier p. 295, also AC 17 (half plate), HP 52 (7d8+21), speed 30 feet: https://online.anyflip.com/tqblu/xfac/files/basic-html/page296.html and independently https://onyx5e.com/en/bestiary/karrnathi-undead-soldier/ .
- Hit dice floor(7×4.5)+21 = 52, exact Italian metric speed 9 m. Identity, CA, PF, speed, page, checksum, flags, and source role are sealed. No exceptions to HP gates.
- Old ordinary two-reader OCR PR #399 did **not** yield `all_gates_pass` because column segmentation produced uncertain numeric candidates, so it is not used as positive OCR evidence. The registered bilingual source review documents the distinct, guarded basis for a potential **status-only** change.
- PR-only integration; never write to DB during audit. Merge only with read-only audit positive, backend/frontend CI green and Vercel green. Supabase update/history is an independently guarded operation after merge.

# Bigby IT: Rampollo Di Memnor registered-source adjudication

- Exact identity `ref_7bc4d1c262b355668531f7e2331550f4`, registered source `bgg_2023_it` Bigby Italian pages **172 and 173**, checksum `77865ad5531eb46dc82ce8f4f73d6bce35e3b34f8502c34566021c5a6ffd3bd2`, active licensed authority. Pending, review flags empty, no canonical duplicate.
- Original Italian full_text and structured attributes match: **CA20 (armatura naturale)**, **PF656 (32d20 + 320)**, **18 m; volare24 m (fluttuare)**. All source fields must remain byte-for-byte unchanged.
- English original *Bigby Presents: Glory of the Giants*, printed p167, Scion of Memnor AC20 (natural armor), HP656 (32d20+320), speed 60ft and flying 80ft (hover). Independent documentation: https://onyx5e.com/en/bestiary/scion-of-memnor/ ; https://anyflip.com/fmtsi/jmxv/basic/151-192 .
- HP: floor(32*10.5)+320 = 656. Speed 60ft≈18m, flying 80ft≈24m.
- Paired-Italian OCR PR #434 returned timeout. That is **not** a passing OCR audit. Separate read-only, exact-source status review on immutable registered Italian snapshot and independent English original is required, with unchanged numeric gates and negative-drift tests.
- Promotion requires successful source audit, CI+Vercel, an independent SQL compare-and-swap and review history; no DB writes in the audit workflow.

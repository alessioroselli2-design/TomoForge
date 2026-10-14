# Eberron IT: Morfico (Shifter), p. 321 — editorial discrepancy review

- Scoped record: `ref_808e61bb52e050a8a7576b0941cfb3b9` (monster only; NOT the distinct player race `other`).
- Source: registered licensed Italian translation `erlw_2019_it`, `618795464-Eberron.pdf`, physical page 321, checksum `9822846d066cff3e847352cd6c1962bbc26b5de1ecec1070cd4e912c62acf685`.
- Italian physical page: **19 (3d8 + 8)**; user visually verified the page image. Registered source text independently contains the exact same expression. Italian raw is retained unmodified in `full_text` and in review notes/history.
- English original `Eberron: Rising from the Last War`, creature `Shifter` (p. 319), reads **19 (3d8 + 6)**, with CON 14 (+2), AC 14 (leather), Speed 30 ft.; matching Italian AC 14 and speed 9 m. Republished English source: https://anyflip.com/kpthp/rntq/basic/301-326 . Publisher book listing: https://www.dndbeyond.com/sources/dnd/erftlw .
- Arithmetic: floor(3*(8+1)/2) + 3*(+2) = 19. Italian `+8` yields a different average and is an apparent translation/typesetting typo, **not an OCR character confusion**.
- Editorially corrected **playable** HP: **19 (3d8 + 6)**, without altering AC, speed, or any other original attribute. Preserve the Italian printed `+8` and its provenanced checksum as source evidence, not as the operational dice formula.
- This adjudication does **not** excuse numeric anomalies in any other monster or change `monster_semantic_numeric_flags`; the Italian observed expression must fail the same mathematical gate, while the explicitly corrected source-reconciled value must pass it.
- Audit is read-only and fail-closed on all mismatches: exact ID/name/type/pending, one active authority source page and filename, initial flags, checksum, full-text source excerpt, all unchanged attributes and verified HP arithmetic. Mutation, if independently approved, is a **separate, atomic, guarded database transaction** with review history.
- The ordinary Italian OCR audit is expected to remain blocked on the **printed** `+8`; that is correct behavior. Do not present ordinary OCR as `all_gates_pass` for this editorial case.

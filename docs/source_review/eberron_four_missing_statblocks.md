# Four Eberron Italian `other` records containing actual monster stat blocks

These are not missing rows. Four pre-existing database records have been incorrectly classified as generic `other` (three generically verified, one needs_review). Existing name, source key `618795464-Eberron.pdf`, checksum, original prose, source_attributes={} and historical status are sealed.

| Name | Original PDF narrative p | SAME-NAME monster statblock PDF p | CA | HP | Speed |
|---|---:|---:|---|---|---|
| Corridore | 292 | 292 | 14 | 9 (2d8) | 15 m |
| Dolgaunt | 293 | 293 | 16 (Difesa Senza Armatura) | 33 (6d8+6) | 12 m |
| Mordakhesh | 306 | 306 | 18 (armatura completa) | 170 (20d8+80) | 12 m |
| Sul Khatesh | 314 | 315 | 22 natural | 475 (50d10+200) | 12 m, volare 12 m (fluttuare) |

- Visually inspected original Italian source PDF at these pages with matching heading and boxed stat block; native text independently corroborates numeric values. Dice arithmetic and global strict numeric gate passed unchanged. Neighboring `Piedartiglio` on page 292 is a **different monster** from Corridore; `Rak Tulkhesh` occupies page 314 where Sul Khatesh's narrative appears, while Sul Khatesh's **own boxed statblock** is page 315. Do not mix these characters.
- The Sul Khatesh original narrative authority p314 must be retained, and p315 appended to the existing source_refs **only after** guarded data promotion. Other records retain their original page reference.
- Every record has an exact original SHA256, checksum, identity, source refs, original `reference_type='other'`, original attrs, history and review status: explicit negative regression tests fail closed.
- This PR contains only source-locked read-only verification and tests, no PDF contents, user private text, or database writes. One CI+Vercel round for four source audits, then four separate CAS transitions and history rows after positive independent checks.
- Fifth Eberron missing candidate `Destriero Valenar` is a **genuinely absent row** (not one of these four), with a real boxed stat block p285. It must be added separately with its own source-backed candidate creation policy.

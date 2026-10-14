# Eberron (Italian): Assassino Tarkanan — registered source adjudication

## Identity and independent evidence
- Exact monster ID `ref_ab2cf767c3f25e00a1e4720ef6c01d44`, currently pending, no review flags.
- Registered authority: Eberron: Rinascita dopo l'Ultima Guerra `erlw_2019_it`, single PDF `618795464-Eberron.pdf`, exactly pages **317 and 318** in `source_refs`; source text checksum `33c3843afcd29a46b03ecc70bca51365849897d644d2df975693e7afd2c1e2ca`.
- Original registered Italian full_text says **Classe Armatura 15 (cuoio borchiato); Punti Ferita 45 (7d8 + 14); Velocità 9 m**. A non-core OCR artifact `a/lineamento` exists in `full_text` and must remain a preserved source token, not be silently rewritten.
- The English original `Tarkanan Assassin`, *Eberron: Rising from the Last War* p. **320**, says **Armor Class 15 (studded leather), Hit Points 45 (7d8 +14), Speed 30ft**. Independent original edition transcription: https://anyflip.com/kpthp/rntq/basic/301-326 ; separate bestiary confirmation https://onyx5e.com/en/bestiary/tarkanan-assassin/ .
- 30 ft. = 9.144 m = 9 m in common D&D metric notation. Dice mean floor(7 × 4.5) + 14 = 45.
- The older two-reader Italian OCR PR #410 found a matching target at 360 DPI but yielded `review_required/attribute_change_required` for CA and speed text renderings. **That OCR audit is not a positive verdict** and is not merged. The existing original Italian stored CA/PF/speed were independently checked against the source text *and* English original; all remain byte-for-byte identical.
- This special source-based review makes **no exceptions to OCR or numeric gates** and supports only status-only review on one record: exact id/name/type, pending, no review flags, no canonical link, checksum, exact full_text and attrs, two active authority refs at pages 317/318 in same registered PDF.
- Follow-up guarded database UPDATE and review history require the read-only audit, green backend/frontend CI and Vercel deployment, and explicit source adjudication. Never promote other entities using this result.

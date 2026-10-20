# Rampollo Di Grolantor — registered Italian Bigby p170–171

- Target `ref_4e249fc0d86753919cbb7bec5b96b661`, `bgg_2023_it`, source title *Bigby Presenta: La Gloria dei Giganti*, pages 170 and 171, original checksum `2b6b51820c7af89cec93586b89f30e4ff8674692e48257c4c492bdd9c5067f7d`.
- Original Italian structured values: CA18 (armatura naturale), PF402 (23d20+161), velocità18m. Original full_text includes OCR-spaced digits (`1 8`, `1 61`), retained unmodified.
- The English *Bigby Presents: Glory of the Giants*, printed p165, Scion of Grolantor has AC18 natural armor, HP402 (23d20+161), speed60ft. Independent documentation: https://onyx5e.com/en/bestiary/scion-of-grolantor/ and https://anyflip.com/fmtsi/jmxv/basic/151-192 .
- HP math: floor(23*10.5)+161=402. 60ft=18.288m, rounded to 18m per Italian 5e presentation. The title *Scion of Grolantor* is distinct from *Cradle of the Hill Scion*; source identity must remain fixed and neither can be substituted.
- The paired Italian OCR in PR #402 returned `review_required/attribute_change_required` for speed presentation, **not a passed audit**. This separate source-locked review checks exact record, attributes, full text, registered pages and original checksum, with unchanged global gates. No DB writes in CI; a separate guarded status-only SQL history operation is required after all-green reviews.

# Bigby: seven complete original Italian monster titles

The 71/71 registered monster count is correct. Seven existing verified monster IDs have an abbreviated or OCR-truncated display name. The original licensed Italian PDF statblock titles are:

| Page (physical PDF) | Current display name | Full original title |
|---:|---|---|
| 146 | Invocatore | Gigante del Fuoco Invocatore |
| 148 | Modellaghiaccio | Gigante del Gelo Modellaghiaccio |
| 149 | Valanghivo | Gigante delle Colline Valanghivo |
| 151 | Giocatore del Destino | Gigante delle Nuvole Giocatore del Destino |
| 152 | T'Erra Malvagia | Gigante delle Pietre della Terra Malvagia |
| 153 | Linguarupestre | Gigante delle Pietre Linguarupestre |
| 154 | Chiamaburrasche | Gigante delle Tempeste Chiamaburrasche |

The first six were verified against the same named source statblock's title and nearby descriptive prose; the seventh follows the same rule. The printed text on p152 describes **Terra malvagia**, and the statblock OCR contains a stray apostrophe in T'ERRA. No spell, class feature, or neighboring creature replaces any of the seven records.

Only the existing record's visible `name` and `normalized_name` may change after all gates pass. Preserve the original `source_name`, `source_normalized_name`, source excerpt, checksum, OCR attributes, source refs, numeric attrs, original IDs and audit history. Add an audit-history entry and a note about the naming correction. No new monster insertion.

Require a read-only exact-record source audit with duplicate target-name check; green backend/frontend CI and exact-head Vercel preview before merging to `develop`. Then use seven separately guarded compare-and-set updates, with zero writes on any drift.

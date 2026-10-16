# Troll Feroce — original boxed monster statblock versus class ability misclassification

Original Italian *Mordenkainen Presenta: Mostri del Multiverso*, PDF `Mostri del multiverso 201-294.pdf`, physical p59/logical p259, independently visually inspected. The named Troll Feroce statblock is fully present on this page: **Gigante Enorme**, AC15 natural, HP172 (15d12+75), speed12m, CON21 (+5); hit-dice average floor(15×6.5+75)=172.

The preexisting ID `ref_a41ee771f9fb58ed9d335d873d1364bc` was incorrectly classified `ability/needs_review` with the historical `sezione_potenzialmente_continua` warning. Full original boxed statblock is separately present on that exact page. The warning should be cleared **only after** exact original-source audit, green backend/frontend CI and Vercel, squash merge and guarded per-record CAS transaction. Preserve historical warning in audit notes. Do not mark unrelated historical OCR verified, do not rewrite source narrative/OCR/checksum/refs or create a duplicate.

No database writes within this PR; the live workflow asserts the original immutable record and fail-closes on any drift.

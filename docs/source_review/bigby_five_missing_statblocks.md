# Bigby — five original registered records misclassified as `other`

These five Bigby Italian records are **already in Supabase**; do not create duplicates. Each review is independent and fail-closed. Direct visual review of the original Italian PDF (plus its independently extracted text layer) identified the distinct same-name boxed stat block and checked AC, HP, speed and constitutional HP arithmetic.

| Existing record | Italian monster | Original narrative PDF page | Named stat block PDF page | CA | PF | Speed | Old status |
|---|---|---:|---:|---|---|---|---|
| ref_df2773e308da52269e7a546b78263197 | Furia Di Kostchtchie | 139 | 139 | 16 natural | 216 (16d12+112) | 12 m | verified (other) |
| ref_995df9449a30503b98317cea591de39b | Gelovivente | 144 | 144 | 13 natural | 195 (17d12+85) | 12 m | needs_review (other) |
| ref_73e5654442de579c8fbcd8185426b031 | Infernale Del Fuoco | 165 | 165 | 18 plate | 175 (14d12+84) | 9 m | verified (other) |
| ref_b921e7e721755bbbac1b62bd6d70240b | Rampollo Di Surtur | 178 | 179 | 20 natural | 546 (28d20+252) | 18 m | verified (other) |
| ref_1c9f8b60117d5649a6742b1de5e09b52 | Rampollo Di Thrym | 180 | 181 | 19 natural | 499 (27d20+216) | 18 m | verified (other) |

- **Non-interchangeable Rampollo/Culla blocks:** p178 contains the separate **Culla del Rampollo del Fuoco** and p180 contains **Culla del Rampollo del Gelo**. The named Rampollo di Surtur stat block is specifically on p179 (CA20/PF546) and Rampollo di Thrym on p181 (CA19/PF499). Their original narrative source refs p178/p180 are retained, with p179/p181 independently added upon promotion.
- Other source confusions: Gelovivente is an undead frost giant (not a generic living frost giant); Furia di Kostchtchie is a Huge demonic fiend; Infernale del Fuoco is a Huge devil. Review each boxed identity, not adjacent prose/table numbers.
- All original `source_full_text`, `full_text`, registered source checksums, historical `source_attributes={}`, source name, import filename and provenance remain immutable. There is no claim that an old OCR candidate correctly captured core fields. Raw body SHA256 values are sealed in `bigby_five_reclass_review.py`. Global `monster_semantic_numeric_flags` is unchanged.
- Five separate exact-ID auditors run read-only and retain individual verdicts. One PR saves repeated CI/Vercel builds, but **five separate guarded CAS DB transitions** must follow only after live audit, backend/frontend CI and Vercel checks all pass and the PR has squash-merged to `develop`.
- Each DB transition requires original timestamp, source content SHA, checksum, original `other` type and review state, zero conflicting monster of same normalized name and same manual, then updates only `reference_type`, existing operational `attributes`, `review_notes/status/timestamp`, and for the Rampolli **appends** the independently proven stat block page to `source_refs`. A fresh review-history entry is mandatory. Do not reclassify by trusting the old `other verified` value.

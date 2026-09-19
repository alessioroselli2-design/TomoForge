# Monster Manual core-field pilot audit — 2026-09-12

This audit records only aggregate, privacy-safe diagnostics from the read-only Monster Manual OCR/parser pilot triggered from `ai-canonical-library` at commit `91ce342334803f418af3e0d922a73b502588b2a9`.

## Provenance and safety

- Source workflow: `Pilot local OCR parser from R2`, run 4.
- Artifact: `mm-local-ocr-parser-pilot`.
- Source PDF window: pages 12–23 (12 requested / 12 read).
- OCR: local Tesseract only (`ita+eng`), 220 DPI, primary PSM 6, comparison PSM 4.
- Supabase writes: none.
- Hosted AI/API calls: none.
- Persisted values below are aggregate counts/quality metrics only; no OCR text, monster names, descriptions, or stat-block values are included.

## Result

- Quality-gated OCR pages: 12 / 12 passed.
- Generic parser detections: 35 total.
- Generic types: 1 monster, 9 other, 25 weapon.
- Records flagged for review: 35 / 35.
- Records carrying OCR review flag: 35 / 35.
- Source pages represented: 11.

### Conservative monster parser

- Primary OCR candidates: 2.
- Comparison OCR candidates: 3.
- Independently agreed candidates: 0.
- Primary candidates with a same-start-page candidate: 2 / 2.
- Primary candidates with a same normalized-name candidate: 1 / 2.
- Primary candidates with an exact page+name key candidate: 1 / 2.
- Exact-key candidates with all three core fields matching: 0 / 1.
- Exact-key `classe_armatura` matches: 0 / 1.
- Exact-key `punti_ferita` matches: 0 / 1.
- Exact-key `velocita` matches: 0 / 1.

## Interpretation / review gate

The page alignment is not the primary blocker: both primary candidates have a candidate on the same start page. Name normalization still blocks one candidate. For the one exact page+name pair, all three core fields differ between the two independent OCR layout modes.

This is not evidence that the review gate should be relaxed. The safe next diagnostic should determine whether those three field mismatches are caused by OCR/layout suffix noise versus disagreement in the semantic leading stat values. Until that distinction is measured, no candidate should be promoted or canonicalized automatically.

## Next safe step

Add aggregate-only semantic-signature diagnostics for the three core fields (without persisting source text or raw values), cover them with regression tests, and rerun the same bounded 12-page pilot. Only after those diagnostics should parser normalization be changed.

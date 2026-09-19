# AGENTS.md — TomoForge operating contract

This file defines mandatory repository-wide rules for Codex and any other coding agent working on TomoForge.
These rules are fail-closed: when evidence, parsing, tests, provenance, or repository state is ambiguous, stop the affected operation and surface the ambiguity instead of guessing, silently repairing, canonicalizing, or writing uncertain data.

## 1. Repository and change-management rules

- Never commit or push directly to the canonical branch (`main`).
- Every change must be made on a dedicated branch and delivered through a Pull Request.
- Do not merge a Pull Request unless all required CI checks and repository tests for the affected area are green.
- If required CI is absent, unavailable, cancelled, inconclusive, or cannot be executed, treat the merge gate as failed.
- Do not bypass branch protection, required reviews, required checks, or repository rules.
- Keep changes scoped to the requested task. Do not mix unrelated refactors, formatting sweeps, dependency upgrades, or data migrations into the same PR.
- Before opening or updating a PR, inspect the diff and confirm that no secrets, credentials, private manual contents, generated OCR dumps, or unrelated artifacts have been added.
- Never delete or rewrite canonical production data, Supabase data, R2 objects, or source manuals unless the task explicitly authorizes that exact destructive action.
- Never alter repository secrets or production credentials from an ordinary coding task.

## 2. Mandatory verification before PR completion

For Python/backend changes:

- Respect `backend/pytest.ini` exactly.
- Do not modify its configured xdist options as a workaround for failing tests.
- Run the relevant pytest suite for the change.
- Run Ruff on the Python files affected by the change.
- A failing, flaky, skipped-for-convenience, or unavailable required test is not a pass.

For frontend changes:

- Install dependencies from the repository lockfile.
- Run the relevant frontend tests when present and applicable.
- Run the production build before considering the change ready for review.
- Do not suppress build, lint, type, or test failures merely to obtain a green result.

For OCR/parser/data-pipeline changes:

- Run the smallest representative pilot that exercises the changed logic.
- Preserve diagnostic output needed to explain why a record passed or failed a gate.
- A parser change must not reduce provenance, reviewability, or fail-closed behavior.

## 3. Fail-closed data policy

TomoForge extraction is conservative by design.

- No uncertain extraction may become canonical automatically.
- Missing evidence, conflicting evidence, malformed values, weak semantic context, or parser disagreement must route the candidate to review/quarantine rather than canonical output.
- Never infer a missing core value from neighboring records, prior pages, layout similarity, model knowledge, or an expected D&D value.
- Never repair OCR text silently when the repair changes a canonical field.
- Any normalization that changes meaning must be traceable to source evidence and must pass the same gates as a direct extraction.
- Preserve raw/source evidence separately from normalized/canonical values.
- Do not turn an OCR confidence score by itself into acceptance of a canonical record.
- If a required gate cannot be evaluated, that gate fails closed.

## 4. OCR window limit

- OCR processing windows must contain at most 12 source pages.
- Do not combine windows to evade the 12-page limit.
- A job covering more than 12 pages must be split into deterministic, traceable windows of 12 pages or fewer.
- Each window must retain its own source/page provenance and diagnostic outcome.
- Cross-window deduplication may occur only after individual windows have completed their own extraction and gate evaluation.
- A record spanning a window boundary must not be reconstructed by guessing; use explicit overlapping evidence or route it to review.

## 5. Semantic gate for monster/stat-block candidates

A candidate may proceed toward canonicalization only when the surrounding source evidence is semantically consistent with the same stat block.

Required principles:

- The entity name/identity and its core fields must belong to the same local structural block.
- Structural anchors must support that interpretation; nearby unrelated prose is not sufficient.
- Standard D&D Italian ability abbreviations are valid structural tokens and must not be rejected as truncated words:
  - `For` = Forza
  - `Des` = Destrezza
  - `Cos` = Costituzione
  - `Int` = Intelligenza
  - `Sag` = Saggezza
  - `Car` = Carisma
- When independent extraction/parser paths are available, disagreement on a core field fails the semantic/core-field agreement gate.
- A value appearing on the same page is not enough: it must be structurally associated with the candidate entity.
- Headers, footers, page furniture, sidebars, examples, indexes, captions, running text, and unrelated table rows must not satisfy semantic gates.

## 6. Numeric gate — Armor Class (CA)

Armor Class is a core field and must pass a strict numeric gate.

A CA value is acceptable only when:

- it is explicitly supported by source text structurally associated with the same stat block;
- the numeric portion parses unambiguously as a single integer;
- surrounding qualifiers, when present, remain attached as provenance/context rather than being discarded;
- independent extraction/parser paths, when available, agree on the same numeric CA;
- the value is not taken from a table column, page number, challenge rating, ability score, hit-point value, spell level, equipment list, or another nearby numeric source.

If more than one plausible CA remains, if the integer is malformed, or if independent paths disagree, fail closed and send the candidate to review.

Do not "correct" CA to a value that merely looks more plausible for D&D.

## 7. Numeric gate — hit points and Hit Dice

Hit points and Hit Dice are core numeric evidence and must remain internally coherent.

For a Hit Dice expression:

- accept only an unambiguous dice expression structurally associated with the same stat block (for example `NdM`, optionally with an explicit signed modifier);
- preserve the source expression exactly in provenance;
- do not invent a missing die count, die size, sign, or modifier;
- do not derive a canonical Hit Dice expression from hit points alone;
- when both an average HP value and a Hit Dice expression are present, validate that they are mathematically compatible under the normal dice-average calculation;
- allow only explicitly defined rounding behavior; do not force a match by ad-hoc rounding or editing the OCR;
- when independent extraction/parser paths are available, disagreement on HP or Hit Dice fails the core numeric gate.

If the source exposes only HP but not Hit Dice, store only what the schema/task explicitly allows; never fabricate Hit Dice.
If HP/Hit Dice evidence is ambiguous, malformed, semantically detached, or numerically inconsistent, fail closed and route to review.

## 8. Isolation of OCR debris ("scorie")

OCR debris must never contaminate canonical records.

Treat as non-canonical/quarantined material unless positively proven otherwise:

- isolated characters or fragments;
- repeated headers/footers;
- page numbers;
- crop-edge text;
- decorative glyphs;
- broken multi-column joins;
- duplicated OCR lines;
- fragments from adjacent stat blocks;
- detached labels or values with no reliable structural association;
- obvious scan artifacts;
- tokens produced by image/table segmentation without sufficient semantic context.

Keep debris available for diagnostics when useful, but outside canonical entity fields.

## 9. Isolation of structured tables

Structured tables are a separate extraction domain and must not be interpreted as ordinary stat-block prose by default.

- Detect and isolate table regions/rows before applying free-text stat-block canonicalization.
- Do not let values from class tables, spell tables, encounter tables, equipment tables, indexes, contents pages, advancement tables, or similar structured layouts leak into monster core fields.
- Row/column adjacency alone is not semantic proof.
- If a structured table is itself the target of a task, use a table-specific parser/schema and retain row/column provenance.
- If table segmentation is uncertain, quarantine the affected extraction instead of flattening it into canonical prose.

## 10. Provenance and reviewability

Every canonical extraction produced by an OCR/parser pipeline must be traceable back to its source.

Preserve as applicable:

- source/manual identifier;
- source page number(s);
- OCR window identifier;
- raw extracted text or source excerpt reference;
- parser/extractor version or path;
- gate results;
- review status;
- transformation/normalization decisions.

Do not overwrite raw evidence with normalized text.
Do not mark a record as independently agreed when both values originate from the same extraction path.

## 11. `updated_at` synchronization

Whenever the pipeline writes or updates a logical batch of related canonical records:

- generate the batch timestamp once;
- use that exact same timestamp for every record affected by that logical write;
- express it in UTC ISO-8601;
- use a timezone-explicit UTC representation, preferably the `Z` form (for example `2026-09-19T08:57:00Z`);
- never mix local time, naive timestamps, and UTC within the same pipeline;
- do not generate slightly different per-row `updated_at` values inside one logical batch.

Retries must follow the operation's explicit idempotency policy; do not silently create misleading timestamps that make a failed partial write look like a clean synchronized batch.

## 12. Canonical write gate

Before any OCR-derived record can be written to a canonical datastore, all required gates for that record must pass.

At minimum, when applicable:

1. source/provenance gate;
2. semantic/structural association gate;
3. core-field agreement gate;
4. CA numeric gate;
5. HP/Hit-Dice numeric/coherence gate;
6. debris/table-isolation gate;
7. task-specific validation and review requirements.

A single required gate failure blocks canonicalization of that record.
Partial success in unrelated fields does not override a failed core gate.

Dry-run and pilot modes must remain non-canonical unless the task explicitly authorizes a write phase.

## 13. Supabase and external-service safety

- Prefer read-only inspection and dry-run behavior during parser/OCR development.
- Do not perform production writes merely to test connectivity.
- Never weaken Row Level Security, authentication, or authorization as a debugging shortcut.
- Do not expose service-role keys, OpenAI keys, R2 credentials, Stripe secrets, or other credentials in code, logs, commits, PRs, fixtures, or screenshots.
- External API/OCR/model calls must retain enough metadata to reproduce or review the decision without storing secrets.
- If Supabase or another required dependency is unavailable, do not manufacture a successful result; report the dependency failure and fail closed where it affects canonical output.

## 14. Pull Request completion contract

A coding task is complete only when:

- work is on a non-canonical branch;
- the requested implementation is present;
- the diff contains no unrelated changes;
- applicable local tests/checks pass;
- the Pull Request is opened against `main`;
- required CI checks pass before merge;
- unresolved gate failures, parser disagreements, or data-quality concerns are disclosed in the PR rather than hidden;
- no direct push to `main` has occurred.

Codex/agents may create or update branches and Pull Requests, investigate CI failures, and push fixes to the PR branch.
They must not use successful local execution as a substitute for required CI before the canonical branch is changed.

## 15. Priority rule

When a task instruction conflicts with this file, choose the safer interpretation unless the repository owner explicitly overrides the specific rule.
Security, provenance, fail-closed behavior, canonical-data integrity, Pull Request workflow, and required CI checks take precedence over speed or convenience.

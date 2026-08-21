---
name: Live Supabase verification
description: How to distinguish live catalogue state from static completion-review claims.
---

When a delivery depends on a Supabase migration or imported private catalogue data, treat the target instance's authenticated read as the source of truth. A completion review can assess only repository state or an older environment snapshot and may report an absent PostgREST relation after the migration has been applied live.

**Why:** Operational SQL application and account-scoped imports are external state; they are not represented by a source diff alone.

**How to apply:** Keep a read-only, committed verifier that fails clearly when the catalogue table is unavailable and probes the required record categories. Run it with the target account before accepting a claimed schema absence, and retain the normal OCR consent rules even when review feedback asks for more scanned content.
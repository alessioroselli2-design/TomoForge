# Preserving TomeForge data during the Supabase migration

The migration is intentionally **additive and idempotent**: it never deletes MongoDB records, legacy artwork, or Supabase records. Run it only after `supabase_schema.sql` has been applied and the private `tomeforge-assets` bucket exists.

## Required temporary secrets

Set these through Replit Secrets for the migration session:

- `LEGACY_MONGO_URL`, `LEGACY_DB_NAME`
- `LEGACY_STORAGE_URL` (the former object-storage API URL)
- either `LEGACY_STORAGE_KEY`, or `LEGACY_EMERGENT_LLM_KEY` so the script can obtain a temporary storage key
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

The regular application also needs `SUPABASE_ANON_KEY` for Google OAuth and `OPENAI_API_KEY` for AI generation.

## Safe migration sequence

1. Apply `backend/supabase_schema.sql` in Supabase SQL Editor and configure Google under **Authentication → Providers**. Add `<your app URL>/oauth/callback` as an allowed redirect URL.
2. Run `python backend/migrate_legacy_data.py --dry-run` and compare the printed counts with the legacy collections.
3. Back up the legacy database and run `python backend/migrate_legacy_data.py`.
4. Verify representative password and Google accounts, cards, public QR pages, artwork, and Premium entitlement before retiring the former services.

The script preserves user IDs, card IDs, artwork paths, password hashes, Stripe subscription fields, and Premium flags. Existing Google users are matched by their verified email at their first Supabase Google sign-in, so their migrated cards remain attached to the same TomeForge account.
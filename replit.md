# TomeForge

Private D&D 5e library app. Extracts structured content (spells, classes, features, monsters, items) from owner-supplied PDF manuals and stores it in a personal Supabase database. Cards are generated from library entries and exported as printable PNGs.

---

## Project structure

| Directory | Purpose |
|-----------|---------|
| `frontend/` | React (CRA) single-page app |
| `backend/` | FastAPI server — service role only, never exposes keys to the browser |
| `backend/supabase_schema.sql` | Single source of truth for the Supabase schema |
| `scripts/` | Dev helpers and startup scripts |

## Running locally

The `Start application` workflow runs `bash scripts/start-preview.sh`, which boots both the FastAPI backend and the React dev server.

The private PDF collection does not belong in Git. By default the importers
read `attached_assets/`; for a recovered or externally mounted collection,
set `REFERENCE_MANUAL_DIRECTORY` to its absolute directory before starting the
backend or an import worker. The local `library_manuals/` recovery directory is
ignored deliberately.

---

## Database migrations (Supabase production)

### How the schema is structured

`backend/supabase_schema.sql` is the **single source of truth**. It is written to be idempotent:
- `CREATE TABLE IF NOT EXISTS` for each table
- `ALTER TABLE … ADD COLUMN IF NOT EXISTS` for every column added after the initial schema
- `DROP CONSTRAINT IF EXISTS` / `ADD CONSTRAINT` for check constraints that have evolved

Running the full file multiple times is safe.

### How to apply a migration to production

Use the Supabase MCP tool from within a Replit Agent session:

```javascript
await mcpSupabase_applyMigration({
  project_id: "ighozdqvarkcshyqteto",
  name: "short_description_in_snake_case",
  query: `
    ALTER TABLE public.some_table
      ADD COLUMN IF NOT EXISTS new_column text NOT NULL DEFAULT '';
  `
});
```

After any DDL change, notify PostgREST to reload its schema cache:

```javascript
await mcpSupabase_executeSql({
  project_id: "ighozdqvarkcshyqteto",
  query: "NOTIFY pgrst, 'reload schema';"
});
```

### How to verify the live schema matches the code

Query `information_schema.columns` for each app table and compare against `backend/supabase_schema.sql`:

```javascript
await mcpSupabase_executeSql({
  project_id: "ighozdqvarkcshyqteto",
  query: `
    SELECT table_name, column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name IN (
        'users', 'cards', 'files', 'payment_transactions',
        'private_spells', 'private_reference_records',
        'private_manual_import_jobs', 'private_reference_review_history'
      )
    ORDER BY table_name, ordinal_position;
  `
});
```

### Adding a new column — checklist

1. Add the column to the `CREATE TABLE` block in `backend/supabase_schema.sql`
2. Add the corresponding `ALTER TABLE … ADD COLUMN IF NOT EXISTS` migration block below it
3. Apply the migration to production via `mcpSupabase_applyMigration`
4. Run `NOTIFY pgrst, 'reload schema'` to flush the PostgREST cache
5. Update any Pydantic models or SQLAlchemy queries in `backend/` that read/write the column

### Last verified

Schema drift audit run on 2026-08-23. All 8 tables (users, cards, files, payment_transactions, private_spells, private_reference_records, private_manual_import_jobs, private_reference_review_history) confirmed in sync with `backend/supabase_schema.sql`. Supabase project: `ighozdqvarkcshyqteto`.

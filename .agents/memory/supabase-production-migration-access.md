---
name: Supabase production migration access
description: How this project applies external Supabase schema changes when REST credentials are insufficient.
---

Apply schema DDL through an authenticated PostgreSQL pooler connection, not through the application service-role key. For pooled Supabase connections, use the project-scoped database role (`postgres.<project-ref>`) and pass the database password separately rather than parsing an untrusted URI.

**Why:** The service-role JWT grants data-API access but not Supabase Management SQL access, and the pooler rejects the unscoped `postgres` role without a tenant identifier. A malformed connection URI can also corrupt authentication when a password contains reserved URL characters.

**How to apply:** Derive the project ref from `SUPABASE_URL`, use the configured database-password secret through `PGPASSWORD`, run idempotent schema files with `psql -v ON_ERROR_STOP=1`, then execute the project's read-only operational verifier against the target owner.
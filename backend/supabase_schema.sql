-- Run this once in Supabase SQL Editor before starting TomeForge.
-- The FastAPI server uses SUPABASE_SERVICE_ROLE_KEY only; never expose that key to React.

create table if not exists public.users (
  user_id text primary key,
  email text not null unique,
  name text not null,
  picture text,
  auth_provider text not null default 'email',
  supabase_auth_id uuid unique,
  password_hash text,
  is_admin boolean not null default false,
  premium_manual boolean not null default false,
  premium_until timestamptz,
  stripe_subscription_id text,
  stripe_customer_id text,
  created_at timestamptz not null default now()
);
alter table public.users add column if not exists supabase_auth_id uuid unique;

create table if not exists public.cards (
  id text primary key,
  user_id text not null references public.users(user_id) on delete cascade,
  type text not null,
  custom_type text,
  name text not null default '',
  description text not null default '',
  story text not null default '',
  language text not null default 'it',
  attributes jsonb not null default '{}'::jsonb,
  artwork_path text,
  frame text not null default 'gold',
  appearance jsonb not null default '{"title_effect":"gold","title_shadow":true,"description_opacity":0.64,"text_panel_color":"#05080a","text_color":"#f5f1df","front_background_start":"#151311","front_background_end":"#151311","front_background_gradient":false,"title_custom_color_enabled":false,"title_custom_color":"#f8d764","frame_custom_color_enabled":false,"frame_custom_color":"#d4af37"}'::jsonb,
  back jsonb not null default '{"style":"classic","color":"#7f1d1d","emblem":"flame","motto":""}'::jsonb,
  reference_ids jsonb not null default '[]'::jsonb,
  spell_ids jsonb not null default '[]'::jsonb,
  source_refs jsonb not null default '[]'::jsonb,
  rule_sources jsonb not null default '[]'::jsonb,
  reference_snapshots jsonb not null default '[]'::jsonb,
  change_history jsonb not null default '[]'::jsonb,
  version integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists cards_user_created_idx on public.cards (user_id, created_at desc);
alter table public.cards
  add column if not exists appearance jsonb
  not null default '{"title_effect":"gold","title_shadow":true,"description_opacity":0.64,"text_panel_color":"#05080a","text_color":"#f5f1df","front_background_start":"#151311","front_background_end":"#151311","front_background_gradient":false,"title_custom_color_enabled":false,"title_custom_color":"#f8d764","frame_custom_color_enabled":false,"frame_custom_color":"#d4af37"}'::jsonb;
alter table public.cards
  add column if not exists reference_ids jsonb not null default '[]'::jsonb,
  add column if not exists spell_ids jsonb not null default '[]'::jsonb,
  add column if not exists source_refs jsonb not null default '[]'::jsonb,
  add column if not exists rule_sources jsonb not null default '[]'::jsonb,
  add column if not exists reference_snapshots jsonb not null default '[]'::jsonb,
  add column if not exists change_history jsonb not null default '[]'::jsonb,
  add column if not exists version integer not null default 0;

create table if not exists public.files (
  id text primary key,
  storage_path text not null unique,
  user_id text not null references public.users(user_id) on delete cascade,
  original_filename text,
  content_type text not null,
  is_deleted boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.payment_transactions (
  session_id text primary key,
  user_id text not null references public.users(user_id) on delete cascade,
  lookup_key text not null,
  amount integer not null default 0,
  currency text not null default 'eur',
  status text not null,
  payment_status text not null,
  stripe_subscription_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.payment_transactions add column if not exists stripe_subscription_id text;

-- Spell records are derived once from the owner's supplied PDFs.  The source
-- documents themselves are never uploaded to Storage or exposed by an API.
create table if not exists public.private_spells (
  id text primary key,
  user_id text not null references public.users(user_id) on delete cascade,
  name text not null,
  normalized_name text not null,
  level text not null default '',
  school text not null default '',
  casting_time text not null default '',
  range text not null default '',
  components text not null default '',
  duration text not null default '',
  description text not null default '',
  classes jsonb not null default '[]'::jsonb,
  source_refs jsonb not null default '[]'::jsonb,
  review_flags jsonb not null default '[]'::jsonb,
  imported_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, normalized_name)
);
create index if not exists private_spells_user_name_idx on public.private_spells (user_id, normalized_name);

-- Generic private catalogue for classes, subclasses, features, feats, races,
-- monsters, and other structured facts extracted from owner-supplied manuals.
-- Source PDF binaries are intentionally never stored in this table or Storage.
create table if not exists public.private_reference_records (
  id text primary key,
  user_id text not null references public.users(user_id) on delete cascade,
  reference_type text not null check (reference_type in (
    'class', 'subclass', 'class_feature', 'spell', 'feat', 'race', 'subrace',
    'monster', 'ability', 'weapon', 'armor', 'shield', 'equipment',
    'tool', 'magic_item', 'vehicle', 'ammunition', 'mount', 'trade_good',
    'service', 'other'
  )),
  name text not null,
  normalized_name text not null,
  description text not null default '',
  full_text text not null default '',
  attributes jsonb not null default '{}'::jsonb,
  parent_class text not null default '',
  parent_subclass text not null default '',
  level text not null default '',
  tags jsonb not null default '[]'::jsonb,
  source_refs jsonb not null default '[]'::jsonb,
  review_flags jsonb not null default '[]'::jsonb,
  review_status text not null default 'pending' check (review_status in ('pending', 'verified', 'needs_review')),
  review_notes text not null default '',
  review_corrections jsonb not null default '{}'::jsonb,
  source_key text not null default '',
  source_language text not null default 'it',
  source_normalized_name text not null default '',
  source_name text not null default '',
  source_description text not null default '',
  source_full_text text not null default '',
  source_attributes jsonb not null default '{}'::jsonb,
  source_text_checksum text not null default '',
  translation_status text not null default 'not_required' check (translation_status in ('not_required', 'translated', 'failed', 'processing')),
  translation_error text not null default '',
  translation_lease_id text not null default '',
  translation_lease_expires_at bigint not null default 0,
  imported_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, reference_type, normalized_name)
);
-- Existing installations created before equipment support need their original
-- type check widened as well; CREATE TABLE IF NOT EXISTS alone cannot alter it.
alter table public.private_reference_records
  drop constraint if exists private_reference_records_reference_type_check;
alter table public.private_reference_records
  add constraint private_reference_records_reference_type_check check (reference_type in (
    'class', 'subclass', 'class_feature', 'spell', 'feat', 'race', 'subrace',
    'monster', 'ability', 'weapon', 'armor', 'shield', 'equipment',
    'tool', 'magic_item', 'vehicle', 'ammunition', 'mount', 'trade_good',
    'service', 'other'
  ));
alter table public.private_reference_records
  add column if not exists review_corrections jsonb not null default '{}',
  add column if not exists parent_class text not null default '',
  add column if not exists parent_subclass text not null default '',
  add column if not exists level text not null default '';
alter table public.private_reference_records
  add column if not exists source_key text not null default '',
  add column if not exists source_language text not null default 'it',
  add column if not exists source_normalized_name text not null default '',
  add column if not exists source_name text not null default '',
  add column if not exists source_description text not null default '',
  add column if not exists source_full_text text not null default '',
  add column if not exists source_attributes jsonb not null default '{}'::jsonb,
  add column if not exists source_text_checksum text not null default '',
  add column if not exists translation_status text not null default 'not_required',
  add column if not exists translation_error text not null default '',
  add column if not exists translation_lease_id text not null default '',
  add column if not exists translation_lease_expires_at bigint not null default 0;
-- AI canonicalisation remains owner-scoped and only stores selected structured
-- records plus provenance; it never stores PDF bytes or page images.
alter table public.private_reference_records
  add column if not exists canonical_id text,
  add column if not exists ai_review_status text not null default 'pending',
  add column if not exists ai_confidence numeric not null default 0,
  add column if not exists ai_review_model text not null default '',
  add column if not exists ai_reviewed_at timestamptz,
  add column if not exists ai_review_notes text not null default '',
  add column if not exists ai_review_corrections jsonb not null default '{}'::jsonb;
create index if not exists private_reference_records_canonical_idx
  on public.private_reference_records (user_id, canonical_id);

create table if not exists public.private_reference_canonical (
  id text primary key,
  user_id text not null references public.users(user_id) on delete cascade,
  canonical_key text not null,
  reference_type text not null,
  normalized_name text not null,
  name text not null default '',
  description text not null default '',
  full_text text not null default '',
  attributes jsonb not null default '{}'::jsonb,
  parent_class text not null default '',
  parent_subclass text not null default '',
  level text not null default '',
  source_record_ids jsonb not null default '[]'::jsonb,
  source_refs jsonb not null default '[]'::jsonb,
  source_count integer not null default 0,
  confidence numeric not null default 0,
  verification_status text not null default 'pending',
  conflict_fields jsonb not null default '[]'::jsonb,
  verification_model text not null default '',
  verification_notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, canonical_key)
);
create index if not exists private_reference_canonical_owner_idx
  on public.private_reference_canonical (user_id, verification_status);
alter table public.private_reference_records
  drop constraint if exists private_reference_records_canonical_id_fkey;
alter table public.private_reference_records
  add constraint private_reference_records_canonical_id_fkey
  foreign key (canonical_id) references public.private_reference_canonical(id) on delete set null;
alter table public.private_reference_records
  drop constraint if exists private_reference_records_translation_status_check;
alter table public.private_reference_records
  add constraint private_reference_records_translation_status_check
  check (translation_status in ('not_required', 'translated', 'failed', 'processing'));
update public.private_reference_records
  set source_key = coalesce(nullif(source_refs->0->>'filename', ''), source_key),
      source_normalized_name = coalesce(nullif(source_normalized_name, ''), normalized_name),
      source_name = coalesce(nullif(source_name, ''), name),
      source_description = coalesce(nullif(source_description, ''), description),
      source_full_text = coalesce(nullif(source_full_text, ''), full_text),
      parent_class = coalesce(nullif(parent_class, ''), attributes->>'parent_class', ''),
      parent_subclass = coalesce(nullif(parent_subclass, ''), attributes->>'parent_subclass', ''),
      level = coalesce(nullif(level, ''), attributes->>'level', attributes->>'livello', '')
  where source_key = ''
     or source_normalized_name = ''
     or source_name = ''
     or (
       reference_type in ('class_feature', 'ability')
       and (
         (parent_class = '' and coalesce(attributes->>'parent_class', '') <> '')
         or (parent_subclass = '' and coalesce(attributes->>'parent_subclass', '') <> '')
         or (level = '' and coalesce(attributes->>'level', attributes->>'livello', '') <> '')
       )
     );
alter table public.private_reference_records
  drop constraint if exists private_reference_records_user_id_reference_type_normalized_name_key;
alter table public.private_reference_records
  drop constraint if exists private_reference_records_user_id_reference_type_normalized_key;
alter table public.private_reference_records
  add constraint private_reference_records_user_type_name_source_key
  unique (user_id, reference_type, normalized_name, source_key);
create index if not exists private_reference_records_user_name_idx
  on public.private_reference_records (user_id, reference_type, normalized_name);
create index if not exists private_reference_records_user_source_idx
  on public.private_reference_records (user_id, source_key, source_normalized_name);
create index if not exists private_reference_records_user_progression_idx
  on public.private_reference_records (user_id, parent_class, level)
  where reference_type in ('class_feature', 'ability');

-- One durable, owner-scoped queue per locally supplied manual.  It retains only
-- processing metadata and counters; source PDF bytes and extracted page text
-- stay outside Supabase.
create table if not exists public.private_manual_import_jobs (
  id text primary key,
  user_id text not null references public.users(user_id) on delete cascade,
  filename text not null,
  source_language text not null default 'it',
  source_fingerprint text not null default '',
  status text not null default 'queued' check (status in (
    'queued', 'processing', 'completed', 'failed'
  )),
  current_page integer not null default 1,
  page_count integer not null default 0,
  translation_processing_confirmed boolean not null default false,
  external_processing_confirmed boolean not null default false,
  lease_id text not null default '',
  lease_expires_at bigint not null default 0,
  attempt_count integer not null default 0,
  last_error text not null default '',
  pages_needing_ocr jsonb not null default '[]'::jsonb,
  records_imported integer not null default 0,
  records_updated integer not null default 0,
  records_flagged integer not null default 0,
  records_skipped integer not null default 0,
  translation_retry_at timestamptz,
  translation_retry_attempt integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (user_id, filename)
);
alter table public.private_manual_import_jobs
  add column if not exists source_language text not null default 'it',
  add column if not exists source_fingerprint text not null default '',
  add column if not exists status text not null default 'queued',
  add column if not exists current_page integer not null default 1,
  add column if not exists page_count integer not null default 0,
  add column if not exists translation_processing_confirmed boolean not null default false,
  add column if not exists external_processing_confirmed boolean not null default false,
  add column if not exists lease_id text not null default '',
  add column if not exists lease_expires_at bigint not null default 0,
  add column if not exists attempt_count integer not null default 0,
  add column if not exists last_error text not null default '',
  add column if not exists pages_needing_ocr jsonb not null default '[]'::jsonb,
  add column if not exists records_imported integer not null default 0,
  add column if not exists records_updated integer not null default 0,
  add column if not exists records_flagged integer not null default 0,
  add column if not exists records_skipped integer not null default 0,
  add column if not exists translation_retry_at timestamptz,
  add column if not exists translation_retry_attempt integer not null default 0,
  add column if not exists completed_at timestamptz;
-- Retire consent-waiting states: promote lingering rows to queued before the
-- constraint is tightened so existing imports can resume normally.
update public.private_manual_import_jobs
  set status = 'queued',
      lease_id = '',
      lease_expires_at = 0,
      last_error = '',
      translation_retry_at = null,
      translation_retry_attempt = 0,
      updated_at = now()
where status in ('waiting_ocr_consent', 'waiting_translation_consent');

alter table public.private_manual_import_jobs
  drop constraint if exists private_manual_import_jobs_status_check;
alter table public.private_manual_import_jobs
  add constraint private_manual_import_jobs_status_check check (status in (
    'queued', 'processing', 'completed', 'failed'
  ));
create index if not exists private_manual_import_jobs_owner_status_idx
  on public.private_manual_import_jobs (user_id, status, updated_at);

-- Append-only, owner-scoped audit trail for private-reference review decisions.
-- Keep it separate from the current review state so simultaneous decisions
-- cannot overwrite one another while a manual is being reimported.
create table if not exists public.private_reference_review_history (
  id text primary key,
  reference_id text not null references public.private_reference_records(id) on delete cascade,
  user_id text not null references public.users(user_id) on delete cascade,
  reviewer_id text not null references public.users(user_id) on delete cascade,
  reviewer_name text not null default '',
  reviewer_email text not null default '',
  review_status text not null check (review_status in ('pending', 'verified', 'needs_review')),
  review_notes text not null default '',
  reviewed_at timestamptz not null default now()
);
create index if not exists private_reference_review_history_owner_record_idx
  on public.private_reference_review_history (user_id, reference_id, reviewed_at desc, id desc);

-- Private bucket; FastAPI streams authorized files and public card artwork.
insert into storage.buckets (id, name, public)
values ('tomeforge-assets', 'tomeforge-assets', false)
on conflict (id) do nothing;

alter table public.users enable row level security;
alter table public.cards enable row level security;
alter table public.files enable row level security;
alter table public.payment_transactions enable row level security;
alter table public.private_spells enable row level security;
alter table public.private_reference_records enable row level security;
alter table public.private_reference_canonical enable row level security;
alter table public.private_manual_import_jobs enable row level security;
alter table public.private_reference_review_history enable row level security;

-- The browser has no direct access to this catalogue. FastAPI uses the service
-- role and enforces ownership on every read/write.
revoke all on table public.private_spells from anon, authenticated;
revoke all on table public.private_reference_records from anon, authenticated;
revoke all on table public.private_reference_canonical from anon, authenticated;
revoke all on table public.private_manual_import_jobs from anon, authenticated;
revoke all on table public.private_reference_review_history from anon, authenticated;
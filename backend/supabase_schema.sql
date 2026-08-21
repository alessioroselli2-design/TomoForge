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
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists cards_user_created_idx on public.cards (user_id, created_at desc);
alter table public.cards
  add column if not exists appearance jsonb
  not null default '{"title_effect":"gold","title_shadow":true,"description_opacity":0.64,"text_panel_color":"#05080a","text_color":"#f5f1df","front_background_start":"#151311","front_background_end":"#151311","front_background_gradient":false,"title_custom_color_enabled":false,"title_custom_color":"#f8d764","frame_custom_color_enabled":false,"frame_custom_color":"#d4af37"}'::jsonb;

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
  tags jsonb not null default '[]'::jsonb,
  source_refs jsonb not null default '[]'::jsonb,
  review_flags jsonb not null default '[]'::jsonb,
  review_status text not null default 'pending' check (review_status in ('pending', 'verified', 'needs_review')),
  review_notes text not null default '',
  source_key text not null default '',
  source_language text not null default 'it',
  source_normalized_name text not null default '',
  source_name text not null default '',
  source_description text not null default '',
  source_full_text text not null default '',
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
  add column if not exists source_key text not null default '',
  add column if not exists source_language text not null default 'it',
  add column if not exists source_normalized_name text not null default '',
  add column if not exists source_name text not null default '',
  add column if not exists source_description text not null default '',
  add column if not exists source_full_text text not null default '',
  add column if not exists source_text_checksum text not null default '',
  add column if not exists translation_status text not null default 'not_required',
  add column if not exists translation_error text not null default '',
  add column if not exists translation_lease_id text not null default '',
  add column if not exists translation_lease_expires_at bigint not null default 0;
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
      source_full_text = coalesce(nullif(source_full_text, ''), full_text)
  where source_key = '' or source_normalized_name = '' or source_name = '';
alter table public.private_reference_records
  drop constraint if exists private_reference_records_user_id_reference_type_normalized_name_key;
alter table public.private_reference_records
  add constraint private_reference_records_user_type_name_source_key
  unique (user_id, reference_type, normalized_name, source_key);
create index if not exists private_reference_records_user_name_idx
  on public.private_reference_records (user_id, reference_type, normalized_name);
create index if not exists private_reference_records_user_source_idx
  on public.private_reference_records (user_id, source_key, source_normalized_name);

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

-- The browser has no direct access to this catalogue. FastAPI uses the service
-- role and enforces ownership on every read/write.
revoke all on table public.private_spells from anon, authenticated;
revoke all on table public.private_reference_records from anon, authenticated;
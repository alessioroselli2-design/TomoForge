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

-- Private bucket; FastAPI streams authorized files and public card artwork.
insert into storage.buckets (id, name, public)
values ('tomeforge-assets', 'tomeforge-assets', false)
on conflict (id) do nothing;

alter table public.users enable row level security;
alter table public.cards enable row level security;
alter table public.files enable row level security;
alter table public.payment_transactions enable row level security;
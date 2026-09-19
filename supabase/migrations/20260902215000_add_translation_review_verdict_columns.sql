alter table public.private_reference_records
  add column if not exists translation_review_status text not null default 'pending',
  add column if not exists translation_review_confidence numeric not null default 0,
  add column if not exists translation_review_model text not null default '',
  add column if not exists translation_reviewed_at timestamptz,
  add column if not exists translation_review_notes text not null default '',
  add column if not exists translation_review_conflict_fields jsonb not null default '[]'::jsonb,
  add column if not exists translation_review_fingerprint text not null default '';

alter table public.private_reference_records
  drop constraint if exists private_reference_records_translation_review_status_check;
alter table public.private_reference_records
  add constraint private_reference_records_translation_review_status_check
  check (translation_review_status in (
    'pending', 'ai_verified', 'conflict', 'low_confidence', 'failed', 'not_required'
  ));

update public.private_reference_records
set translation_review_status = 'not_required',
    translation_review_confidence = 1
where translation_status = 'not_required';

create index if not exists private_reference_records_translation_review_idx
  on public.private_reference_records (user_id, translation_review_status)
  where translation_status = 'translated';

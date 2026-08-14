-- 0014_annotations.sql
-- spec: docs/specs/annotation-surface.md §2.1, §6
-- consumer: backend/finetune/build_dataset.py (its column expectations are authoritative)
--
-- Migration numbering note: 0009 is used TWICE on disk (0009_avatar_id.sql,
-- 0009_teacher_identity.sql). Both were hand-run against the live project under
-- those names, and supabase/migrations/ is a record of what a human executed
-- (AGENTS.md "Project-Specific Invariants") — there is no CLI ordering to repair
-- and no ledger table to update. Renaming them now would make the repo disagree
-- with what actually ran, trading a visible collision for an invisible lie. Left
-- alone deliberately; 0014 is the next free number and does not extend the mess.

create table annotations (
  pair_id         text not null,          -- opaque; minted by build_dataset.mint_pair_id
  annotator_id    uuid not null references auth.users(id) on delete cascade,

  -- ⚠️ POLARITY. true = the two images show the SAME character, matching
  -- VlmVerdict.same_character so a human label and a judge verdict share one
  -- serialization. The manuscript's positive class is `label = not
  -- same_character`, converted in build_dataset.build_records and NOWHERE else
  -- (annotation-surface.md §2.1). Do not invert here, in a view, or in the UI.
  same_character  boolean not null,

  -- Both GATE Attempt.passed in pipeline/consistency_check.py, so both are
  -- human-annotated rather than defaulted (judge-finetune.md §5.2, amended
  -- 2026-08-14). A judge trained to emit true unconditionally for either would
  -- break the control loop while scoring well.
  -- `default true` mirrors the VlmVerdict/ManifestRecord schema defaults: an
  -- unticked "problem" checkbox and an absent value both read "nothing wrong seen".
  anatomy_intact  boolean not null default true,
  text_free       boolean not null default true,

  failure_reasons text[] not null default '{}',
  created_at      timestamptz not null default now(),

  primary key (pair_id, annotator_id),

  -- The closed 7-item taxonomy (judge-finetune.md §4, contracts/story_memory.py
  -- FailureReason). Frozen permanently at 7 by ADR-028 — Objective 4's F1 is
  -- computed over this set. A DB constraint, not an app-level promise: an 8th
  -- value arriving mid-annotation invalidates every label already collected.
  -- `<@` also accepts '{}', which is the correct value for a `same_character`
  -- annotation.
  constraint annotations_failure_reasons_closed check (
    failure_reasons <@ array[
      'wrong_colour', 'wrong_species', 'wrong_body_feature', 'wrong_clothing',
      'wrong_style', 'different_face', 'character_absent'
    ]::text[]
  )
);

alter table annotations enable row level security;

-- ── RLS ──────────────────────────────────────────────────────────────────────
-- This policy pair IS the independence mechanism (CC-4): "two researchers label
-- independently" is a database rule here, not a promise. An annotator can never
-- read another annotator's row, so neither can the UI, so neither can they.
--
-- No UPDATE and no DELETE policy, deliberately. §4: submit is forward-only and a
-- submitted row is final for that annotator; adjudication is the only correction
-- path, not self-revision. The composite primary key makes a double-submit a
-- conflict rather than a duplicate row, and the client resolves it with
-- `on conflict do nothing` — first write wins, no UPDATE grant required.
--
-- Annotators are `researcher` profiles (0007's role check has no separate
-- 'annotator' value and profiles.role is the only role source — ADR-017).

create policy "annotators read own annotations"
  on annotations for select to authenticated
  using (auth_role() = 'researcher' and annotator_id = auth.uid());

create policy "annotators write own annotations"
  on annotations for insert to authenticated
  with check (auth_role() = 'researcher' and annotator_id = auth.uid());

-- NOT WRITTEN HERE: the adjudicator's read-all policy. §2.1 calls for "the
-- researcher role with the adjudicator flag", and no adjudicator flag exists —
-- profiles has no such column and 0007's role check is
-- ('teacher','student','researcher'). That is an open schema decision, logged as
-- D-L in docs/product/DECISION_BACKLOG.md. Until it is decided, `adjudicate/`
-- has no policy to run under and this migration grants no read-all to anyone.

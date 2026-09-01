-- 0018_annotation_rounds.sql
-- spec: docs/specs/annotation-surface.md §2.1, §4.1
-- consumer: backend/finetune/annotation_truth.py (_partition / is_adjudication are authoritative)
--
-- WHY THIS EXISTS
-- 0014 keyed annotations on (pair_id, annotator_id) because ADR-026 and this
-- spec described two independent researchers plus a third adjudicator. That
-- staffing never materialized: the capstone has exactly ONE rater, permanently
-- (settled 2026-07-29). Under the old key one human can produce at most one row
-- per pair, so `resolve_annotations` raised "Pair <id> has <2 ordinary
-- annotations" for every non-pilot pair, `build_dataset.build_records` raised
-- before emitting a single manifest record, and the whole
-- freeze -> train -> evaluate chain for Objective 4 was unreachable. This is a
-- schema hole, not a data problem — no amount of labelling fixes it.
--
-- THE FIX: intra-rater test-retest. The same human labels every pair twice,
-- cold, with a gap. `round` distinguishes the two passes, and the two rounds
-- become the two "ordinary" labels the existing consensus and adjudication
-- machinery already expects. The statistic this yields is intra-rater
-- (test-retest) agreement. Inter-rater kappa is UNDEFINED for this dataset and
-- stays undefined — a stated limitation, not pending work (annotation-surface.md
-- §4.1).
--
-- Round 3 is the adjudication slot. With one human, the spec's "a third
-- annotator adjudicates" can only mean the same human looking a third time,
-- knowing rounds 1 and 2 disagreed. It is a NEW row, never an edit of round 1
-- or 2, so §4's forward-only rule survives intact: rounds 1 and 2 remain in the
-- table exactly as submitted and stay the only evidence the agreement statistic
-- is computed from. Adjudication cannot retroactively inflate agreement.
--
-- A distinct adjudicator PROFILE (0016's `profiles.is_adjudicator`) still
-- overrides, at whatever round it is written. Neither mechanism replaces the
-- other; `annotation_truth.is_adjudication` ORs them.

alter table annotations
  add column round integer not null default 1;

-- 1 and 2 are the two test-retest passes; 3 is the adjudication slot. Nothing
-- above 3 has a meaning, and a 4th round would silently become a self-revision
-- path that §4 forbids — so the range is closed here rather than trusted to the
-- server action.
alter table annotations
  add constraint annotations_round_range check (round between 1 and 3);

-- The key change. Existing rows all defaulted to round 1, so this is
-- non-destructive: every pre-0018 row keeps its identity and remains its
-- annotator's round 1. `annotation_truth._round` reads a missing/NULL round as
-- 1 for the same reason.
alter table annotations
  drop constraint annotations_pkey;

alter table annotations
  add constraint annotations_pkey primary key (pair_id, annotator_id, round);

-- ── RLS is deliberately UNCHANGED ────────────────────────────────────────────
-- 0014's two policies ("annotators read own annotations", "annotators write own
-- annotations") and 0016's "adjudicators read all annotations" gate on
-- annotator_id = auth.uid() and on auth_role(), never on the key shape, so they
-- keep exactly their old meaning: an annotator still sees and inserts only their
-- OWN rows, across every round.
--
-- There is still NO update and NO delete policy, and that omission does more
-- work now than it did in 0014. Round 2 is the one place this design could
-- degenerate into the self-revision §4 forbids, and the absence of an update
-- grant is what stops it: a round-2 submit can only ever INSERT a new row
-- alongside round 1, and the client's `on conflict do nothing` still resolves a
-- double-submit of the SAME round as first-write-wins. Round 2 is a second
-- independent observation, not a back button.
--
-- What the database cannot enforce, and what is therefore process discipline
-- for whoever runs the labelling (recorded in annotation-surface.md §4.1
-- alongside the held-out "read once" rule): that round 2 is genuinely COLD —
-- run after a gap, with no memory of and no access to the round-1 answer. The
-- annotate surface never shows a submitted label back to the rater, which is the
-- most a schema can contribute; the elapsed gap itself is a calendar fact, not a
-- constraint.

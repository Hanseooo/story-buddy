-- Label audit queries — C3, run during adjudication, 2026-09-24
-- Read-only. Nothing here writes, and nothing here is part of the freeze path.
-- Tables are schema-qualified: the Supabase SQL editor does not always carry
-- public on the search_path, which reports as 42P01 "relation does not exist".
--
-- WHY: during adjudication several pairs turned up where BOTH raters answered
-- Different and the frozen rulebook says Same (clothing-only reasons; an
-- occluded character marked Character Absent). Pairs both raters agreed on
-- never reach the adjudicator, so those errors are invisible unless counted.
-- Q1 counts them. Q2 shows what reasons the agreed-Different pairs used.
-- Q3 says how much of the conflict queue is a real Same/Different split.

-- Q1 ─ agreed pairs: the split, and two suspect buckets
with lab as (
  select a.pair_id,
         count(distinct a.annotator_id)                                   as n,
         bool_and(a.same_character)                                       as all_same,
         bool_or(a.same_character)                                        as any_same,
         coalesce(array_agg(distinct r) filter (where r is not null), '{}') as rs
  from public.annotations a
  left join lateral unnest(a.failure_reasons) as r on true
  where a.round <= 2
  group by a.pair_id
)
select count(*)                                                       as agreed_total,
       count(*) filter (where all_same)                               as agreed_same,
       count(*) filter (where not all_same)                           as agreed_different,
       count(*) filter (where not all_same
              and rs <@ array['wrong_clothing','wrong_style']::text[]) as diff_presentation_only,
       count(*) filter (where not all_same
              and 'character_absent' = any(rs))                        as diff_character_absent
from lab
where n = 2 and all_same = any_same;

-- Q2 ─ which reason combinations the agreed-Different pairs used
with lab as (
  select a.pair_id,
         count(distinct a.annotator_id)                                   as n,
         bool_and(a.same_character)                                       as all_same,
         bool_or(a.same_character)                                        as any_same,
         coalesce(array_agg(distinct r) filter (where r is not null), '{}') as rs
  from public.annotations a
  left join lateral unnest(a.failure_reasons) as r on true
  where a.round <= 2
  group by a.pair_id
)
select rs as reason_set, count(*) as pairs
from lab
where n = 2 and all_same = any_same and not all_same
group by rs
order by pairs desc;

-- Q3 ─ what kind of conflicts are left in the queue
-- Mirrors isConsensus (frontend/app/(research)/_shared/validation.ts): a pair is
-- consensus only when label, reason set, anatomy and text all match. The four
-- columns partition the two-rater pairs, so the last one should equal the
-- 'complete' count and the first three should sum to the 'conflicted' count.
-- (The first version of Q3, run 2026-09-24, mislabelled agreed_different as
-- reason conflicts: it returned 112, which is Q1's agreed_different.)
with per_rater as (
  select a.pair_id, a.annotator_id, a.same_character, a.anatomy_intact, a.text_free,
         array(select distinct r from unnest(a.failure_reasons) as r order by r) as rs
  from public.annotations a
  where a.round <= 2
),
lab as (
  select pair_id,
         count(*)                       as n,
         count(distinct same_character) as labels,
         count(distinct rs)             as reason_sets,
         count(distinct anatomy_intact) as anatomy,
         count(distinct text_free)      as text
  from per_rater
  group by pair_id
)
select count(*) filter (where labels > 1)                               as label_conflicts,
       count(*) filter (where labels = 1 and reason_sets > 1)           as reason_conflicts,
       count(*) filter (where labels = 1 and reason_sets = 1
                          and (anatomy > 1 or text > 1))                as anatomy_or_text_conflicts,
       count(*) filter (where labels = 1 and reason_sets = 1
                          and anatomy = 1 and text = 1)                 as consensus
from lab
where n = 2;

-- Q4 ─ the agreed-Different pairs resting on clothing/style alone, one row each
-- These are Q1's diff_presentation_only. Step 3 of the rulebook calls every one a
-- mistake. status says whether the adjudication queue will already reach it.
with lab as (
  select a.pair_id,
         count(distinct a.annotator_id)                                   as n,
         bool_and(a.same_character)                                       as all_same,
         bool_or(a.same_character)                                        as any_same,
         coalesce(array_agg(distinct r) filter (where r is not null), '{}') as rs
  from public.annotations a
  left join lateral unnest(a.failure_reasons) as r on true
  where a.round <= 2
  group by a.pair_id
)
select p.id, p.split, p.status, lab.rs as reason_set
from lab
join public.research_pairs p on p.id = lab.pair_id
where lab.n = 2 and not lab.any_same
  and lab.rs <@ array['wrong_clothing','wrong_style']::text[]
order by p.split, p.id;

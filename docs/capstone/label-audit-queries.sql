-- Label audit queries — C3, run during adjudication, 2026-09-24
-- Read-only. Nothing here writes, and nothing here is part of the freeze path.
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
  from annotations a
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
  from annotations a
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
with lab as (
  select a.pair_id,
         count(distinct a.annotator_id) as n,
         bool_and(a.same_character)     as all_same,
         bool_or(a.same_character)      as any_same
  from annotations a
  where a.round <= 2
  group by a.pair_id
)
select count(*) filter (where all_same <> any_same)                 as label_conflicts,
       count(*) filter (where all_same = any_same and not all_same) as agreed_diff_reason_conflicts
from lab
where n = 2;

-- Label audit re-label — C3, 2026-09-24
-- The 10 pairs in AUDIT_PAIRS (backend/finetune/annotation_truth.py). Why these ten:
-- adjudication-notes-2026-09.md, "Label audit of agreed pairs".
-- Run the three steps in order. Only step 2 writes.

-- Step 1 ─ the images, and nothing else. The raters' labels are left out on purpose.
-- Open each path in Storage → private_assets. Judge by the rulebook as for any pair:
-- Same/Different, reasons if Different, Broken Anatomy, Text.
select p.id, p.canonical_storage_path, p.scene_storage_path
from public.research_pairs p
where p.id in ('0a7623239b552142','4bff6091f800f312','71e74774a21ee599','89ec648100898455',
               '9d9ae24e3523b38f','b3e1b5aa75025e83','b45bf1c8e0f07d9d','d552d7dad1711c20',
               'f01326c778127f66','ca57de2b96f78d37')
order by p.id;

-- Step 2 ─ one row per pair, filled in from step 1. Round 3 is the adjudication round.
-- same = true for Same. A Different needs at least one reason from the closed seven:
-- wrong_colour, wrong_species, wrong_body_feature, wrong_clothing, wrong_style,
-- different_face, character_absent. anatomy = false means Broken Anatomy. text = false means text on the page.
-- The subquery fails if there is not exactly one adjudicator, which is intended.
insert into public.annotations
  (pair_id, annotator_id, round, same_character, failure_reasons, anatomy_intact, text_free)
select v.pair_id, (select id from public.profiles where is_adjudicator), 3,
       v.same, v.reasons, v.anatomy, v.text
from (values
  --  pair_id              same   reasons                          anatomy text
  ('0a7623239b552142',     null::boolean, '{}'::text[],            true,   true),
  ('4bff6091f800f312',     null,  '{}',                            true,   true),
  ('71e74774a21ee599',     null,  '{}',                            true,   true),
  ('89ec648100898455',     null,  '{}',                            true,   true),
  ('9d9ae24e3523b38f',     null,  '{}',                            true,   true),
  ('b3e1b5aa75025e83',     null,  '{}',                            true,   true),
  ('b45bf1c8e0f07d9d',     null,  '{}',                            true,   true),
  ('d552d7dad1711c20',     null,  '{}',                            true,   true),
  ('f01326c778127f66',     null,  '{}',                            true,   true),
  ('ca57de2b96f78d37',     null,  '{}',                            true,   true)
) as v(pair_id, same, reasons, anatomy, text)
returning pair_id, same_character, failure_reasons, anatomy_intact, text_free;
-- The `null` in the same column is deliberate: same_character is NOT NULL, so the insert
-- fails until every row has been decided. Replace each null with true or false.

-- Step 3 ─ check. Expect 10 rows, every one with problem = null.
select a.pair_id, a.same_character, a.failure_reasons,
       case when not a.same_character and cardinality(a.failure_reasons) = 0
            then 'Different with no reason' end as problem
from public.annotations a
where a.round = 3
  and a.pair_id in ('0a7623239b552142','4bff6091f800f312','71e74774a21ee599','89ec648100898455',
                    '9d9ae24e3523b38f','b3e1b5aa75025e83','b45bf1c8e0f07d9d','d552d7dad1711c20',
                    'f01326c778127f66','ca57de2b96f78d37')
order by a.pair_id;

# 02 — Dataset page

Index: [../research-page-refresh.md](../research-page-refresh.md). Current code:
`frontend/app/(research)/research/(reference)/dataset/{page.tsx,data.ts,data.test.ts}`. Data:
`data/judge/freezes/obj4-v1/` (the registered freeze). Starting draft copy:
`evidence/audit-1-dataset.md` §(b) B1–B8. The draft must still satisfy SH-02: any sentence whose
fact is not in a tracked doc gets its runbook entry first.

**Verified on 2026-11-21:** every count on the current page matches the freeze, and the page's data
test passed 12/12. The problems are clarity, omissions and two wrong statements, not stale numbers.

## US-04 What a pair is

As a groupmate with no ML background, I want to know what one item of the dataset is, so that I can
describe the dataset correctly in the paper.

Applies: SH-02, SH-03, SH-09

- **AC-01** Before any table, the page defines a **pair**: one character's reference portrait plus
  one drawing of a book page where that character should appear.
- **AC-02** It says every drawing attempt counts as a page drawing, including rejected ones. A new
  fact, cited after its runbook entry: 422 of the 795 natural pairs use a second or later attempt.
- **AC-03** It says a page with two characters makes two pairs.
- **AC-04** It gives the totals: 899 pairs from 42 books, of which 795 are natural pairs (from the
  app, labelled by people) and 104 constructed pairs (made by a script).

## US-05 Same, Different, and who decided

As a groupmate, I want the labelling rules and the people behind each label, so that I can write
the Annotation Procedure and Criteria sections without contradicting the rulebook.

Applies: SH-02, SH-03, SH-09

- **AC-05** Same = species, face, body colours and countable body parts all match the reference.
  Pose, expression, clothing, art style and lighting may change. Different = at least one identity
  feature is wrong, or the character is absent, and it needs a ticked reason.
- **AC-06** Clothing or style alone is Same. This sentence is visible at phone width next to the
  reasons table that lists Wrong Clothing (12) and Wrong Style (4)
  (`evidence:audit-5-render.md#F5`).
- **AC-07** Who decided:
  - Two group members labelled all 795 natural pairs independently, seeing only the two pictures.
  - The study owner settled the 172 pairs whose labels differed on any field, 85 of them on
    Same/Different. The owner could see which rater gave which label.
  - The owner also relabelled 10 pairs with AI assistance, as a reported deviation.
  - Constructed pairs were not labelled by anyone.

  The 172, 85 and visibility facts need a runbook entry first.
- **AC-08** The sentence "No test label changed" is replaced with: the AI-assisted review changed no
  test label, and ordinary adjudication settled conflicted test pairs as it did every split. New
  fact, after its runbook entry: 23 final labels differ from both raters' first answer, 13 of them
  from ordinary adjudication.
- **AC-09 (D-12)** The page states, as known errors kept because the freeze is registered: 9 final
  labels are Different with only Wrong Clothing or Wrong Style ticked (train 6, validation 1, test
  2). This needs a runbook entry and a changelog row first.

## US-27 Why the team built its own labelling tool

As a groupmate writing the Annotation Procedure, I want the reason the team built its own labelling
tool instead of using spreadsheets or an off-the-shelf tool, so that I can justify it in the paper.

Applies: SH-02, SH-03

- **AC-26** A short section next to US-05 gives the reasons in plain words.
  - Owner-stated (D-24):
    - It saves time.
    - Both raters can label in parallel.
    - Every label saves to the cloud as it is made.
    - It is easy for teammates to use.
  - Documented in ADR-026 and `docs/specs/annotation-surface.md`:
    - The images stay in a private bucket and are opened only through short-lived signed links.
    - No training data sits on a shared lab PC.
    - Independent labelling is enforced by database rules: a rater cannot see the other rater's
      labels.
- **AC-27** The owner-stated reasons are first written into a tracked doc (`annotation-surface.md`,
  a rationale section) so the page test can pin them (SH-02).
- **AC-28** The section links to the existing public labelling demo (`docs/specs/research-labelling-demo.md`)
  if it is reachable without sign-in. Otherwise it shows the existing synthetic demo screenshots.
  Implementer to verify which.

## US-06 One real record

As a groupmate, I want to see one actual record with each field explained, so that I know what the
data looks like.

Applies: SH-01, SH-02, SH-03

- **AC-10** The page shows validation row `033b8372e89e4c06` from `manifest.val.jsonl` verbatim,
  with long values shortened by "…" only. It is a synthetic validation row, so it is allowed under
  SH-01.
- **AC-11** A field table explains every field. It must state that `label` is the opposite of
  `same_character` (`true` = Different, the class the judge is scored on), and that
  `differences_observed` is written by a script, not by a rater, and does not describe the picture.
- **AC-12** The data test reads the row from `manifest.val.jsonl` and fails if the shown JSON
  differs.

## US-07 How the splits were made, and why

As a groupmate, I want the split decisions and their reasons, so that I can write Dataset Division
and answer a panel question about leakage.

Applies: SH-02, SH-03, SH-09

- **AC-13** Splits are by story, assigned when each story was entered. No story or character is in
  two splits, so the judge is tested on characters it never saw.
- **AC-14** Train has 24 synthetic stories and validation has 6, with 8 train and 2 validation
  stories per art style. The held-out test set is every donated story that finished: 12 of 15, with
  the 3 failures replaced by same-style backups.
- **AC-15** Why donated stories are test only: there are too few donated characters to spare for
  training, and testing on them measures real children's writing (external validity).
- **AC-16** Constructed pairs are in train only. There was no class balancing, so validation has
  only 4 Different pairs and every checkpoint choice rests on them.
- **AC-17** Where the repo has no reason, the page says "Reason not recorded": why syn-025–syn-030
  became validation, and why validation is 6 stories. It invents none.
- **AC-18** Constructed pairs are described as 14 hand-picked character matches of the same species
  and art style, 12 of them human with human. Not "chosen to maximize similarity": no code does
  that (`evidence:audit-1-dataset.md` B5).

## US-08 The whole process

As a groupmate, I want the process from story to test in order, so that I can explain it in one
paragraph or one figure.

Applies: SH-03, SH-06

- **AC-19** A numbered list of ten steps near the top: story → generated book → pairs → two raters →
  adjudication → freeze → splits → training → checkpoint choice → one read of the held-out test.
  Draft in `evidence:audit-1-dataset.md` B6.
- **AC-20** The dataset-flow diagram (US-21) sits beside the list, with its PNG download (SH-06).

## US-09 Corrections

As the owner, I want the page's wrong statements fixed, so that groupmates don't copy them into the
paper.

Applies: SH-02, SH-09

- **AC-21 (D-12)** The human/non-human table counts by species. Train becomes 12 human and 32
  non-human characters (178 and 306 pairs); validation is unchanged. A note says the earlier table
  matched names to the intake roster and counted 7 animals or machines as human. This needs a
  runbook entry and a changelog row first. Recount script: `evidence/kinds.py`.
- **AC-22** The "other 795 pairs" sentence (`page.tsx:147`) states one base only. 104 of train's 157
  Different pairs are constructed and the other 53 come from the app. Separately, 795 of all 899
  pairs come from the app.
- **AC-23** The sentence "Character kind follows the intake-declared non-human roster…"
  (`page.tsx:156-160`) is rewritten in plain words or removed by AC-21.
- **AC-24** One vocabulary (SH-09): "natural pair", not "pipeline pair"; "study owner" throughout.
  "Freeze", "registered", "held-out" and "seed" are defined where first used.
- **AC-25** `data.test.ts` checks the split totals against the runbook table, not against numbers
  typed into the test.

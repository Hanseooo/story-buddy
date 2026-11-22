# 10 — New diagrams: IPO, dataset flow, student and teacher journeys

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** Four new `.drawio.svg` figures exist with their sources noted.
**Source criteria:** US-21 AC-04, AC-05; SH-06
**Scope:** IPO model, dataset build and annotation flow, student journey, teacher journey, in `docs/diagrams/drawio/`. Nothing in D-13's excluded list.
**Out of scope:** Placing them on pages (06, 12, 15). PNG (11).
**Complexity:** Medium — four hand-authored figures
**Blast radius:** Local — new files
**Unblocks:** 06, 11, 12

## Context
Source files per diagram: `evidence/audit-4-diagrams.md` §(b).

## Read first
- `evidence/audit-4-diagrams.md` §(b)
- `docs/specs/research-page-refresh/02-dataset.md` US-08 — the ten steps the flow must match
- `docs/capstone/group-guide.md` §3 — the user journeys

## Behavior this changes
None

## Acceptance criteria
- [x] Four files, each with a source note inside
- [x] The dataset flow matches US-08's ten steps
- [x] No excluded diagram is created
- [x] The shared rules listed under the source stories hold (index §2)

## Guidance
Same tooling note as 09.

## Verification
Decode and render each in Chromium.
**Full suite:** not needed

## Blocked by
None

## Answer

Four figures added in `docs/diagrams/drawio/`: `ipo_model.drawio.svg`, `dataset_build_and_annotation_flow.drawio.svg`, `student_journey.drawio.svg`, `teacher_journey.drawio.svg`. Each has a source note inside (files read, date 2026-11-21). Each decodes with `decode.py` and rendered in Chromium without overlaps. No excluded diagram was created.

- The dataset flow uses US-08 AC-19's ten steps, in its order. `audit-1-dataset.md` B6 differs (it has "Constructed pairs" as step 6 and no "Splits" step). AC-19 governs. Constructed pairs sit in step 6 (`build_dataset.constructed_records`) and the splits in step 7.
- Contradiction, code over docs: US-21 AC-04 lists "PDF" in the teacher journey. `backend/app/pdf_export.py` serves only active students (a non-student gets 404) and only approved books. The teacher journey shows approval unlocking the student PDF, and the student journey shows Download PDF.
- `docs/capstone/group-guide.md` section 3 describes the pipeline, not user journeys. The journeys come from code and `docs/specs/USER_FLOW.md`.
- The reveal button reads "Redraw <name>" in the UI (API action `try_again`), so the diagrams say Redraw.
- Teacher review is a global flag (`enable_teacher_moderation_review`, default true), not a classroom setting. Classroom settings hold only review themes and notes for students.

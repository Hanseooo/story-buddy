# 03 — Any researcher can open failed and unapproved runs

**Status:** ready-for-agent
**Type:** task
**Progress:** implemented; signed-in browser verification pending
**Blocked by:** None
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md) US-07
**What to build:** A signed-in researcher who is not the adjudicator sees titles for every run in
`/research/metrics`, can open failed, complete-but-unapproved, in-progress and approved runs, and
`GET /research/runs/{job_id}` returns 200 for all of them.
**Source criteria:** AC-16; ADR-079 decisions 1–5; research-run-browser §§2, 4, 5.1, 5.4, 6, 8.
**Scope:** Backend access rule in `get_run`; frontend `canOpenRun`/`hideTitles`; remove the
`not_approved` forbidden state and its copy from the detail page and `loadRun`; Langfuse control
eligibility follows `canOpenRun`; access tests; spec status line and `CHANGELOG.md`.
**Out of scope:** Teacher release, resume or moderation authority (05–15); new logging or
historical classifier fields (ADR-079 decision 3); RLS changes; #111 demo mode.
**Complexity:** Low — one predicate on each side plus removing one forbidden branch.
**Blast radius:** Shared — research list, detail page, Langfuse button and the backend route.
Widens who sees unapproved child-derived content (ADR-079 consequences).
**Unblocks:** None

## Context

ADR-079 (accepted 2026-10-26) replaces ADR-064's adjudicator-only exception with a researcher-role
rule so researchers can investigate moderation failures such as run `314fafc9`. The spec amendment
is written; the code still enforces ADR-064.

## Read first

- `docs/product/adr/ADR-079-researchers-can-inspect-failed-and-unapproved-runs.md` — the rule and its exclusions.
- `docs/specs/research-run-browser.md` §2, §5.1, §8 — access table, error contract, required tests.
- `backend/app/research.py` — `get_run`: the `not_approved` check and its ADR-064 comment.
- `frontend/app/(research)/_shared/viewer.ts` — `canOpenRun`, `hideTitles`.
- `frontend/app/(research)/research/metrics/page.tsx` — the "Not approved yet" lock in the list.
- `frontend/app/(research)/research/metrics/[jobId]/loadRun.ts` and `page.tsx` — `not_approved` reason and copy.

## Behavior this changes

- `backend/tests/test_research_runs.py::test_annotator_cannot_open_an_unapproved_run` asserts 403
  `not_approved`. ADR-079 decision 1 overturns it: the annotator now gets 200.
- `frontend/app/(research)/_shared/viewer.test.ts` `canOpenRun` table expects `false` for an
  annotator on an unapproved run; now `true`.
- Detail `page.test.tsx`/`loadRun.test.ts` cases for `not_approved`, if present, are replaced, not deleted
  without a replacement assertion.

## Acceptance criteria

- [ ] An ordinary researcher receives 200 from `GET /research/runs/{job_id}` on failed,
      complete-but-unapproved, in-progress and approved jobs; the adjudicator keeps the same access.
- [ ] Signed out stays 401, teacher/student stay 403 `researchers_only`, unknown job 404, non-UUID
      422, on direct backend requests.
- [ ] No response contains `input.raw_text`, `jobs.input_text`, `profile_id` or `classroom_id`
      (sentinel string check). `get_signed_url` default stays 300.
- [ ] The list shows titles and run links to every researcher; no approval lock or "Not approved
      yet" message for them. Signed-out and other roles keep their restrictions.
- [ ] Langfuse controls render (flag on) for any researcher who can open the run; none for others.
- [ ] Existing loading, empty, missing-data, error, keyboard and focus states still work.
- [ ] research-run-browser access-amendment line and `CHANGELOG.md` updated to say it is built.

## Guidance

Suggestion: `canOpenRun` becomes `viewer?.role === "researcher"`; keep its `job` parameter only if
a caller still needs it, else remove the orphan. Keep the backend and frontend rules independent:
the frontend helper decides rendering only.

## Verification

Precedent: `test_research_runs.py` `_get_as(ANNOTATOR, …)`; `viewer.test.ts`.
Main journey: as an ordinary researcher, open a failed synthetic run from a filtered list and return
to the filtered list, in a browser at desktop and phone width, clean console. Owner signs in; stop at
the login wall. Failure check: a teacher's direct backend request still gets 403.
**Targeted:** `cd backend && uv run pytest tests/test_research_runs.py`; `cd frontend && pnpm test "app/(research)"`
**Full suite:** required now (Shared): `uv run ruff check . && uv run pytest`; `pnpm lint && pnpm build && pnpm test`.

## Blocked by

None.

## Comments

Implemented 2026-10-26. Backend route/projection tests pass (28), and targeted frontend
helper/list/detail tests pass (36). The access regressions were observed red before the fix.
See `CHANGELOG.md` for full-suite evidence and the local WeasyPrint DLL blocker.
The ordinary-researcher desktop/phone browser journey remains unverified.

# 04 — "Draw again" is undoable: other versions of a character at the reveal

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Blocked by:** None

**Parent:** `docs/specs/magic-pencil.md` (US-01)
**What to build:** On a job submitted with the new setting on in `teacher_review_v1`, after a child taps
"Draw again", "Meet your characters" shows "Other versions" for that character. It lists the pictures
that were replaced. Picking one makes it the reference again at no image or go cost.
**Source criteria:** US-01 / AC-01, AC-02 (earlier pictures; flagged or withdrawn never offered), AC-04,
AC-05; SH-01, SH-07, SH-08; OD-02, OD-04, OD-05; edge rows "Draw again replaces a picture the child
liked", "An earlier picture was flagged or withdrawn", "Setting turned off after submission",
"Job submitted in baseline moderation mode", "Character accepted on its first draw", "Story deleted"
**Scope:** the new setting and its per-job snapshot; the OD-04 job-owned table (versions and, for
later tickets, pencil-use rows) with RLS and cascade delete; recording a replaced reference as a
version; the reveal payload's `versions`; a choose-version request at the reveal; guarded delivery
of version images; the process page "Other versions" control with all SH-07 states
**Out of scope:** unchosen first-round draws and on-open moderation (05); the pencil (06); page
versions (09)
**Complexity:** High — a version choice must change the paused checkpoint's reference through a
resume, stay inside the recursion bounds and keep the delivery guard exact
**Blast radius:** Shared — graph resume path, `authorized_asset`, the reveal projection read by the
process page, `signPaths`, a schema migration
**Unblocks:** 05, 06, 09

## Context
ADR-082 Decisions 1 and 6. This is the enabling slice: it owns the setting, the table and version
delivery that 05–11 reuse. OD-04 approved the table; follow `0022_teacher_moderation_hold.sql`'s
pattern (service-role only, `on delete cascade` from `jobs`).

## Read first
- `backend/app/main.py` — `create_storybook` (`review_mode` snapshot), `confirm_job`, `ConfirmRequest`
- `backend/app/moderation_hold.py` — `confirm_review_job`, `authorized_asset`, `job_image`
- `backend/pipeline/reveal.py` — `_project_reveal`, `reveal` (resume payload handling)
- `backend/pipeline/graph.py` — `route_reveal`; `backend/app/config.py` — `RECURSION_LIMIT`, `TEACHER_REVIEW_RECURSION_LIMIT`
- `backend/pipeline/char_bible.py` — `_mint_targeted` (the overwrite that now must record the old picture)
- `frontend/app/s/[profileId]/process/[jobId]/page.tsx` — reveal render, `handleConfirm`; `frontend/lib/signedUrls.ts` — `signPaths`
- `supabase/migrations/0022_teacher_moderation_hold.sql` — RLS, storage policy, cascade pattern

## Behavior this changes
- `_mint_targeted` keeps overwriting, but the replaced path is now a version (AC-02, OD-02).
- `ConfirmRequest.action` gains a version choice; `confirm_review_job` validates it against the
  stored reveal. Existing confirm/try-again tests in `test_main.py` / `test_teacher_hold.py` stay green.

## Acceptance criteria
- [ ] Setting off at submission, or job in baseline mode: the reveal payload has no versions and the
      page shows no new control, even if the setting is later turned on (SH-01).
- [ ] First-draw accept: no "Other versions" control at all (AC-01, AC-05).
- [ ] After "Draw again": the earlier picture is offered; choosing it restores it as the reference;
      `image_count` and `ref_retry_count` unchanged (AC-04, AC-05).
- [ ] A picture that was flagged, or whose teacher clearance was withdrawn, is never offered (AC-02).
- [ ] The request carries the source picture; a stale source is rejected, nothing changes; a double
      submit changes state once (SH-08).
- [ ] Version images are served only through the guarded product route; no browser can name a path.
- [ ] UI: loading, error, empty, disabled states; focus moves into the list and returns to its
      opener on Escape/Cancel; Enter chooses; accessible names include the character name (SH-07).
- [ ] Deleting the story deletes the version rows (AC-22, cascade).

## Guidance
Suggestion: snapshot the setting into `jobs.moderation_settings_snapshot` instead of a new column;
`create_storybook` already writes it. Trap: `authorized_asset` resolves `ref-<char_id>` to the
current reference only, and `signPaths` derives asset ids from `reveal.characters`; versions need
their own asset ids. *Inferred, check it:* LangGraph counts recursion per invocation, so a
choose-version resume adds steps only inside that run.

## Verification
Pure projection test of `_project_reveal` versions; API tests with providers mocked; vitest on the
process page; a `playwright-cli` pass on a seeded synthetic classroom (no project E2E runner).
**Targeted:** `cd backend && uv run pytest tests/test_reveal_node.py tests/test_main.py tests/test_teacher_hold.py tests/test_graph.py tests/test_rls_isolation.py` · `cd frontend && pnpm exec vitest run "app/s/[profileId]/process/[jobId]/page.test.tsx" lib/signedUrls.test.ts`
**Full suite:** required now (Shared): backend and frontend pre-merge verify

## Blocked by
None.

## Comments

## Answer (2026-11-01)

Done behind the new off-by-default `ENABLE_MAGIC_PENCIL`, snapshotted as
`moderation_settings_snapshot.magic_pencil` next to `review_mode` (before redaction, so a mid-request
switch-off cannot downgrade the job). It reaches `ModerationContext.magic_pencil`; `has_versions`
also requires `teacher_review_v1`.

- **State is the source of truth.** A "Draw again" on a feature job keeps the replaced, cleared
  reference as a `Character.versions` entry with its status and verdict (`char_bible._kept`).
- **Choosing** is a `choose_version` resume carrying `char_id`, `version_id` and `source` (the
  current picture). `confirm_review_job` rejects anything not offered in `jobs.reveal` with 422
  `choice_unavailable`; baseline `confirm_job` always rejects it; the status CAS dedupes a double
  submit. `reveal` records a `ReferenceChoice`, `route_reveal` sends it to `char_bible`, which swaps
  with no draw, no judge and no cost change and re-checks the source against the checkpoint. The
  displaced picture becomes a version. `char_ref_mod` passes the cleared picture and the run pauses
  at `reveal` again (graph test proves it inside the recursion bound).
- **Delivery:** `authorized_asset` serves `version-<version_id>` only to the author, on an
  `awaiting_confirm` feature job, for a cleared version. `signPaths` maps version paths to that id.
- **Record:** `0027_job_picture_records.sql` (OD-04: service-role only, RLS on, cascade from `jobs`),
  written by the worker with the reveal; `kind` allows only `version` until 06 adds pencil rows.
- **UI:** "Other versions" under each character with versions; absent when there are none (AC-05
  read over SH-07's "empty state"). Loading, error with retry, disabled while a request runs,
  "Changing your picture…", focus into the list group and back to the opener on Escape/Cancel,
  names with the character name. Enter is the native button press.

Checks: node tests (reveal, char_bible), graph tests, `test_main` baseline 422, and one Postgres
integration run (tap → version offered and served → stale and unknown choices 422 → double submit
enqueues once → restored, no draw, `image_count`/`ref_retry_count` unchanged → cascade delete).
Each guard was broken on purpose and the test went red, except the cleared-status check on version
assets, which no reachable state exercises. Full suites: backend 1633 passed, 6 failed
(`test_pdf_export`, identical on a clean `HEAD`, local PDF `OSError`); frontend lint, build, 771 tests pass.

Not done or not verified:
- **No `playwright-cli` pass.** It needs a signed-in synthetic child (login wall) and real draws.
- `test_rls_isolation` skipped (no `SUPABASE_DB_URL`); the new table is not in it.
- **Owner decision:** a teacher cannot withdraw a `teacher_allowed` picture once it is a version
  (`teacher_withdraw` accepts only the current reference), yet it is still offered. Before this
  ticket the picture was simply gone. Restoring it makes it current and withdrawable again.
- A teacher `replace_reference` keeps no version: what it replaces is flagged, so never offerable.
- Focus lands on the list group, not its first picture: pictures stay disabled until loaded.

# 04 — "Draw again" is undoable: other versions of a character at the reveal

**Status:** ready-for-agent
**Type:** task
**Progress:** open
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

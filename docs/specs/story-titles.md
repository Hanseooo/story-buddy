# Feature Spec — Story titles end to end

**Status:** implemented 2026-09-10; backend slice and frontend surfaces are built and verified.
**Owner:** story submission, job metadata, and existing child/teacher book surfaces.
**Derived from:** [MASTER_SPEC](../MASTER_SPEC.md) §5, [DESIGN](../../DESIGN.md),
[book persistence](kid-flow-book-persistence.md), [classroom sharing](classroom-sharing.md).

## 1. Purpose and accepted decisions

Children name their books and recognize them consistently wherever books appear.
The title is required for new submissions, limited to 80 characters independently of
the story word count, and fixed once submitted. It names the book only: it does not
provide characters, events, captions, or instructions to the illustration pipeline.
Titles receive safety and privacy checks. Existing untitled books retain their
story-excerpt label. No generated titles, rename flow, new cover image, or export work.

This is a feature across existing surfaces, not a new pipeline node. This document
owns title behavior; [failure recovery](story-failure-recovery-ux.md) owns explanations
and [character review](character-review-ux.md) owns redraw interactions.

## 2. Current integration points and decision gate

Observed 2026-09-10:

- `backend/app/main.py`: `CreateStorybookRequest` accepts `text`, required `title`, optional
  `title_ack`, and `style_preset_id`. `create_storybook` checks the title synchronously, writes
  its checked value with `input_text`, and then enqueues the job.
- `backend/worker/run_job.py`: `run_storybook_job` reads that text and constructs
  `StoryMemory.input`. `backend/pipeline/input_gate.py` performs pipeline redaction.
- `frontend/app/s/[profileId]/write/page.tsx`: visible title field, validation, style-aware
  `sb.prefill` restore, and redaction-confirmation round trip.
- `frontend/lib/displayTitle.ts`: shared stored-title/first-line/60-character/`Untitled`
  presentation fallback used by every title surface.
- `frontend/app/s/[profileId]/page.tsx`, `frontend/app/s/[profileId]/gallery/page.tsx`,
  child process/reader pages, and `frontend/app/classroom/[classroomId]/books/page.tsx` render
  the title from their existing job projections.
- `frontend/lib/useJob.ts`, `frontend/lib/types/jobs.ts`, and
  `frontend/components/FailureScreen.tsx` carry title/style through retry and revision recovery.

**Architecture decision:** ADR-059 accepts a nullable `jobs.title` for legacy rows and a required
`CreateStorybookRequest.title` for new submissions, with `MAX_TITLE_CHARS = 80` in
`backend/app/config.py`. The backend checks and redacts titles synchronously before persistence,
uses `title_ack` for an explicit privacy-replacement confirmation, and keeps the title as job
metadata outside generation inputs. No title field is added to `backend/contracts/`.

The current raw-story write preceding pipeline redaction remains a separate conflict
with CC-2, not a pattern to copy for titles. ADR-059 bounds the title path without authorizing
a broader privacy refactor.
No migration, policy change, provider call, or contract edit is made by this spec.

## 3. Writing and validation

One page contains a visible **Story title** label and single-line native input above
the existing story textarea, followed by the existing style picker and submit action.
Children may fill either field first. Use a separate `n / 80` title counter and keep
the story word counter unchanged.

Proposed validation details for written review:

- Trim outer whitespace, preserve interior spacing and case, and reject line breaks.
  Count Unicode code points consistently in client and server, not UTF-16 units.
  Compound emoji may count as multiple characters; no new counting dependency.
- Require 1–80 characters after trimming. Accept duplicate titles, Filipino/Taglish,
  punctuation, and emoji. Titles are not unique keys or filenames.
- Do not silently truncate pasted input. Show “Keep your title to 80 characters.”
  An empty/whitespace-only submission shows “Give your story a title.”
- On invalid submission, prevent the request, focus the first invalid field, and
  retain title, story, and selected style. Associate errors with their fields.
- On a request failure, retain all entered values and offer retry. A transport error
  is not evidence that the title failed moderation. Do not claim a job never started
  when the response was lost. Do not automatically send another paid submission.
- Enter in the title moves focus to the story; Enter in the textarea adds a newline.
  The explicit submit button starts submission. Disable duplicate submits while pending.
- Keep an in-app bookshelf exit. Do not introduce persistent draft autosave in this feature.

## 4. Safety, persistence, and lifecycle requirements

Title and story remain separate. Never prepend the title to narrative text passed to
analysis, segmentation, prompts, judges, or captions. The title does not affect scene
count, story word bounds, or image budget.

Apply existing safety/privacy policy through the provider seam, including ADR-045's
structured-identifier redaction policy. Do not introduce a new moderation model.
Unchecked titles must not reach shared cards, logs, traces, queue payloads, or durable
storage. A privacy-check failure must not fall back to storing the raw title.
Render titles as text, never HTML. Do not log request values in validation errors.

The finalized stored title is the checked/redacted version. Explain any privacy
replacement before the child commits a submission; if it becomes empty or exceeds
the limit, ask for a different title without discarding the story. The architecture
decision must satisfy this interaction without creating a silent post-submit rename.

Once accepted, the same finalized title appears during processing, character review,
failure, completion, and sharing. No child or teacher rename endpoint or control.
Immutability must be enforced at authorized write boundaries, not only by hiding UI.
Do not allow a client to bypass checks through a direct metadata update.

**Make the story again** creates a new job with the finalized title, story, and style.
**Change my words** opens a new-submission form with those three values editable.
It never edits the previous job. Use one revision payload, preserve safe values if
navigation fails, and do not silently navigate to an empty form when transfer storage
is unavailable. Provide an inline recovery message and keep the source view available.

An old untitled job remains valid to read and resume. A new submission made from it
requires a title: open the form with the legacy excerpt prefilled as an editable
suggestion and retain story/style. The child explicitly submits it through the same
checks. Do not bypass required validation or backfill existing rows.

## 5. Display contract

Use one shared display rule across the existing consumers: nonblank stored title,
otherwise the existing first-line/60-character excerpt, otherwise `Untitled`.
The fallback is presentation only, never a migration or inferred authored title.
For legacy shared books, compute the excerpt only from text already authorized for
that viewer and permitted by existing privacy policy; do not broaden access to raw
story text merely to populate a card. Resolve unsafe legacy data in the architecture
session rather than assuming old rows were redacted. The shared classroom gallery spans every
classmate's approved book, so no excerpt is authorized there: it selects `title` alone and a
legacy untitled book reads `Untitled`. Do not re-add `input_text` to that query.

| Surface | Required display |
|---|---|
| Child bookshelf | Title above secondary status, across queued, paused, failed, and complete books |
| Shared classroom gallery | Title plus existing author identity and cover |
| Teacher book review | Title in pending, approved, rejected, and failed lists and preview |
| Child processing/reveal | Book title as context without competing with the current action |
| Reader, including shared reader | Full title as the book heading, existing captions unchanged |
| Failure/revision | Checked title identifies the failed book and survives recovery |

Cards allow two lines and visually truncate overflow; accessible link names retain
the full display label. Reader headings wrap long unbroken text without horizontal
overflow. Duplicate titles stay distinguishable by existing author/status/cover context.
Do not render the title into generated artwork or create an extra story page.
Missing covers retain a title-bearing placeholder. Loading skeletons reserve title
space; failed reads must not masquerade as an empty library.

## 6. Cross-cutting checklist

- [x] CC-1: titles checked without bypassing existing image gates.
- [x] CC-2: redaction before persistence/display; legacy safety is an explicit gate.
- [x] CC-3: explicit new-job retries, no title generation or extra image call.
- [x] CC-4: existing classroom isolation and signed assets; immutable metadata enforcement.
- [x] CC-5: validation outcomes/counts only, no title text in diagnostics.
- [x] CC-6: native labeled controls, keyboard flow, visible focus, 44px targets, 200% zoom.
- [x] CC-8: existing DESIGN.md tokens and child/teacher typography.
- [x] CC-9: retained form state and actionable errors.
- [x] CC-10: existing untitled jobs resume; titles survive new-job recovery.
- CC-7: no change to generation seed or research instruments.

## 7. Verification and completion

Extend existing `write/page.test.tsx`, `FailureScreen.test.tsx`, gallery/process/reader
tests, `backend/tests/test_main.py`, and worker tests after the architecture is accepted.
Use existing fixtures and mock only network/provider boundaries. First demonstrate
failure for changed behavior. Cover at most one main path and one critical failure
path per changed behavior, using parameterized boundary cases where appropriate:

- title submission, checked persistence, and consistent rendering through completion;
- empty/81-character input rejected without loss, 80 accepted, Unicode count parity;
- title-only visual details never enter generation inputs;
- unsafe/private title cannot leak or bypass validation through retry/direct writes;
- legacy read/resume and explicit titled resubmission;
- revision/retry retains title/story/style, including storage/network failure;
- full title accessible when card text is clipped.

Manual QA: mobile width and 200% zoom, keyboard-only writing, long titles, duplicate
titles, safe legacy fallback, teacher review and classroom sharing. Fuzzy safety
quality remains offline evaluation, not deterministic CI or a new research claim.

Before marking built, update affected existing submission/persistence/moderation,
sharing, teacher review, and reader specs to link to this title contract. Search root
repository consumers excluding `.worktrees/` and secret files. Do not leave competing
title rules. Run from `frontend/`: `pnpm lint`, `pnpm build`, `pnpm test`; from
`backend/`: `uv run ruff check .`, `uv run pytest`. Apply and verify the accepted
migration explicitly in the intended environment; migration files are not self-applying.

**Next gate:** manual frontend QA — mobile/zoom, keyboard flow, duplicate titles, and legacy
shared books. `0019_jobs_title.sql` was applied to the Supabase environment on 2026-09-10.

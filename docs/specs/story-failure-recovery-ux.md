# Feature Spec — Specific, safe story failure recovery

**Status:** §3's copy table implemented 2026-09-09 with story-only wording; §4, §5 and §6 are
unchanged as written. Product direction approved 2026-09-09.
**Owner:** existing child failure screens and teacher failed-book cards.
**Derived from:** [failure diagnostics](failure-diagnostics.md),
[failure semantics](kid-flow-failure-semantics.md),
[ADR-038](../product/adr/ADR-038-safe-failure-diagnostics-one-fixed-reason-taxonomy-for.md),
[DESIGN](../../DESIGN.md).

## 1. Purpose and scope

Explain whether submitted text, a generated character picture, a generated scene
picture, or a technical problem stopped the book. Give a safe explanation and an
honest next action. Do not blame the child for a generated picture or imply that
retrying repairs only the failed stage.

This is a presentation/recovery amendment to `failure-diagnostics.md`, not another
taxonomy or classifier. Its accepted reason contract remains authoritative. On
approval, this spec owns the revised copy/action rules below. The diagnostics spec
must point here when implementation lands instead of maintaining a second copy table.

Out: moderation categories/flagged spans, raw errors, provider names, partial books,
automatic paid retries, new support tools, heartbeats, or inferred crash detection.

## 2. Current path and contract

`backend/worker/failure_classifier.py:classify_failure_reason` already maps exact
sentinels and known exception types to ADR-038 reasons. Worker run/resume terminal
handlers persist `jobs.failure_reason`. `frontend/lib/useJob.ts` supplies it to
process and reader pages, which render `frontend/components/FailureScreen.tsx`.
`frontend/app/classroom/[classroomId]/books/page.tsx` shows teacher failure labels.

Keep the existing values: `child_text`, `character_safety`, `scene_safety`,
`service_busy`, `service_limit`, `book_limit`, `worker_stopped`, `system_error`.
Null, legacy `machine`, and unknown values use the system fallback. No schema,
pipeline, exception contract, or provider change is required by this spec.

The user's report of generic errors does not establish a production classification
bug. Before changing backend classification, reproduce with a sanitized job reason
and known failure path. Never infer cause from `current_stage` or arbitrary exception
prose. A separately evidenced classifier fix must retain ADR-038's contract.

## 3. Child copy and actions

Each failure screen has a cause heading, short explanation, primary action when
available, **Back to bookshelf**, and the existing copyable story reference.
The checked book title is context once [story titles](story-titles.md) ships.

| Reason | Heading / explanation | Primary action |
|---|---|---|
| `child_text` | “Some words need changing.” / “Your title or story didn't pass our safety check. You can change your words and try again.” | Change my words |
| `character_safety` | “We couldn't use a character picture.” / “A character picture we made didn't pass our safety check. Your story's words passed.” | Make the story again |
| `scene_safety` | “We couldn't use a story picture.” / “A picture we made for your story didn't pass our safety check. Your story's words passed.” | Make the story again |
| `service_busy` | “The story maker couldn't finish right now.” / “A service we need was busy or unavailable. You can try making your book again.” | Make the story again |
| `worker_stopped` | “The story maker stopped before finishing.” / “You can try making your book again.” | Make the story again |
| `service_limit` | “The story-making allowance has run out.” / “Show your teacher this story reference for help.” | No paid retry; teacher guidance |
| `book_limit` | “This book reached its picture-making limit.” / “Show your teacher this story reference for help.” | No paid retry; teacher guidance |
| `system_error` | “Something went wrong while making your book.” / “We couldn't finish it this time. You can try making it again.” | Make the story again |

Until titles ship, `child_text` says “Your story didn't pass our safety check.” The
title release changes that sentence atomically with its validation path. Do not claim
which field was blocked when the safe reason cannot distinguish them. Form-level
validation may identify a title field only when its trusted result actually does so.

The image-safety reassurance states that story text passed the input check, not that
it is universally safe or that the image checker is infallible. Never show the blocked
image, name a sensitive category, or suggest wording to evade moderation.

Every new-job action has adjacent text: **“This starts the whole book again. The
pictures may look different.”** It appears before activation, not after payment.
Teacher-help text is guidance, not a button that pretends to contact a teacher.

## 4. Recovery behavior and edge cases

- Reuse explicit submission and the existing failure-chain/off-ramp policy. No new
  cross-run counter. A paid retry requires a deliberate click and creates a new job.
- Preserve story/style and, when available, the immutable checked title. Titleless
  legacy retry behavior belongs to `story-titles.md`: open the prefilled form and
  obtain a title before submitting. Do not add a bypass here.
- **Change my words** edits a new submission, leaving the failed job untouched.
  **Write something new** remains an available secondary route under existing rules.
- Pending submission disables competing submit controls and announces “Starting your
  book again…” On HTTP or network failure, remain on the screen with retained values
  and an inline alert. Never automatically replay an ambiguous request.
- Keep the complete job ID copyable with an abbreviated visible reference. Announce
  clipboard failure honestly; do not display “Copied” unless copying succeeded.
- Preserve distinctions for missing jobs, expired pauses, and failed image loading.
  Failure to fetch/sign an image is a read problem, not proof generation failed:
  offer reloading the existing book/read, not a new paid generation as its primary fix.
- A long-running job remains a wait state until the backend marks it terminal.
  Keep existing stage progress and honest long-wait guidance. No fake countdown.
- Do not expose a title until its title safety/privacy conditions are satisfied.

## 5. Teacher presentation

Keep the existing safe teacher cause mapping and story reference. Show the same
distinction between submitted text, generated character image, generated scene image,
temporary service failure, worker stop, allowance, book budget, and unknown system
failure. For input rejection after titles ship, use “The submitted title or story did
not pass the input safety check.” Do not add teacher retry controls or moderation
details. Title display follows the title spec, including legacy fallback.

## 6. Accessibility and cross-cutting checklist

Use existing components/tokens, separate heading from supporting text, and avoid a
wall of diagnostic copy. Alerts announce errors once; pending status is polite.
Keyboard focus remains predictable after a failed retry. Enter/Space activate buttons;
no modal or Escape interception is added. Preserve 44px targets, visible focus,
reduced motion, 320px layout, and 200% zoom.

- [x] CC-1/CC-2/CC-4: no blocked images, raw diagnostic content, or unchecked titles.
- [x] CC-3: explicit whole-book retry, no paid retry for limit reasons.
- [x] CC-5: reason and job reference, no new content logging or support service.
- [x] CC-6/CC-8/CC-9: accessible audience-appropriate cause and recovery.
- [x] CC-10: distinguish new generation from reading/resuming an existing job.
- CC-7: no change to model/evaluation behavior.

## 7. Verification and completion

Extend `frontend/components/FailureScreen.test.tsx`, existing process/reader tests,
and teacher review tests. Reuse real existing job-shaped fixtures and mock network
boundaries. Demonstrate failure before implementing changed branches. Parameterize
the reason-to-copy/action mapping; test a retained-values failed retry as the critical
failure path. Existing classifier tests remain the evidence for cause selection.
Verify unknown values do not blame the child, limit reasons offer no paid retry,
raw error sentinels never render, and image-read recovery never submits a new book.

Manually check that a child can answer “What stopped?” and “What will this button do?”
from each screen. Check teacher cards, keyboard use, zoom, and slow/pending states.
No generated-content quality assertions or real provider calls in CI.

Implementation updates `failure-diagnostics.md`'s copy table to point here, plus
relevant recovery sections in `kid-flow-reader-and-wait-states.md` and
`teacher-review-and-approval.md`, so competing wording is not kept authoritative.
Their historical status/command prose can drift: actual code already implements the
taxonomy, and CI requires `pnpm build` even though the diagnostics spec omits it.

Run from `frontend/`: `pnpm lint`, `pnpm build`, `pnpm test`. If an evidenced backend
fix is included, also run from `backend/`: `uv run ruff check .`, `uv run pytest`.
Report skipped checks. This spec can ship independently with story-only copy, then
consume titles when their architecture and implementation are accepted.

# Feature Spec — Failure diagnostics and recovery UI

**Status:** approved design; written-spec review pending · **Phase:** 2 · **Owner:**
`backend/worker/`, `frontend/components/FailureScreen.tsx`, and the existing child/teacher job
surfaces

**Derived from:** ADR-025 Decision 5, `kid-flow-failure-semantics.md`,
`kid-flow-reader-and-wait-states.md`, `teacher-review-and-approval.md`, and `DESIGN.md`

## 1. Purpose

StoryBuddy currently collapses every terminal cause except rejected input text into `machine`.
That prevents blame, but it also leaves children and teachers guessing whether a generated picture
was blocked, a provider was temporarily busy, the paid-image breaker fired, or the worker stopped.

This change gives both audiences an honest, safe explanation and one useful next step without
exposing raw exceptions, providers, moderation labels, or implementation details. It reuses the
existing `jobs.failure_reason` column, terminal job flow, `FailureScreen`, and teacher failed-book
section.

## 2. Scope

### In

- A fixed safe failure taxonomy written by the two existing worker entrypoints.
- Distinct child-safe copy and recovery actions for each reason.
- The same safe cause on teacher failed-book cards.
- A compact story reference that displays an abbreviated job ID and copies the complete ID.
- Clearer copy when a live stage has not changed for 90 seconds.

### Out

- A new table, column, status, diagnostic JSON object, or support workflow.
- Browser-side crash inference, worker heartbeats, or dead-container detection.
- Automatic retry, partial restart, or any change to retry economics.
- Raw `jobs.error`, stack traces, provider names, moderation categories, or flagged phrases in UI.
- A message for every exception subtype. Unknown values deliberately share one fallback.

## 3. Contract

`backend/contracts/` is unchanged. `jobs.failure_reason` remains extensible text; no migration is
required. Its safe values become:

| Value | Meaning | Reliable source |
|---|---|---|
| `child_text` | Submitted text did not pass input moderation | Exact `content_flagged` sentinel |
| `character_safety` | A generated canonical reference remained flagged after its allowed redraw | Exact `ref_flagged` sentinel |
| `scene_safety` | A generated scene remained flagged after soften-and-redraw | Exact `output_moderation_failed` sentinel |
| `service_busy` | A provider or moderation service failed transiently | Network/timeout, HTTP 429, HTTP 5xx, or exact `moderation_error` sentinel |
| `service_limit` | A provider explicitly reported exhausted credit or quota | An explicit provider response; never inference from elapsed time or truncated output |
| `book_limit` | The paid-image circuit breaker stopped the run | Existing image-budget exception |
| `worker_stopped` | RQ reported that the job process crashed or exceeded its deadline | `_ReportingWorker.handle_job_failure` |
| `system_error` | A defect, invalid provider response, authentication/configuration problem, or unknown failure | Fail-safe default |

Old, null, and unrecognized values remain valid database values and render as `system_error`.
`jobs.error` remains a developer-only diagnostic written alongside the safe reason and is never
used to select or render frontend copy.

## 4. Backend behavior

One small classifier maps an exception to a safe reason. Both `run_storybook_job` and
`resume_storybook_job` call it from their existing `except` blocks before the existing terminal row
update. The RQ horse-death handler writes `worker_stopped` directly because it owns that fact.

Classification uses exact sentinels, installed provider exception types, and response status codes.
It does not search arbitrary exception prose for child-facing meaning. An explicit provider credit
or quota response may map to `service_limit`; a response-token ceiling, malformed structured output,
401/403 configuration error, or ambiguous “limit” message maps to `system_error`. This prevents a
model-output problem from being presented as an exhausted account balance.

The existing compare-and-set behavior in the horse-death path remains: it may update only queued or
running jobs and may not overwrite a completed, paused, or already-failed row.

## 5. Child experience

The existing full-screen failure card keeps the Cobalt Playroom visual language and presents:

1. A plain-language title explaining what stopped.
2. One reassuring sentence that avoids blame.
3. One primary recovery action.
4. A quiet story reference with an abbreviated ID and a copy control for the full ID.
5. A route back to the bookshelf when useful.

| Reason | Child-facing explanation | Primary recovery |
|---|---|---|
| `child_text` | “Some words need changing before we can make this book.” | Change my words |
| `character_safety` | “We couldn’t safely use the character picture we made. Your words aren’t in trouble.” | Make the story again |
| `scene_safety` | “One of the pictures we made couldn’t be used.” | Make the story again |
| `service_busy` | “The story-making service is busy right now.” | Try again |
| `worker_stopped` | “The story maker stopped before it finished.” | Try again |
| `service_limit` | “The story-making allowance has run out.” | Ask a teacher; no retry control |
| `book_limit` | “This book reached its picture-making limit.” | Ask a teacher; no retry control |
| `system_error` | “Something interrupted your story.” | Try again |

The existing explicit-submit rule remains: a retry creates and pays for a new job only after the
child presses the action. Persistent `service_limit` and `book_limit` failures omit the paid retry
control and direct the child to show the story reference to a teacher.

## 6. Teacher experience

The existing failed-book section displays the story reference and one exact safe label:

| Reason | Teacher-facing label |
|---|---|
| `child_text` | The submitted story did not pass the input safety check. |
| `character_safety` | A generated character reference did not pass the image safety check. |
| `scene_safety` | A generated scene did not pass the image safety check. |
| `service_busy` | A required story-making service was temporarily unavailable. |
| `worker_stopped` | The worker process stopped or exceeded its job deadline. |
| `service_limit` | The configured story-making service reported exhausted quota or credits. |
| `book_limit` | The job reached its paid-image circuit breaker. |
| `system_error` | The job ended because of an unclassified system error. |

Unknown values use the `system_error` label. The teacher card remains informational and adds no
retry or support control. It does not display `jobs.error`, provider identity, moderation categories,
flagged spans, or stack traces. The teacher can understand the recovery and give the job reference
to the owner without StoryBuddy adding an in-product support channel.

## 7. Loading state

The four real pipeline stages and per-picture count remain the only progress shown. If
`current_stage` does not change for 90 seconds, the live region says:

> This step is taking longer than usual. Your progress is saved, so you can leave and come back.

A long browser wait does not become a terminal failure. Slow image generation is valid, and only
the backend can truthfully mark a job failed. There is no fake percentage, countdown, or inferred
worker crash.

## 8. Accessibility and interaction

- Terminal messages use `role="alert"`; live progress uses `aria-live="polite"`.
- Retry controls disable while submitting, retain a 44px minimum target, and expose inline failure
  if the new submission cannot be created.
- The copy-reference control has an explicit accessible name and confirms success without relying
  on color alone.
- Repeating decorative motion stops under `prefers-reduced-motion: reduce`.
- Error copy remains readable at 320px and 200% zoom.

## 9. Deterministic verification

Backend tests are table-driven and mock every provider call:

- Each exact moderation sentinel maps to its intended safe reason.
- Network/timeout, 429, and 5xx failures map to `service_busy`.
- Only an explicit credit/quota response maps to `service_limit`.
- The image breaker maps to `book_limit`; unknown exceptions map to `system_error`.
- Both run and resume entrypoints write the classifier result.
- Horse death writes `worker_stopped` and cannot overwrite a terminal or paused row.

Frontend tests assert:

- Every reason renders its approved copy and action.
- `service_limit` and `book_limit` render no retry control.
- Null, legacy, and unknown values render the `system_error` fallback.
- Process, reader, and teacher surfaces never render a distinctive `jobs.error` sentinel,
  moderation label, provider name, or stack trace.
- The visible story reference is abbreviated and its copy control yields the complete job ID.
- The delayed loading message appears at 90 seconds and resets when `current_stage` changes.

Verification commands remain the project defaults:

```bash
cd backend
uv run ruff check .
uv run pytest

cd ../frontend
pnpm lint
pnpm test
```

## 10. Cross-cutting concerns

- **CC-1 Moderation ordering:** unchanged. The UI explains terminal outcomes and never bypasses a
  gate.
- **CC-3 Cost control:** persistent limit reasons cannot start another paid run from the error
  screen; other retries remain explicit and create a new bounded job.
- **CC-4 Security:** no new data or policy surface. Raw error text remains undisplayed.
- **CC-5 Observability:** `jobs.error`, current stage, and the full job ID remain available to the
  owner through existing logs and traces; the user supplies only the job reference.
- **CC-6 Accessibility:** alert/live-region, focus, target-size, zoom, and reduced-motion behavior
  are explicit in §8.
- **CC-8 Audience:** children and teachers see the same truthful safe cause in their existing visual
  registers; neither sees provider internals.
- **CC-9 Failure states:** this spec deepens the existing terminal screen without creating another
  failure surface.
- **CC-10 Resumability:** unchanged. A terminal failure is not resumed; a slow in-flight job remains
  resumable and is never declared dead by the browser.

## 11. Documentation and decision gate

ADR-038 amends ADR-025 Decision 5 before implementation. Once the owner approves this written spec,
ADR-038 becomes accepted and the current two-value assertions in
`kid-flow-failure-semantics.md`, `kid-flow-reader-and-wait-states.md`, and
`teacher-review-and-approval.md` must be amended in the same documentation change. Implementation
must not start while ADR-038 remains proposed.

## 12. Definition of done

The change is done when the safe reason is written at every existing terminal worker path, all
three user-facing job surfaces render the approved cause and action, persistent limits cannot be
retried from the error screen, the long-wait message is honest, raw diagnostics remain absent from
UI, the relevant specs reflect ADR-038, and the complete frontend/backend deterministic suites pass.

It is not done if the browser guesses that a slow job crashed, arbitrary exception text selects UI
copy, a child sees a moderation category or provider detail, an unknown reason blames the child, or
a persistent budget failure offers another paid retry.

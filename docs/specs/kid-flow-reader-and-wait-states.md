# Feature Spec — kid-flow reader & wait-state experience

**Status:** draft · **Phase:** 2 · **Owner:** `frontend/app/{process,book,write}/`, `frontend/lib/useJob.ts`,
`frontend/components/FailureScreen.tsx`, plus one loop in `backend/worker/run_job.py`
**Derived from:** `docs/specs/kid-flow-ui-docket.md` S4 · **Rationale:** ADR-029 (the reveal),
ADR-025 (never partial, terminal posture), ADR-013 (verbatim caption), ADR-006 (signed URLs),
ADR-020 (narration — deliberately *not* here), `DESIGN.md`, `USER_FLOW.md` §4/§6,
`ROUTE_MAP.md` §1/§6/§8, S1 (`kid-flow-book-persistence.md`), S2 (`kid-flow-pause-lifecycle.md`),
S3 (`kid-flow-failure-semantics.md`)

> **This is the rendering session.** S1 said what a book is, S2 said how a pause lives and dies, S3
> said what each recovery means. This spec draws every state the child can observe, including the
> ones nobody wants to see. It re-opens none of them.

## 1. Purpose

Three of the four surfaces the child reaches are wrong today, and each is wrong in the same way — a
state that exists in the data has no rendering, so it renders as *nothing*:

- `/process/[jobId]` (`page.tsx:18-38`) subscribes with **no initial `SELECT`**. A child returning to
  a paused job sees the bare string `queued` forever, because at a pause the next UPDATE never comes.
  A child returning to a *failed* job sees the same thing, because the failing UPDATE already fired.
- `/book/[jobId]:61` treats every non-`complete` row as not-ready, so a `failed` job renders
  *"Loading your book…"* permanently. S3 invariant 5 forbids exactly this.
- `jobs.current_stage` is written **twice in the entire system**, both inside `_finish`
  (`run_job.py:24`, `:35`). Until the job ends, `/process` has nothing to show. `USER_FLOW.md` §6
  promises a per-scene stepper synced via Realtime; there is no per-scene data to sync.

There is also no reveal screen at all, so ADR-029's pause — now fully built through
`POST /jobs/{id}/confirm` — parks a child in front of a job that no client can un-stick.

This spec fixes all four by adding one data hook, one pure classifier, one shared component, and one
loop in the worker.

## 2. Contract slice

`backend/contracts/` is **unchanged** — no `StoryMemory` field, no `schema_version` bump. No
migration, no new column, no new endpoint, no new status value, no new RLS policy.

- **Reads (from `jobs`):** the whole row via `select("*")` — `status`, `current_stage`, `pages`,
  `reveal`, `input_text`, and `failure_reason` once it exists (§3.2)
- **Reads (from Storage):** `createSignedUrls` over `pages[].image_path` and
  `reveal.characters[].image_path`, bucket `storybook-images`
- **Writes (frontend):** `POST /storybooks` (`revise`, `retry`) and `POST /jobs/{id}/confirm`
  (`redraw`, confirm) — both existing, both unchanged
- **Writes (backend):** `jobs.current_stage`, and **only** `current_stage`, from the new progress
  loop (§3.4). Never `status`, never `pages`, never `reveal`.
- **Invariants:** see §5

### 2.1 Scope

**In:** the wait state, the reveal, the reader, the failure screens — the four surfaces the docket's
S4 cluster names.

**Out, and why:**

| Not here | Owner |
|---|---|
| TTS narration / the reader's play button | `narration` (ADR-020; `providers.narrate()` unbuilt) |
| The style-preset picker (`/write/style`) | a pre-job authoring step, not a job state |
| Bookshelf / home / gallery | needs a per-child list query, which S1 constraint 4's capability-link model cannot express — `auth-and-classroom` |
| The `failure_reason` enum itself | `job-failure-reason`, migration `0006` (§3.2 removes the build-order dependency) |
| The swept-pause status *value* | `data-deletion` (§4.4.4 states the one requirement) |

## 3. Architecture

### 3.1 One hook, one classifier, four page files

Two units are shared, because exactly two things are genuinely rendered by more than one route.

**`useJob(jobId)`** — `frontend/lib/useJob.ts`. Used by `/process/[jobId]` and `/book/[jobId]`.
Returns `{ bucket, row, refetch }`.

**`classify(row)`** — a pure function exported from the same file. It takes a row (or `null`) and
returns a bucket. Being pure is the point: it is the hardest logic in the session and it is table-
testable with no Supabase, no DOM, and no mocks.

**`<FailureScreen kind inputText />`** — `frontend/components/FailureScreen.tsx`. The one component
both routes render. Owns the recovery button, the chain counter increment, and the prefill handoff.

Everything else is inline Tailwind in the page file against the tokens already in `globals.css`.

> **Rejected:** a `<JobGate>` wrapper that renders buckets through slots. Tidier on paper, but it
> forces the reader and the stepper — which share no chrome whatsoever — through one layout shape.
> The hook returns a discriminated union and each page writes its own `switch`.

> **Rejected:** a `frontend/components/kid/` primitive kit (Button, Card, Screen). It would be an
> abstraction designed for two callers that do not exist yet — the bookshelf and the gallery — whose
> interfaces this session cannot see. `auth-and-classroom` builds them when it has the callers.

### 3.2 `select("*")` — and why the column list is wrong here

The read is `select("*")`, not an explicit column list.

`jobs.failure_reason` does not exist yet; it is migration `0006`, owned by `job-failure-reason`.
Naming a missing column in a PostgREST `select` **fails the entire read**, so an explicit list either
omits the column (and S4 cannot select `revise` at all) or hard-blocks S4 on `0006` shipping.

With `*`, `row.failure_reason ?? null` evaluates to `null` today — which S3 constraint 19 maps to
`retry`, the fail-safe default — and to the real value the day `0006` lands, **with no frontend
change and no redeploy coupling**. This dissolves the docket's build-order dependency: S4 ships
complete and correct before the enum exists, and starts differentiating the moment it does.

`*` also pulls `jobs.error` into the browser. That is **not a new exposure**: the Realtime
`payload.new` already delivers the whole row today, under the same `0001_jobs_table.sql:18-21`
policy. S3 invariant 4 forbids *showing* it, and nothing shows it (§7 pins that with a test).

### 3.3 Subscribe first, then seed

S2 and S3 both require *"seed from a `SELECT`, then subscribe."* Done in that literal order there is a
gap: an UPDATE landing between the `SELECT` and the `subscribe()` is lost forever.

**The order is: `subscribe()`, then `SELECT`, and the seed is discarded if a live UPDATE already
landed.** One `useRef<boolean>` is the whole mechanism. It is safe without a version column because
job status only ever moves forward — `queued → running → awaiting_confirm → running → complete |
failed` — so a live UPDATE is never older than the seed.

The hook also exposes **`refetch()`**, called after every `POST /jobs/{id}/confirm` response. This is
S2's carry-in requirement: re-read the row after each resume so a stale chip list can never surface a
`422` to a child. The subscription would deliver the same row a moment later; the explicit refetch is
what makes the ordering guaranteed rather than probable.

The channel is removed once the bucket is terminal — no UPDATE will ever come for a terminal row.

### 3.4 Four buckets, and a fail-safe fifth branch

```
classify(row):
  no row                                  → 'not-found'
  status 'complete' && pages.length > 0   → 'terminal-success'
  status 'awaiting_confirm'               → 'paused'
  status 'queued' | 'running'             → 'in-flight'
  status 'failed'                         → 'terminal-failure'
  anything else                           → 'terminal-failure'
```

The last line is load-bearing and covers two cases:

- **An unknown status.** Including whatever `data-deletion` eventually picks for a swept pause. The
  child gets the machine screen and a working `retry` rather than an infinite spinner. It is the
  wrong *copy* (S3 §4.8 wants gentler words) and the right *action* — see §4.4.4.
- **`complete` with empty `pages`.** S1 constraint 3 says this cannot happen, and the single atomic
  terminal write in `_finish` is why. If it ever does, it is a broken book, not a wait state.

**The swept pause is never inferred from a non-empty `reveal`.** S2 constraint 9 states that
consumers switch on `status` and never on the presence of `reveal`, which is deliberately left stale
on finished rows. This spec obeys that even though it costs a nicer default.

### 3.5 The progress loop

`run_job.py` gets one new helper. Both entrypoints call it and then call `_finish`, so **S2
constraint 10 is untouched — `_finish` is still the only writer of `pages` or `reveal`, and there is
still one tail.**

`invoke()` is already exactly this loop. `pregel/main.py:3913-3943` shows the v1 implementation:
`invoke(stream_mode="values")` iterates `stream(stream_mode=["updates","values"])`, keeps the last
`values` payload as `latest`, harvests `__interrupt__` from the `updates` chunks, and returns
`{**latest, "__interrupt__": interrupts}` when any fired. Inlining that loop hands `_finish` a
**byte-identical `result`**; the only addition is a write inside it.

```
_run_with_progress(supabase, job_id, app_graph, graph_input, config) -> dict:
    latest, interrupts, last_stage = None, [], None
    for each chunk from app_graph.stream(graph_input, config, stream_mode=["updates","values"]):
        unpack (mode, payload)          # 2-tuple, or 3-tuple with a namespace — mirror invoke()
        if mode == "values":
            latest = payload
        else:                            # "updates"
            if "__interrupt__" in payload: interrupts.extend(payload["__interrupt__"])
            stage = _stage_string(node_name_from(payload), latest)
            if stage != last_stage:
                supabase.table("jobs").update({"current_stage": stage}).eq("id", job_id).execute()
                last_stage = stage
    return {**latest, "__interrupt__": interrupts} if interrupts else latest
```

`_stage_string(node, latest)` is pure:

```
scenes = (latest or {}).get("scenes") or []
if node in {"generate_scene","consistency_check","regenerate","output_mod"} and scenes:
    done = count(s.final_image_ref is not None for s in scenes)
    return f"{node}:{min(done+1, len(scenes))}/{len(scenes)}"
return node
```

**Three properties this deliberately has:**

1. **`k` and `N` need no contract change.** `N = len(scenes)` and `k` = finished scenes + 1, both read
   off the `values` payload the stream already carries. There is no scene pointer in `StoryMemory`
   and this spec does not add one.
2. **Writes are deduped.** Only a *changed* stage string is written. A 15-scene book produces roughly
   twenty writes, not one per super-step, and Realtime traffic is proportional to visible progress.
3. **It writes `current_stage` and nothing else.** S1 constraint 6 ("progress writes never touch
   `pages`") holds structurally, not by convention.

> `ponytail:` `current_stage` encodes two facts — phase and scene counter — in one text column,
> because S1 constraint 6 forbids a progress column. Upgrade path if it ever needs a third fact: a
> `jobs.progress` jsonb column, which is a schema decision and needs an amendment.

## 4. Behavior & edge cases

Copy below is the shipped copy, not a placeholder. `DESIGN.md`'s register applies throughout:
Nunito 18/20px, `.neo-border` + `.neo-shadow`, `rounded-3xl` cards, `rounded-2xl` buttons, 44×44px
minimum targets, one or two accents per screen.

### 4.1 `in-flight` — the wait state (`/process/[jobId]`)

A four-step vertical stepper, driven by `current_stage`. Steps are the child's phases, not the
graph's nodes:

| Step | `current_stage` values | Label |
|---|---|---|
| 1 | `queued`, `input_gate`, `analyze`, `segment` | *Reading your story* |
| 2 | `char_bible`, `char_ref_mod`, `reveal` | *Meeting your characters* |
| 3 | `generate_scene:k/N`, `consistency_check:k/N`, `regenerate:k/N`, `output_mod:k/N` | *Drawing picture k of N* |
| 4 | `compose` | *Putting your book together* |

Steps above the current one are done (Mint Lime check), the current one animates, the ones below are
grey. Step 3's label carries the counter; before `segment` runs, `N` is unknown and step 3 reads
*Drawing your pictures*.

**An unrecognised `current_stage` highlights no step** and shows the heading alone —
*"Making your book!"*. It never crashes and never guesses. Old rows written before this ships hold
`reveal` or `compose`, both of which map.

**Step 2 completing is the reveal appearing.** The pause is the character step, so the stepper and
the reveal are continuous rather than a context switch.

**The stall message.** After **90 seconds with no UPDATE**, a gentle line is *added* beneath the
stepper — *"Still going! We saved your spot, so you can leave and come back."* (`USER_FLOW.md` §6).
The timer resets on every UPDATE. It is never an action, never a failure, and never replaces the
stepper.

> A single fal.ai image call can legitimately exceed 90s, so this **will** sometimes fire on a
> healthy job. That is accepted: the line is additive and reassuring, so a false positive costs
> nothing, and a threshold tuned to never false-positive would be too long to reassure anyone. The
> constant is named and tunable.

On `terminal-success`, `/process` pushes to `/book/[jobId]`.

### 4.2 `paused` — the reveal (`/process/[jobId]`, inline)

**The reveal is not its own route.** S2 made the pause a *status on the same job*, so
`/process/[jobId]` renders it inline. `ROUTE_MAP.md` §1's `/process/[jobId]/reveal` row is removed by
this spec (§10). The reasons are concrete: one route means one subscription and one four-bucket
`switch` instead of two independent copies of the hardest logic in the session; there is no redirect
racing the Realtime UPDATE; and a child deep-linking to a `/reveal` URL on a running or failed job
cannot land on a screen with nothing to render.

**Rendering.** S2 constraint 9's projection `{characters:[{char_id, name, image_path, chips}],
taps_left}` is rendered **as-is**. The screen signs `image_path` at read time and does not re-derive
chips, recompute `taps_left`, or read graph state. At most two characters exist (ADR-004): side by
side in landscape and on desktop, stacked in portrait.

Per character: the reference image, the name (*"Meet Luna!"*), and its chips as tappable pills.

**A chip tap submits immediately.** `POST /jobs/{id}/confirm {action:"try_again", char_id,
attribute}` fires on tap — no selection state, no second confirm step. One tap, one thing happens,
which is the model a Grade-5 reader can hold. The cost is real and is accepted: an accidental tap
spends one of three draws and there is no undo.

**One confirm button, one label: *"Use this one!"*** The docket requires that label at
`taps_left == 0` so the button never dead-ends. Nothing requires a different label above zero, and
using it always deletes a branch from the screen that can least afford one. It sends
`{action:"confirm"}` (`main.py:53-56`).

**At `taps_left == 0` the chips are not rendered at all** — not disabled. A disabled chip is a
dead-end button wearing a hint.

**The redraw must not bounce through the stepper.** The CAS in `confirm_job` flips `status` to
`queued`, so the bucket becomes `in-flight` and the four-step stepper would replace the reveal for
the duration of one redraw, then hand back. A `justConfirmed` ref is set on press and cleared when
the status returns to `awaiting_confirm` or goes terminal; while it is set, `in-flight` renders a
reveal-local *"Drawing it again…"* state instead of the stepper. A page reload during the redraw
loses the ref and shows the stepper — acceptable and honest, because the job really is running.

**Every confirm response calls `refetch()`** before the screen re-renders (§3.3).

**A `200` carrying a status other than `queued`** — S2 constraint 11's duplicate / late / swept /
finished path — is not an error and shows no error. The row is refetched and the bucket re-classified;
whatever the job actually is now, that is what renders.

**A reveal image that will not sign.** Re-sign once. If the second attempt also fails, render the
reveal **without images**, with the character names and the single *"Use this one!"* button. This is
deliberately *not* a failure screen: the job is not failed, the pause is live, and offering `retry`
would abandon a resumable job to the sweeper and bill a whole new book. A bare confirm costs nothing,
un-sticks the job, and gets the child a book. S3 §4.7's re-sign rule was scoped to the reader; this
extends the same posture to the pause.

### 4.3 `terminal-success` — the reader (`/book/[jobId]`)

One page at a time, out of `jobs.pages` — array order is page order (S1 constraint 1).

**Orientation: no lock and no rotate prompt.** `screen.orientation.lock('landscape')` needs a
fullscreen context and iOS Safari does not support it at all (`ROUTE_MAP.md` §8's open question).
One CSS media query answers it instead: portrait stacks image over caption, landscape places them
side by side. Portrait gives the image less room than a forced-landscape reader would; in exchange
there is no JS, no iOS gap, and — decisively — no wall for a child whose device has rotation locked
in system settings, which a rotate-prompt can neither detect nor escape. **This closes §8's open
question by making it moot.**

**Controls.** Giant tap zones, left and right 30% of the viewport (`USER_FLOW.md` §4.7), plus arrow
keys and a `k / N` page indicator (CC-6). Zones at the ends of the book are not rendered — a
one-page book has neither. Images use `object-contain` so a portrait illustration is never cropped.

**Page position is component state.** Not a URL segment and not a query param — `ROUTE_MAP.md` §7
reserves query params for filters and pagination, and there is no bookshelf to return to until
`auth-and-classroom`. A reload starts at page 1.

**Alt text.** The image carries `alt={caption}` and the visible caption is `aria-hidden`. Today's
page does both without the `aria-hidden`, so every page is read twice to a screen reader. The caption
is the verbatim story text (ADR-013), so it is the correct accessible name for the illustration.

**Signing.** One `createSignedUrls` batch over every path, 3600s. Any per-path error or null URL
fails the whole read (S1 constraint 7, ADR-025 — no page-shaped holes). **The failure is retried once
automatically, with no button.** A signing failure is transient by nature — an expired URL, a network
blip — and S3 §4.7 forbids offering `retry` here, because redrawing an N-page book to repair an
expired link is real money. If the second attempt also fails, fall through to the machine failure
screen, and **that press does not increment the chain counter** (§4.5): a signing failure is not a
failed story.

### 4.4 `terminal-failure` and `not-found` — the failure screens

One component, four kinds, one action each. Every kind gets the same design care as the reader
(AGENTS.md, CC-9): confused-mascot illustration, Comic Red accent, one giant button. **No screen
renders a moderation category, a flagged span, or `jobs.error`** (S3 invariant 4).

The kind is selected by `failure_reason` (or the 8-value safe taxonomy in ADR-038), which is **never rendered as text**.

#### 4.4.1 `child_text` (revise) — the child's own text was rejected

Selected when `failure_reason` equals `child_text`. *"Some words need changing before we can make this book."* Button: **Change my words**.

Pressing it stashes `jobs.input_text` and navigates to `/write` (§4.5).

#### 4.4.2 Safe retry kinds (`character_safety`, `scene_safety`, `service_busy`, `worker_stopped`, `system_error`)

Renders approved reassure-and-retry copy per reason (e.g. *"One of the pictures we made couldn’t be used."*, *"The story-making service is busy right now."*, *"The story maker stopped before it finished."*, or *"Something interrupted your story."*). Button: **Make the story again** or **Try again**. Unknown values, `machine`, and `null` fail-safe to `system_error`.

Pressing it posts `input_text` verbatim to `POST /storybooks` and navigates to the new
`/process/[jobId]`. The button disables on press — required by `DESIGN.md` §5 anyway, and it
incidentally covers S3 §4.11's double-press case without a dedupe mechanism.

#### 4.4.3 Safe limit kinds (`service_limit`, `book_limit`)

Renders allowance/budget limit copy (*"The story-making allowance has run out."* or *"This book reached its picture-making limit."*) and subtext *"Ask a teacher to help."*. Omits the paid retry button and directs the child to show a teacher.

#### 4.4.4 `not-found` — no row

*"We can't find that story."* Button: **Write a new story** → `/write`, empty.

No `input_text` exists, so there is nothing to revise and nothing to retry. S3 §4.9: this is the one
child-facing state with no recovery, and it is correct that it has none. The counter does not move.

#### 4.4.4 `asleep` — a swept pause

*"Your story went to sleep while you were away."* Button: **Make it again** — the same `retry`
mechanism, different words (S2 constraint 15, S3 §4.8). The counter does not move: nobody failed.

**This kind is not reachable yet, by design.** `data-deletion` owns the status value a swept pause
lands on, and has not picked it. Until it does, an unknown status falls to §3.4's fail-safe branch and
renders `retry` — right action, wrong copy. **The requirement handed to `data-deletion` is one line:
name the value, and S4 maps it to this kind.** S3 §4.8's other requirement on that row still stands —
the swept row must survive with `input_text` readable, or this degrades to §4.4.3's no-action state.

### 4.5 The chain counter and the prefill

Both live in `sessionStorage`, both are read by `/write`.

| Key | Holds | Written by | Consumed by |
|---|---|---|---|
| `sb.failChain` | integer | `<FailureScreen>` on press; cleared by `/book` once a book actually renders | `/write` on mount |
| `sb.prefill` | the failed job's `input_text` | `<FailureScreen>` on a `revise` press | `/write` on mount, then deleted |

**Not a query param.** `ROUTE_MAP.md` §7 bans query params for navigation state, and the child's raw
text in a URL would land in browser history — text S3 §4.3 already flags as un-redacted.

**Counter rules** (S3 §4.5, verbatim in behaviour):

- **Incremented on a `revise` or `retry` press from a `failed` job.** Not on render — counting renders
  double-counts a reload.
- **Not incremented** by `asleep`, by `not-found`, or by the §4.3 signing fall-through. None of those
  is evidence that a story is not working.
- **Reset when a book actually renders** — signed pages on screen — and when `/write` mounts with no
  `sb.prefill`. Deliberately *not* on the `terminal-success` bucket alone: a `complete` book whose
  images will not sign classifies as `terminal-success` and then falls through to a failure screen
  (§4.3). Resetting on the bucket would let a broken book zero a chain the child is still inside.
- **At ≥ 3, `/write` shows a third offer** — *"Want to try a different story instead?"*, which simply
  clears the box. It is a variant of `revise`, not a fourth verb.
- **It never gates.** Both buttons stay live at 4, 5 and 40.
- `sessionStorage` being unavailable (blocked storage, hardened privacy mode) is caught and ignored.
  The counter stays 0 and the offer never appears — which is safe precisely because it never gates.

Being tab-scoped matches S3's "two devices, two independent counters" exactly.

### 4.6 One widening of scope, named

`/write`'s submit handler swallows a failed POST — `page.tsx:34-36` is `if (!res.ok) return;` with no
message and no state change. The button re-enables and nothing happens.

That is pre-existing and would normally be out of bounds under AGENTS.md §3. It is in bounds here
because `revise` deposits a child in that editor and presses that button: on a 5xx, S4's own recovery
flow dead-ends silently. **This spec adds one inline error message with `role="alert"`** (`DESIGN.md`
§ Error States) and changes nothing else in that file. Recorded as a deliberate widening rather than
done quietly.

### 4.7 Edge cases

| Case | Behavior |
|---|---|
| UPDATE lands between `subscribe()` and the seed `SELECT` | The seed is discarded; the live row wins (§3.3) |
| Child opens `/process` on an already-`complete` job | Seed classifies `terminal-success`; push to `/book`. No flash of stepper |
| Child opens `/process` on a `failed` job, no further UPDATE | Failure screen from the seed. Today: nothing, forever |
| Child opens `/book` on a `failed` job | Failure screen. Today: *"Loading your book…"*, forever (S3 §4.6) |
| Child opens `/book` on a `queued` job | The wait state — `/book` handles all four buckets, not just two |
| Child opens `/process` on a paused job | Reveal, from the seed. Today: the bare word `queued`, forever |
| Chip tap while `taps_left == 0` | Unreachable — chips are not rendered (§4.2) |
| 4th tap arrives anyway (stale tab) | `route_reveal` converts it to a confirm (S2 constraint 12); the refetch shows the job running. No error, no failure screen |
| Confirm returns `200` with `complete` | Refetch reclassifies to `terminal-success`; push to `/book` |
| Confirm returns `503` (Redis down, S2's rollback) | The pause is intact and un-consumed. Inline *"That didn't work — try once more"*; the button re-enables |
| Reveal image fails to sign twice | Names + *"Use this one!"*, no images, no failure screen (§4.2) |
| Book signs on the second attempt | Renders normally. Nothing recorded, no job created, counter unmoved |
| Book fails to sign twice | Machine failure screen; the counter does **not** move (§4.3) |
| `current_stage` is a value the stepper does not know | Heading only, no step highlighted. Never crashes |
| `current_stage` is `generate_scene:3/8` but `pages` is empty | Normal in-flight. `pages` is written once, at the end (S1 constraint 2) |
| `complete` with empty `pages` | `terminal-failure`, machine copy. Should be impossible (S1 constraint 3) |
| Unknown status value (a swept pause, today) | `terminal-failure`, machine copy, working `retry` (§3.4, §4.4.4) |
| `failure_reason` is `null` on an old row | `retry`. The fail-safe default (S3 constraint 19) |
| `failure_reason` holds an unrecognised value | `retry`. Same default |
| Child reloads a failure screen five times | Counter unchanged — presses are counted, not renders |
| Counter at 3, child presses `retry` anyway | Works. The offer suggests; it never gates |
| `sessionStorage` unavailable | Counter stays 0, offer never shows, prefill silently absent. Nothing breaks |
| Child navigates to `/write` directly with a stale `sb.prefill` | Consumed once on mount and deleted; the next visit is empty |
| Job stalls past 90s on a healthy image call | Stall line appears. Additive and harmless (§4.1) |
| One-page book | No tap zones, no arrows, indicator reads `1 / 1` |
| Device has rotation locked to portrait | The reader works. No prompt, no wall (§4.3) |
| `prefers-reduced-motion` | `DESIGN.md` §3.5 — durations capped at 150ms, no overshoot, opacity-only transitions |

## 5. Invariants

1. **Every URL-reachable surface handles all four buckets.** `/process/[jobId]` and `/book/[jobId]`
   both route through `classify` (S3 constraint 20).
2. **A terminal row never renders as a wait state** (S3 invariant 5).
3. **An unknown status, an unknown `failure_reason`, and a `null` `failure_reason` all render
   `retry`.** The default never blames the child (S3 constraint 19).
4. **No child-facing surface renders a moderation category, a flagged span, or `jobs.error`**
   (S3 invariant 4).
5. **The reveal renders S2's projection as-is** — signs `image_path` at read time, does not re-derive
   chips, does not recompute `taps_left`, never reads graph state (S2 constraint 9).
6. **Consumers switch on `status`, never on the presence of `reveal`** (S2 constraint 9).
7. **Progress writes touch `current_stage` and nothing else.** `_finish` remains the only writer of
   `pages` or `reveal`, and both worker entrypoints still converge on it (S1 constraint 6, S2
   constraint 10).
8. **Every surface subscribes before it seeds, and discards a seed that a live UPDATE has overtaken**
   (§3.3).
9. **No child-facing action spends money unless the child pressed `revise` or `retry`.** A re-sign, a
   reload, a bare confirm, and a `404` all cost nothing (S3 invariant 6).
10. **The chain counter suggests and never gates** (S3 invariant 7).
11. **The tap cap is not a failure.** A spent budget renders *"Use this one!"* and never reaches the
    failure vocabulary (S3 invariant 8).

## 6. Access & the trust boundary

**No new surface.** Reads go through `0001_jobs_table.sql:18-21`; signing goes through
`0004_jobs_pages.sql`'s `storage.objects` policy. `revise` and `retry` are the existing
`POST /storybooks`; `redraw` and confirm are S2's existing `POST /jobs/{id}/confirm`. **Still exactly
two policy surfaces** — S1 constraint 4, S2 constraint 16 and S3 constraint 23 all unchanged, and
`auth-and-classroom` still replaces exactly two.

**The client is not a trust boundary and this spec does not treat it as one.** Hiding chips at
`taps_left == 0` is a rendering courtesy; `route_reveal` enforces the cap (S2 constraint 12,
ADR-029). The endpoint validates `char_id` and `attribute` against the row (S2 constraint 11). Nothing
here is the enforcement point for anything.

**`select("*")` widens what the browser holds, not what it may hold.** `jobs.error` and the
un-redacted `jobs.input_text` are already delivered by every Realtime `payload.new` under the
existing policy. §3.2 explains why the alternative is worse. `auth-and-classroom` scopes both when it
replaces the policy; S3 §6 already flags the `input_text` half.

**The retry buttons are a cost surface.** Each press is a full book against ADR-025 D4's per-book
breaker. S3 §6 named this for `rate-limiting`; this spec is where the buttons actually appear.

## 7. Tests

Frontend, Vitest, every Supabase call mocked (`AGENTS.md` testing bright line).

**`classify` — a table test, no DOM.** Every row of §3.4, plus: unknown status; `complete` with empty
`pages`; `null` row.

**Regression tests S3 §7 requires by name:**

- A `failed` row at `/book/[jobId]` renders the failure screen, **not** the not-ready state — this is
  a regression test against today's `page.tsx:61`.
- A `failed` row at `/process/[jobId]` with **no subsequent UPDATE** renders the failure screen —
  the seed-then-subscribe fix, against today's `page.tsx:18-38`.
- The child's-text `failure_reason` renders `revise`; **every other value, an unknown value, and
  `null` render `retry`.**
- `revise` stashes `jobs.input_text` and lands in the editor with it prefilled; `retry` posts it
  unchanged; **neither issues any write against the old job.**
- No screen renders a moderation category or `jobs.error` — asserted against a row whose `error`
  holds a distinctive sentinel string.
- A per-path signing failure re-signs once before any failure screen appears.
- The counter increments on press, not on render; three presses surface the start-something-new
  offer; a fourth press still works.

**This spec's own additions:**

- A paused row at `/process/[jobId]` with no subsequent UPDATE renders the reveal from the seed.
- A chip tap POSTs `{action:"try_again", char_id, attribute}` and calls `refetch()`.
- At `taps_left == 0` no chip is rendered and *"Use this one!"* posts `{action:"confirm"}`.
- A confirm returning `200` with a non-`queued` status shows no error.
- While `justConfirmed` is set, an `in-flight` row renders *"Drawing it again…"*, not the stepper.
- A reveal whose paths fail to sign twice still renders the confirm button.
- `current_stage = "generate_scene:3/8"` highlights step 3 and reads *Drawing picture 3 of 8*; an
  unrecognised value highlights nothing and does not throw.
- The stall line appears after the threshold and disappears on the next UPDATE.
- `/book` renders the wait state for a `queued` row (the four-bucket rule applies to the reader too).

**Backend, pytest, providers mocked:**

- `_run_with_progress` hands `_finish` a result **equal to what `invoke()` returns** — asserted on
  both the complete path and the interrupt path.
- Progress writes update `current_stage` only; no call touches `status`, `pages` or `reveal`.
- The same stage string is not written twice in a row.
- `_stage_string` is unit-tested pure: before `segment` (no scenes), mid-loop, and on the last scene.

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-9 Failure states = success states** — four failure kinds, each designed, each with one
  action (§4.4); the no-recovery state is named as such (§4.4.3); a terminal row can never render as
  in-flight (§3.4, invariant 2); the tap cap and a swept pause stay out of the failure vocabulary
  (§4.2, §4.4.4).
- [x] **CC-6 Accessibility** — 44×44px minimums; arrow-key paging beside the tap zones; the
  double-read alt-text bug fixed (§4.3); `role="alert"` on inline errors; `aria-live` on the stepper;
  `prefers-reduced-motion` honoured per `DESIGN.md` §3.5. **Narration is `narration`'s** (ADR-020),
  so CC-6's TTS leg is not closed by this spec.
- [x] **CC-4 Security** — no new endpoint, no new policy surface, still exactly two (§6). The
  `failure_reason` value selects a screen and is never rendered.
- [x] **CC-8 Kid vs teacher design** — this is the kid register throughout: Nunito 18/20px, oversized
  targets, `.neo-border`/`.neo-shadow`, minimal text. No teacher surface is touched.
- [x] **CC-5 Observability** — S3 §9's per-action line is emitted here, since here is where the
  actions are: one line per `revise` / `retry` / re-sign, carrying the `failure_reason` that selected
  the screen and the chain count at press time. It is the only evidence that will ever exist for
  whether PRD §11.4's N=3 is the right number.
- [x] **CC-3 Cost control** — a re-sign never rebuilds a book (§4.3); a signing failure at the reveal
  confirms rather than retries (§4.2); the retry button disables on press; the press-loop stays named
  for `rate-limiting` (§6).
- [ ] CC-1 Moderation ordering — N/A. No render path shortcuts the pipeline.
- [ ] CC-2 PII redaction — flagged, not clean: the `revise` prefill re-serves the un-redacted
  `jobs.input_text` (S3 §4.3). Unchanged by this spec and unfixable without a schema change; carried
  forward so it is not lost.
- [ ] CC-7 Reproducibility — N/A.
- [ ] CC-10 Checkpointing — the wait state *displays* checkpoint progress; it owns none of it.

## 9. Eval / quality checks

No new instrument. CC-5's per-action line (§8) is the measurement, and §4.1's stall threshold is the
one number in this spec chosen by judgement rather than derivation — if the logs show children
leaving during the stall window, the threshold is the first thing to move.

## 10. Blast radius

**Frontend:**

| File | Change |
|---|---|
| `frontend/lib/useJob.ts` | **New.** The hook and `classify` |
| `frontend/components/FailureScreen.tsx` | **New.** Four kinds, one action each, owns the counter |
| `frontend/app/process/[jobId]/page.tsx` | Rewritten: seed-then-subscribe, four buckets, the stepper, the reveal inline |
| `frontend/app/book/[jobId]/page.tsx` | Rewritten: four buckets, one-page-at-a-time reader, orientation media query, the automatic re-sign, the alt-text fix |
| `frontend/app/write/page.tsx` | Prefill + counter consumption on mount, the N≥3 third offer, and §4.6's one inline error |
| `frontend/app/globals.css` | Keyframes for the stepper, shimmer, and the reveal's drawing state — tokens already exist |
| the three existing `*.test.tsx` | Updated alongside their pages; new tests per §7 |

**Backend:**

| File | Change |
|---|---|
| `backend/worker/run_job.py` | `_run_with_progress` + `_stage_string`; both entrypoints call it, then `_finish` unchanged |
| `backend/tests/test_run_job.py` | §7's four backend assertions |

**Docs changed in the same change:**

| File | Change |
|---|---|
| `docs/specs/ROUTE_MAP.md` | §1 drops the `/process/[jobId]/reveal` row and §6 its back-button entry (§4.2); §8's landscape-lock open question is **resolved** (§4.3); §8's loading-state table gains the reader's four-bucket note |
| `docs/specs/USER_FLOW.md` | §4.6's stepper and §4.7's reader gain the orientation decision; §6's stall copy is pinned to a threshold |
| `docs/specs/kid-flow-ui-docket.md` | S4 → DONE with its constraints; the roster note fires |
| `docs/MASTER_SPEC.md` §7, `docs/product/DECISION_BACKLOG.md` | The `kid-flow-ui` row becomes four specs — the docket's roster note says to do this only once the docket is DONE throughout, which S4 completes |
| `docs/product/DECISION_BACKLOG.md` | `data-deletion` gains §4.4.4's naming requirement; `narration` records that the reader ships without a play button |

**Not touched:** `backend/contracts/`, `backend/pipeline/`, `backend/app/main.py`,
`supabase/migrations/`.

## 11. The migration number

**This spec claims none, and adds no column.** `0006` remains `job-failure-reason`'s. Next free is
`0007`, unclaimed. §3.2 is what lets S4 ship before `0006` does.

## 12. Linked decisions & open questions

**Depends on:** ADR-029 (the reveal, the cap, *"use this one"*) · ADR-025 (never partial, terminal
posture, the D4 breaker) · ADR-013 (verbatim caption) · ADR-006 (signed URLs) · ADR-012 (the cap
notice) · `DESIGN.md` · `USER_FLOW.md` §4/§6 · `ROUTE_MAP.md` §1/§6/§7/§8 · S1 constraints 1–8 ·
S2 constraints 9–16 · S3 constraints 17–23.

**Takes no schema decision, no contract decision, and no new dependency.** `lottie-react` and
`motion` were considered and rejected: the register `DESIGN.md` describes is delivered with CSS
keyframes on tokens that already exist, and neither library survives AGENTS.md §2 for a session whose
job is rendering states that currently render as nothing.

**Resolves:** `ROUTE_MAP.md` §8's landscape-lock open question (§4.3), and S3's build-order dependency
on `job-failure-reason` (§3.2 — S4 no longer waits on `0006`).

**Handed onward:**

| Owner | What |
|---|---|
| `data-deletion` | Name the swept-pause status value; S4 maps it to the `asleep` kind (§4.4.4). Until then it renders machine copy |
| `narration` | The reader's play button and its states. §2.1 |
| `auth-and-classroom` | The bookshelf, the gallery, and the `/s/[profileId]` move — a directory rename against these files |
| `rate-limiting` | §6's press-loop, now with actual buttons attached |
| `repeated-failure-offramp` | §4.5's counter is the client-side version; `jobs.parent_job_id` is still the durable upgrade path |

**Open:**

- **The stall threshold is a guess** (§4.1). 90s is chosen so the reassurance arrives before a child
  gives up, accepting that a slow image call trips it. CC-5's logs are what would correct it.
- **`current_stage` encodes two facts in one text column** (§3.5). Forced by S1 constraint 6's "there
  is no progress column"; the upgrade path is named and needs an amendment.
- **The `asleep` screen is written but unreachable** until `data-deletion` names its status (§4.4.4).
  It ships tested against a synthetic value rather than a real one.
- **Portrait reading gives the image less room** than the forced-landscape reader `USER_FLOW.md` §4.7
  imagined (§4.3). Accepted in exchange for a reader that has no unreachable state. If child testing
  shows portrait reading is genuinely worse, the fix is a *dismissible* rotate hint, never a wall.
- **An accidental chip tap costs one of three draws with no undo** (§4.2). Accepted for the one-tap
  mental model. If testing shows accidental taps are common, the fix is a select-then-confirm step,
  which is additive.

## 13. Definition of done

1. `classify` exists as a pure exported function and its table test covers every branch in §3.4.
2. `/process/[jobId]` and `/book/[jobId]` both seed-then-subscribe and both render all four buckets.
3. Both of S3 §7's regression tests are green: `failed` at `/book` is not a wait state, and `failed`
   at `/process` with no further UPDATE is not a blank screen.
4. The reveal renders S2's projection, taps submit, `taps_left == 0` renders no chips and a working
   *"Use this one!"*, and every confirm refetches.
5. The stepper advances through all four steps on a real multi-scene run, with a real `k / N`.
6. `_run_with_progress` is proven to hand `_finish` the same result `invoke()` did, on both paths.
7. `pnpm lint && pnpm test` green, `uv run ruff check . && uv run pytest` green.

**Not done** if: any surface renders a terminal row as a wait state; an unknown or `null`
`failure_reason` renders anything but `retry`; a moderation category or `jobs.error` reaches a child;
a progress write touches `status`, `pages` or `reveal`; a second writer of `pages` or `reveal`
appears; the chain counter gates a button; the reveal re-derives chips or reads graph state; a
signing failure bills a new book; or the reader has a state a child cannot get out of.

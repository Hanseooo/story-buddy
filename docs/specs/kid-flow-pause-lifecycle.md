# Feature Spec — kid-flow pause & resume lifecycle

**Status:** built (`f0319eb`..`6ea9030`) · **Phase:** 2 · **Owner:** `backend/pipeline/reveal.py`,
`supabase/migrations/0005_jobs_awaiting_confirm.sql`, `backend/worker/run_job.py`,
`backend/app/main.py`
**Derived from:** `docs/specs/kid-flow-ui-docket.md` S2 · **Rationale:** ADR-029 (the whole shape),
ADR-024 (pure routers, `recursion_limit`), ADR-025 (D4 breaker, failure posture), ADR-028 (`RefVerdict`),
ADR-011 / PRD §13 (moderation ordering), ADR-006 (durable paths)

> ADR-029 froze the reveal's shape and listed its consequences to build. This spec builds all of them
> **except the screen** (S4's): the two contract fields, the `reveal` node and `route_reveal`,
> `char_bible`'s targeted mode, the status migration, the confirm endpoint, and the worker's
> pause branch.

## 1. Purpose

A book pauses once for a human. PRD §8 step 7 promises the child sees the moderated canonical
reference before full generation, with a confirm and a *"try again."* ADR-029 decided its shape and
built nothing. This spec gives the pause a durable lifecycle: how the worker enters it, what the
paused row exposes, how a client leaves it, and what every way of leaving it twice — or never — does.

## 2. Contract slice

The three additions are **ADR-029's, verbatim**. This session executes a contract change an accepted
ADR already specified; it does not decide one. Both new fields default, so per
`story-memory-contract` §3 there is **no `schema_version` bump**, no restart path, no capstone edit.

```python
class ReferenceRetry(BaseModel):        # ADR-029
    char_id: str
    attribute: str        # the tapped chip, restated verbatim in the redraw prompt

class Cost(BaseModel):
    ...
    ref_retry_count: int = 0            # ADR-029 — the 3-tap budget, per book

class StoryMemory(BaseModel):
    ...
    reference_retry: Optional[ReferenceRetry] = None   # set by `reveal`, consumed by `char_bible`
```

- **Reads:** `characters[]` (`char_id`, `name`, `description`, `canonical_ref_image`, `ref_verdict`),
  `cost.ref_retry_count`, `reference_retry`
- **Writes:** `reference_retry` (`reveal` sets, `char_bible` clears), `cost.ref_retry_count`,
  `cost.image_count`, `characters[].canonical_ref_image` / `.ref_verdict` (`char_bible`)
- **Writes (to `jobs`):** `status='awaiting_confirm'`, `reveal jsonb`
- **Invariants:** see §5.

## 3. Position in the system map

One node, one router, one loop-back edge, and one changed line in an existing router.

```
char_bible → char_ref_mod → moderation_router ─ scenes ─→ reveal → route_reveal ┬ "confirm"   → route_next_scene
     ▲                                                                          │
     └───────────────────────────── "try_again" ────────────────────────────────┘
```

`moderation_router`'s scene branch returns `"reveal"` instead of choosing `generate_scene` /
`output_mod` itself. That choice is not lost — it moves to `route_reveal`'s confirm path, which calls
`route_next_scene`, the function that already made it. The `if state.scenes` discriminator separating
the post-`input_gate` call from the post-`char_ref_mod` call is untouched: `segment` runs before
`char_bible`, so scenes always exist by the second call.

**The loop-back targets `char_bible`, not `generate_scene`.** A redrawn reference therefore re-enters
`char_ref_mod` before it can reach a child — PRD §13's ordering (`input gate → char-ref → reveal →
output`) holds on the retry path, not only the first pass. It also means `character-bible` invariant 6
(skip any character that already has a reference) needs no exception: the targeted mode overwrites
unconditionally (ADR-029 §2).

### `reveal` performs no effect

Its body is one `interrupt()` and one partial return. That property is the entire reason it is a
separate node (ADR-029 §1): LangGraph re-executes a resumed node from the top, so an `interrupt()` at
the tail of `char_bible` would redraw up to six references on every confirm. Building the projection
dict it hands to `interrupt()` (§4.2) is computation, not an effect — no provider call, no upload, no
write outside its own return.

### `route_reveal` is pure and holds no policy

```python
def route_reveal(state: StoryMemory) -> str:
    if state.reference_retry is not None and state.cost.ref_retry_count < 3:
        return "try_again"
    return route_next_scene(state)
```

The cap is enforced **here**, not only in the UI. The resume payload arrives from a client and is a
trust boundary (ADR-029 §1).

## 4. Behavior & edge cases

### 4.1 Entering the pause — and when not to

```python
def reveal(state: StoryMemory) -> dict:
    payload = _project_reveal(state)
    if not payload["characters"]:
        log.info("reveal: no reference to show — skipping the pause")
        return {}                                     # no interrupt, no pause
    answer = interrupt(payload)
    if isinstance(answer, dict) and answer.get("action") == "try_again":
        return {"reference_retry": ReferenceRetry(char_id=answer["char_id"], attribute=answer["attribute"])}
    return {}
```

**A book with no canonical reference must not pause.** `char_bible` returns `{}` when
`state.characters` is empty or every character already has a reference, so a story from which
`analyze` extracted no characters reaches `reveal` with nothing to show. Without this guard the child
is parked on an empty screen in front of a confirm button that confirms nothing, and — because no
client would ever send a confirm for a screen it cannot render — **the job sits in `awaiting_confirm`
until the `data-deletion` sweep**. A pause with nothing to reveal is not a pause.

**An unrecognised resume payload is treated as a confirm, not an error.** The node fails toward
progress: the endpoint (§4.9) is the guard that rejects malformed payloads, and by the time one
reaches the node it has already been validated against the row. A node that raised here would turn a
client bug into a destroyed book.

### 4.2 The reveal projection is the interrupt payload

`_project_reveal` is a **pure function in `reveal.py`**, and its output is what the node passes to
`interrupt()`. The worker writes `result["__interrupt__"][0].value` into `jobs.reveal` verbatim.

This placement is deliberate. The node is the thing that knows what the child should be shown, and a
pure projection is unit-testable with no worker, no DB and no mocks. It also means the worker never
has to reach into graph state to reconstruct the screen — the pause carries its own content, which is
exactly what `interrupt()`'s payload is for.

```json
{"characters": [{"char_id": "c0", "name": "Kiko", "image_path": "job-1/ref-c0-1.png",
                 "chips": ["orange sock", "one floppy ear"]}],
 "taps_left": 2}
```

- **Only characters with a `canonical_ref_image` appear.** `char_bible` caps at two references
  (`character-bible` invariant 1), so a story with five characters reveals two. A character with no reference has no
  image to show and nothing to redraw; listing it would offer a tap that cannot be honoured.
- **`image_path` is a durable Storage path, never a signed URL** — the same rule as `pages` and
  `canonical_ref_image` (ADR-006). Signing happens at read time.
- **`taps_left = 3 - cost.ref_retry_count`.** At `0` the button becomes *"use this one"* rather than
  disappearing or refusing (ADR-029 §2). What that looks like is S4's.

### 4.3 Chips, and why the list can never be empty

`chips` are the described attributes the judge could not find: the `species`, `colours`,
`body_features` and `clothing` axes of `CharacterDescription`, minus `ref_verdict.attributes_present`,
compared case-insensitively. `notes` is excluded — it is free prose, not an attribute, and not a thing
a child can tap.

**Two fallbacks, in order, because an empty chip list dead-ends the button.** The endpoint validates a
tap against the offered chips (§4.9), so a character offering none can never be retried — and
ADR-029's *"the button never dead-ends"* would be false at the top of the pause rather than at the cap.

1. **Nothing missing** — `ref_verdict is None` (a judge outage; `char_bible` accepts the draw unchecked
   and records `None`) or `matches_description is True`. Fall back to the **full axis list**: a child
   may disagree with a reference the judge passed, and that disagreement is the entire point of the
   reveal (ADR-029 context).
2. **No axes at all** — `analyze` produced a bare name with no species, colours, features or clothing.
   Fall back to **`[name]`**. The tap then restates the character's name, which is all
   `char_bible._describe` had to work with anyway, so the redraw is an honest blind re-roll. ADR-029's
   "targeted, not blind" premise assumes described attributes exist; where none do, blind is the only
   retry available, and it beats no retry.

### 4.4 The counter increments in `char_bible`, not in `reveal`

ADR-029's test list phrases the bump as `reveal`'s. It is placed one node later, deliberately, and
flagged rather than absorbed.

If `reveal` bumped, the 3rd tap would take the count 2 → 3 and the router's `< 3` would deny the very
tap it had just counted. The only repairs are `<= 3`, after which the constant no longer means
"3 taps", or a counter that reaches 4 under a cap of 3. With the bump in `char_bible`'s targeted mode
— the thing that actually spends a tap — `ref_retry_count` equals taps that bought a draw, equals the
3 extra images CC-3's prelude of 9 is sized for. **A denied tap draws nothing and counts nothing.**

ADR-029 froze the cap, the field and the router's enforcement. It did not freeze which node writes
the field, so this is a placement choice inside the frozen shape, not an amendment.

### 4.5 `char_bible`'s targeted mode

When `state.reference_retry` is set, `char_bible` takes a second path: exactly **one**
`text_to_image` for that `char_id` with the tapped attribute restated in the prompt, **one** `judge`
call to refresh `ref_verdict`, an unconditional overwrite of `canonical_ref_image` and `ref_verdict`,
`cost.image_count + 1`, `cost.ref_retry_count + 1`, and `reference_retry` cleared. No re-roll, no
best-of, one code path away from the ADR-028 loop it sits beside.

The overwrite is unconditional by decision, not oversight (ADR-029 §2): best-of over old-versus-new
would let the pipeline show the child the same picture back — the worst available answer to
*"try again."*

**The ADR-025 D4 breaker is not checked here, and that is deliberate.** `IMAGE_BUDGET`'s prelude of 9
is sized as 2 references × 3 draws + 3 taps × 1 draw, and the 3-tap router cap is what bounds this
path. A breaker check would guard a ceiling the cap already makes unreachable. Named so it is not
rediscovered as a missing guard.

### 4.6 A redraw must land on a new Storage path

`char_bible._upload` writes `f"{story_id}/ref-{char_id}.png"` with `upsert: "true"`. A targeted
redraw would overwrite that object **in place**, so the reveal projection's `image_path` is byte-identical
before and after the tap. The child taps *"try again"*, the pipeline pays for a draw, and the screen
re-signs the same path — against any browser or CDN cache, **showing them the same picture back.**
That is the exact outcome ADR-029's unconditional overwrite was chosen to prevent, arriving through
the storage layer instead of through best-of.

```python
def _upload(image: bytes, story_id: str, char_id: str, n: int) -> str:
    path = f"{story_id}/ref-{char_id}-{n}.png"
```

`n = cost.ref_retry_count + 1`, evaluated **after** the targeted mode's bump — so the first pass writes
`-1`, the first tap `-2`, and so on. This mirrors `regeneration-controller`'s per-attempt scene path
(`{scene_id}-{n}.png`), adopted there for this same class of reason, and it takes that spec's
"uniform beats a special case" position: the first draw is `-1`, not a bare name.

**`n` is a uniqueness suffix, not a per-character draw count.** `ref_retry_count` is per *book*, so a
child who taps character A then character B leaves B's second draw at `-3`. Path uniqueness is the
only property required, and stating this here is cheaper than a per-character counter that would be a
second source of truth.

The superseded object is left in place. It costs one PNG and it is the *before* half of a
before/after pair on a human-judged retry — the most valuable thing `annotation-surface` could be
handed (§9). `data-deletion` already owns removing a job's objects wholesale.

### 4.7 The retry loop re-moderates every character

`char_ref_mod` iterates `state.characters` unconditionally — it has no skip on
`ref_moderation_status == "passed"`. So a tap costs a fresh sign + primary + backstop classification
for **both** references, not just the redrawn one: up to 12 redundant classifier calls across 3 taps.

**This is left as-is.** The primary classifier is a local 0.6B model and the backstop is one
OpenRouter call; re-moderating an unchanged image is cheap and unconditionally safe.

⚠️ **The trap, named so nobody springs it later:** the obvious optimisation — skip any character
already marked `"passed"` — is a **CC-1 safety hole** unless `char_bible`'s targeted mode also clears
`ref_moderation_status` on the character it overwrote. A status describes the image that was in
`canonical_ref_image` when it was written; overwriting the image invalidates it. Adding the skip
without the clear routes an unmoderated image straight to a child.

### 4.8 The worker's branch and the shared tail

`invoke()` returns a state dict carrying `__interrupt__` when a node yielded. Both worker entrypoints
converge on one tail function, which is the **only** writer of either `pages` or `reveal`:

```python
def _finish(supabase, job_id: str, result: dict) -> None:
    if "__interrupt__" in result:
        supabase.table("jobs").update(
            {"status": "awaiting_confirm", "current_stage": "reveal",
             "reveal": result["__interrupt__"][0].value}
        ).eq("id", job_id).execute()
        return
    pages = [...]                                    # unchanged, S1 §4.1
    supabase.table("jobs").update(
        {"status": "complete", "current_stage": "compose", "pages": pages}
    ).eq("id", job_id).execute()
```

**An interrupt with no usable payload raises**, taking the job to `failed` by the existing `except`.
Writing an empty `reveal` instead would produce the §4.1 hang — a row claiming to await a human, in
front of a screen with nothing on it. A hard failure is the honest outcome (ADR-025 posture).

`awaiting_confirm` is a status value, not a boolean beside `running`: a job waiting on a human is not
running, and every consumer that switches on status should have to see that (ADR-029 §5).

`reveal` stays on the row after the book completes. It is stale, deliberately, and harmless:
**consumers switch on `status`, never on the presence of `reveal`** — the same rule S1 set for `pages`.

### 4.9 Leaving the pause — `POST /jobs/{id}/confirm`

```
{"action": "confirm"}
{"action": "try_again", "char_id": "c0", "attribute": "orange sock"}
```

**Three checks, in this order.** The order is load-bearing and pinned by tests:

1. **The row exists** → else `404`. The only non-`200` outcome besides a rejected payload: there is no
   status to report and the capability does not resolve.
2. **Identity, against `jobs.reveal`** → else `422`. `char_id` must appear in *that row's* projection,
   and `attribute` must be one of the chips that row offered **for that char** — chips are validated
   per-character, never as a flat set. Nothing is enqueued and no status changes. This runs **before**
   the CAS so a malformed payload can never consume a pause.
3. **The CAS**, which is the lock:

```sql
update jobs set status = 'queued' where id = ? and status = 'awaiting_confirm'
```

- **Rows affected** → enqueue `resume_storybook_job(job_id, payload)`, return `200` with the new status.
- **Zero rows** → someone already resumed, or the job never paused, or it was swept → return `200`
  with the current status and **enqueue nothing.**

`status='queued'` rather than `'running'` because that is what is true: it is enqueued, and the worker
sets `running` itself exactly as the first pass does. No new status value beyond `awaiting_confirm`.

A duplicate returning `200` rather than `409` is a deliberate child-facing choice: a double-tapping
six-year-old must not be shown an error, and S4 should never have to design a screen for one. Machine
clients lose nothing — the returned status says exactly what happened.

**Validation is against the current row, so a stale client gets `422`.** A tap held over from the
previous pause may name a chip that the redraw has since satisfied and the new projection no longer
offers. Rejecting it is correct: the child would be asking to fix something that is no longer wrong,
and their screen is out of date. S4 refreshes from the row.

**A failed enqueue rolls the CAS back.** If the queue write raises after the status flipped, the
endpoint restores `status='awaiting_confirm'` and returns `503`:

```python
try:
    queue.enqueue("worker.run_job.resume_storybook_job", job_id, payload)
except Exception:
    supabase.table("jobs").update({"status": "awaiting_confirm"}).eq("id", job_id).execute()
    raise HTTPException(503, "could not resume — try again")
```

Without it, a Redis outage consumes the pause and strands the book permanently: no worker is coming,
and the child can never re-confirm because `awaiting_confirm` is gone. The rollback is safe precisely
because nothing consumed the pause — no graph step ran, no state changed, and a retry re-runs the
identical CAS.

### 4.10 Resuming — a second entrypoint

```python
def resume_storybook_job(job_id: str, payload: dict) -> None:
    supabase.table("jobs").update({"status": "running"}).eq("id", job_id).execute()
    ...
    result = app_graph.invoke(Command(resume=payload), config={...})   # NO initial_state
    _finish(supabase, job_id, result)
```

It never constructs a `StoryMemory`, so it **structurally cannot** rebuild and clobber a live thread —
the failure mode a single resume-aware `run_storybook_job(job_id, resume=None)` would leave one `if`
away. The `except` block, the config, and `_finish` are shared with the first entrypoint; only the
first argument to `invoke()` differs.

The pause machinery needs nothing else: `run_job.py` already invokes under `PostgresSaver` with
`thread_id = job_id`, so the checkpoint is durable across processes, and `jobs` is already in the
`supabase_realtime` publication, so the transition is observable with no new channel (ADR-029 §5).

### 4.11 A pause nobody ever confirms

ADR-029 named this and did not solve it: no TTL, no reaper, and the sweep belongs to `data-deletion`.
This spec binds three properties and **picks no status value**:

1. **Resumable from any device holding the UUID, for as long as the row says `awaiting_confirm`.** The
   reveal is on the row, not in a session. Any surface that renders the pause must seed from a
   `SELECT` and then subscribe — `/process/[jobId]` subscribes today without an initial fetch, so a
   child returning to a paused job sees nothing until the next UPDATE. S4 fixes that; S2 states the
   requirement.
2. **A swept pause is not ADR-025 `failed`,** and must not read to the child as their story breaking.
   Nobody failed; a child closed a tab. `data-deletion` picks the terminal value and the TTL.
3. **A confirm against a swept job takes the same CAS-miss path as a double-confirm** — `200`, current
   status, no enqueue. No separate code path, no separate screen, whatever value the sweep picks.

No resource is held while paused: the worker returned at the `interrupt()`. This is storage growth,
not a stuck job.

### 4.12 A resumed run that fails

Identical to a first-pass failure: the shared `except` sets `status='failed'` with the error, `pages`
keeps its `'[]'` default, and the stale `reveal` is left on the row (§4.8). A book is never delivered
partial (ADR-025).

A resume against a **missing checkpoint** — the thread was wiped, or the DB restored from before the
pause — takes the same route: `invoke(Command(resume=...))` finds no thread, raises, job `failed`. It
is not silently restarted from the top, which would redraw the whole book and bill for it.

### 4.13 `RECURSION_LIMIT`'s prelude is wrong once `reveal` is wired

`RECURSION_LIMIT = MAX_SCENES * 4 + 9` reserved a **9-super-step** prelude as headroom for this node
(`regeneration-controller` §4). The reservation under-counted: ADR-029's `fixed_prelude + 7` assumed a
retry cycle of `char_bible + reveal`, but `char_ref_mod` sits between them (§3), so a cycle is 3
super-steps, not 2.

Worst case is **15**: `input_gate·analyze·segment·char_bible·char_ref_mod·reveal` = 6, plus three
retry cycles of `char_bible·char_ref_mod·reveal` = 9. A 15-scene book whose child uses all three taps
raises `GraphRecursionError` — on precisely the path this spec exists to build.

```python
# app/config.py
SUPER_STEP_PRELUDE = 15               # ADR-029 reveal: 6 linear + 3 retry cycles × 3
RECURSION_LIMIT = MAX_SCENES * 4 + SUPER_STEP_PRELUDE
IMAGE_BUDGET = MAX_SCENES * 2 + 9     # unchanged — 9 IMAGES, a different unit
```

**The two constants stop sharing a number, and that is ADR-029's own position:** the super-step prelude
"remains a different unit from CC-3's image prelude, exactly as `character-bible` §5 warns." They were
only ever coincidentally equal at 9. Raising `IMAGE_BUDGET` in sympathy would buy 6 phantom draws of
headroom (~$0.12–$0.22) before the CC-3 breaker trips — weakening a cost guard to preserve a symmetry
the ADR already disowned. `regeneration-controller` §4's "share one number" comment is corrected in
this change.

### 4.14 Edge cases

| Case | Behavior |
|---|---|
| **Confirm on first pause** | `route_reveal` → `route_next_scene` → the scene loop. `ref_retry_count` stays 0, cost unchanged. The typical book. |
| **Tap, then confirm** | Loop back through `char_bible` → `char_ref_mod` → `reveal`; the second pause rewrites `jobs.reveal` with a new `image_path` and `taps_left: 2`. |
| **4th tap** | Endpoint accepts (identity is valid), router returns `"confirm"`, the book proceeds. No draw, no bump. |
| **Double-tap of confirm** | Second request: CAS matches zero rows → `200`, current status, no second RQ job. |
| **Confirm on a `complete` / `failed` / swept job** | Same CAS-miss path → `200`, current status, no enqueue. |
| **Unknown job UUID** | `404` — no status to return, capability does not resolve. |
| **`char_id` not in `jobs.reveal`** | `422`. Nothing enqueued, status unchanged, pause not consumed. |
| **`attribute` valid for another char, not this one** | `422` — chips are validated per-character, not as a flat set. |
| **Stale chip from the previous pause** | `422`. The client's screen is out of date; the redraw already satisfied that attribute. |
| **Missing / unknown `action`** | `422` at the Pydantic boundary. Never reaches the CAS. |
| **Redis down at enqueue** | CAS rolled back to `awaiting_confirm`, `503`. The pause survives and the child can retry (§4.9). |
| **No characters in the story** | `reveal` returns `{}` without interrupting; the book runs straight through. No empty screen, no permanent pause (§4.1). |
| **Five characters** | Two references exist (`char_bible` cap); the projection lists those two. The other three offer no tap. |
| **A character with an empty description** | Chips fall back to `[name]`; the tap is a blind re-roll (§4.3). |
| **`ref_verdict is None`** (judge outage upstream) | Chips fall back to the full axis list; the child still has something to tap. |
| **Reference passed the judge** (`matches_description=True`) | Same fallback. The pause happens regardless — the child's disagreement is the point. |
| **A retried reference is flagged by `char_ref_mod`** | `moderation_router` raises `content_flagged`, job `failed`. The retry path is not exempt from the gate. |
| **Process dies between `reveal` and `char_bible`** | Checkpoint resumes at `char_bible` with `reference_retry` set and `ref_retry_count` un-bumped; the tap is re-spent, not lost or double-counted. |
| **Two different taps race** | First wins the CAS; the second gets `200` and its `char_id`/`attribute` are discarded. One resume per pause, always. |
| **Resume against a missing checkpoint** | Raises → `failed`. Never silently restarted from the top (§4.12). |
| **Interrupt with an unusable payload** | Raises → `failed`. Never an empty `reveal` and a permanent pause (§4.8). |

## 5. Invariants

1. **The terminal write (`status='complete'` + `pages`) happens exactly once per book,** in `_finish`,
   however many pauses intervened. S1 constraint 2 survives because both entrypoints share one tail.
2. **A pause write never touches `pages`; a terminal write never touches `reveal`.**
3. **The pause is entered only when at least one character has a `canonical_ref_image`** (§4.1), and
   every character in the projection has one.
4. **A character in the projection always offers at least one chip** (§4.3). An empty chip list makes
   try-again unreachable and dead-ends the button.
5. **`cost.ref_retry_count` counts taps that bought a draw.** A denied tap increments nothing (§4.4).
6. **A redraw never reuses a Storage path** (§4.6). No object a child has been shown is overwritten
   in place.
7. **Every `attribute` that reaches an image prompt was authored by the worker and offered on that row
   for that character** (§4.9).
8. **A resume is only ever enqueued by a CAS that observed `awaiting_confirm`,** and a pause is never
   consumed without a resume actually being enqueued (§4.9). There is no other path to
   `resume_storybook_job`.
9. **`reveal` performs no effect** — no provider call, no upload, no write outside its partial return.
10. **Every `image_path` in the projection is a durable path.** No signed URL is ever stored.

Enforced by the CAS and by the single tail function, not by a `CHECK` constraint — the same posture,
and the same reasoning, as S1 §5.

## 6. Access & the trust boundary

`reveal` is a column on `jobs`, so it inherits `0001_jobs_table.sql:18-21`
(`for select to anon using (true)`). The reference images live in `storybook-images`, which
`0004`'s `storage.objects` policy already covers. **No third policy surface is created** — S1
constraint 4 holds, and `auth-and-classroom` still replaces exactly two policies.

`POST /jobs/{id}/confirm` carries the same capability as every other kid route: the job UUID. It adds
no new trust model, and §4.9's identity check is what stops that capability from becoming a
prompt-injection surface — the `attribute` that reaches `text_to_image` is always a string the worker
itself authored from already-moderated input. No moderation call is added at the endpoint, because a
closed set of worker-authored strings has nothing left to moderate.

**Realtime:** the `awaiting_confirm` UPDATE carries `reveal` to any anon subscriber on the existing
channel. Same `using(true)` exposure that already applies to every other column, closed by the same
future migration (S1 §6.3).

## 7. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

**Router (`route_reveal`, pure — no mocks), extending `test_graph_stub.py`:**
- `reference_retry` set, `ref_retry_count < 3` → `"try_again"`.
- `reference_retry` set, `ref_retry_count == 3` → `"confirm"` — the trust boundary, pinned.
- `reference_retry is None` → `"confirm"`, and the destination is `route_next_scene`'s answer
  (`generate_scene` with unfinalized scenes, `output_mod` without).
- `moderation_router` with scenes present → `"reveal"`; with scenes empty → `"analyze"`; the
  raise-on-flag paths are unchanged.

**Node (`reveal`), new `backend/tests/test_reveal_node.py`:**
- A confirm resume returns `{}`; a try-again resume returns `reference_retry` only.
- **No character with a reference → returns `{}` and `interrupt` is never called** (§4.1).
- An unrecognised resume payload is treated as a confirm, not raised (§4.1).
- Neither path calls a provider or touches Storage (invariant 9).
- `cost` is untouched by the node (invariant 5 — the bump is `char_bible`'s).

**Projection (`_project_reveal`, pure — no mocks), same file:**
- Chips are described-minus-`attributes_present`, case-insensitively.
- **Full axis list** when `ref_verdict is None`, and when `matches_description is True`.
- **`[name]`** when the description carries no axes at all (§4.3).
- `notes` never appears as a chip.
- A character with `canonical_ref_image is None` is **absent** from `characters`.
- `taps_left == 3 - ref_retry_count`.

**`char_bible` targeted mode, extending `test_char_bible_node.py`:**
- Exactly one `text_to_image` and one `judge` call; the tapped attribute appears in the prompt.
- Only the flagged character mutates; every other `Character` is returned byte-identical.
- `image_count + 1`, `ref_retry_count + 1`, `reference_retry` cleared to `None`.
- The overwrite is unconditional: a character that already has `canonical_ref_image` is redrawn.
- **The upload path differs from the previous one** — `ref-c0-1.png` → `ref-c0-2.png` (invariant 6).
- The ADR-028 loop path is unchanged when `reference_retry is None`; existing first-pass assertions
  move from `ref-{char_id}.png` to `ref-{char_id}-1.png` and stay otherwise untouched.

**Worker, extending `test_run_job.py`:**
- An `invoke` returning `__interrupt__` writes `status='awaiting_confirm'` and `reveal`, with **no**
  `pages` key in the update dict; `reveal` equals the interrupt value verbatim.
- A clean `invoke` writes `status='complete'` and `pages`, with **no** `reveal` key (invariant 2).
- An `__interrupt__` with no usable value raises → `status='failed'`, no `reveal` write (§4.8).
- `resume_storybook_job` calls `invoke` with a `Command` and **never** constructs a `StoryMemory`.
- A raising resume writes `status='failed'` and no `pages`.

**Endpoint, extending `test_main.py`:**
- Unknown job UUID → `404`.
- Unknown `char_id` → `422`; an `attribute` offered for a *different* char → `422`; a missing
  `action` → `422`. **None of them change `status`** — the pause is not consumed.
- A valid try-again → one enqueue, `status='queued'`, payload carries `char_id` and `attribute`.
- A valid confirm → one enqueue, `status='queued'`.
- A **second identical request** → `200`, zero enqueues (the CAS).
- Confirm against a `complete` job → `200`, zero enqueues.
- **A raising `enqueue` → `503` and `status` is back to `awaiting_confirm`** (§4.9).

**Config, extending `test_config.py`:**
- `RECURSION_LIMIT == MAX_SCENES * 4 + 15`; `IMAGE_BUDGET` unchanged at `MAX_SCENES * 2 + 9`.

**Graph:**
- A run that taps once reaches `compose` having visited `char_ref_mod` twice (the re-moderation path).
- A run that taps four times makes three targeted draws and proceeds — the cap terminates the loop.
- A run with **no characters** reaches the scene loop without pausing.

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-1 Moderation ordering** — `reveal` sits behind `char_ref_mod` on the first pass **and** on
  every retry, because the loop-back targets `char_bible` (§3). No unmoderated image reaches a child
  by construction. The one way to break that is named in §4.7.
- [x] **CC-3 Cost control** — the 3-tap cap is enforced in the router; `ref_retry_count` counts only
  taps that drew (§4.4), so it can never exceed the 3 images CC-3's prelude of 9 budgets.
  `SUPER_STEP_PRELUDE` is split from `IMAGE_BUDGET` (§4.13) and the image breaker is unchanged. The
  redundant re-moderation of unchanged references is measured and accepted (§4.7).
- [x] **CC-4 Security** — the confirm payload is a closed set validated against the row before the CAS
  (§4.9); durable paths only; no new policy surface (§6).
- [x] **CC-9 Failure states = success states** — a double-confirm, a confirm on a finished job, and a
  confirm on a swept job all take one non-error path; a tap at the cap becomes *"use this one"*; a
  queue outage returns the pause rather than eating the book (§4.9); a book with nothing to reveal
  never pauses (§4.1).
- [x] **CC-10 Checkpointing / resumability** — the pause is durable across processes and devices
  (§4.11); a crash between `reveal` and `char_bible` re-spends the tap without double-counting; a
  missing checkpoint fails rather than silently restarting (§4.12).
- [x] **CC-5 Observability** — one line per pause (`char_ids`, `taps_left`, or the skip reason when it
  does not pause) and one per resume (`action`, `char_id`, `attribute`, `ref_retry_count`). A book with
  a bad reference must show whether the child was offered a retry, took one, or was denied at the cap.
- [ ] CC-2 PII redaction — N/A (chips derive from `CharacterDescription`, already downstream of the
  input gate; the endpoint accepts no free text).
- [ ] CC-6 Accessibility — S4's (the reveal screen).
- [ ] CC-7 Reproducibility — a recorded resume payload replays exactly as input text does (ADR-029 §1).
  No new instrument.
- [ ] CC-8 Kid vs teacher design — S4's.

## 9. Eval / quality checks

No new instrument. Two rules this spec imposes on an existing one:

1. **A tapped attribute is a free human label on reference quality** (ADR-029 §2), and
   `annotation-surface` should join it to the `RefVerdict` that preceded it.
2. **§4.6's per-draw paths make that a before/after pair.** The superseded reference is still in
   Storage, so the corpus can carry *"this is what the child rejected, this is what they were given,
   and this is the attribute they named"* — the strongest signal in the whole flow. Named, not built.

## 10. Blast radius — changed in the same change

| File | Change |
|---|---|
| `backend/contracts/story_memory.py` | `ReferenceRetry`, `Cost.ref_retry_count`, `StoryMemory.reference_retry` (§2) |
| `backend/pipeline/reveal.py` | new — the node and `_project_reveal` (§4.1–4.3) |
| `backend/pipeline/graph.py` | `route_reveal`; the `reveal` node; `moderation_router`'s scene branch → `"reveal"`; `add_conditional_edges("reveal", route_reveal)`; the `try_again` → `char_bible` edge |
| `backend/pipeline/char_bible.py` | the targeted mode (§4.5); `_upload` takes `n` and writes `ref-{char_id}-{n}.png` (§4.6) |
| `backend/app/config.py` | `SUPER_STEP_PRELUDE = 15`; `RECURSION_LIMIT` uses it (§4.13) |
| `backend/app/main.py` | `POST /jobs/{id}/confirm` — the 404/422/CAS order and the enqueue rollback (§4.9) |
| `backend/worker/run_job.py` | `_finish`, `resume_storybook_job` (§4.8, §4.10) |
| `supabase/migrations/0005_jobs_awaiting_confirm.sql` | new — widen the `status` CHECK, add `reveal jsonb not null default '{}'` |
| `backend/tests/test_reveal_node.py` | new — per §7 |
| `backend/tests/{test_graph_stub,test_char_bible_node,test_run_job,test_main,test_config}.py` | per §7 |
| `docs/specs/character-bible.md` | the targeted mode is built; the `_upload` path scheme; §5's CC-3 note gains the retry draw |
| `docs/specs/regeneration-controller.md` | §4 — the "both backstops share one number" comment is corrected (§4.13) |
| `docs/specs/moderation-stack.md` | `char_ref_mod` now runs once per tap; the skip-optimisation trap of §4.7 |
| `docs/specs/story-memory-contract.md` | §2 — the two fields land, no `schema_version` bump |
| `docs/MASTER_SPEC.md` | §2 — the `reveal` row loses its *(Phase 2)* marker |
| `docs/product/DECISION_BACKLOG.md` | `job-failure-reason` renumbered `0005` → `0006` (§11) |

**Not touched:** `frontend/` — the reveal screen, the confirm call, and the `SELECT`-then-subscribe fix
are all S4's (§4.11). `docs/specs/ROUTE_MAP.md` documents kid routes, not API routes, so the new
endpoint is not in it.

## 11. The migration number

S1 constraint 8 left `0005` free, and S1's blast radius simultaneously renumbered
`DECISION_BACKLOG`'s `job-failure-reason` row from `0004` to `0005`. Both cannot hold. This spec takes
`0005` — it is being built now, and `job-failure-reason` is a deferred row with no date — and moves
that row to `0006` in the same change. Next free number after this spec is `0006`, and it is claimed.

## 12. Linked decisions & open questions

**Depends on:** ADR-029 (the entire frozen shape — node, router, targeted mode, 3-tap cap,
`awaiting_confirm`, the endpoint) · ADR-024 (pure label-returning routers, `recursion_limit`'s formula)
· ADR-025 (D4 breaker; failure posture; never partial) · ADR-028 (`RefVerdict.attributes_present`, the
source of the chips) · ADR-011 / PRD §13 (moderation ordering) · ADR-006 (durable paths, signed at read
time) · S1 (`docs/specs/kid-flow-book-persistence.md`) constraints 1–8.

**Deviates from ADR-029 in one placement, deliberately:** the `ref_retry_count` bump lives in
`char_bible`, not `reveal` (§4.4). The cap, the field and router-side enforcement are unchanged.

**Corrects one number ADR-029 got wrong:** the super-step prelude is 15, not `fixed_prelude + 7`
(§4.13). The ADR did not account for `char_ref_mod` sitting inside the retry cycle.

**Handed to later sessions:**
- **S3 (failure semantics)** — the two "try again"s now have one concrete referent each: this spec's
  is the ADR-029 reference redraw, addressed by `char_id` + `attribute` against a paused job. Whatever
  S3 names the resubmit-a-different-story action, it is not this endpoint.
- **S4 (reader & wait states)** — the reveal screen; the *"use this one"* rendering at `taps_left == 0`;
  the `SELECT`-then-subscribe fix on `/process/[jobId]` that §4.11 property 1 requires; and re-reading
  the row after a resume so a stale chip list cannot produce a `422` the child can see.
- **`data-deletion`** — the TTL, the reaper, and the terminal status a swept pause gets, constrained
  only by §4.11 property 2 (it is not ADR-025 `failed`). Its object sweep now also covers the
  superseded reference draws of §4.6.
- **`annotation-surface`** — the tapped attribute plus the before/after reference pair (§9).

**Open:**
- **`__interrupt__` as the pause signal is a LangGraph implementation detail**, not a documented
  stable contract, and §4.8 now depends on it for both detection *and* content. If a version bump
  changes it, the alternative is `app_graph.get_state(config)` — `.next` for detection, `.tasks[0].interrupts[0].value`
  for the payload. One change, in one place, because the branch exists exactly once.
- **Chip matching is exact and case-insensitive.** A judge that reports `"an orange sock"` against a
  described `"orange sock"` yields a chip that is arguably already present. The failure mode is a
  redundant chip, not a missing one, and §4.3's fallbacks mean the list is never empty. Fuzzy matching
  is not built.
- **A tap can make the reference worse and the child keeps it** (ADR-029 §2, stated honestly there).
  Unchanged by this spec; §4.6 means the better earlier draw still exists in Storage, but nothing
  offers it back, and nothing should — ranking over the child's head is what the reveal exists to stop.

## 13. Definition of done

1. §2's three contract additions exist, defaulted, with `CURRENT_SCHEMA_VERSION` unchanged.
2. `backend/pipeline/reveal.py` holds the no-reference guard, one `interrupt()`, one partial return,
   and the pure `_project_reveal` with both chip fallbacks. No effect on any path.
3. `graph.py` wires §3: `route_reveal`, the node, the changed `moderation_router` branch, and the
   loop-back edge to `char_bible`.
4. `char_bible` has the targeted mode of §4.5, the per-draw upload path of §4.6, and an ADR-028 loop
   unchanged when `reference_retry is None`.
5. Migration `0005` widens the `status` CHECK and adds `reveal`.
6. `POST /jobs/{id}/confirm` implements §4.9: the 404 → 422 → CAS order, the 200-on-miss, and the
   enqueue rollback.
7. `run_job.py` has one `_finish` shared by both entrypoints, and `resume_storybook_job` never builds
   a `StoryMemory`.
8. `SUPER_STEP_PRELUDE = 15` and `RECURSION_LIMIT` uses it; `IMAGE_BUDGET` is unchanged.
9. Every §7 assertion exists and passes.
10. Backend verify is green and its output is **shown, not claimed**:
    `uv run ruff check . && uv run pytest` from `backend/`.
11. Status line above flips to `built` with the commit range (MASTER_SPEC §7).
12. Every §10 doc hit is fixed in the same change.

**Not done** if: `reveal` performs an effect; a book with no reference can pause; a projected character
can offer zero chips; the cap is enforced only in the endpoint or only in the UI; the endpoint accepts
a `char_id` or `attribute` not offered on that row for that character; a rejected payload or a failed
enqueue consumes the pause; a duplicate confirm enqueues a second resume or returns an error; a redraw
reuses a Storage path; `resume_storybook_job` can construct an initial state; `pages` gains a second
writer; a pause write touches `pages`; `IMAGE_BUDGET` is raised to 15; or `char_ref_mod` gains a
`"passed"` skip without §4.7's clear.

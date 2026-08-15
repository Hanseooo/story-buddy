# ADR-029 — The character reveal: an effect-free pause node, a child-driven single redraw, prelude 9

**Status:** Accepted (2026-07-31) · resolves **D-I** (DECISION_BACKLOG) · **amends ADR-003** (branch count,
not rationale), **ADR-024** (wiring diagram, `fixed_prelude`) and **ADR-025 Decision 4** (the `prelude` term of
the CC-3 breaker) · **corrects `character-bible` §5**, which fixed that term at 6

**Context:** PRD §8 flow step 7 promises the child sees the **moderated** canonical reference(s) before full
generation, with a lightweight confirm / *"try again."* ADR-024's canonical graph contains no such interrupt and
`backend/pipeline/graph.py` runs `char_bible → generate_scene` straight through. The gap was surfaced by
`docs/specs/character-bible.md` §8 and deliberately scoped out of it.

It is load-bearing rather than cosmetic for one measured reason. ADR-028 put a 3-draw acceptance loop in front of
the canonical reference and recorded its own ceiling: at the Phase-0.5 draw quality, **~42% of books still ship an
off-spec reference**. Best-of picks the least-wrong draw; it cannot pick a right one. Nothing in the pipeline
knows that Kiko's sock is orange except the child who wrote it. The confirm button is therefore the largest
un-designed mitigation in the flow, not a nicety.

**And one number is already wrong.** `character-bible` §5 fixes the CC-3 breaker's `prelude` term at **6**
(2 references × 3 draws) *"on the assumption of exactly one machine-driven pass."* That spec is marked **built**.
If the reveal ever ships, the bound is understated and the cost breaker under-trips. Deciding D-I now — rather
than when `kid-flow-ui` is designed — is what gives that constant an owner and a correct value.

**Decision:**

### 1. A dedicated `reveal` node holding an `interrupt()` and no effects.

```
char_bible → [char-ref moderation · Phase 2] → reveal → route_reveal ─ "confirm"   → route_next_scene
                  ▲                                                   └ "try_again" ┘
                  └────────────────────────────────────────────────────────────────
```

The node's body is one `interrupt()` and one partial-return. **It performs no effect** — no provider call, no
upload, no write outside its own return. That property is the whole reason it is a separate node: LangGraph
re-executes a resumed node from the top, so an `interrupt()` placed at the tail of `char_bible` would redraw up
to six references on every *confirm*. Effect-free, re-execution costs nothing.

`route_reveal` is pure and label-returning (ADR-024 Decision 4): `"try_again"` iff `reference_retry` is set
**and** `cost.ref_retry_count < 3`, else `"confirm"`. **The cap is enforced in the router, not only in the UI** —
the resume payload arrives from a client and is a trust boundary.

The loop-back targets `char_bible` rather than clearing `canonical_ref_image` and re-entering blind: the targeted
mode below overwrites the flagged character unconditionally, so `character-bible` invariant 6 (skip any character
that already has a reference) needs no exception and no compensating write.

**ADR-003 is amended on its count, not its rationale.** ADR-003 records *"only two real branch points."* This is a
third. Its reasoning survives intact: `route_reveal` is a pure function of state, deterministic and reproducible,
and the nondeterminism it admits is **a human**, which is categorically not the autonomous LLM orchestrator
ADR-003 rejected for nondeterminism, cost and debuggability. A pre-registered replay of a run replays the
recorded resume payload exactly as it replays the input text.

**ADR-024 is amended** on its wiring diagram (one node, one router, one loop-back edge) and on
`recursion_limit`: `fixed_prelude` grows by **7** — one `reveal`, plus three `char_bible` + `reveal` retry
cycles; conditional edges are not super-steps. This is the *super-step* prelude and remains a different unit from
CC-3's image prelude, exactly as `character-bible` §5 warns.

### 2. One tap = one draw, one judge call, the flagged character only, capped at 3 taps per book.

ADR-028's 3-draw internal loop exists to **substitute for a human judgment that was not available**. At the
reveal the human is present and is a better instrument than the judge. Re-running the machine loop per tap would
make the child wait through three draws and three judge calls to answer a question they have already answered.

So `char_bible` gains a **targeted mode**. When `reference_retry` is set it makes exactly **one**
`text_to_image` call for that `char_id` with the tapped attribute restated in the prompt, **one** `judge` call to
refresh `ref_verdict`, overwrites `canonical_ref_image` and `ref_verdict`, bumps `cost.image_count` by 1, and
clears `reference_retry`. No re-roll, no best-of, one code path away from the ADR-028 loop it sits beside.

**The overwrite is unconditional, and that is the decision, not an oversight.** Best-of over old-versus-new would
let the pipeline discard the draw the child asked for and show them the same picture back — the worst available
answer to *"try again."* The cost is stated honestly: a tap can make the reference worse, and a child who
exhausts the budget keeps it. The child is the judge here; ranking over their head is what ADR-028's best-of is
for when no child is watching.

**The button never dead-ends.** At the cap it becomes *"use this one"* rather than disappearing or refusing —
the same posture ADR-010 and ADR-028 set for scenes and references (never a failed job, never a placeholder).

**The tap is targeted, not blind.** PRD §8's button as written is a blind re-roll: same prompt, new noise, the
same ~42%. `CharacterDescription`'s attributes are already in state and `RefVerdict.attributes_present` already
records which ones the judge could not find, so the reveal screen renders the missing ones as chips and the
tapped one is restated in the redraw prompt. Same cost, targeted instead of stochastic, and it mirrors the
attribute→correction pairing `judge-finetune.md` §4 already defines. It also produces a free human label on
reference quality, which is `annotation-surface`'s currency.

### 3. Contract additions — additive, defaulted, no `schema_version` bump.

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

Both new fields default, so per `story-memory-contract` §3 there is **no `schema_version` bump**, no restart
path and no capstone edit — the same cheapness argument ADR-028 Decision 2 made. `ref_retry_count` is a stored
counter rather than a derived one because the number of taps is not recoverable from `image_count` after the
fact.

### 4. CC-3: `prelude` 6 → 9. CC-1 sequences the build.

The breaker bound of ADR-025 Decision 4 becomes `max_scenes × 2 + 9` — 2 references × 3 draws, plus 3 taps × 1
draw. Worst-case added spend is **3 image draws ≈ $0.06–0.11** on a $0.30–0.65 book, and the typical case is $0
because most children confirm.

PRD §13 line 463 fixes the ordering `input gate → char-ref moderation → reveal → output moderation`. The
char-ref moderation node is Phase 2 and does not exist. Therefore **`reveal` is not wired in Phase 1**: this ADR
freezes the shape, and the node, the status migration and the endpoint all land in Phase 2 alongside the moderation
gate. No unmoderated image can reach a child by construction rather than by discipline.

### 5. Job lifecycle: `awaiting_confirm` + `POST /jobs/{id}/confirm`.

A migration widens the `check` constraint on `jobs.status` to include **`awaiting_confirm`**. Its number is
assigned when it lands, not reserved here — `style-presets` builds first and takes `0002` for
`jobs.style_preset_id`. The worker
sets it when `invoke()` returns with an interrupt pending instead of writing `complete`; `POST /jobs/{id}/confirm`
carries the resume payload and enqueues a second RQ job that resumes the same `thread_id`. The pause machinery
needs nothing new: `run_job.py` already invokes under `PostgresSaver` with `thread_id = job_id`, so the
checkpoint is already durable across processes, and `jobs` is already in the `supabase_realtime` publication, so
PRD flow step 6's processing view observes the transition with no new channel.

`awaiting_confirm` is a status value, not a boolean beside `running`: a job waiting on a human is not running,
and every consumer that switches on status should have to see that.

**Consequences:**

- **`character-bible` §5 is corrected in this change** — CC-3's `prelude` reads 9, and its CC-1 tick names
  `reveal` as the surface it was left open for. Its `built` status survives; the node's code is unchanged until
  the Phase-2 build adds the targeted mode.
- **`story-memory-contract` is edited in the same change** (§2 schema, §5 CC-3). Its `approved` status and frozen
  shape survive — every change is additive with a default.
- **MASTER_SPEC §2 gains a `reveal` row** and the node diagram gains the pause; §5's CC-3 row points at this ADR
  for the corrected bound.
- **Consequences to build** (not this session — `CLAUDE.md §1`), all Phase 2: the two contract fields; the
  `reveal` node and `route_reveal`; `char_bible`'s targeted mode; the `jobs.status` migration; the confirm endpoint; the
  worker's interrupt-pending branch; and the reveal screen in `kid-flow-ui`.
- **Tests the build must leave behind.** `reveal`: confirm → `"confirm"`; try-again → `"try_again"` and
  `ref_retry_count` bumps; a retry payload arriving at the cap → the router returns `"confirm"` anyway (guards
  the trust boundary). `char_bible` targeted mode: exactly one `text_to_image` and one `judge`, only the flagged
  character mutates, `image_count` +1, `reference_retry` cleared.
- **Phase 1 is unaffected.** `graph.py`, `char_bible.py` and the `jobs` table are untouched by this decision;
  `style-presets` is now built (2026-07-31); `prompt-optimizer` is also built (2026-07-31); `image-generator` is also built (2026-07-31). Next: `consistency-checker`.

⚠️ **Open, named rather than solved: a job can sit in `awaiting_confirm` forever.** There is no TTL and no
reaper. A child who closes the tab leaves a paused thread and a checkpoint behind. No resource is held — the
worker returned at the `interrupt()` — so this is storage growth, not a stuck job, and the sweep is one predicate
over the existing `jobs.updated_at`. Handed to `data-deletion` (retention — it must decide the terminal status a
swept pause gets, which is not ADR-025-`failed`) and `rate-limiting` (per-classroom pressure), both carrying a
pointer in `DECISION_BACKLOG.md`, rather than invented here, because the right policy
depends on classroom mechanics this ADR has no information about.

⚠️ **This does not fix the reference generator either.** ADR-028's warning applies unchanged: the fix for the
*rate* is swapping `fal_image_model` (ADR-001's seam). The reveal gives the child recourse on a bad draw; it does
not make good draws more likely.

**Alternatives:**

- **Cut the reveal and amend PRD §8 step 7** — the genuinely lazy option, and the one considered longest. ADR-028's
  loop already does machine-side what the button does by hand, the `jobs` state disappears, and ADR-003's
  two-branch-point rule stays literally true. Rejected because best-of selects the least-wrong draw from a
  population that is 42% wrong, and no automated signal can supply the fact that distinguishes right from
  least-wrong. Cutting it removes the mitigation, not the ceremony.
- **`interrupt()` at the tail of `char_bible`** — no new node, no new edge, and superficially the ADR-028
  precedent of keeping the loop node-internal. Rejected on cost: a resumed node re-executes from the top, so
  every *confirm* would re-pay the entire 6-draw prelude. The precedent does not transfer, because ADR-028's loop
  returns once and this one yields.
- **Two graphs — the run ends at `char_bible`, the confirm invokes a scene-only graph** — no interrupt primitive
  and a plain RQ lifecycle. Rejected: two graphs to keep in sync, `recursion_limit` computed twice, and ADR-024's
  single canonical wiring diagram stops being single. The interrupt primitive is already paid for.
- **`interrupt_before=["generate_scene"]` at compile time** — no node and no `interrupt()` call, but it fires on
  every entry into `generate_scene`, i.e. once per scene rather than once per book. Wrong granularity; making it
  right needs router logic that costs more than the node.
- **A fresh ADR-028 allowance (3 draws + best-of) per tap** — one code path, no second acceptance policy to
  specify. Rejected: it triples the child's wait per tap and inflates `prelude` to `6 × (1 + taps)` to buy a
  machine judgment that the present human supersedes.
- **Spend only the unspent remainder of the original 3 draws** — bounds total cost at the current prelude of 6
  and needs no CC-3 change at all. Rejected on an inversion: a book that exhausted the loop gets zero retries,
  and that is precisely the ~42% population the button exists for.
- **Unbounded taps, with the CC-3 breaker as the only cap** — no counter and no new constant. Rejected on failure
  mode: the breaker's action is job `failed` (ADR-025), so an engaged child would destroy their own book by using
  the feature as intended.
- **3 taps per character (`prelude` 12)** — fairer, in that fixing one character never costs another its
  retries. Rejected as the smaller half of a worse trade: it doubles the pre-scene ceiling and makes `prelude` a
  function of the reference cap, so two constants must thereafter move together.
- **Reuse `running` plus an `awaiting_confirm` boolean column** — leaves the status enum and its consumers
  untouched. Rejected: it makes *"is this job waiting on a human"* a two-column question and lets a paused job
  keep claiming it is running.
- **Defer D-I to the `kid-flow-ui` session** — cheapest today, and the backlog correctly records that D-I blocks
  nothing. Rejected because of `character-bible` §5: deferring leaves a known-wrong cost constant in a spec
  marked `built`, with no owner and no date.

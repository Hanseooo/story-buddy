# ADR-024 — LangGraph node & edge conventions (partial-return, sequential per-scene loop, pure routers)

**Status:** Accepted (2026-07-22) · resolves **D-B** (DECISION_BACKLOG) · **amends ADR-003** (deterministic
state machine) and **ADR-023** (state = `StoryMemory`) · amended 2026-08-13

**Amendment (2026-08-13) — the per-scene loop is five super-steps deep, not four.**

`output_mod` ran once over the finished book, after every scene was drawn. It now runs **once per scene**,
immediately after that scene is finalized, so the deepest path a single scene can take is
`generate_scene → consistency_check → regenerate → consistency_check → output_mod` — five, not four.
Prod job `4f7698d5` (2026-08-12) is the reason it moved: a flag on scene `s2` failed an 8-scene book
*after* all 11 paid images had been drawn, where a per-scene gate would have stopped it at ~2. Decision 3's
formula becomes **`≈ max_scenes × 5 + fixed_prelude`**. `fixed_prelude` (`SUPER_STEP_PRELUDE = 15`,
`kid-flow-pause-lifecycle` §4.13) and `IMAGE_BUDGET` are **unchanged**: this buys graph headroom for a gate
that already ran, not additional images — and the whole point of the move is to spend *fewer*.

**Context:** ADR-003 froze the pipeline as a deterministic LangGraph state machine; ADR-023 froze the runtime
state as the single `StoryMemory` Pydantic model but explicitly deferred *how nodes write to it*. Today the
Phase-0 nodes mutate a 5-field `TypedDict` in place (`state["stage"] = ...; return state`) — a convention no
ADR sanctions and not the LangGraph idiom. Eight Phase-1 nodes will each reinvent the write convention, the
per-scene loop, and the branch wiring unless it is fixed first. This ADR fixes them. It does **not** decide
provider resilience or the failure-screen policy (**D-C**) or the field-order enforcement technique (**D-D**).

**Decision:**

1. **Node signature = partial-return, never in-place mutation.** `def node(state: StoryMemory) -> dict` returns
   a dict of **only the channels it writes**; LangGraph merges each through its channel reducer. Nodes never
   mutate `state` and return the whole object. This replaces the Phase-0 `state[...] = ...; return state`
   pattern wholesale.

2. **`scenes[]` uses an upsert-by-`scene_id` reducer (replace-matching, keep-others).** Declared
   `Annotated[list[Scene], upsert_scenes]` on the contract. A per-scene node reads the current `Scene` from
   `state`, produces a complete updated copy (appending its own `Attempt` if any), and returns
   `{"scenes": [that_scene]}`. The reducer replaces the scene with the matching `scene_id` and leaves the rest
   untouched:

   ```python
   def upsert_scenes(current: list[Scene], update: list[Scene]) -> list[Scene]:
       by_id = {s.scene_id: s for s in current}
       for s in update:
           by_id[s.scene_id] = s      # replace-by-id; the node already built the full scene
       return list(by_id.values())
   ```

   **This corrects ADR-023's "reducer on `scenes[]` *and* `attempts[]`."** There is no separate `attempts`
   reducer, and none is needed: the unit of any future parallelism is the *scene* (unique `scene_id`), so two
   writes never target the same scene's `attempts` concurrently — even under the `Send` escape hatch below.
   Attempts are appended by the owning node against current state, not merged in the reducer. (LangGraph reduces
   top-level channels only, so a nested-field `attempts` reducer was never buildable regardless.) Because scene
   writes never collide, the reducer is not even correctness-critical under the sequential loop — it is kept for
   the slice-write convention and to hold the `Send` escape hatch open at zero cost.

3. **The per-scene loop is sequential; position is derived from data, not a cursor.** No `Send` fan-out, no
   per-scene subgraph, and **no cursor field** (which would reintroduce the mutable-status block ADR-023
   Decision 3 removed). The "current scene" is the first `Scene` whose `final_image_ref is None`. Reference
   wiring:

   ```
   char_bible → [char-ref moderation] → route_next_scene ─ none unprocessed → compose
                                                          └ scene remains    → generate_scene
   generate_scene → consistency_check → route_after_check ─ not finalized → regenerate → consistency_check
                                                           └ finalized     → route_next_scene
   ```

   - **Loop invariant (load-bearing):** every entry into `generate_scene`…`consistency_check` finalizes exactly
     one scene — sets its `final_image_ref` — whether by a passing attempt or by ADR-010 best-of after the one
     allowed retry. The loop terminates because each pass reduces the count of `final_image_ref is None` scenes
     by one.
   - **`recursion_limit` is set explicitly**, derived from the scene cap (a function of ADR-012's word cap):
     `≈ max_scenes × 5 + fixed_prelude` (×4 as first written; see the 2026-08-13 amendment). A normal book exceeds LangGraph's default of 25 super-steps, so this is
     required, not optional. It also **backstops the invariant**: a scene that never finalizes (e.g. a hard
     provider failure) trips `GraphRecursionError` instead of looping forever. The failure *policy* that
     prevents that (retry / off-ramp / failure screen) is **D-C**, not this ADR.
   - **`route_next_scene` sits at the loop head**, so it also handles the empty-`scenes[]` case (segment produced
     none) → straight to `compose`.

4. **Routing functions are pure and label-returning; state writes never happen in a router.** Registered via
   `add_conditional_edges`. A router reads state and returns an edge label; any decision that mutates state
   (best-of selection, setting `final_image_ref`) happens in a **node**. The two real branch points (ADR-003):
   - `route_after_check` (after `consistency_check`): `"regenerate"` if the scene is not finalized and the
     ADR-010 retry budget remains, else loop back to `route_next_scene`.
   - `route_moderation` (char-ref gate now; output-image gate in Phase 2): `"pass" | "fail"`. **The fail-branch
     destination and policy are D-C** (CC-9 failure screen, N=3 off-ramp); this ADR only fixes that the gate is
     a conditional edge with a pure router and a single terminal fail target.
   - *Which node sets `final_image_ref`, and how best-of ranks two failing attempts, are node-internal* — owned
     by the `consistency-checker` / `regeneration-controller` specs, not this ADR.

**Consequences:**
- The Phase-0 nodes are rewritten to partial-return when each is built from its spec; `graph.py` gains the two
  routers and the loop-back edge. Not done in this decision session (CLAUDE.md §1) — this ADR unblocks those
  builds.
- Checkpointing is finer than ADR-005's "per scene": LangGraph checkpoints after every node (super-step), so a
  resume never re-runs an already-completed, already-paid-for `generate_scene`. The at-least-once gap (a crash
  *after* the image API call but *before* the checkpoint re-pays on resume) is a worker idempotency concern —
  **D-C**.
- The `Send` fan-out escape hatch stays open at zero extra design cost: because the reducer is
  upsert-by-`scene_id`, switching the loop to `Send` later is a wiring change in `graph.py`, not a contract
  change. Concurrency policy (rate limits, cost spike) is the reason it is *not* done now — **D-C**.

**Alternatives:** `Send` map fan-out and subgraph-per-scene were considered in the D-B session; sequential was
chosen for ADR-005-literal resumability and to avoid settling D-C's concurrency policy inline. A cursor field
for loop position — rejected (reintroduces mutable status into the contract, ADR-023 Decision 3).

**Handoffs (named so they are not silently absorbed into a build):**
- **D-C** owns: the provider-failure → scene-finalization guarantee (the invariant's teeth), the moderation
  fail-branch policy, worker idempotency, and `recursion_limit`'s exact constant if it becomes cost-relevant.
- **`consistency-checker` / `regeneration-controller` specs** own: which node writes `final_image_ref`, and the
  **best-of ranking signal** — `VlmVerdict` currently carries no scalar score, so ADR-010's "keep the
  higher-scoring image" is under-defined and may force an *additive* `VlmVerdict` field (a normal, non-breaking
  schema change).
- **Build-time verification:** confirm that `Annotated`-field reducers on a Pydantic *model* state (not a
  `TypedDict`) behave as specified against the pinned LangGraph version before relying on it (same discipline as
  ADR-002's "re-query before implementing") — do not assume it from docs.

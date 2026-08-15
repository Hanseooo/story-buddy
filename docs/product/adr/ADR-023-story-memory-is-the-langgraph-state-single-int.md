# ADR-023 — Story Memory is the LangGraph state; single-int versioning; status lives in the job row

**Status:** Accepted (2026-07-22) · resolves **D-A** (DECISION_BACKLOG) · governs the `story-memory-contract` spec

**Context:** MASTER_SPEC §3 names the Story Memory Pydantic model "the" inter-module contract and calls it
"authoritative and versioned," but leaves three things unresolved that every Phase-1 node depends on. Today
`backend/contracts/job_state.py` is an explicit *"Phase 0 provisional"* 5-field `TypedDict`; the real shape
exists only as prose (PRD §19 sketch, MASTER_SPEC §2/§3). This ADR freezes the **structural** decisions;
field-level detail is frozen in the `story-memory-contract` spec written in the same change. The **node
signature / reducer / per-scene-loop conventions are deliberately out of scope** — they are D-B (amends
ADR-003), decided in their own session. The seam is: this ADR fixes *what the state is*; D-B fixes *how nodes
write to it*.

**Decision:**

1. **The LangGraph runtime state *is* the `StoryMemory` Pydantic model** — not a `TypedDict` wrapper holding
   it, and not a decomposition into section channels. One object is simultaneously the inter-module contract,
   the object that flows node-to-node, and the blob checkpointed to Postgres (ADR-005). There is no
   projection layer, so the checkpoint bytes *are* the contract: resume-at-scene-N and export read the same
   validated object with zero translation, and `CLAUDE.md §2` ("a module reads/writes through the schema") is
   satisfied literally because no ad-hoc dict can exist between nodes.
2. **`schema_version: int` (starts at `1`), fail-fast on mismatch, no migration machinery.** Bump it **only**
   on a *breaking* change; additive changes (a new `Optional` field) do not bump it and deserialize via
   Pydantic defaults. On resume the worker compares the checkpoint's `schema_version` to the current one; on
   mismatch it **does not migrate — it restarts the job** (reusing `eval.seed`, so the rebuild is
   reproducible — CC-7). One version covers the whole contract, **including the failure-reason enum**: an enum
   change is a contract change (`CLAUDE.md §2`) and rides the same number. Migration functions are a
   documented later option the version field already makes room for — not built now (YAGNI for 1–3 min jobs
   whose schema changes are human-gated and rare).
3. **Live status/progress is owned solely by the Supabase job row, never by Story Memory.** The job row is
   what Realtime watches (RLS-scoped, cheap to update) and it *references* the checkpoint. Story Memory
   therefore carries **content + durable provenance** (`story_id`, `classroom_id`, `profile_id`, `style`,
   `cost`, `eval.seed`) and **no mutable job/status block** — dropping the PRD §19 `job` sketch object from
   the contract. This removes a dual-source-of-truth for status that Decision 1 would otherwise create.
4. **The failure-reason taxonomy is frozen as a closed 7-value set** (`wrong_colour`, `wrong_species`,
   `wrong_body_feature`, `wrong_clothing`, `wrong_style`, `different_face`, `character_absent` — `judge-finetune.md`
   §4), defined **once** in `backend/contracts/` and imported by the judge verdict schema, the
   regeneration-controller, *and* the Phase-2.5 finetune tooling in `backend/finetune/` (import direction:
   finetune → contracts). Pydantic must reject any value outside it. Extend only in Phase 1, never during
   Phase-2.5 annotation (MASTER_SPEC §7) — a mid-annotation change invalidates every label.

**Consequences:**

- **Nodes read/write `StoryMemory` directly; the top-level model is a mostly-`Optional` container.** Early in a
  run it is nearly empty, so almost every field is `Optional` / `default_factory`. The top-level model is
  therefore a *weak* validator — real per-field validation lives in the **structured-output sub-schemas** at
  each LLM boundary (ADR-002), which is exactly where `CLAUDE.md §2` puts it. "It's Pydantic" must not be
  mistaken for "the pipeline validates completeness mid-run"; it does not.
- **This ADR creates a hard obligation on D-B:** because the whole model is one state object, scene fan-out
  needs a merge reducer on `scenes[]` (and `attempts[]`) or parallel scene writes clobber. Reducer
  annotations will live as `Annotated[...]` metadata **on the contract model's list fields** — a contained,
  honest coupling (the object genuinely *is* the runtime state); Pydantic ignores it for serialization.
  **Resolved by ADR-024:** the reducer is on `scenes[]` **only** — `Annotated[list[Scene], upsert_scenes]`,
  upsert-by-`scene_id` — and there is **no** `attempts[]` reducer (the unit of parallelism is the scene, so
  attempts never collide; a nested-field reducer is not buildable in LangGraph anyway). D-B also chose a
  *sequential* loop over fan-out, so the reducer is not even correctness-critical today; it is kept for the
  slice-write convention and the `Send` escape hatch.
- **Asset fields store durable Storage *paths*, never signed URLs** (`canonical_ref_image`, `image_ref`,
  `final_image_ref`, `audio_ref`) — signed URLs are minted on read (CC-4) and would otherwise expire inside a
  checkpoint.
- **`vlm_verdict` declares `differences_observed` before `same_character`** at the schema level (ADR-004
  amendment). This ADR freezes the *order*; the enforcement technique is **D-D (resolved 2026-07-22):**
  `providers._assert_field_order` compares parsed JSON key order (`json.loads` preserves document order)
  against `schema.model_fields`, immune to a value that quotes a field name (MASTER_SPEC §3).
- The escape hatch, recorded so it is not a re-decision later: if D-B's fan-out design proves section-level
  channels are unavoidable, moving to a `TypedDict` of section channels is a mechanical refactor of the state
  wiring — the frozen field-level schema and this versioning/enum decision are unaffected.

**Alternatives:**

- **`TypedDict` wrapper holding `StoryMemory` as a field** — rejected. Its only benefit (contract stays
  LangGraph-agnostic) is portability to a second runtime that ADR-003/005 guarantees will never exist (YAGNI),
  and a single `story` channel makes fan-out *harder*: parallel scene writes force a reducer that merges whole
  `StoryMemory` objects, burying D-B's problem instead of enabling it.
- **`TypedDict` of top-level section channels** (`input`, `characters`, `scenes`, …), with `StoryMemory` as an
  assembled persistence view — the serious alternative; it fits the §2 node-I/O table and makes per-section
  reducers natural. Rejected *for now* because it buys that fit with a second representation plus
  project/assemble glue — speculative machinery (`CLAUDE.md §6`) until D-B's fan-out proves it necessary. Kept
  as the documented escape hatch above.
- **`schema_version` + migration functions** — rejected as speculative for 1–3 min, human-gated jobs; the
  version field leaves the door open to add them iff a breaking-change-on-live-data case ever appears.
- **No version field (additive-only + drain the queue)** — rejected: contradicts MASTER_SPEC §3 ("versioned"),
  leaves stored artifacts un-stampable, and turns an incompatible mismatch into a silent misparse instead of a
  clean restart.

**Open questions:**

- ~~**D-B** (amends ADR-003): node signature + partial-return convention, the `scenes[]`/`attempts[]` reducers
  this ADR requires, the per-scene loop shape (loop node vs. `Send` fan-out vs. subgraph), and the two
  routing-function branch points.~~ **Resolved → ADR-024** (partial-return; sequential loop; upsert-by-`scene_id`
  reducer on `scenes[]` only; two pure routers).
- ~~**D-D**: robust field-order enforcement for `differences_observed` → `same_character` (this ADR freezes the
  order, not the mechanism).~~ **Resolved (2026-07-22):** parsed-key-order check in `providers._assert_field_order`
  (MASTER_SPEC §3).

**Amendment (2026-07-22) — resolves D-F and D-G** (DECISION_BACKLOG Tier 2; unblocks the
`story-memory-contract` freeze). Both are conventions the contract needs; neither warrants a new ADR number.

- **D-F — where structured-output sub-schemas live.** The dividing line is **embedding, not
  LLM-boundary-ness**: a sub-schema lives in `backend/contracts/` **iff `StoryMemory` embeds it**
  (`VlmVerdict` inside `Attempt`, `CharacterDescription` inside `Character`); a **transient wrapper** the node
  unpacks into contract fields and never persists as-is (`SceneSegmentation` → `scenes[]`) lives **beside
  its node** in `backend/pipeline/`. This is *forced*, not stylistic: `contracts/` must never import from
  `pipeline/`, so any embedded sub-schema **must** be in `contracts/` — "all sub-schemas beside their node" is
  impossible. The CLAUDE.md §6 "crosses a module boundary → through `contracts/`" rule is satisfied because the
  thing that crosses is `StoryMemory`; a transient wrapper is consumed only by its own node (+ generic
  `providers.structured_text` + tests) and **is never imported cross-node** — peers read each other through the
  contract, never through a peer's LLM schema. Note `VlmVerdict` is an LLM-boundary schema that lives in
  `contracts/` *because it is embedded* — do not read this rule as "LLM schemas go beside the node."

- **D-G — id minting for `scene_id` / `char_id` / `loc_id` / `obj_id`.** Format `{prefix}{zero-based-index}`
  with prefixes `s` / `c` / `loc` / `obj` (`loc`/`obj` spelled out — `l0`/`o0` misread as `10`/`00` in traces,
  and these ids exist partly for CC-5 debugging). **Minted once by the node that creates the collection**
  (`segment` → scenes; `story-analyzer` → characters/locations/objects), by assigning the index over the
  parsed list. **The LLM boundary schema carries NO id fields** — the model returns names/descriptions, the
  node assigns ids post-parse; an LLM that emits ids would hallucinate/vary them and defeat mint-once. Ids are
  **stable within a run and across a resume** (LangGraph checkpoints after the minting node, so resume reuses
  persisted ids and never re-mints); a schema-version **restart** discards the checkpoint and mints a fresh set
  from the re-run, which is fine because nothing survives a restart to be inconsistent with. This corrects the
  DECISION_BACKLOG framing "must be deterministic or a restart differs": the real requirement is within-run /
  resume stability (the ADR-024 `scenes[]` reducer keys on `scene_id`), **not** reproducibility from `eval.seed`
  — which LLM non-determinism cannot guarantee anyway. Ids are **run-scoped**, unique within one `StoryMemory`
  (cross-job uniqueness comes from `story_id`), not global. **Invariant (documented ceiling, not guarded):**
  entities are minted once and **never merged or re-indexed** within a run — the reducer trusts this (it
  silently overwrites a duplicate id and silently keeps an orphan); a future merge/dedup node would have to
  revisit this.

**Amendment (2026-07-22b) — resolves the §9 construction gate** (`story-memory-contract` §9; DECISION_BACKLOG
"Recommended next session"). This is provenance-*sourcing*, so it amends Decision 3 rather than opening a new
ADR. The three required provenance fields had no equal Phase-1 source; nothing could construct a `StoryMemory`.

- **`story_id = job_id`.** One job produces one story, so the job's existing `id` (the uuid minted at
  `app/main.py:create_storybook`) *is* the story identity — no new column, no separate uuid. It stays `= job_id`
  across a schema-version restart (same `thread_id`).
- **`classroom_id` / `profile_id` carry Phase-1 dev sentinels** — `settings.dev_classroom_id` /
  `settings.dev_profile_id` in `backend/app/config.py` (values `"dev-classroom"` / `"dev-profile"`, deliberately
  non-uuid so they read as placeholders in CC-5 traces). Both are genuinely Phase-2 concepts (`auth-and-classroom`);
  Phase 1 has no classroom or child profile to name.
- **The worker (`worker/run_job.py`) is the supplier.** It constructs
  `StoryMemory(schema_version=CURRENT_SCHEMA_VERSION, story_id=job_id, classroom_id=settings.dev_classroom_id,
  profile_id=settings.dev_profile_id, input=Input(raw_text=input_text))`. The `create_storybook` insert path and
  the jobs table are unchanged — no provenance columns added.
- **The contract is unweakened.** All three fields stay required and non-defaulted (spec §2 unchanged) — provenance
  is never silently null. When `auth-and-classroom` lands, real selection replaces the two sentinels: a value swap
  at the one construction site, **additive — no contract change and no data migration** (Phase-1 sentinel rows name
  no real classroom, so nothing needs backfilling).

Rejected: **(a) land `auth-and-classroom` first** — inverts the roadmap to build the classroom system before the
pipeline runs, and with no Phase-1 auth flow you would seed a default row anyway (= this decision, plus FK
ceremony); **(b) make the two fields `Optional`** — reopens this frozen contract and spreads null-handling across
every consumer plus a Phase-2 backfill, the exact silent-missing failure Decision 3 exists to prevent.

This closes `story-memory-contract` §9; the `job_state.py` port is now unblocked.

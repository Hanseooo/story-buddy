# StoryBuddy — Decision Backlog

The queue of **decisions not yet made**. Distinct from `ROADMAP.md` (build *order*) and
`ADRs.md` (decisions already *frozen*). This file only holds what is still open.

**How to use it.** Each row below is **one dedicated session** → one ADR (or a MASTER_SPEC /
spec edit). Per `CLAUDE.md §1`, architectural decisions are made in their own session, not
inline while building a module. When a row is decided: write the ADR, delete the row from
this file (git keeps the history), and update the affected spec in the same change.

**ADR numbering.** ADRs are append-only sequential; the last is **ADR-022**, so the next free
number is **ADR-023**. Numbers are assigned *when the ADR is written*, not reserved here —
the items below use stable `D-*` ids instead, because the write order can shift.

**Two non-decisions, recorded so they don't get reopened by reflex:**
- The **provider abstraction layer** is already decided — ADR-015 + `backend/providers.py`
  (four thin functions, one impl each, *"not a plugin framework"*). What's open is its
  *internals* (D-C below), not whether to build a wrapper/adapter layer.
- The **structured-output → Pydantic funnel** is already consistent — every LLM call goes
  through `providers.structured_text` / `judge`. Only the field-order *enforcement technique*
  is open (D-D).

---

## Tier 1 — resolved

- ~~**D-1 · Moderation backstop routing**~~ → **ADR-011 (revised 2026-07-21c):** primary Qwen3Guard-Gen
  on the worker CPU, backstop routed to `gpt-oss-safeguard-20b` on OpenRouter.
- ~~**D-2 · PDF renderer**~~ → **ADR-013 (revised 2026-07-21):** WeasyPrint.

---

## Tier 2 — implementation-architecture (Phase-1 blockers, the real meat)

The ADRs froze *what* (models, pipeline shape); these freeze *how the code is built*. All three
are currently ad-hoc in the Phase-0 skeleton with no governing decision.

### D-A · Story Memory contract: schema shape + versioning  *(new ADR + the `story-memory-contract` spec)*
- **The gate.** Today `backend/contracts/job_state.py` is an explicit *"Phase 0 provisional"*
  5-field `TypedDict`. The real Story Memory exists only as prose (PRD §19, MASTER_SPEC §2/§3).
- **Decide:**
  - Is the **LangGraph state itself** the Pydantic Story Memory model, or a `TypedDict` wrapper
    around it? (Interacts with D-B's node/reducer convention.)
  - How is *"versioned"* (MASTER_SPEC §3) realized — a `schema_version` field? a migration rule?
  - **Freeze the failure-reason enum** as a shared closed set (`wrong_colour`, `wrong_species`,
    `wrong_body_feature`, `wrong_clothing`, `wrong_style`, `different_face`, `character_absent` —
    `judge-finetune.md §4`). It is consumed by **`regeneration-controller`** *and* the Phase-2.5
    annotators; MASTER_SPEC §7 says design it once in Phase 1 or invalidate every later label.
- **Read first:** MASTER_SPEC §3 + §7, PRD §19, `judge-finetune.md §4`, `contracts/job_state.py`,
  `CLAUDE.md §2` (contract-first).
- **Blocks:** *everything downstream.* MASTER_SPEC §7: `story-memory-contract` is written first.
- **Output:** likely a short schema/versioning ADR **plus** the `story-memory-contract` spec.

### D-B · LangGraph node & edge conventions  *(amends ADR-003)*
- **Open:** ADR-003 froze "deterministic state machine," not the code contract. `graph.py` is a
  linear stub whose nodes **mutate the whole dict in place and return it** — a real choice with no
  ADR/spec, and *not* the LangGraph idiom (partial-state returns + reducers).
- **Decide:**
  - Node signature + state-write convention (in-place mutation vs. partial-return + reducers);
    how a node reads/writes only its Story Memory slice; whether nodes may mutate shared lists
    (`scenes[]`) — matters once scenes fan out.
  - **The per-scene loop shape:** `generate → consistency_check → regenerate (best-of)` — a loop
    node vs. `Send`/map-fan-out vs. a subgraph. ADR-003 does not answer this and it shapes
    `generate_scene`, `consistency_check`, and `regenerate` (the last has no file yet).
  - Routing-function pattern for the two real branch points (moderation pass/fail, consistency
    pass/fail) — none exist in code today.
- **Read first:** ADR-003, ADR-005 (checkpointing), ADR-010 (regen policy), `pipeline/graph.py`,
  MASTER_SPEC §2 (node I/O table).
- **Blocks:** Phase-1 pipeline assembly; `regeneration-controller`, `image-generator`,
  `consistency-checker` specs.

### D-C · Provider resilience & failure-mode policy  *(new ADR)*
- **Open:** the provider *layer* exists; its resilience does not. `providers.py` has **no retry,
  no backoff, no rate-limit handling**, and one hardcoded `httpx` timeout (`60.0`). CC-3
  (cost circuit-breaker) and CC-9 (failure screens) are principles with **no backend pattern**.
- **Decide:** retry/backoff/timeout policy; transient-vs-hard error taxonomy; cost circuit-breaker
  (CC-3); node-failure → kid-legible failure screen (CC-9); the **N=3 repeated-failure off-ramp**
  (ADR-012 / MASTER_SPEC §6); the self-refusal soften-and-retry fallback (ADR-011 mechanism 4).
- **Read first:** ADR-005, ADR-010, ADR-011 (mech. 4), ADR-012, MASTER_SPEC §5 (CC-3, CC-9), §6,
  `providers.py`, `worker/run_job.py` (only the top-level try/except exists today).
- **Blocks:** production-readiness of every node; the CC-9 failure-screen UI work.

---

## Tier 3 — convention formalizations (likely MASTER_SPEC edits, not ADRs)

Smaller than Tier 2 and arguably not ADR-weight — but currently undocumented conventions that 8+
Phase-1 nodes will each reinvent if not written down first.

### D-D · Structured-output field-order enforcement
- **Open:** `providers._assert_field_order` enforces ADR-004's reason-then-score by **substring-
  scanning raw JSON** for field names — self-flagged (`# ponytail:`) as able to false-trigger when
  a string value quotes a field name. Every judge/verdict schema depends on it.
- **Decide:** replace with a robust technique (e.g. assert on parsed-key order / a schema-level
  guarantee). Record in MASTER_SPEC §6 or a one-paragraph ADR amendment to ADR-004.

### D-E · Testing-seam convention
- **Open:** `CLAUDE.md §3` says "mock every `providers.py` call," but the **actually-used** seam is
  finer — each node wraps its provider calls in a module-level helper that tests patch
  (`pipeline.analyze.caption_for`, `pipeline.generate_scene.generate_and_store`). Emergent,
  undocumented convention.
- **Decide:** codify the node-helper seam in MASTER_SPEC §6 so Phase-1 nodes follow one pattern.

---

## Feature-spec backlog (not decisions — normal brainstorming → spec flow)

Tracked here for one-file visibility. These follow the `CLAUDE.md §4` spec-before-code workflow
(`docs/specs/`, from `TEMPLATE.md`), **not** the ADR-session flow above. Written just-in-time in
roadmap order. Source: MASTER_SPEC §7.

**Phase 1 (core) — `story-memory-contract` FIRST (see D-A):**
- [ ] `story-memory-contract`  ← freezes MASTER_SPEC §3 for everything downstream
- [ ] `story-analyzer`   *(code: `pipeline/analyze.py` — partial)*
- [ ] `scene-segmentation`   *(code: `pipeline/segment.py` — stub)*
- [ ] `character-bible`   *(code: `pipeline/char_bible.py` — stub)*
- [ ] `style-presets`   *(ADR-022; 3 presets)*
- [ ] `prompt-optimizer`
- [ ] `image-generator`   *(code: `pipeline/generate_scene.py` — partial, still text-to-image)*
- [ ] `consistency-checker`   *(code: `pipeline/consistency_check.py` — stub)*
- [ ] `regeneration-controller`   *(no file yet; needs the D-A failure-reason enum + D-B loop shape)*

**Phase 2 (safety / classroom):**
- [ ] `moderation-stack`   *(D-1 decided → ADR-011c; `input_gate` + output-moderation have no file yet)*
- [ ] `filipino-pii-recognizers`
- [ ] `self-refusal-fallback`
- [ ] `length-guard`
- [ ] `auth-and-classroom`
- [ ] `teacher-dashboard`
- [ ] `classroom-sharing`   *(display-only gallery — no `peer-reflection`/`story-map`, cut per ADR-021)*
- [ ] `narration`   *(ADR-020; `providers.narrate()` not yet implemented)*
- [ ] `export-pdf`   *(D-2 decided → ADR-013: WeasyPrint)*
- [ ] `rate-limiting`
- [ ] `data-deletion`
- [ ] `kid-flow-ui`

**Phase 2.5 (fine-tune):**
- [x] `judge-finetune`  ✅ written

**Phase 3 (eval):**
- [ ] `tier1-rating-harness`
- [ ] `comprehension-instrument`
- [ ] `tier2-fun-toolkit`
- [ ] `metrics-export`

---

## Recommended next session

**D-A (Story Memory contract).** It is the gate — MASTER_SPEC §7 says it is written first, and
D-B's node convention and every Phase-1 spec depend on the schema it freezes. Do D-A, then D-B
(they interact on the state-object question), then D-C. Tier 1 (D-1, D-2) is now closed.

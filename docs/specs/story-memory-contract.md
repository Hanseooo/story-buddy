# Feature Spec — story-memory-contract

**Status:** built (2026-07-29, commits b4fb044–8777217, branch `feat/story-memory-contract` — `backend/contracts/story_memory.py` exists, `job_state.py` deleted, seven nodes on partial-return, `input_gate` entry point wired; shape frozen 2026-07-22; D-F + D-G resolved via ADR-023 amendment; §9 construction gate resolved 2026-07-22b; D-H resolved 2026-07-29 → ADR-028) · **Phase:** 1 · **Owner:** `backend/contracts/` (the Pydantic contract itself — not a pipeline node)
**Derived from:** MASTER_SPEC §2 (system map), §3 (frozen contract) · **Rationale:** ADR-023, ADR-004, ADR-002, ADR-028, PRD §19

> This is the one spec that is not a node. It freezes the **field-level shape** of the Story Memory
> Pydantic model — the inter-module contract every Phase-1 node reads and writes (`CLAUDE.md §2`).
> It is written **first** (MASTER_SPEC §7). Architectural decisions behind it are frozen in **ADR-023**;
> read that ADR before changing anything here.
>
> ✅ **Shape frozen (2026-07-22).** The two conventions this contract needed are resolved in the ADR-023
> amendment: **D-F** (embedded → `contracts/`, transient wrapper → beside its node, so `SceneCaption` moves to
> `pipeline/`) and **D-G** (id minting — see §2.1 below). Freezing the *shape* was not the same as the build
> being runnable; **§9's construction gate is now resolved** (ADR-023 amendment 2026-07-22b): the worker supplies
> `story_id = job_id` and Phase-1 dev sentinels for `classroom_id` / `profile_id`. The port is unblocked.

## 1. Purpose

Define the single Pydantic `StoryMemory` model that is simultaneously (a) the inter-module data contract,
(b) the LangGraph runtime state, and (c) the Postgres checkpoint blob (ADR-023, Decision 1). It also freezes
the **closed failure-reason taxonomy** shared by the judge, the regeneration-controller, and the Phase-2.5
finetune tooling.

## 2. The schema (this is the freeze)

Target module: `backend/contracts/story_memory.py` (replaces the provisional `job_state.py`, which is deleted
when this is built). Everything is `Optional` / `default_factory` unless a value exists at job creation — the
top-level model is a **mostly-optional container**, not a mid-run completeness validator (ADR-023,
Consequences). Real per-field validation lives in each node's structured-output sub-schema at its LLM
boundary (ADR-002).

```python
from enum import Enum
from typing import Annotated, Optional
from pydantic import BaseModel, Field

CURRENT_SCHEMA_VERSION = 1

# --- Closed taxonomy: ONE home, imported by judge schema, regen-controller, finetune tooling ---
class FailureReason(str, Enum):
    wrong_colour       = "wrong_colour"
    wrong_species      = "wrong_species"
    wrong_body_feature = "wrong_body_feature"
    wrong_clothing     = "wrong_clothing"
    wrong_style        = "wrong_style"
    different_face     = "different_face"
    character_absent   = "character_absent"

# --- Analysis products (analyze / char_bible) ---
class CharacterDescription(BaseModel):
    # minimal, aligned to the failure-reason axes; refined by `character-bible` (§8, additive)
    species: Optional[str] = None
    colours: list[str] = Field(default_factory=list)
    body_features: list[str] = Field(default_factory=list)
    clothing: list[str] = Field(default_factory=list)
    notes: Optional[str] = None

# --- Reference acceptance verdict (ADR-028 Decision 3). Reason-then-score, like every judge call. ---
class RefVerdict(BaseModel):
    differences_observed: str          # MUST be declared before matches_description (ADR-004)
    matches_description: bool
    attributes_present: list[str] = Field(default_factory=list)   # best-of key when all draws fail

class Character(BaseModel):
    char_id: str
    name: str
    description: CharacterDescription = Field(default_factory=CharacterDescription)
    canonical_ref_image: Optional[str] = None       # durable Storage PATH, never a signed URL
    ref_moderation_status: Optional[str] = None
    ref_verdict: Optional[RefVerdict] = None        # ADR-028: the reference is checked, not assumed

class Location(BaseModel):     # minimal; refined by `story-analyzer` (§8, additive)
    loc_id: str
    name: str
    description: Optional[str] = None

class StoryObject(BaseModel):  # minimal; refined by `story-analyzer` (§8, additive)
    obj_id: str
    name: str
    description: Optional[str] = None

class TimelineEvent(BaseModel):  # minimal; refined by `story-analyzer` (§8, additive)
    order: int
    summary: str

# --- Input gate ---
class ModerationResult(BaseModel):  # minimal; refined by `moderation-stack` Phase 2 (§8, additive)
    passed: bool = False
    categories: list[str] = Field(default_factory=list)

class Input(BaseModel):
    raw_text: str
    redacted_text: Optional[str] = None   # CC-2: redacted_text is what downstream nodes consume
    word_count: int = 0
    truncated: bool = False
    moderation: Optional[ModerationResult] = None

# --- Style (ADR-007, ADR-022) ---
class Style(BaseModel):
    style_preset_id: Optional[str] = None
    prompt_fragment: Optional[str] = None

# --- Consistency verdict (ADR-004). FIELD ORDER IS LOAD-BEARING. ---
class VlmVerdict(BaseModel):
    differences_observed: str          # MUST be declared before same_character (ADR-004 amendment)
    same_character: bool
    attributes_present: list[str] = Field(default_factory=list)
    style_match: bool = False
    anatomy_intact: bool = True        # ADR-028: merged, missing or duplicated body parts. Declared
                                       # LAST so the ADR-004 ordering above is untouched. Additive →
                                       # no schema_version bump. Best-of (ADR-010) ranks
                                       # lexicographically: same_character → anatomy_intact → style_match.
                                       # ponytail: bool, not a score — widen only if a measured tie forces it.

class Attempt(BaseModel):
    image_ref: str                     # durable Storage PATH
    prompt: Optional[str] = None       # the prompt THIS attempt used; regeneration corrects it (ADR-010),
                                       # so Scene.prompt alone loses per-attempt provenance (CC-5 tracing)
    vlm_verdict: Optional[VlmVerdict] = None
    failure_reasons: list[FailureReason] = Field(default_factory=list)  # closed set; extras rejected
    passed: bool = False

class Scene(BaseModel):
    scene_id: str
    text_excerpt: str
    caption: Optional[str] = None
    characters_present: list[str] = Field(default_factory=list)  # char_ids
    prompt: Optional[str] = None
    attempts: list[Attempt] = Field(default_factory=list)        # no reducer — appended by the owning node (ADR-024, §8)
    final_image_ref: Optional[str] = None                        # best-of (ADR-010); durable path
    regeneration_count: int = 0
    moderation_status: Optional[str] = None

# --- LangGraph reducer (ADR-024): upsert-by-scene_id, replace-matching, keep-others ---
# SCENE LIST ORDER IS THE CONTRACT: dict semantics keep an upserted scene in its original
# slot and append new ones, so order == segmentation order and survives the JSON round-trip.
# The ADR-024 loop ("first Scene whose final_image_ref is None") and page sequence both rely
# on this. There is deliberately no Scene.order field — it would be a second source of truth.
def upsert_scenes(current: list["Scene"], update: list["Scene"]) -> list["Scene"]:
    by_id = {s.scene_id: s for s in current}
    for s in update:
        by_id[s.scene_id] = s      # replace-by-id; the node already built the full scene
    return list(by_id.values())

# --- Accessory blocks ---
class NarrationEntry(BaseModel):
    scene_id: str
    audio_ref: Optional[str] = None    # durable path

class Sharing(BaseModel):
    teacher_approved: bool = False
    in_gallery: bool = False

class Cost(BaseModel):                 # CC-3
    image_count: int = 0
    regen_count: int = 0
    usd_estimate: float = 0.0
    ref_retry_count: int = 0           # ADR-029 — the child's 3-tap reveal budget, per book

class Eval(BaseModel):                 # CC-7
    seed: Optional[int] = None

class ReferenceRetry(BaseModel):       # ADR-029 — set by `reveal`, consumed by `char_bible`
    char_id: str
    attribute: str                     # the tapped chip, restated verbatim in the redraw prompt

# --- Root ---
class StoryMemory(BaseModel):
    schema_version: int                # REQUIRED, no default — see §3
    # durable provenance (ADR-023 Decision 3 — NO mutable job/status block; that lives in the DB job row)
    story_id: str
    classroom_id: str
    profile_id: str
    input: Input
    characters: list[Character] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    objects: list[StoryObject] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    style: Style = Field(default_factory=Style)
    scenes: Annotated[list[Scene], upsert_scenes] = Field(default_factory=list)  # upsert-by-scene_id reducer (ADR-024, §8)
    narration: list[NarrationEntry] = Field(default_factory=list)
    sharing: Sharing = Field(default_factory=Sharing)
    cost: Cost = Field(default_factory=Cost)
    eval: Eval = Field(default_factory=Eval)
    reference_retry: Optional[ReferenceRetry] = None   # ADR-029; None except between `reveal` and `char_bible`
```

### 2.1 ID minting (D-G, ADR-023 amendment)

The four id fields (`scene_id`, `char_id`, `loc_id`, `obj_id`) are bare `str`, but their **values** follow a
fixed convention:

- **Format** `{prefix}{zero-based-index}` — prefixes `s` (scene), `c` (character), `loc` (location),
  `obj` (object). `loc`/`obj` are spelled out on purpose: `l0`/`o0` misread as `10`/`00` in the traces these
  ids exist to make debuggable (CC-5).
- **Minted once, by the node that creates the collection** — `segment` mints `scene_id` over its segmented
  list; `story-analyzer` mints `char_id` / `loc_id` / `obj_id` over the entities it extracts. The node assigns
  the index after parsing the LLM output. **The LLM boundary schema carries no id field** — the model returns
  names/descriptions only; ids that came from the model would vary run-to-run and break mint-once.
- **Stability** — ids are stable **within a run and across a resume** (LangGraph checkpoints after the minting
  node, so resume reuses persisted ids and never re-mints). A `schema_version` **restart** (§3) discards the
  checkpoint and mints a fresh set from the re-run — fine, because nothing survives a restart to be
  inconsistent with. The requirement is within-run/resume stability (the ADR-024 `scenes[]` reducer keys on
  `scene_id`), *not* reproducibility from `eval.seed`.
- **Scope** — unique within one `StoryMemory`; cross-job uniqueness comes from `story_id`. Not global.
- **Invariant (documented ceiling, not guarded):** entities are minted once and **never merged or re-indexed**
  within a run — the `upsert_scenes` reducer trusts this (it silently overwrites a duplicate id and silently
  keeps an orphan). A future merge/dedup node would have to revisit this.

**Who reads/writes which fields** is the MASTER_SPEC §2 node-I/O table — this spec does not restate it. Each
node's own spec declares its contract slice against the fields above.

## 3. Versioning (ADR-023 Decision 2)

- `schema_version: int`, starts at `1`. **Bump only on a breaking change.** Additive changes (a new `Optional`
  field — e.g. the §8 refinements) do **not** bump it and deserialize via Pydantic defaults.
- **It has no default, deliberately.** If it defaulted to `CURRENT_SCHEMA_VERSION`, a checkpoint written
  *without* the key would deserialize as current and pass the check below silently — the exact silent
  misparse ADR-023's alternatives reject. Missing key ⇒ `ValidationError` ⇒ restart. The constructor sets it
  explicitly at job creation.
- On resume, the worker — in `backend/worker/run_job.py`, before handing state to the graph — compares the
  checkpoint's `schema_version` to `CURRENT_SCHEMA_VERSION`; on mismatch, and on a `ValidationError` from a
  missing/unparseable version, it **restarts the job** (reusing `eval.seed` — CC-7). It does **not** migrate.
  No migration machinery in v1.
- One version covers the whole contract, **including `FailureReason`** — an enum change is a contract change.

## 4. Failure-reason taxonomy (frozen — ADR-023 Decision 4)

The 7 values in `FailureReason` above are the **closed set** from `judge-finetune.md §4`. Defined once here in
`backend/contracts/`; imported by the judge verdict schema, the regeneration-controller, and the Phase-2.5
finetune tooling in `backend/finetune/` (import direction: **finetune → contracts**). Pydantic rejects any
value outside it. ~~**Extend only in Phase 1**, never during Phase-2.5 annotation (MASTER_SPEC §7).~~

🔒 **Frozen permanently — ADR-028 Decision 1 (2026-07-29).** The Phase-1 window to extend it was the decision
above, and the decision is **not to**. This is the **identity** taxonomy: every value names an attribute of the
*character* that a regeneration prompt can restate. Anatomy and composition are properties of the *rendering*,
not of the character, and they live on `VlmVerdict.anatomy_intact` instead (ADR-028 Decision 2) — additive, no
version bump, and outside the closed set Objective 4's F1 is computed over. The 7 values are also enumerated
verbatim in four capstone manuscript sources (`methodology.md`, `research_instruments.md`,
`evaluation_instruments_brief.md`, `model_finetuning.md`), so an enum change is a manuscript edit, not a schema
edit. Read ADR-028 before proposing an eighth value.

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-2 PII redaction** — `Input.redacted_text` is the field downstream nodes consume; the contract makes
  the redacted text the persisted/consumed one.
- [x] **CC-3 Cost control** — `Cost` block carries the running per-book counters the circuit-breaker reads.
  `ref_retry_count` (ADR-029) is the one counter that is a *budget* rather than a metric: `route_reveal` caps
  the child's reveal taps at 3, and the breaker bound is `max_scenes × 2 + 9`.
- [x] **CC-4 Security** — all asset fields (`canonical_ref_image`, `image_ref`, `final_image_ref`, `audio_ref`)
  store durable Storage **paths**, never signed URLs; URLs are minted on read.
- [x] **CC-7 Reproducibility** — `Eval.seed` is carried and drives job restarts on version mismatch.
- [x] **CC-10 Checkpointing / resumability** — the model *is* the checkpoint blob (ADR-023); `schema_version`
  gates a clean restart-vs-resume decision.
- [x] **CC-1 Moderation** — the contract *carries* the three gate results (`input.moderation`,
  `Character.ref_moderation_status`, `Scene.moderation_status`); it does not enforce ordering (graph edges do).
- [ ] CC-5, CC-6, CC-8, CC-9 — not the contract's concern (tracing, UI, DB job row).

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Models mocked (there are no model calls here — this is pure schema). Assertions:

- A fully-populated `StoryMemory` round-trips: `StoryMemory(**sm.model_dump()) == sm`.
- A minimal `StoryMemory` — only `story_id`, `classroom_id`, `profile_id`, `input.raw_text` — **validates**
  (proves the mostly-optional container).
- `schema_version` is **required**: `StoryMemory(**{d without "schema_version"})` raises `ValidationError`,
  and it is present after `model_dump()`.
- **Scene order is stable:** upserting a middle scene leaves the list order unchanged; a new `scene_id`
  appends. (Guards the ADR-024 loop position and page sequence — see the reducer comment in §2.)
- **Reducer works on a Pydantic-model state** — construct the graph with `StateGraph(StoryMemory)` against
  the pinned LangGraph version and confirm `Annotated[list[Scene], upsert_scenes]` actually fires on a
  partial return. ADR-024's consequences require verifying this before relying on it; it is a version-
  sensitive behaviour, not a given.
- **Field order:** `VlmVerdict.model_json_schema()["properties"]` lists `differences_observed` **before**
  `same_character` (ADR-004). Declaration order only — **runtime enforcement already exists** and is not this
  spec's job: `providers._assert_field_order` (`backend/providers.py:68-85`) checks parsed key order on every
  structured call, with a regression test at `tests/test_providers.py:83`.
- `Attempt(failure_reasons=["not_a_real_reason"])` raises `ValidationError` (closed taxonomy).
- **`anatomy_intact` is declared last** (ADR-028): `list(VlmVerdict.model_fields)[-1] == "anatomy_intact"`, and
  the §245 `differences_observed`-before-`same_character` assertion still holds with it present.
- **`RefVerdict` reason-then-score:** `model_json_schema()["properties"]` lists `differences_observed` before
  `matches_description` (ADR-004 applies to every judge call, not only the two-image one).
- Assets: no field is asserted to be a URL — a plain path validates. *(Guards against signed-URL storage by
  convention; documented, not type-enforced.)*

## 7. Eval / quality checks

N/A — the contract produces no generated content.

## 8. Linked decisions & open questions

- **ADR-023** — the four structural decisions this spec implements.
- **Resolved → ADR-024** (amends ADR-003): the state-write convention is **partial-return**, the per-scene loop
  is **sequential** (position derived from `final_image_ref is None`, no cursor), and `scenes[]` carries an
  `Annotated[list[Scene], upsert_scenes]` **upsert-by-`scene_id`** reducer (defined in the code block above).
  There is **no** `attempts[]` reducer — attempts are appended by the owning node, and the scene is the unit of
  any parallelism so they never collide. `differences_observed`-before-`same_character` and the closed
  `FailureReason` set are unchanged.
- ~~**Handoff → D-D**~~ → **resolved 2026-07-22:** field-order enforcement is `providers._assert_field_order`
  (parsed-key-order check, MASTER_SPEC §3). This spec freezes the *declaration* order; runtime enforcement is
  already implemented and needs nothing from the contract.
- ~~**Open → D-F / D-G**~~ → **Resolved 2026-07-22 (ADR-023 amendment):** D-F — sub-schema lives in
  `contracts/` iff `StoryMemory` embeds it, else beside its node (so `SceneCaption` → `pipeline/`, §9). D-G —
  id convention in §2.1. Both freeze this spec's shape.
- ~~**Deferred, additive when its spec lands:** a scalar ranking signal on `Attempt` / `VlmVerdict`.~~
  → **Resolved 2026-07-29 (ADR-028 Decision 2).** No scalar. `VlmVerdict` now carries three booleans, and
  ADR-010's *"keep the higher-scoring image"* is a **lexicographic order** over `same_character` →
  `anatomy_intact` → `style_match`. `regeneration-controller` still owns the rule (and any tie-break); what it
  was missing — something to rank on — now exists. Widen to a scalar only if a measured tie forces it.
- **Resolved 2026-07-29 (ADR-028 Decision 3):** the canonical reference is no longer assumed correct
  (amends ADR-007). `char_bible` judges each draw against `CharacterDescription`, re-rolls to a cap of 3 draws,
  keeps the draw with the most `attributes_present` on exhaustion, and persists `Character.ref_verdict`. This is
  a **node-internal loop, not a conditional edge** — ADR-003's branch points and ADR-024's routers are
  unchanged *by ADR-028*. (ADR-029 later added a third branch point for the reveal; that is a separate change
  and does not affect this loop.)
- **Deferred:** `pdf_ref` / composed-book reference for the export leg (MASTER_SPEC §2). Nothing in Phase 1
  writes it; `export-pdf` (Phase 2) adds it additively.
- **Removed 2026-07-22:** `Scene.consistency_check_status` — an untyped `Optional[str]` with no owner spec and
  no defined value set, while `Attempt.passed` and `final_image_ref` already answer the question. Left in, a
  Phase-1 consumer would invent values for it.
- **Field-level details deliberately left minimal, refined later by the normal schema-change process**
  (`CLAUDE.md §2`); all are **additive** (`Optional`), so none bump `schema_version`:
  - `CharacterDescription` — refined by the `character-bible` spec (Phase 1).
  - ~~`Location` / `StoryObject` / `TimelineEvent` — refined by the `story-analyzer` spec (Phase 1).~~
    → **Resolved 2026-07-29: no refinement.** `docs/specs/story-analyzer.md` decided the minimal shapes
    are sufficient for every Phase-1 consumer. No contract change, no `schema_version` bump.
  - `ModerationResult` and the `*_moderation_status` string fields — refined by the `moderation-stack` spec
    (Phase 2).

## 9. Migration off `job_state.py` (every consumer, per `CLAUDE.md §2`)

§2 deletes `backend/contracts/job_state.py`. That is a **breaking change across 14 files**, listed here so the
migration is a checklist rather than a discovery. Verified against the tree 2026-07-22; **re-verified and
corrected 2026-07-29** — every line citation below still resolves exactly, but the count was two short.

> ⚠️ **The original 12 was a grep for `JobState` / `SceneCaption`, and two consumers don't import either.**
> `tests/test_graph_stub.py` and `tests/test_generate_scene_node.py` construct the 5-key state as a **dict
> literal** and assert on `result["caption"]` / `result["image_path"]` — both keys vanish in `StoryMemory`.
> They are invisible to a symbol search and break immediately on `StateGraph(StoryMemory)`. Listed under
> *Tests* below. **The lesson generalises past this migration:** a `TypedDict` contract has consumers coupled
> to its *shape* that no grep for its *name* will find. `StoryMemory` being a real Pydantic model is what
> removes that failure mode.

**State type — `JobState` (TypedDict) → `StoryMemory`:**
- `pipeline/graph.py:4,14` — `StateGraph(JobState)` → `StateGraph(StoryMemory)`.
  **Also during this migration:** add `input_gate` as a pass-through stub node and set it as
  the new entry point (`set_entry_point("input_gate")`). The stub (`backend/pipeline/input_gate.py`)
  reads `state.input.raw_text` and returns
  `{"input": Input(raw_text=..., redacted_text=state.input.raw_text, moderation=ModerationResult(passed=True))}`
  — a no-op that keeps the graph shape correct so Phase 2 (`moderation-stack` spec) is a
  single-file replacement, not a topology change. Mark it
  `# ponytail: stub — Phase 2 moderation-stack replaces with real Qwen3Guard-Gen + Presidio`.
- Six nodes, all currently `def node(state: JobState) -> JobState` with mutate-and-return, the pattern
  ADR-024 §1 replaces wholesale → `def node(state: StoryMemory) -> dict`, partial-return:
  `analyze.py:13`, `segment.py:4`, `char_bible.py:4`, `generate_scene.py:21`, `consistency_check.py:4`,
  `compose.py:4`.

**`SceneCaption` — new home decided (D-F): beside its node, `pipeline/analyze.py`** (transient wrapper, not
embedded in `StoryMemory`).
- Defined `contracts/job_state.py:18` → move to `pipeline/analyze.py`. Update imports: `pipeline/analyze.py:1`,
  `tests/test_analyze_node.py:3`, `tests/test_contracts.py:4`. `tests/test_providers.py:6` imports it only as a
  throwaway sample `BaseModel` to exercise the provider — replace that with a local dummy schema rather than a
  backwards test-dependency on a pipeline node. (`test_contracts.py` tests a node-local schema; consider moving
  those cases to `test_analyze_node.py` when porting.)

**Worker — `worker/run_job.py`:**
- `:15-21` builds a 5-key dict (`job_id`, `input_text`, `caption`, `image_path`, `stage`); `:40-42` reads
  `result["caption"]` / `result["image_path"]`. **Neither key exists in `StoryMemory`** — captions live at
  `scenes[].caption`, images at `scenes[].final_image_ref`. The port replaces this dict with a constructed
  `StoryMemory` and reads results off `scenes[]`.
- ✅ **Provenance sourcing resolved (ADR-023 amendment 2026-07-22b).** The worker is the supplier and constructs
  `StoryMemory(schema_version=CURRENT_SCHEMA_VERSION, story_id=job_id, classroom_id=settings.dev_classroom_id,
  profile_id=settings.dev_profile_id, input=Input(raw_text=input_text))`. `story_id = job_id` (one job = one
  story). `classroom_id` / `profile_id` are Phase-1 dev sentinels in `backend/app/config.py`
  (`"dev-classroom"` / `"dev-profile"`), replaced by real selection when `auth-and-classroom` lands — a value
  swap at this one site, no contract change. The `create_storybook` insert path (`app/main.py`) and the jobs
  table are unchanged; `:10`'s `select("input_text")` stays as-is.

**Tests coupled to the state shape without importing it** (added 2026-07-29 — see the ⚠️ above):
- `tests/test_graph_stub.py:12-19,32-43` — builds the 5-key dict literal, invokes the real compiled graph, and
  asserts `result["stage"] == "compose"`, `result["caption"]`, `result["image_path"]`. The one test that fails
  the instant `StateGraph(JobState)` becomes `StateGraph(StoryMemory)`. Rewrite to construct `StoryMemory` and
  assert against `scenes[].caption` / `scenes[].final_image_ref`.
- `tests/test_generate_scene_node.py:18-29` — same dict-literal pattern; asserts `result["image_path"]` and
  `result["stage"]`.

Both also assert on `stage`, which `StoryMemory` does not carry — job status lives on the **job row**, not in
state (ADR-023). Porting them is not a mechanical rename; decide what they assert on now.

**Also fix while porting** (pre-existing, not caused by this spec): `analyze.py:14` writes a top-level
`caption`, while MASTER_SPEC §2's node-I/O table assigns `scenes[].caption` to `segment`.

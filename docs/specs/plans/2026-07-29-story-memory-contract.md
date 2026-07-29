# Story Memory Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the frozen `StoryMemory` Pydantic contract, port all 14 `job_state.py` consumers to it, and delete `job_state.py`.

**Architecture:** `backend/contracts/story_memory.py` becomes the single model that is simultaneously the inter-module contract, the LangGraph runtime state, and the Postgres checkpoint blob (ADR-023 Decision 1). Nodes change from `def node(state: JobState) -> JobState` mutate-and-return to `def node(state: StoryMemory) -> dict` partial-return (ADR-024 §1). `scenes[]` carries an `Annotated[list[Scene], upsert_scenes]` upsert-by-`scene_id` reducer. The graph gains an `input_gate` pass-through stub as its new entry point so Phase 2's `moderation-stack` is a single-file replacement, not a topology change.

**Tech Stack:** Python 3.12, Pydantic 2.13.4, LangGraph 1.2.8, pytest, ruff, uv.

---

## Global Constraints

- **Source spec:** `docs/specs/story-memory-contract.md`. The §2 code block is a **freeze** — transcribe it verbatim, including comments. Do not add fields, do not reorder fields, do not add validators.
- **`schema_version` has no default.** A missing key must raise `ValidationError`. Never give it `= CURRENT_SCHEMA_VERSION`.
- **Field order is load-bearing** (ADR-004): `differences_observed` before `same_character` in `VlmVerdict`; `differences_observed` before `matches_description` in `RefVerdict`; `anatomy_intact` declared **last** in `VlmVerdict` (ADR-028).
- **`FailureReason` is frozen permanently** (ADR-028 Decision 1). Exactly 7 values. An eighth value is a manuscript edit across four capstone files, not a schema edit.
- **Asset fields store durable Storage paths, never signed URLs** (CC-4): `canonical_ref_image`, `image_ref`, `final_image_ref`, `audio_ref`.
- **Scene list order is the contract.** No `Scene.order` field — it would be a second source of truth.
- **ID convention (§2.1):** `{prefix}{zero-based-index}` — `s`, `c`, `loc`, `obj`. Minted once by the node that creates the collection, after parsing LLM output. The LLM boundary schema carries **no** id field.
- **All commands run from `backend/`.** Lint: `uv run ruff check .` Tests: `uv run pytest`. Line length 120. `ruff format` is **not** adopted — never run it.
- **Deterministic tests mock every model call** (MASTER_SPEC §6 Tier A). Nothing in `providers.py` runs in CI.
- **Do not start `story-analyzer`.** DECISION_BACKLOG says don't; every module built against the old contract is another consumer to migrate. `analyze` stays a stub in this plan.

## Decisions settled during planning

Two forks in the spec were resolved before writing this plan. Both are load-bearing for Tasks 5 and 6.

**D-1 — What replaces `result["stage"]` as proof the graph is wired.**
`StoryMemory` has no `stage` (job status lives on the job row, ADR-023 Decision 3), and with four
pass-through stubs a graph that runs every node and one that runs none produce nearly identical state.
**Resolution: `stream_mode="updates"`.** Probed against the pinned LangGraph 1.2.8: `app.stream(...)`
yields exactly one chunk per node execution, keyed by node name, in execution order — **including
nodes that return `{}`**. This is a strictly better `stage` (ordered, no state field, and it keeps
working as each stub becomes real). Verified probe output: `ran: ['a', 'b', 'c']` where `b` returned `{}`.

**D-2 — Who writes `scenes[].caption`.**
§9's "also fix while porting" says MASTER_SPEC §2's node-I/O table assigns `scenes[].caption` to
`segment`, but D-F freezes `SceneCaption` beside `analyze`. **Resolution: `segment` writes the field
and imports `caption_for` from `pipeline/analyze.py`.** This honors both frozen decisions — the
schema stays beside its node (D-F), the field ownership matches the node-I/O table. `analyze` becomes
a pass-through stub, which is correct: its real content is `story-analyzer`, deliberately not started.

**Probed facts you will rely on** (langgraph 1.2.8, pydantic 2.13.4 — re-verify if either is bumped):
- `StateGraph(StoryMemory)` accepts a Pydantic model as state.
- `Annotated[list[Scene], upsert_scenes]` fires on partial return from a node.
- **`app_graph.invoke()` returns a `dict`, not a `StoryMemory` instance.** Values inside are still
  model instances — so `result["scenes"][0].final_image_ref` is correct and `result.scenes` is not.

---

## File Structure

**Created:**
| File | Responsibility |
|---|---|
| `backend/contracts/story_memory.py` | The frozen contract. Enum, sub-models, reducer, root model, `CURRENT_SCHEMA_VERSION`. Nothing else. |
| `backend/pipeline/input_gate.py` | Pass-through moderation/redaction stub; new graph entry point. Replaced wholesale in Phase 2. |
| `backend/tests/test_story_memory.py` | Every §6 deterministic assertion. Pure schema, no graph. |
| `backend/tests/test_story_memory_reducer.py` | The one test that builds a real `StateGraph(StoryMemory)` to prove the reducer fires (ADR-024 consequences). |
| `backend/tests/test_input_gate_node.py` | The stub's contract: redacted_text populated, moderation passed. |

**Modified:**
| File | Change |
|---|---|
| `backend/pipeline/analyze.py` | Gains `SceneCaption` (moved from `job_state.py`); node becomes a `-> dict` stub returning `{}`. |
| `backend/pipeline/segment.py` | Mints `s0`, writes `text_excerpt` + `caption` via `caption_for`. |
| `backend/pipeline/char_bible.py` | `-> dict` stub returning `{}`. |
| `backend/pipeline/generate_scene.py` | ADR-024 loop: first scene with `final_image_ref is None`; writes `prompt`, `attempts[]`, `final_image_ref`. |
| `backend/pipeline/consistency_check.py` | `-> dict` stub returning `{}`. |
| `backend/pipeline/compose.py` | `-> dict` stub returning `{}`. |
| `backend/pipeline/graph.py` | `StateGraph(StoryMemory)`, `input_gate` node + entry point. |
| `backend/worker/run_job.py` | Constructs `StoryMemory`; reads results off `scenes[]`. |
| `backend/app/config.py` | Adds `dev_classroom_id` / `dev_profile_id` sentinels. |
| `backend/tests/test_analyze_node.py` | Imports `SceneCaption` locally; absorbs `test_contracts.py`'s cases; node test asserts `{}`. |
| `backend/tests/test_providers.py` | Local dummy `BaseModel` instead of importing a pipeline symbol. |
| `backend/tests/test_generate_scene_node.py` | `StoryMemory` input; asserts partial-return shape. |
| `backend/tests/test_graph_stub.py` | `stream_mode="updates"` node-order assertion + `scenes[]` effects. |
| `backend/tests/test_run_job.py` | Fake graph returns `{"scenes": [Scene(...)]}`. |

**Deleted:**
| File | Why |
|---|---|
| `backend/contracts/job_state.py` | Replaced by `story_memory.py` (spec §2). |
| `backend/tests/test_contracts.py` | Its two cases test a node-local schema; they move to `test_analyze_node.py` (spec §9). |

---

## Task 1: The frozen contract module

Pure schema. No consumer touched, `job_state.py` still present and the suite still green after this task.

**Files:**
- Create: `backend/contracts/story_memory.py`
- Test: `backend/tests/test_story_memory.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `CURRENT_SCHEMA_VERSION: int`, `FailureReason(str, Enum)`, `CharacterDescription`, `RefVerdict`, `Character`, `Location`, `StoryObject`, `TimelineEvent`, `ModerationResult`, `Input`, `Style`, `VlmVerdict`, `Attempt`, `Scene`, `upsert_scenes(current: list[Scene], update: list[Scene]) -> list[Scene]`, `NarrationEntry`, `Sharing`, `Cost`, `Eval`, `StoryMemory`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_story_memory.py`:

```python
"""Deterministic contract tests (spec §6). Pure schema — no model calls, no graph."""
import pytest
from pydantic import ValidationError

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Attempt,
    Character,
    Input,
    RefVerdict,
    Scene,
    StoryMemory,
    VlmVerdict,
    upsert_scenes,
)


def _minimal() -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A dog runs in a field."),
    )


def _populated() -> StoryMemory:
    sm = _minimal()
    sm.characters.append(
        Character(
            char_id="c0",
            name="Rex",
            canonical_ref_image="job-1/ref-c0.png",
            ref_verdict=RefVerdict(differences_observed="none", matches_description=True),
        )
    )
    sm.scenes.append(
        Scene(
            scene_id="s0",
            text_excerpt="A dog runs in a field.",
            caption="A happy dog runs.",
            characters_present=["c0"],
            attempts=[
                Attempt(
                    image_ref="job-1/scene-1.png",
                    prompt="A happy dog runs.",
                    vlm_verdict=VlmVerdict(differences_observed="none", same_character=True),
                    failure_reasons=["wrong_colour"],
                    passed=True,
                )
            ],
            final_image_ref="job-1/scene-1.png",
        )
    )
    return sm


def test_populated_story_memory_round_trips():
    sm = _populated()
    assert StoryMemory(**sm.model_dump()) == sm


def test_minimal_story_memory_validates():
    """Proves the mostly-optional container (ADR-023, Consequences)."""
    sm = _minimal()
    assert sm.scenes == []
    assert sm.characters == []


def test_schema_version_is_required():
    """No default, deliberately: a checkpoint missing the key must NOT deserialize as current."""
    data = _minimal().model_dump()
    del data["schema_version"]
    with pytest.raises(ValidationError):
        StoryMemory(**data)


def test_schema_version_survives_model_dump():
    assert _minimal().model_dump()["schema_version"] == CURRENT_SCHEMA_VERSION


def test_upsert_keeps_a_replaced_scene_in_its_original_slot():
    """Scene list order is the contract — the ADR-024 loop and page sequence both rely on it."""
    current = [Scene(scene_id=f"s{i}", text_excerpt=str(i)) for i in range(3)]
    updated = Scene(scene_id="s1", text_excerpt="1", final_image_ref="p.png")
    result = upsert_scenes(current, [updated])

    assert [s.scene_id for s in result] == ["s0", "s1", "s2"]
    assert result[1].final_image_ref == "p.png"


def test_upsert_appends_a_new_scene_id():
    current = [Scene(scene_id="s0", text_excerpt="0")]
    result = upsert_scenes(current, [Scene(scene_id="s1", text_excerpt="1")])
    assert [s.scene_id for s in result] == ["s0", "s1"]


def test_vlm_verdict_declares_reason_before_score():
    """ADR-004: the judge must reason before it scores. Declaration order only —
    runtime enforcement is providers._assert_field_order, tested in test_providers.py."""
    props = list(VlmVerdict.model_json_schema()["properties"])
    assert props.index("differences_observed") < props.index("same_character")


def test_anatomy_intact_is_declared_last():
    """ADR-028: appended at the end so the ADR-004 ordering above is untouched."""
    assert list(VlmVerdict.model_fields)[-1] == "anatomy_intact"


def test_ref_verdict_declares_reason_before_score():
    """ADR-004 applies to every judge call, not only the two-image one."""
    props = list(RefVerdict.model_json_schema()["properties"])
    assert props.index("differences_observed") < props.index("matches_description")


def test_failure_reason_is_a_closed_set():
    with pytest.raises(ValidationError):
        Attempt(image_ref="p.png", failure_reasons=["not_a_real_reason"])


def test_asset_fields_accept_a_plain_storage_path():
    """CC-4: durable paths, never signed URLs. Documented by convention, not type-enforced —
    this asserts nothing rejects a path."""
    scene = Scene(scene_id="s0", text_excerpt="x", final_image_ref="job-1/scene-1.png")
    assert scene.final_image_ref == "job-1/scene-1.png"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_story_memory.py -v
```

Expected: collection error — `ModuleNotFoundError: No module named 'contracts.story_memory'`.

- [ ] **Step 3: Write the contract module**

Create `backend/contracts/story_memory.py`. This is a **verbatim transcription of spec §2** — the comments are part of the freeze, keep them:

```python
"""The frozen Story Memory contract (spec `docs/specs/story-memory-contract.md`, ADR-023).

Simultaneously (a) the inter-module data contract, (b) the LangGraph runtime state, and
(c) the Postgres checkpoint blob. Everything is Optional / default_factory unless a value
exists at job creation — this is a mostly-optional container, NOT a mid-run completeness
validator. Real per-field validation lives in each node's structured-output sub-schema at
its LLM boundary (ADR-002).

Read ADR-023 and ADR-028 before changing anything here.
"""
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


class Eval(BaseModel):                 # CC-7
    seed: Optional[int] = None


# --- Root ---
class StoryMemory(BaseModel):
    schema_version: int                # REQUIRED, no default — see spec §3
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
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_story_memory.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Lint and run the whole suite**

```bash
uv run ruff check . && uv run pytest
```

Expected: all green. `job_state.py` is untouched, so nothing else moved.

- [ ] **Step 6: Commit**

```bash
git add backend/contracts/story_memory.py backend/tests/test_story_memory.py
git commit -m "feat(contracts): add the frozen StoryMemory contract (spec §2, ADR-023/028)"
```

---

## Task 2: Prove the reducer fires on a Pydantic-model state

Spec §6 requires this explicitly: *"ADR-024's consequences require verifying this before relying on it; it is a version-sensitive behaviour, not a given."* This is the gate before Task 5 rewires the real graph. It is a separate test file because it is the only contract test that imports LangGraph.

**Files:**
- Test: `backend/tests/test_story_memory_reducer.py`

**Interfaces:**
- Consumes: `StoryMemory`, `Scene`, `Input`, `CURRENT_SCHEMA_VERSION` from Task 1.
- Produces: nothing importable. It is a version-pin regression guard.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_story_memory_reducer.py`:

```python
"""ADR-024 requires verifying the reducer against the pinned LangGraph before relying on it.
This is version-sensitive behaviour, not a given — if a LangGraph bump breaks it, it breaks here
rather than silently dropping scene writes in production.
"""
from langgraph.graph import END, StateGraph

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, Scene, StoryMemory


def _state(scenes: list[Scene]) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x"),
        scenes=scenes,
    )


def _build(node):
    graph = StateGraph(StoryMemory)
    graph.add_node("n", node)
    graph.set_entry_point("n")
    graph.add_edge("n", END)
    return graph.compile()


def test_reducer_fires_on_a_partial_return():
    """The node returns ONE scene; the other two must survive."""
    def n(state: StoryMemory) -> dict:
        return {"scenes": [state.scenes[1].model_copy(update={"final_image_ref": "p.png"})]}

    app = _build(n)
    result = app.invoke(_state([Scene(scene_id=f"s{i}", text_excerpt=str(i)) for i in range(3)]))

    assert [s.scene_id for s in result["scenes"]] == ["s0", "s1", "s2"]
    assert result["scenes"][1].final_image_ref == "p.png"
    assert result["scenes"][0].final_image_ref is None


def test_reducer_appends_a_new_scene_id_through_the_graph():
    def n(state: StoryMemory) -> dict:
        return {"scenes": [Scene(scene_id="s1", text_excerpt="1")]}

    app = _build(n)
    result = app.invoke(_state([Scene(scene_id="s0", text_excerpt="0")]))
    assert [s.scene_id for s in result["scenes"]] == ["s0", "s1"]


def test_invoke_returns_a_dict_of_model_values():
    """Documented because it bites: invoke() returns a dict, NOT a StoryMemory —
    but the values inside are still model instances. `result["scenes"][0].caption`, never
    `result.scenes`. Consumers in worker/run_job.py depend on this."""
    app = _build(lambda state: {})
    result = app.invoke(_state([Scene(scene_id="s0", text_excerpt="0", caption="hi")]))

    assert isinstance(result, dict)
    assert result["scenes"][0].caption == "hi"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_story_memory_reducer.py -v
```

Expected: FAIL. (If it unexpectedly passes on the first run, that is fine — the module already exists from Task 1 and this test asserts behaviour, not new code. Confirm it passes for the right reason by temporarily changing `Annotated[list[Scene], upsert_scenes]` to a bare `list[Scene]` in `story_memory.py`, re-running to see `test_reducer_fires_on_a_partial_return` fail with only one scene surviving, then reverting.)

- [ ] **Step 3: No implementation needed — confirm and revert any probe edit**

```bash
git diff backend/contracts/story_memory.py
```

Expected: empty. If the probe edit from Step 2 is still present, revert it.

- [ ] **Step 4: Run the full suite**

```bash
uv run ruff check . && uv run pytest
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_story_memory_reducer.py
git commit -m "test(contracts): verify upsert_scenes reducer fires on StateGraph(StoryMemory) (ADR-024)"
```

---

## Task 3: Move `SceneCaption` to its node (D-F)

`SceneCaption` is a transient LLM-boundary wrapper, not embedded in `StoryMemory`, so D-F puts it beside its node. This task touches no state types — `JobState` is still in use afterward and the suite stays green.

**Files:**
- Modify: `backend/pipeline/analyze.py:1`
- Modify: `backend/tests/test_analyze_node.py:3`
- Modify: `backend/tests/test_providers.py:6,20,21,26,33,41,105,106`
- Delete: `backend/tests/test_contracts.py`
- Modify: `backend/contracts/job_state.py:18-19` (remove `SceneCaption`, keep `JobState`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `pipeline.analyze.SceneCaption` — a `BaseModel` with one field, `caption: str`.

- [ ] **Step 1: Move the two `test_contracts.py` cases into `test_analyze_node.py`**

Delete `backend/tests/test_contracts.py`. Rewrite `backend/tests/test_analyze_node.py` — note the import moves to `pipeline.analyze` and the two former contract cases are appended:

```python
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from contracts.job_state import JobState  # noqa: F401  (removed in Task 5)
from pipeline.analyze import SceneCaption, analyze, caption_for


def test_scene_caption_accepts_valid_shape():
    result = SceneCaption.model_validate({"caption": "A dog runs through a sunny field."})
    assert result.caption == "A dog runs through a sunny field."


def test_scene_caption_rejects_missing_field():
    with pytest.raises(ValidationError):
        SceneCaption.model_validate({})


def test_caption_for_returns_validated_caption():
    with patch(
        "pipeline.analyze.structured_text",
        return_value=SceneCaption(caption="A dog runs through a sunny field."),
    ):
        caption = caption_for("A dog runs in a field.")

    assert caption == "A dog runs through a sunny field."


def test_caption_for_passes_the_schema_to_the_provider():
    with patch(
        "pipeline.analyze.structured_text",
        return_value=SceneCaption(caption="x"),
    ) as mock_structured_text:
        caption_for("A dog runs in a field.")

    prompt, schema = mock_structured_text.call_args.args
    assert "A dog runs in a field." in prompt
    assert schema is SceneCaption


def test_analyze_node_sets_caption_and_stage():
    state = {
        "job_id": "t1",
        "input_text": "A dog runs in a field.",
        "caption": None,
        "image_path": None,
        "stage": "queued",
    }
    with patch("pipeline.analyze.caption_for", return_value="stub caption"):
        result = analyze(state)
    assert result["caption"] == "stub caption"
    assert result["stage"] == "analyze"
```

The unused `JobState` import with `# noqa: F401` is deliberate scaffolding for one task only — Task 5 deletes that line along with `test_analyze_node_sets_caption_and_stage`. If ruff still complains, drop the import line entirely; nothing in this file needs it.

- [ ] **Step 2: Replace the backwards test-dependency in `test_providers.py`**

`test_providers.py` imported `SceneCaption` only as a throwaway sample `BaseModel`. A provider test must not depend on a pipeline node. Add a local dummy near the top of `backend/tests/test_providers.py`, replacing the `from contracts.job_state import SceneCaption` line (`:6`):

```python
class _Caption(BaseModel):
    """Local throwaway schema. Provider tests must not import a pipeline node —
    the dependency runs backwards (spec §9)."""
    caption: str
```

Place it directly after the existing `_fake_completion` helper. Then replace every `SceneCaption` occurrence in this file with `_Caption` — there are 8, at lines `20, 21, 26, 33, 41, 105, 106` in the current file (line 26 is `assert kwargs["model"] == "qwen/qwen3-32b"`, which does not mention it; verify by grep rather than by line number):

```bash
grep -n "SceneCaption" tests/test_providers.py
```

- [ ] **Step 3: Move the class into `analyze.py`**

`backend/pipeline/analyze.py` — add the import and the class, leave the node alone for now:

```python
from pydantic import BaseModel

from contracts.job_state import JobState
from providers import structured_text


class SceneCaption(BaseModel):
    caption: str


def caption_for(text: str) -> str:
    result = structured_text(
        f"Write one short, kid-friendly caption (max 20 words) for this story: {text}",
        SceneCaption,
    )
    return result.caption


def analyze(state: JobState) -> JobState:
    state["caption"] = caption_for(state["input_text"])
    state["stage"] = "analyze"
    return state
```

- [ ] **Step 4: Remove `SceneCaption` from `job_state.py`**

`backend/contracts/job_state.py` becomes:

```python
"""Phase 0 provisional subset of the Story Memory contract (MASTER_SPEC §3).
Full field-level schema is frozen in the Phase 1 `story-memory-contract` spec — do not extend
this file with Phase 1 fields; add them there instead.
"""
from typing import Optional, TypedDict


class JobState(TypedDict):
    job_id: str
    input_text: str
    caption: Optional[str]
    image_path: Optional[str]
    stage: str
```

- [ ] **Step 5: Verify no `SceneCaption` import of `contracts` survives**

```bash
grep -rn "job_state import.*SceneCaption\|SceneCaption" --include=*.py . | grep -v ".venv"
```

Expected: hits only in `pipeline/analyze.py` and `tests/test_analyze_node.py`.

- [ ] **Step 6: Run the full suite**

```bash
uv run ruff check . && uv run pytest
```

Expected: all green. `tests/test_contracts.py` is gone; its two cases now run inside `test_analyze_node.py`.

- [ ] **Step 7: Commit**

```bash
git add -A backend/pipeline/analyze.py backend/contracts/job_state.py backend/tests/
git commit -m "refactor(pipeline): move SceneCaption beside its node (D-F, spec §9)"
```

---

## Task 4: Dev provenance sentinels in config

Small and standalone: the worker in Task 6 needs `classroom_id` / `profile_id` values that do not exist yet (ADR-023 amendment 2026-07-22b).

**Files:**
- Modify: `backend/app/config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `settings.dev_classroom_id: str` (default `"dev-classroom"`), `settings.dev_profile_id: str` (default `"dev-profile"`).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_story_memory.py`:

```python
def test_dev_provenance_sentinels_exist():
    """Phase-1 sentinels (ADR-023 amendment 2026-07-22b). Replaced by real selection when
    `auth-and-classroom` lands — a value swap at one site in worker/run_job.py, no contract change."""
    from app.config import settings

    assert settings.dev_classroom_id == "dev-classroom"
    assert settings.dev_profile_id == "dev-profile"
```

- [ ] **Step 2: Run it to verify it fails**

```bash
uv run pytest tests/test_story_memory.py::test_dev_provenance_sentinels_exist -v
```

Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'dev_classroom_id'`.

- [ ] **Step 3: Add the fields**

In `backend/app/config.py`, insert immediately after the `frontend_origin` line (`:14`):

```python
    # Phase-1 dev provenance sentinels (ADR-023 amendment 2026-07-22b). The worker supplies
    # story_id = job_id; these two stand in until `auth-and-classroom` lands. Swapping them for
    # real selection is a value change at one call site — never a contract change.
    dev_classroom_id: str = "dev-classroom"
    dev_profile_id: str = "dev-profile"
```

- [ ] **Step 4: Run it to verify it passes**

```bash
uv run ruff check . && uv run pytest
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_story_memory.py
git commit -m "feat(config): add Phase-1 dev classroom/profile sentinels (ADR-023 amendment)"
```

---

## Task 5: Port the graph and all seven nodes to `StoryMemory`

**This task is atomic and cannot be split.** Every node is imported by `graph.py`; porting one node while the graph still declares `StateGraph(JobState)` leaves the suite red with no independently testable deliverable in between. Expect a large single commit.

**Files:**
- Create: `backend/pipeline/input_gate.py`
- Create: `backend/tests/test_input_gate_node.py`
- Modify: `backend/pipeline/analyze.py:13-16`, `segment.py:1-6`, `char_bible.py:1-6`, `generate_scene.py:2,21-25`, `consistency_check.py:1-6`, `compose.py:1-6`
- Modify: `backend/pipeline/graph.py:4,14,22`
- Modify: `backend/tests/test_graph_stub.py`, `test_generate_scene_node.py`, `test_analyze_node.py`

**Interfaces:**
- Consumes: `StoryMemory`, `Scene`, `Attempt`, `Input`, `ModerationResult` from Task 1; `caption_for` and `SceneCaption` from `pipeline.analyze` (Task 3).
- Produces: seven node callables, all `(state: StoryMemory) -> dict`: `input_gate`, `analyze`, `segment`, `char_bible`, `generate_scene`, `consistency_check`, `compose`. Plus `build_graph(checkpointer=None)` returning a compiled graph over `StoryMemory` with entry point `input_gate`.

- [ ] **Step 1: Write the failing graph test**

Replace `backend/tests/test_graph_stub.py` entirely:

```python
"""The one test proving the graph is wired at all.

`StoryMemory` carries no `stage` — job status lives on the job row (ADR-023 Decision 3) — and
with four pass-through stubs a graph that runs every node and one that runs none produce nearly
identical state. `stream_mode="updates"` yields exactly one chunk per node execution, keyed by
node name, in order, INCLUDING nodes that return {}. That is the replacement for `stage`.
"""
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
from pipeline.graph import build_graph

EXPECTED_ORDER = [
    "input_gate",
    "analyze",
    "segment",
    "char_bible",
    "generate_scene",
    "consistency_check",
    "compose",
]


def _initial_state(story_id: str) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id=story_id,
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A dog runs in a field."),
    )


def _mock_call_points(monkeypatch):
    monkeypatch.setattr("pipeline.analyze.caption_for", lambda text: "stub caption")
    monkeypatch.setattr("pipeline.segment.caption_for", lambda text: "stub caption")
    monkeypatch.setattr(
        "pipeline.generate_scene.generate_and_store",
        lambda prompt, story_id: "stub/path.png",
    )


def test_stub_graph_runs_all_nodes_in_order(monkeypatch):
    _mock_call_points(monkeypatch)
    app_graph = build_graph()

    ran = [
        next(iter(chunk))
        for chunk in app_graph.stream(
            _initial_state("test-job"),
            config={"configurable": {"thread_id": "test-job"}},
            stream_mode="updates",
        )
    ]

    assert ran == EXPECTED_ORDER


def test_stub_graph_full_run_with_real_call_points_mocked(monkeypatch):
    _mock_call_points(monkeypatch)
    app_graph = build_graph()

    result = app_graph.invoke(
        _initial_state("test-job-2"), config={"configurable": {"thread_id": "test-job-2"}}
    )

    # invoke() returns a dict; the values inside are still model instances.
    assert result["input"].redacted_text == "A dog runs in a field."
    assert result["input"].moderation.passed is True
    assert [s.scene_id for s in result["scenes"]] == ["s0"]
    assert result["scenes"][0].caption == "stub caption"
    assert result["scenes"][0].final_image_ref == "stub/path.png"
```

- [ ] **Step 2: Write the failing `input_gate` test**

Create `backend/tests/test_input_gate_node.py`:

```python
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
from pipeline.input_gate import input_gate


def test_input_gate_passes_raw_text_through_as_redacted_and_marks_moderation_passed():
    """CC-2: redacted_text is what downstream nodes consume, so the stub must populate it —
    a null here silently starves every node after it."""
    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A dog runs in a field."),
    )

    result = input_gate(state)

    assert result["input"].raw_text == "A dog runs in a field."
    assert result["input"].redacted_text == "A dog runs in a field."
    assert result["input"].moderation.passed is True
```

- [ ] **Step 3: Write the failing `generate_scene` test**

Replace the second test in `backend/tests/test_generate_scene_node.py` (keep `test_generate_and_store_uploads_image_bytes` exactly as it is):

```python
from unittest.mock import MagicMock, patch

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, Scene, StoryMemory
from pipeline.generate_scene import generate_and_store, generate_scene


def test_generate_and_store_uploads_image_bytes():
    fake_supabase = MagicMock()

    with patch("pipeline.generate_scene.text_to_image", return_value=b"fake-png-bytes"), \
         patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase):
        path = generate_and_store("a friendly dog", "job-123")

    assert path == "job-123/scene-1.png"
    fake_supabase.storage.from_.assert_called_with("storybook-images")
    fake_supabase.storage.from_.return_value.upload.assert_called_once()


def _state(scenes: list[Scene]) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-123",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        scenes=scenes,
    )


def test_generate_scene_returns_a_partial_scene_update():
    """ADR-024: partial-return, not mutate-and-return. The node returns ONLY the scene it wrote."""
    state = _state([Scene(scene_id="s0", text_excerpt="x", caption="a friendly dog")])

    with patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-1.png"):
        result = generate_scene(state)

    assert set(result) == {"scenes"}
    scene, = result["scenes"]
    assert scene.scene_id == "s0"
    assert scene.final_image_ref == "job-123/scene-1.png"
    assert scene.prompt == "a friendly dog"


def test_generate_scene_records_the_attempt_for_provenance():
    """CC-5: Scene.prompt alone loses per-attempt provenance once regeneration corrects it (ADR-010)."""
    state = _state([Scene(scene_id="s0", text_excerpt="x", caption="a friendly dog")])

    with patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-1.png"):
        result = generate_scene(state)

    attempt, = result["scenes"][0].attempts
    assert attempt.image_ref == "job-123/scene-1.png"
    assert attempt.prompt == "a friendly dog"


def test_generate_scene_picks_the_first_scene_without_an_image():
    """ADR-024: loop position is derived from `final_image_ref is None` — there is no cursor."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", caption="done", final_image_ref="already.png"),
        Scene(scene_id="s1", text_excerpt="1", caption="next"),
    ])

    with patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-2.png"):
        result = generate_scene(state)

    scene, = result["scenes"]
    assert scene.scene_id == "s1"


def test_generate_scene_is_a_no_op_when_every_scene_has_an_image():
    state = _state([Scene(scene_id="s0", text_excerpt="0", final_image_ref="already.png")])

    with patch("pipeline.generate_scene.generate_and_store") as mock_store:
        result = generate_scene(state)

    assert result == {}
    mock_store.assert_not_called()
```

- [ ] **Step 4: Write the failing `segment` / `analyze` tests**

Replace `test_analyze_node_sets_caption_and_stage` in `backend/tests/test_analyze_node.py` (and drop the now-dead `from contracts.job_state import JobState` line added in Task 3):

```python
def test_analyze_is_a_pass_through_stub():
    """`analyze`'s real content is the story-analyzer spec, deliberately not started
    (DECISION_BACKLOG). It owns `caption_for` (D-F) but writes no state — `segment` owns
    scenes[].caption per MASTER_SPEC §2's node-I/O table."""
    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="t1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A dog runs in a field.", redacted_text="A dog runs in a field."),
    )
    assert analyze(state) == {}
```

Add at the top of that file:

```python
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
```

Create `backend/tests/test_segment_node.py`:

```python
from unittest.mock import patch

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
from pipeline.segment import segment


def _state(raw: str, redacted: str | None) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="t1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text=raw, redacted_text=redacted),
    )


def test_segment_mints_a_zero_based_scene_id():
    """§2.1: ids are `{prefix}{zero-based-index}`, minted by the node that creates the collection."""
    with patch("pipeline.segment.caption_for", return_value="stub caption"):
        result = segment(_state("A dog runs in a field.", "A dog runs in a field."))

    scene, = result["scenes"]
    assert scene.scene_id == "s0"
    assert scene.caption == "stub caption"
    assert scene.text_excerpt == "A dog runs in a field."


def test_segment_captions_the_redacted_text_not_the_raw_text():
    """CC-2: redacted_text is what downstream nodes consume. Sending raw_text to the model
    leaks exactly the PII the gate removed."""
    with patch("pipeline.segment.caption_for", return_value="x") as mock_caption_for:
        segment(_state("Ana lives on Elm St.", "[NAME] lives on [ADDRESS]."))

    mock_caption_for.assert_called_once_with("[NAME] lives on [ADDRESS].")
```

- [ ] **Step 5: Run all four test files to verify they fail**

```bash
uv run pytest tests/test_graph_stub.py tests/test_input_gate_node.py \
  tests/test_generate_scene_node.py tests/test_segment_node.py -v
```

Expected: collection errors — `No module named 'pipeline.input_gate'`, and `ImportError` / `TypeError` from the nodes still taking `JobState`.

- [ ] **Step 6: Create the `input_gate` stub**

Create `backend/pipeline/input_gate.py`:

```python
from contracts.story_memory import Input, ModerationResult, StoryMemory


def input_gate(state: StoryMemory) -> dict:
    # ponytail: stub — Phase 2 moderation-stack replaces with real Qwen3Guard-Gen + Presidio.
    # It exists now so the graph shape is already correct: Phase 2 is a single-file swap,
    # not a topology change (spec §9).
    return {
        "input": Input(
            raw_text=state.input.raw_text,
            redacted_text=state.input.raw_text,
            moderation=ModerationResult(passed=True),
        )
    }
```

- [ ] **Step 7: Port `analyze`**

`backend/pipeline/analyze.py` — replace the `JobState` import and the node body:

```python
from pydantic import BaseModel

from contracts.story_memory import StoryMemory
from providers import structured_text


class SceneCaption(BaseModel):
    caption: str


def caption_for(text: str) -> str:
    result = structured_text(
        f"Write one short, kid-friendly caption (max 20 words) for this story: {text}",
        SceneCaption,
    )
    return result.caption


def analyze(state: StoryMemory) -> dict:
    # ponytail: stub — the `story-analyzer` spec fills this in (characters, locations, objects,
    # timeline) and mints c/loc/obj ids per §2.1. Deliberately not started: DECISION_BACKLOG.
    # `caption_for` lives here per D-F (transient wrapper beside its node); `segment` calls it.
    return {}
```

- [ ] **Step 8: Port `segment`**

`backend/pipeline/segment.py`:

```python
from contracts.story_memory import Scene, StoryMemory
from pipeline.analyze import caption_for


def segment(state: StoryMemory) -> dict:
    # ponytail: one scene per story. The real segmenter splits into pages and mints s0..sN;
    # this mints s0 only. scene_id convention: §2.1.
    text = state.input.redacted_text or state.input.raw_text
    return {"scenes": [Scene(scene_id="s0", text_excerpt=text, caption=caption_for(text))]}
```

- [ ] **Step 9: Port the three remaining pass-through stubs**

`backend/pipeline/char_bible.py`:

```python
from contracts.story_memory import StoryMemory


def char_bible(state: StoryMemory) -> dict:
    # ponytail: stub — the `character-bible` spec fills this in (canonical refs + ref_verdict).
    return {}
```

`backend/pipeline/consistency_check.py`:

```python
from contracts.story_memory import StoryMemory


def consistency_check(state: StoryMemory) -> dict:
    # ponytail: stub — the `consistency-check` spec fills this in (VLM verdict per attempt).
    return {}
```

`backend/pipeline/compose.py`:

```python
from contracts.story_memory import StoryMemory


def compose(state: StoryMemory) -> dict:
    # ponytail: stub — the `compose` spec fills this in (page assembly).
    return {}
```

- [ ] **Step 10: Port `generate_scene`**

`backend/pipeline/generate_scene.py` — `generate_and_store` is unchanged; only the node changes:

```python
from app.db import get_supabase_client
from contracts.story_memory import Attempt, StoryMemory
from providers import text_to_image

BUCKET = "storybook-images"


def generate_and_store(prompt: str, job_id: str) -> str:
    # ponytail: text-to-image, no character reference yet. Phase 1's char_bible node
    # produces the reference and this switches to providers.edit_image (ADR-007).
    image_bytes = text_to_image(prompt)

    path = f"{job_id}/scene-1.png"
    supabase = get_supabase_client()
    supabase.storage.from_(BUCKET).upload(
        path, image_bytes, {"content-type": "image/png", "upsert": "true"}
    )
    return path


def generate_scene(state: StoryMemory) -> dict:
    # ADR-024: loop position is the first scene with no final_image_ref — no cursor field.
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is None:
        return {}

    prompt = scene.caption or scene.text_excerpt
    path = generate_and_store(prompt, state.story_id)
    return {
        "scenes": [
            scene.model_copy(
                update={
                    "prompt": prompt,
                    # CC-5: the attempt carries the prompt THIS draw used; regeneration corrects
                    # Scene.prompt and would otherwise erase the provenance (ADR-010).
                    "attempts": [*scene.attempts, Attempt(image_ref=path, prompt=prompt, passed=True)],
                    "final_image_ref": path,
                }
            )
        ]
    }
```

Note: `generate_and_store` still hardcodes `scene-1.png` while the scene is `s0`. That is pre-existing and out of scope for this port — it becomes `{story_id}/{scene_id}.png` when the real segmenter produces more than one scene. Leave it, and leave its test asserting `"job-123/scene-1.png"`.

- [ ] **Step 11: Flip the graph**

`backend/pipeline/graph.py`:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from contracts.story_memory import StoryMemory
from pipeline.input_gate import input_gate
from pipeline.analyze import analyze
from pipeline.segment import segment
from pipeline.char_bible import char_bible
from pipeline.generate_scene import generate_scene
from pipeline.consistency_check import consistency_check
from pipeline.compose import compose


def build_graph(checkpointer=None):
    graph = StateGraph(StoryMemory)
    graph.add_node("input_gate", input_gate)
    graph.add_node("analyze", analyze)
    graph.add_node("segment", segment)
    graph.add_node("char_bible", char_bible)
    graph.add_node("generate_scene", generate_scene)
    graph.add_node("consistency_check", consistency_check)
    graph.add_node("compose", compose)

    graph.set_entry_point("input_gate")
    graph.add_edge("input_gate", "analyze")
    graph.add_edge("analyze", "segment")
    graph.add_edge("segment", "char_bible")
    graph.add_edge("char_bible", "generate_scene")
    graph.add_edge("generate_scene", "consistency_check")
    graph.add_edge("consistency_check", "compose")
    graph.add_edge("compose", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
```

- [ ] **Step 12: Run the ported tests to verify they pass**

```bash
uv run pytest tests/test_graph_stub.py tests/test_input_gate_node.py \
  tests/test_generate_scene_node.py tests/test_segment_node.py tests/test_analyze_node.py -v
```

Expected: all pass. `tests/test_run_job.py` is still red — Task 6 fixes it.

- [ ] **Step 13: Commit**

```bash
git add -A backend/pipeline backend/tests
git commit -m "feat(pipeline): port graph and all nodes to StoryMemory partial-return (ADR-023, ADR-024)

Adds input_gate as the new entry point so Phase 2 moderation is a single-file swap.
segment now owns scenes[].caption per MASTER_SPEC §2's node-I/O table; analyze keeps
caption_for (D-F) but writes no state. test_graph_stub asserts node order via
stream_mode=updates, replacing the removed 'stage' field (ADR-023 Decision 3)."
```

---

## Task 6: Port the worker

**Files:**
- Modify: `backend/worker/run_job.py:15-21,36-43`
- Modify: `backend/tests/test_run_job.py:15-20`

**Interfaces:**
- Consumes: `StoryMemory`, `Input`, `CURRENT_SCHEMA_VERSION` (Task 1); `settings.dev_classroom_id` / `settings.dev_profile_id` (Task 4); `build_graph` over `StoryMemory` (Task 5).
- Produces: `run_storybook_job(job_id: str) -> None` — unchanged signature.

- [ ] **Step 1: Write the failing test**

Replace `backend/tests/test_run_job.py`:

```python
from unittest.mock import MagicMock, patch

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Scene
from worker.run_job import run_storybook_job


def _fake_supabase() -> MagicMock:
    fake = MagicMock()
    select_chain = fake.table.return_value.select.return_value.eq.return_value.single.return_value
    select_chain.execute.return_value.data = {"input_text": "A dog runs in a field."}
    return fake


def _fake_graph() -> MagicMock:
    graph = MagicMock()
    # invoke() returns a dict whose values are model instances (verified against langgraph 1.2.8).
    graph.invoke.return_value = {
        "scenes": [
            Scene(
                scene_id="s0",
                text_excerpt="A dog runs in a field.",
                caption="stub caption",
                final_image_ref="job-1/scene-1.png",
            )
        ]
    }
    return graph


def test_run_storybook_job_updates_row_on_success():
    fake_supabase = _fake_supabase()
    fake_checkpointer_cm = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    update_calls = fake_supabase.table.return_value.update.call_args_list
    final_update = update_calls[-1][0][0]
    assert final_update["status"] == "complete"
    assert final_update["caption"] == "stub caption"
    assert final_update["image_path"] == "job-1/scene-1.png"


def test_run_storybook_job_constructs_story_memory_with_dev_provenance():
    """ADR-023 amendment 2026-07-22b: the worker is the supplier. story_id = job_id
    (one job = one story); classroom/profile are Phase-1 sentinels swapped at this one site."""
    fake_supabase = _fake_supabase()
    fake_checkpointer_cm = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    initial_state = fake_graph.invoke.call_args.args[0]
    assert initial_state.schema_version == CURRENT_SCHEMA_VERSION
    assert initial_state.story_id == "job-1"
    assert initial_state.classroom_id == "dev-classroom"
    assert initial_state.profile_id == "dev-profile"
    assert initial_state.input.raw_text == "A dog runs in a field."


def test_run_storybook_job_tolerates_a_run_that_produced_no_scenes():
    """A graph that errored past the DB write must not crash the worker with IndexError —
    the row gets nulls and the failure is visible, not a stack trace in the queue."""
    fake_supabase = _fake_supabase()
    fake_checkpointer_cm = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = MagicMock()
    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {"scenes": []}

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-3")

    final_update = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final_update["caption"] is None
    assert final_update["image_path"] is None


def test_run_storybook_job_marks_failed_on_exception():
    fake_supabase = _fake_supabase()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", side_effect=RuntimeError("db down")):
        try:
            run_storybook_job("job-2")
            assert False, "expected RuntimeError to propagate"
        except RuntimeError:
            pass

    update_calls = fake_supabase.table.return_value.update.call_args_list
    failed_update = update_calls[-1][0][0]
    assert failed_update["status"] == "failed"
    assert "db down" in failed_update["error"]
```

- [ ] **Step 2: Run it to verify it fails**

```bash
uv run pytest tests/test_run_job.py -v
```

Expected: FAIL — `run_job.py` still builds the 5-key dict and reads `result["caption"]`, so `test_run_storybook_job_updates_row_on_success` raises `KeyError: 'caption'` and the provenance test raises `AttributeError` on a dict.

- [ ] **Step 3: Port the worker**

`backend/worker/run_job.py`:

```python
from langgraph.checkpoint.postgres import PostgresSaver

from app.config import settings
from app.db import get_supabase_client
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
from pipeline.graph import build_graph


def run_storybook_job(job_id: str) -> None:
    supabase = get_supabase_client()
    row = supabase.table("jobs").select("input_text").eq("id", job_id).single().execute()
    input_text = row.data["input_text"]

    supabase.table("jobs").update({"status": "running"}).eq("id", job_id).execute()

    # ADR-023 amendment 2026-07-22b: the worker is the supplier of durable provenance.
    # story_id = job_id (one job = one story). classroom/profile are Phase-1 dev sentinels;
    # `auth-and-classroom` swaps these two values here and changes nothing else.
    initial_state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id=job_id,
        classroom_id=settings.dev_classroom_id,
        profile_id=settings.dev_profile_id,
        input=Input(raw_text=input_text),
    )

    try:
        with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
            checkpointer.setup()
            app_graph = build_graph(checkpointer=checkpointer)
            result = app_graph.invoke(
                initial_state, config={"configurable": {"thread_id": job_id}}
            )
    except Exception as exc:
        supabase.table("jobs").update(
            {"status": "failed", "error": str(exc)}
        ).eq("id", job_id).execute()
        raise

    # invoke() returns a dict; the values inside are model instances.
    # Captions live at scenes[].caption, images at scenes[].final_image_ref — the old
    # top-level `caption` / `image_path` keys do not exist in StoryMemory.
    scenes = result["scenes"]
    first = scenes[0] if scenes else None

    supabase.table("jobs").update(
        {
            "status": "complete",
            "current_stage": "compose",
            "caption": first.caption if first else None,
            "image_path": first.final_image_ref if first else None,
        }
    ).eq("id", job_id).execute()
```

The `jobs` table, the `create_storybook` insert path in `app/main.py`, and `:10`'s `select("input_text")` are all unchanged.

**Not implemented here, deliberately:** spec §3's resume-time `schema_version` comparison and job restart. Nothing writes a checkpoint at a different version yet, and `CURRENT_SCHEMA_VERSION` is still `1` — the check has no reachable failing branch to test. It belongs to the first task that bumps the version or adds real resume handling.

- [ ] **Step 4: Run it to verify it passes**

```bash
uv run pytest tests/test_run_job.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run the full suite**

```bash
uv run ruff check . && uv run pytest
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/worker/run_job.py backend/tests/test_run_job.py
git commit -m "feat(worker): construct StoryMemory and read results off scenes[] (ADR-023 amendment)"
```

---

## Task 7: Delete `job_state.py`

**Files:**
- Delete: `backend/contracts/job_state.py`

**Interfaces:**
- Consumes: nothing — this task only removes.
- Produces: nothing.

- [ ] **Step 1: Prove there are no consumers left**

```bash
grep -rn "job_state\|JobState" --include=*.py . | grep -v ".venv"
```

Expected: **no output.** Any hit is a consumer Tasks 3–6 missed — port it before deleting. Also check non-Python references:

```bash
grep -rn "job_state" --include=*.md --include=*.toml . | grep -v ".venv" | grep -v "docs/specs/story-memory-contract.md"
```

Expected: hits only in docs that describe the migration (which Task 8 updates). Note each one for Task 8.

- [ ] **Step 2: Delete the file**

```bash
git rm backend/contracts/job_state.py
```

- [ ] **Step 3: Run the full suite**

```bash
uv run ruff check . && uv run pytest
```

Expected: all green. This is the moment the port is real — if anything imported `job_state` lazily, it fails here.

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor(contracts): delete job_state.py — StoryMemory replaces it (spec §2)"
```

---

## Task 8: Flip the status surface

Phase 1 code now exists, which makes nine files wrong at once. The list is not documentation of a good design — it is the blast radius, written down in `AGENTS.md:316-325` so the grep is bounded. **Do not add a tenth file.**

**Files (the whole surface, per `AGENTS.md`'s table):**
- Modify: `docs/product/PHASE_05_RESULTS.md` — source of truth; mark Phase 0.5 closed.
- Modify: `docs/product/ROADMAP.md` — phase status line, Phase 0.5 exit gate met, Phase 1 entry.
- Modify: `AGENTS.md` (*Validation Notes* `:345`, *Project Context*) — current phase, built-vs-specced.
- Modify: `docs/MASTER_SPEC.md` §"un-run" — which unknowns still block.
- Modify: `docs/TECH_STACK.md` §8 — known gaps / unverified.
- Modify: `docs/WORKFLOW.md` §"Right now" (`:98`) — the single next action.
- Modify: `docs/capstone/methodology.md`, `docs/capstone/research_direction_and_goals.md`, `docs/capstone/design_decisions_and_risks.md` — phase table, contingency framing, sequencing.
- Modify: `backend/.env.example` — only if a model override changed (it did not in this plan; verify and leave alone if so).
- Modify: `docs/specs/story-memory-contract.md` — status line: built, not just approved.

**Interfaces:**
- Consumes: nothing. Documentation only, no code.
- Produces: nothing importable.

- [ ] **Step 1: Establish what is actually true now**

Record these facts once; every file below either states or links to them.

- Phase 0.5 is **closed**. Probe 1 resolved (ADR-001 amendment: Qwen-Image-Edit primary, OmniGen2 a targeted escalation). Probe 3 PASS. Probes 2 and 4 not run, neither gates Phase 1.
- Phase 1 is **in progress**. `story-memory-contract` is **built** — `backend/contracts/story_memory.py` exists, `job_state.py` is deleted, seven nodes are on partial-return, `input_gate` is the entry point.
- Still specced-not-built in Phase 1: `story-analyzer`, `character-bible`, `consistency-check`, `regeneration-controller`, `compose`. `analyze`, `char_bible`, `consistency_check`, `compose` are pass-through stubs in the graph.
- `moderation-stack` is Phase 2; `input_gate` is its single-file placeholder.

- [ ] **Step 2: Update the source of truth first**

In `docs/product/PHASE_05_RESULTS.md`, add a closing line. **Pre-registered docs strike through superseded prose rather than deleting it** — what was believed before the numbers arrived is part of the method. Do not delete anything already in this file.

- [ ] **Step 3: Update `AGENTS.md`**

Replace the *Validation Notes* bullet at `:345` (the one beginning `- **Current phase: Phase 0.5 (Open-Weight Model Spike).**`) so it reads Phase 1, notes Phase 0.5 closed, and **links** to `docs/product/PHASE_05_RESULTS.md` for the probe numbers rather than restating them. Then update *Project Context*'s built-vs-specced list with the Step 1 facts.

Do not touch the table at `:316-325` — the surface list itself is unchanged.

- [ ] **Step 4: Update the remaining seven**

Work down the table in order. `docs/WORKFLOW.md` §"Right now" (`:98`) gets a single next action, not a list. **Capstone docs are last in the grep and first in the consequences** — they are the submitted artifact.

Apply the **point, don't copy** rule everywhere: a doc that needs a probe result links to `PHASE_05_RESULTS.md`.

- [ ] **Step 5: Update the spec's own status line**

`docs/specs/story-memory-contract.md:3` — change **Status:** from `approved` to built, dated, with the commit range. Leave §9's migration checklist in place as the record of what was done.

- [ ] **Step 6: Verify the grep is clean**

```bash
grep -rn "Current phase: Phase 0.5\|Phase 0.5 (Open-Weight" --include=*.md . | grep -v ".venv"
```

Expected: hits only in `PHASE_05_RESULTS.md` (historical record) and struck-through pre-registered prose.

```bash
grep -rn "job_state\|JobState" . | grep -v ".venv" | grep -v ".git/"
```

Expected: hits only where the migration is described in past tense.

- [ ] **Step 7: Commit**

```bash
git add -A docs AGENTS.md
git commit -m "docs: close Phase 0.5 and flip the status surface to Phase 1 (story-memory-contract built)"
```

---

## Verification: the whole port

Run from `backend/`:

```bash
uv run ruff check . && uv run pytest -v
```

Success criteria — all must hold:

1. `backend/contracts/job_state.py` does not exist; `grep -rn "JobState" --include=*.py .` (excluding `.venv`) returns nothing.
2. All 14 §9 consumers are ported: `graph.py`, six nodes + `input_gate`, `analyze.py`'s `SceneCaption` move and its three import sites, `worker/run_job.py`, and the two shape-coupled tests.
3. Every §6 deterministic assertion has a passing test in `tests/test_story_memory.py` or `tests/test_story_memory_reducer.py`.
4. `tests/test_graph_stub.py` asserts the seven-node execution order via `stream_mode="updates"` — the `stage` replacement (D-1).
5. No test asserts on `result["stage"]`, `result["caption"]`, or `result["image_path"]` as graph state keys.
6. `scenes[].caption` is written by `segment` (D-2); `analyze` returns `{}`.
7. The status surface is nine files, still nine, all saying Phase 1.

## Deliberately out of scope

- **`story-analyzer`** — DECISION_BACKLOG says don't, and the reason is live: every module built against the old contract is another consumer to migrate. `analyze` stays a stub.
- **§3's resume-time version check and restart.** `CURRENT_SCHEMA_VERSION` is `1` and nothing writes a different one, so the branch is unreachable and untestable today. It lands with the first version bump or with real resume handling.
- **`generate_and_store`'s hardcoded `scene-1.png`.** Pre-existing; becomes `{story_id}/{scene_id}.png` when the real segmenter produces more than one scene.
- **`schema_version` bumps of any kind.** Every ADR-028 addition is additive by construction.

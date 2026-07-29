# Story Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `analyze` pass-through stub with one extraction call that produces the story's `characters[]` (≤3, prominence-ordered), `locations[]`, `objects[]`, and a densely re-indexed `timeline[]`.

**Architecture:** `backend/pipeline/analyze.py` gains id-less boundary mirrors (`Extracted*` + the `StoryAnalysis` wrapper) that live beside their node per D-F, a single module-level `extract_entities(text) -> StoryAnalysis` helper that is the only effect boundary (MASTER_SPEC §6), and a node body that only truncates, mints ids by list position, re-indexes `timeline[].order`, and partial-returns four keys (ADR-024). `backend/contracts/` is **not** touched.

**Tech Stack:** Python 3.12, Pydantic 2.13.4, LangGraph 1.2.8, pytest, ruff, uv.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **Source spec:** `docs/specs/story-analyzer.md` (status `approved`, 2026-07-29). Its §4 code block is the schema shape; its §6 is the test list; its §9 is the Definition of Done.
- **Do not modify `backend/contracts/`.** `CharacterDescription.species` stays `Optional[str] = None` there. Requiring it in the contract is a contract change (ADR session, never inline) and would break `Character.description`'s `default_factory`. Spec §9 lists this under **Not done**.
- **The LLM boundary schema carries no id field** (D-G). Ids are `c{i}` / `loc{i}` / `obj{i}`, zero-based, minted node-side by list position after parsing.
- **`len(characters) <= 3`, enforced by the node**, not by prompt text alone. The prompt also asks for ≤3; the node is the control. Spec §9's **Not done** names prompt-only enforcement explicitly.
- **`timeline[].order` is re-assigned by the node** from list index — zero-based and dense. Never trusted from the model.
- **Every emitted character has a non-empty `description.species`** — required at the boundary via `ExtractedDescription`, never relaxed to Optional (spec §9 **Not done**).
- **No new contract fields, no `schema_version` bump.** `CURRENT_SCHEMA_VERSION` stays `1`.
- **No conditional edge.** ADR-003's two branch points are moderation pass/fail and consistency pass/fail; this node is neither. The graph topology in `pipeline/graph.py` does not change.
- **Do not absorb a §8 handoff.** `Scene.characters_present` belongs to `scene-segmentation`; description *richness* belongs to `character-bible`; character dedup is an unowned documented ceiling. Writing any of them here is a **Not done** condition.
- **`caption_for` / `SceneCaption` are untouched.** They live in this file per D-F but belong to `segment`; this spec does not change them, and their existing tests stay green.
- **Deterministic tests mock every model call** (MASTER_SPEC §6 Tier A). No assertion may touch extraction *quality* — that is Tier B, offline, never CI.
- **One patch point per node in graph tests** (MASTER_SPEC §6 rule 1). Node and graph tests patch `pipeline.analyze.extract_entities`; the helper's own tests patch `pipeline.analyze.structured_text`.
- **All commands run from `backend/`.** Lint: `uv run ruff check .` Tests: `uv run pytest`. Line length 120. `ruff format` is **not** adopted — never run it.
- **Provider SDKs and model IDs are not named here.** `providers.structured_text` picks the model from `settings.text_model`. Never pass a model string at this call site.

## Decisions settled during planning

Three gaps in the spec were resolved before writing this plan. All three are load-bearing.

**P-1 — The prompt string is unspecified, deliberately.** Spec §4 states the *rules* (short descriptive label, never a proper noun, never a redaction placeholder, ≤3, `species` always answerable) but writes no prompt. That makes the prompt the one artifact where a sloppy implementation passes every §6 assertion. **Resolution: the prompt is a named module constant `EXTRACTION_PROMPT`, and Task 2 adds a prompt-content test beyond §6** asserting the three asks survive. The assertions are deliberately loose (substring, case-insensitive) so rewording the prompt does not redden CI, but deleting an ask does.

**P-2 — CC-5 says "the helper logs extracted counts and the minted ids", but minting is node-side.** The helper cannot log ids it never sees. **Resolution: split it** — `extract_entities` logs the four extracted counts, `analyze` logs the minted ids. Mechanism is stdlib `logging.getLogger(__name__)`; the backend has no logging infrastructure today and this plan does not add any (the only `print`s in the repo are in `spikes/`, which is offline research tooling, not the pipeline).

**P-3 — The existing graph test breaks the moment `analyze` becomes real.** `tests/test_graph_stub.py::_mock_call_points` patches `pipeline.analyze.caption_for`, which after this change is no longer the analyze node's call point — the real `extract_entities` would fire and hit the network. **Resolution: Task 3 swaps the patch point** (`pipeline.analyze.extract_entities`) so CI stays green at the end of Task 3, and Task 4 adds the roster-survival assertion on top.

**Two open items are recorded in the spec and closed nowhere in this plan** (deliberate, confirmed):
- **CC-7 seed reproducibility for text extraction** — `providers.structured_text` accepts no seed. Adding one is a `providers.py` change and therefore its own decision session. Spec §5 and §8 record it. **Do not add a seed parameter in this plan.**
- **Filipino / Taglish extraction quality is unmeasured** — flagged in spec §8, to be raised before Phase 2 hardening. **Do not open a `DECISION_BACKLOG.md` row for either.** That file's *Recommended next session* block explicitly says not to; it is a decision queue, not a TODO list.

**Probed facts you rely on** (openai SDK + pydantic 2.13.4):
- `providers.structured_text(prompt, schema)` calls `chat.completions.parse` and raises `ValueError` when `message.parsed is None`. A model self-refusal therefore surfaces as a raise, which is the ADR-025 hard failure spec §4 describes. **Do not catch it** — no node-level retry, no partial roster.
- `providers._assert_field_order` only fires for schemas whose emitted top-level keys are `model_fields` of the schema. `StoryAnalysis`'s four list fields have no reason-then-score ordering constraint; the check is harmless here.
- A Pydantic subclass's `model_dump()` includes every inherited field, so `CharacterDescription(**extracted.description.model_dump())` round-trips all five axes and yields exactly the contract type.

---

## File Structure

**Modified:**

| File | Change |
|---|---|
| `backend/pipeline/analyze.py` | Gains `ExtractedDescription` / `ExtractedCharacter` / `ExtractedLocation` / `ExtractedObject` / `StoryAnalysis`, `EXTRACTION_PROMPT`, `extract_entities`, and a real `analyze` body. `SceneCaption` + `caption_for` unchanged. Stub comment removed. |
| `backend/tests/test_analyze_node.py` | Gains boundary-strictness, provider-seam, prompt-content, and node tests. `test_analyze_is_a_pass_through_stub` **deleted**. |
| `backend/tests/test_graph_stub.py` | Patch point swapped to `extract_entities`; gains one roster-survival assertion. |

**Docs modified (Task 5 — spec §9.5's finding-change grep):**

| File | Change |
|---|---|
| `docs/specs/story-analyzer.md` | Status flips to `built` with the commit range. |
| `docs/product/DECISION_BACKLOG.md` | Tick the `story-analyzer` line; replace the stale *Recommended next session* block. |
| `docs/WORKFLOW.md` §"Right now" | Currently names writing this spec as the next action. |
| `AGENTS.md` *Validation Notes* + *Project Context* | Drop `story-analyzer` from remaining Phase-1 specs; drop `analyze` from the pass-through stub lists. |
| `docs/specs/story-memory-contract.md` §8 | Mark the `Location` / `StoryObject` / `TimelineEvent` refinement item resolved — **no refinement** — citing this spec. |
| `docs/MASTER_SPEC.md` §2 | No edit expected; **confirm** the `analyze` row still reads true. |

**No new file is created.** Spec §9.6: nothing is added to AGENTS.md's nine-file status surface.

---

### Task 1: Boundary schemas

The id-less mirrors the LLM boundary uses, and the strictness that makes ADR-028's re-roll safe. No provider, no node — pure schema.

**Files:**
- Modify: `backend/pipeline/analyze.py`
- Test: `backend/tests/test_analyze_node.py`

**Interfaces:**
- Consumes: `contracts.story_memory.CharacterDescription`, `contracts.story_memory.TimelineEvent`
- Produces: `ExtractedDescription(CharacterDescription)` with `species: str` required; `ExtractedCharacter(name: str, description: ExtractedDescription)`; `ExtractedLocation(name: str, description: str | None = None)`; `ExtractedObject(name: str, description: str | None = None)`; `StoryAnalysis(characters: list[ExtractedCharacter], locations: list[ExtractedLocation], objects: list[ExtractedObject], timeline: list[TimelineEvent])`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_analyze_node.py`:

```python
def test_extracted_description_requires_species():
    """Invariant 5 + ADR-028: an all-empty description makes `matches_description` vacuously
    true, collapsing the 3-draw re-roll to 1 draw with nobody noticing."""
    with pytest.raises(ValidationError):
        ExtractedDescription.model_validate({"colours": ["red"]})


def test_extracted_description_requires_no_visual_attribute():
    """Guards against someone later 'tightening' this into a Pydantic validator that fires
    AFTER a successful, paid call — under ADR-025 that fails the child's whole job because
    they never said what their dog was wearing. Spec §4."""
    assert ExtractedDescription(species="dog").species == "dog"


def test_extracted_description_inherits_every_contract_axis():
    """One source of truth for the axes — they are aligned to the FailureReason taxonomy
    the judge scores against, so re-deriving them here would fork it."""
    assert set(CharacterDescription.model_fields) <= set(ExtractedDescription.model_fields)


def test_contract_character_description_is_unchanged():
    """The boundary is strict; the contract stays a mostly-optional container (ADR-023)."""
    assert CharacterDescription().species is None
    assert Character(char_id="c0", name="x").description == CharacterDescription()


@pytest.mark.parametrize(
    ("model", "id_field"),
    [
        (ExtractedCharacter, "char_id"),
        (ExtractedLocation, "loc_id"),
        (ExtractedObject, "obj_id"),
    ],
)
def test_no_extraction_model_declares_an_id(model, id_field):
    """D-G: ids are minted node-side by list position; the LLM schema carries none."""
    assert id_field not in model.model_fields


def test_story_analysis_accepts_the_four_collections():
    analysis = StoryAnalysis.model_validate(
        {
            "characters": [{"name": "the narrator", "description": {"species": "girl"}}],
            "locations": [{"name": "the beach"}],
            "objects": [{"name": "a red bucket"}],
            "timeline": [{"order": 0, "summary": "They go to the beach."}],
        }
    )
    assert analysis.characters[0].description.species == "girl"
    assert analysis.locations[0].description is None
    assert analysis.timeline[0].summary == "They go to the beach."
```

Update the import block at the top of the file to:

```python
from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Input,
    StoryMemory,
)
from pipeline.analyze import (
    ExtractedCharacter,
    ExtractedDescription,
    ExtractedLocation,
    ExtractedObject,
    SceneCaption,
    StoryAnalysis,
    analyze,
    caption_for,
)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_analyze_node.py -v`
Expected: collection error — `ImportError: cannot import name 'ExtractedDescription' from 'pipeline.analyze'`

- [ ] **Step 3: Write the schemas**

In `backend/pipeline/analyze.py`, extend the contract import and place the new classes **after** `SceneCaption` / `caption_for` and **before** `analyze`:

```python
from contracts.story_memory import CharacterDescription, StoryMemory, TimelineEvent
```

`Character`, `Location`, and `StoryObject` are **not** imported yet — nothing uses them until Task 3, and ruff's F401 would flag them. Task 3 adds them.

```python
# --- LLM boundary (D-F: transient wrapper, so it lives beside its node) ---
# The contract types all carry a REQUIRED id and D-G forbids an id at the boundary, so the
# boundary uses id-less mirrors that the node maps into contract types.


class ExtractedDescription(CharacterDescription):
    """Boundary-strict subclass. The contract's `CharacterDescription` is all-Optional by
    design (ADR-023: mostly-optional container); real per-field validation belongs at the
    LLM boundary (ADR-002). Subclassed rather than mirrored so the axes — deliberately
    aligned to the `FailureReason` taxonomy the judge scores against — stay in one place.

    `species` is required HERE and Optional in the contract. ADR-028's reference-acceptance
    loop judges each draw against `CharacterDescription`; an entirely empty description makes
    `matches_description` vacuously true, so the 3-draw re-roll silently collapses to 1 draw.
    One always-answerable string guarantees the judge has something to check against.
    No visual attribute is required — strict `json_schema` cannot express "at least one of
    three lists is non-empty", so that constraint would have to fire after a paid call.
    """

    species: str


class ExtractedCharacter(BaseModel):
    name: str
    description: ExtractedDescription


class ExtractedLocation(BaseModel):
    name: str
    description: str | None = None


class ExtractedObject(BaseModel):
    name: str
    description: str | None = None


class StoryAnalysis(BaseModel):
    """The transient wrapper — never persisted."""

    characters: list[ExtractedCharacter]   # prominence order, protagonist first
    locations: list[ExtractedLocation]
    objects: list[ExtractedObject]
    timeline: list[TimelineEvent]          # already id-less in contracts/
```

Note: `Character`, `Location`, `StoryObject` are imported now and used in Task 3. If ruff's F401 flags them at this step, add them in Task 3 instead — do not add a `noqa`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_analyze_node.py -v && uv run ruff check .`
Expected: all PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/analyze.py backend/tests/test_analyze_node.py
git commit -m "feat(analyze): add id-less LLM boundary schemas with required species"
```

---

### Task 2: The `extract_entities` helper and its prompt

The single effect boundary (MASTER_SPEC §6). Everything downstream patches this function.

**Files:**
- Modify: `backend/pipeline/analyze.py`
- Test: `backend/tests/test_analyze_node.py`

**Interfaces:**
- Consumes: `StoryAnalysis` (Task 1), `providers.structured_text`
- Produces: `EXTRACTION_PROMPT: str` (a `{text}`-templated module constant) and `extract_entities(text: str) -> StoryAnalysis`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_analyze_node.py`:

```python
def _analysis(**overrides) -> StoryAnalysis:
    """A minimal valid StoryAnalysis; override any collection per test."""
    return StoryAnalysis.model_validate(
        {
            "characters": [{"name": "the narrator", "description": {"species": "girl"}}],
            "locations": [{"name": "the beach"}],
            "objects": [{"name": "a red bucket"}],
            "timeline": [{"order": 0, "summary": "They go to the beach."}],
            **overrides,
        }
    )


def test_extract_entities_passes_the_text_and_schema_to_the_provider():
    with patch("pipeline.analyze.structured_text", return_value=_analysis()) as mock_provider:
        extract_entities("I went to the beach with my sister.")

    prompt, schema = mock_provider.call_args.args
    assert "I went to the beach with my sister." in prompt
    assert schema is StoryAnalysis


def test_extract_entities_returns_the_parsed_wrapper_unchanged():
    analysis = _analysis()
    with patch("pipeline.analyze.structured_text", return_value=analysis):
        assert extract_entities("I went to the beach.") is analysis


def test_extract_entities_does_not_name_a_model():
    """Model IDs are env-overridable settings in app/config.py; a call site never names one
    (AGENTS.md, ADR-015)."""
    with patch("pipeline.analyze.structured_text", return_value=_analysis()) as mock_provider:
        extract_entities("I went to the beach.")

    assert mock_provider.call_args.kwargs == {}
    assert len(mock_provider.call_args.args) == 2


def test_extract_entities_propagates_a_provider_failure():
    """ADR-025: a hard provider failure (including `message.parsed is None` on a self-refusal)
    raises → job `failed`. No node-level retry, never a partial roster."""
    with patch("pipeline.analyze.structured_text", side_effect=ValueError("no parsable output")):
        with pytest.raises(ValueError):
            extract_entities("A story about mild peril.")


def test_extraction_prompt_carries_the_three_asks():
    """The prompt string is the one artifact spec §4 states rules for but does not write, so
    a prompt that quietly drops an ask passes every other test in §6. Loose substring checks:
    rewording is fine, deleting an ask is not.

    - the <=3 character cap (belt-and-braces; the node is the real control)
    - the short-descriptive-label rule, so no proper noun or `<PERSON_1>` reaches a prompt
    - the always-answerable `species` ask that keeps ADR-028's re-roll from collapsing
    """
    prompt = EXTRACTION_PROMPT.lower()
    assert "3" in prompt
    assert "descriptive label" in prompt
    assert "species" in prompt


def test_extract_entities_logs_the_extracted_counts(caplog):
    """CC-5: a wrong reference downstream traces back to a specific roster entry."""
    with caplog.at_level(logging.INFO, logger="pipeline.analyze"):
        with patch("pipeline.analyze.structured_text", return_value=_analysis()):
            extract_entities("I went to the beach.")

    assert "1 characters" in caplog.text
```

Add to the top of the file:

```python
import logging
```

and extend the `pipeline.analyze` import with `EXTRACTION_PROMPT` and `extract_entities`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_analyze_node.py -v`
Expected: collection error — `ImportError: cannot import name 'EXTRACTION_PROMPT' from 'pipeline.analyze'`

- [ ] **Step 3: Write the prompt and the helper**

In `backend/pipeline/analyze.py`, after `StoryAnalysis`:

```python
log = logging.getLogger(__name__)

# `analyze` reads redacted text, and the expected kid story is first-person ("I went to the
# beach with my sister"), so the protagonist is usually unnamed by construction. Asking for a
# short descriptive label rather than a proper noun works identically on redacted and
# un-redacted text, and it is what `char_bible` needs anyway — the canonical reference is drawn
# from `CharacterDescription`, not from the name. Consequence, stated plainly: the child's
# actual name never appears in their storybook. That is correct under CC-2 (spec §4).
EXTRACTION_PROMPT = """Extract the entities from this child's story.

Characters: at most 3, most important first — the first one is the story's protagonist.
Give each a short descriptive label, never a proper noun and never a redaction placeholder
like <PERSON_1>: "the narrator", "the younger sister", "the orange cat". The story is usually
first-person, and the narrator is usually a character. Every character needs a species — one
plain word for what they are: "girl", "dog", "robot". Fill colours, body_features and clothing
only from what the story actually says; leave them empty rather than inventing details.

Locations and objects: whatever the story mentions.

Timeline: the story's events in the order they happen, one short summary each.

Story:
{text}"""


def extract_entities(text: str) -> StoryAnalysis:
    """The node's single effect boundary (MASTER_SPEC §6). One strict-`json_schema` call.

    A provider hard failure raises and the job fails (ADR-025 Decision 1) — the `openai` SDK's
    bounded retry is the entire policy. In Phase 1 a model self-refusal surfaces the same way,
    knowingly blunt; soften-and-retry is `self-refusal-fallback`'s (Phase 2, ADR-011 mech. 4).
    """
    analysis = structured_text(EXTRACTION_PROMPT.format(text=text), StoryAnalysis)
    log.info(
        "analyze: extracted %d characters, %d locations, %d objects, %d timeline events",
        len(analysis.characters),
        len(analysis.locations),
        len(analysis.objects),
        len(analysis.timeline),
    )
    return analysis
```

`EXTRACTION_PROMPT.format(text=text)` is safe with braces in the story: `str.format` only scans the template for fields, so `{`/`}` inside the substituted value passes through untouched.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_analyze_node.py -v && uv run ruff check .`
Expected: all PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/analyze.py backend/tests/test_analyze_node.py
git commit -m "feat(analyze): add extract_entities helper and the extraction prompt"
```

---

### Task 3: The node — truncate, mint, re-index, partial-return

The node body does no I/O. It maps the boundary types into contract types and enforces every invariant the prompt cannot.

**Files:**
- Modify: `backend/pipeline/analyze.py`
- Modify: `backend/tests/test_analyze_node.py` (delete `test_analyze_is_a_pass_through_stub`)
- Modify: `backend/tests/test_graph_stub.py:32-39` (`_mock_call_points` patch point)

**Interfaces:**
- Consumes: `extract_entities(text) -> StoryAnalysis` (Task 2); `contracts.story_memory.Character`, `CharacterDescription`, `Location`, `StoryObject`, `TimelineEvent`
- Produces: `analyze(state: StoryMemory) -> dict` returning exactly the keys `characters`, `locations`, `objects`, `timeline`

- [ ] **Step 1: Delete the stub test**

Remove this from `backend/tests/test_analyze_node.py` — it asserts the behaviour this task replaces (spec §9.2):

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

- [ ] **Step 2: Write the failing tests**

Append to `backend/tests/test_analyze_node.py`:

```python
def _state(raw_text="A dog runs in a field.", redacted_text="A dog runs in a field.") -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="t1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text=raw_text, redacted_text=redacted_text),
    )


def _character(name: str, species: str = "girl") -> dict:
    return {"name": name, "description": {"species": species}}


def test_analyze_mints_ids_by_list_position():
    analysis = _analysis(
        characters=[_character("the narrator"), _character("the younger sister")],
        locations=[{"name": "the beach"}, {"name": "the car"}],
        objects=[{"name": "a red bucket"}],
    )
    with patch("pipeline.analyze.extract_entities", return_value=analysis):
        result = analyze(_state())

    assert [c.char_id for c in result["characters"]] == ["c0", "c1"]
    assert [loc.loc_id for loc in result["locations"]] == ["loc0", "loc1"]
    assert [o.obj_id for o in result["objects"]] == ["obj0"]


def test_analyze_caps_characters_at_three_keeping_the_first_three():
    """Invariant 1. Prominence survives the cut — index 0 is the protagonist. The prompt also
    asks for <=3, so this is belt-and-braces; the node is the control (spec §4)."""
    names = ["first", "second", "third", "fourth", "fifth"]
    analysis = _analysis(characters=[_character(n) for n in names])
    with patch("pipeline.analyze.extract_entities", return_value=analysis):
        result = analyze(_state())

    assert [c.name for c in result["characters"]] == ["first", "second", "third"]
    assert [c.char_id for c in result["characters"]] == ["c0", "c1", "c2"]


@pytest.mark.parametrize("model_orders", [[1, 2, 5], [0, 0, 0], [3, 1, 2]])
def test_analyze_reindexes_timeline_order_from_list_position(model_orders):
    """Invariant 4. Gapped or duplicated `order` values validate fine against Pydantic and
    would silently corrupt the only ordering `segment` receives."""
    analysis = _analysis(
        timeline=[{"order": o, "summary": f"event {i}"} for i, o in enumerate(model_orders)]
    )
    with patch("pipeline.analyze.extract_entities", return_value=analysis):
        result = analyze(_state())

    assert [e.order for e in result["timeline"]] == [0, 1, 2]
    assert [e.summary for e in result["timeline"]] == ["event 0", "event 1", "event 2"]


def test_analyze_accepts_an_empty_roster_without_raising():
    """CC-9: an empty roster is valid, not a failure. `char_bible` mints no references and
    scenes generate unreferenced — a book with drifting art beats no book (ADR-010)."""
    analysis = _analysis(characters=[], timeline=[])
    with patch("pipeline.analyze.extract_entities", return_value=analysis):
        result = analyze(_state())

    assert result["characters"] == []
    assert result["timeline"] == []
    assert [loc.loc_id for loc in result["locations"]] == ["loc0"]


def test_analyze_prefers_redacted_text():
    """CC-2: `redacted_text` is what downstream nodes consume."""
    with patch("pipeline.analyze.extract_entities", return_value=_analysis()) as mock_extract:
        analyze(_state(raw_text="raw version", redacted_text="redacted version"))

    assert mock_extract.call_args.args[0] == "redacted version"


def test_analyze_falls_back_to_raw_text():
    """The same fallback `segment` already uses — `input_gate` is a pass-through stub today."""
    with patch("pipeline.analyze.extract_entities", return_value=_analysis()) as mock_extract:
        analyze(_state(raw_text="raw version", redacted_text=None))

    assert mock_extract.call_args.args[0] == "raw version"


def test_analyze_partial_returns_exactly_four_keys_and_does_not_mutate_state():
    """ADR-024: nodes partial-return; they never mutate `state`."""
    state = _state()
    before = state.model_dump()
    with patch("pipeline.analyze.extract_entities", return_value=_analysis()):
        result = analyze(state)

    assert set(result) == {"characters", "locations", "objects", "timeline"}
    assert state.model_dump() == before


def test_analyze_persists_the_contract_type_not_the_strict_subclass():
    """What is persisted is exactly `CharacterDescription`, never `ExtractedDescription` —
    the strictness is a boundary concern and must not leak into the checkpoint."""
    with patch("pipeline.analyze.extract_entities", return_value=_analysis()):
        result = analyze(_state())

    description = result["characters"][0].description
    assert type(description) is CharacterDescription
    assert description.species == "girl"


def test_analyze_logs_the_minted_ids(caplog):
    """CC-5: a wrong reference downstream traces back to a specific roster entry."""
    analysis = _analysis(characters=[_character("the narrator"), _character("the cat", "cat")])
    with caplog.at_level(logging.INFO, logger="pipeline.analyze"):
        with patch("pipeline.analyze.extract_entities", return_value=analysis):
            analyze(_state())

    assert "c0" in caplog.text
    assert "c1" in caplog.text
```

Extend the `pipeline.analyze` import with `extract_entities`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_analyze_node.py -v`
Expected: FAIL — `test_analyze_mints_ids_by_list_position` and its neighbours fail with `KeyError: 'characters'`, because the stub still returns `{}`.

- [ ] **Step 4: Write the node**

Replace the `analyze` function in `backend/pipeline/analyze.py` — the `# ponytail: stub` comment and its `DECISION_BACKLOG` pointer go with it:

```python
def analyze(state: StoryMemory) -> dict:
    """One extraction call, one roster. Every downstream node works from `characters[]`
    instead of re-reading the child's prose (spec `docs/specs/story-analyzer.md`).

    This body does no I/O — it truncates, mints, re-indexes, and partial-returns (ADR-024).
    `caption_for` above lives here per D-F but belongs to `segment`; it is not called here.
    """
    analysis = extract_entities(state.input.redacted_text or state.input.raw_text)

    # The 3-character cap IS the pre-scene cost ceiling (CC-3): at most 9 reference draws
    # (3 characters x ADR-028's 3-draw cap) before a single scene is generated. The prompt
    # asks for <=3 too, but a prompt is not enforceable — this slice is the control.
    characters = [
        Character(
            char_id=f"c{i}",
            name=extracted.name,
            # the strict subclass is a boundary concern; what is persisted is the contract type
            description=CharacterDescription(**extracted.description.model_dump()),
        )
        for i, extracted in enumerate(analysis.characters[:3])
    ]
    # locations/objects are deliberately uncapped — neither costs an image, so neither is a
    # CC-3 lever. Cap them only if a measured checkpoint problem appears (spec §4).
    locations = [
        Location(loc_id=f"loc{i}", name=extracted.name, description=extracted.description)
        for i, extracted in enumerate(analysis.locations)
    ]
    objects = [
        StoryObject(obj_id=f"obj{i}", name=extracted.name, description=extracted.description)
        for i, extracted in enumerate(analysis.objects)
    ]
    # `order` is re-assigned from list position, never trusted from the model: a returned
    # `1, 2, 5` or a duplicate validates fine against Pydantic and would silently corrupt the
    # only ordering `segment` receives.
    timeline = [
        TimelineEvent(order=i, summary=event.summary) for i, event in enumerate(analysis.timeline)
    ]

    log.info(
        "analyze: minted %s",
        [c.char_id for c in characters]
        + [loc.loc_id for loc in locations]
        + [o.obj_id for o in objects],
    )
    return {
        "characters": characters,
        "locations": locations,
        "objects": objects,
        "timeline": timeline,
    }
```

- [ ] **Step 5: Run the node tests to verify they pass**

Run: `uv run pytest tests/test_analyze_node.py -v`
Expected: all PASS.

- [ ] **Step 6: Run the full suite and watch the graph test fail**

Run: `uv run pytest`
Expected: FAIL in `tests/test_graph_stub.py` — `_mock_call_points` patches `pipeline.analyze.caption_for`, which is no longer the analyze node's call point, so the real `extract_entities` fires and hits the provider.

- [ ] **Step 7: Swap the graph test's patch point**

In `backend/tests/test_graph_stub.py`, add to the imports:

```python
from pipeline.analyze import StoryAnalysis
```

Replace `_mock_call_points` (currently lines 32-39) with:

```python
STUB_ANALYSIS = StoryAnalysis.model_validate(
    {
        "characters": [{"name": "the orange dog", "description": {"species": "dog"}}],
        "locations": [{"name": "a field"}],
        "objects": [],
        "timeline": [{"order": 0, "summary": "A dog runs."}],
    }
)


def _mock_call_points(monkeypatch):
    # One patch point per node (MASTER_SPEC §6 rule 1): `extract_entities` is analyze's seam.
    monkeypatch.setattr("pipeline.analyze.extract_entities", lambda text: STUB_ANALYSIS)
    monkeypatch.setattr("pipeline.segment.caption_for", lambda text: "stub caption")
    monkeypatch.setattr(
        "pipeline.generate_scene.generate_and_store",
        lambda prompt, story_id: "stub/path.png",
    )
```

- [ ] **Step 8: Run the full suite to verify it is green**

Run: `uv run pytest && uv run ruff check .`
Expected: all PASS, ruff clean.

- [ ] **Step 9: Commit**

```bash
git add backend/pipeline/analyze.py backend/tests/test_analyze_node.py backend/tests/test_graph_stub.py
git commit -m "feat(analyze): mint roster ids, cap characters at 3, re-index timeline order"
```

---

### Task 4: Graph — the roster survives `input_gate → analyze → segment`

Task 3 kept the graph test green; this adds the assertion spec §6 actually asks for.

**Files:**
- Modify: `backend/tests/test_graph_stub.py`

**Interfaces:**
- Consumes: `analyze` via the compiled graph; `STUB_ANALYSIS` and `_mock_call_points` from Task 3

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_graph_stub.py`:

```python
def test_analyze_roster_survives_the_graph(monkeypatch):
    """Spec §6: patch the single helper and assert the roster reaches the end of the run.
    `analyze` runs before `segment`, so a roster that is dropped by a reducer or overwritten
    by a later node shows up here and nowhere else."""
    _mock_call_points(monkeypatch)
    app_graph = build_graph()

    result = app_graph.invoke(
        _initial_state("test-job-3"), config={"configurable": {"thread_id": "test-job-3"}}
    )

    assert [c.char_id for c in result["characters"]] == ["c0"]
    assert result["characters"][0].name == "the orange dog"
    assert result["characters"][0].description.species == "dog"
    assert [loc.loc_id for loc in result["locations"]] == ["loc0"]
    assert result["objects"] == []
    assert [e.order for e in result["timeline"]] == [0]
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/test_graph_stub.py::test_analyze_roster_survives_the_graph -v`
Expected: PASS immediately — Task 3 already made this true. If it FAILS, a later node is clobbering the roster; that is a real bug, fix it before continuing.

This is the one test in the plan that does not start red. That is correct for a regression guard over an integration path — its job is to fail *later*, when a future node overwrites `characters[]`.

- [ ] **Step 3: Run the full verify**

Run: `uv run ruff check . && uv run pytest`
Expected: all PASS, ruff clean. **Paste the output into the completion report** — spec §9.3 requires it shown, not claimed.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_graph_stub.py
git commit -m "test(graph): assert the analyze roster survives the full run"
```

---

### Task 5: Definition of done — the finding-change grep and the status flip

**Do not skip this because the tests are green.** Spec §9.5 makes it a completion condition, and four docs beyond the code currently assert things this change makes false. Green CI is not done.

**Files:**
- Modify: `docs/specs/story-analyzer.md:3`
- Modify: `docs/product/DECISION_BACKLOG.md`
- Modify: `docs/WORKFLOW.md` §"Right now"
- Modify: `AGENTS.md` (*Project Context*, *Validation Notes*)
- Modify: `docs/specs/story-memory-contract.md` §8
- Verify only: `docs/MASTER_SPEC.md` §2

- [ ] **Step 1: Run the grep and see the surface for yourself**

```bash
cd /c/Users/Asus/Desktop/story-buddy
grep -rn "story-analyzer\|story_analyzer" --include="*.md" .
grep -rn "pass-through stub" --include="*.md" .
```

Expected: hits in `docs/WORKFLOW.md`, `AGENTS.md`, `docs/product/DECISION_BACKLOG.md`, `docs/specs/story-memory-contract.md`, `docs/MASTER_SPEC.md`, and this plan. Every hit outside this plan is either fixed below or confirmed still-true.

- [ ] **Step 2: Get the commit range**

```bash
git log --oneline e523b77..HEAD
```

Record the first and last commit SHAs of Tasks 1-4 — the spec status line needs the range.

- [ ] **Step 3: Flip the spec status line**

`docs/specs/story-analyzer.md:3` currently reads:

```markdown
**Status:** approved (2026-07-29) · **Phase:** 1 · **Owner node:** `backend/pipeline/analyze.py`
```

Change to (substitute the real range from Step 2):

```markdown
**Status:** built (2026-07-29, commits <first>–<last>) · **Phase:** 1 · **Owner node:** `backend/pipeline/analyze.py`
```

Leave §5's two unticked boxes (CC-7, and CC-1/4/6/8 N/A) and §8's two **Open** items exactly as they are — both are recorded limitations, not work this change closes. Per the planning decision, no `DECISION_BACKLOG.md` row is opened for either.

- [ ] **Step 4: Update `docs/product/DECISION_BACKLOG.md`**

Replace the `story-analyzer` line in the Phase 1 feature-spec list:

```markdown
- [ ] `story-analyzer`   *(spec **approved 2026-07-29** — `docs/specs/story-analyzer.md`; code:
      `pipeline/analyze.py` still the pass-through stub. Caps characters at 3 — the pre-scene cost ceiling
```

with:

```markdown
- [x] `story-analyzer`   *(spec **built 2026-07-29** — `docs/specs/story-analyzer.md`;
      `pipeline/analyze.py` mints the roster. Caps characters at 3 — the pre-scene cost ceiling
```

Keep the rest of that entry's parenthetical (the ADR-028 / `species` / handoff sentences) verbatim — it is still true.

Then replace the **Recommended next session** block. It currently names the completed `job_state.py` migration and tells the reader to build `story-analyzer`. Rewrite to:

```markdown
## Recommended next session

> **Phase 0.5 is closed (2026-07-29).** Numbers and branches in `docs/product/PHASE_05_RESULTS.md` — not
> restated here (AGENTS.md → *Definition of Done*, "point, don't copy").
>
> ✅ **The `job_state.py` migration is done (2026-07-29).** See `docs/specs/story-memory-contract.md`
> (status `built`).
>
> ✅ **`story-analyzer` is built (2026-07-29).** `pipeline/analyze.py` mints `characters[]` (capped at 3),
> `locations[]`, `objects[]`, and a densely re-indexed `timeline[]`. See `docs/specs/story-analyzer.md`
> (status `built`).

**Write and build `scene-segmentation`** — no spec exists yet (`docs/specs/`), so this is a
brainstorm-then-plan session. It owns `Scene.characters_present`, handed to it by `story-analyzer` §8;
the join key is `Character.name`. `pipeline/segment.py` mints `s0` only today.

**No open decision blocks Phase 1.** Tiers 1, 2, 2b, and 3 are all resolved. `story-analyzer`'s two
recorded limitations — CC-7 seed reproducibility for text extraction, and unmeasured Filipino/Taglish
extraction quality — are deliberately **not** rows here. The first needs a `providers.py` seed parameter
and is its own decision if it is ever taken; the second is a measurement gap to flag before Phase 2
hardening, not a decision. Both live in `docs/specs/story-analyzer.md` §5/§8.

After that, in roadmap order: `character-bible`.
```

- [ ] **Step 5: Update `docs/WORKFLOW.md` §"Right now" (lines ~98-105)**

Replace the **Next action** paragraph:

```markdown
**Next action: `story-analyzer` spec** — write `docs/specs/story-analyzer.md` from `docs/specs/TEMPLATE.md`
before writing any code (CLAUDE.md §2). The node is already a pass-through stub in `backend/pipeline/analyze.py`.
```

with:

```markdown
`story-analyzer` is **built** (2026-07-29): `backend/pipeline/analyze.py` mints `characters[]` (capped at 3),
`locations[]`, `objects[]`, and a densely re-indexed `timeline[]`. See `docs/specs/story-analyzer.md`.

**Next action: `scene-segmentation` spec** — write `docs/specs/scene-segmentation.md` from
`docs/specs/TEMPLATE.md` before writing any code (CLAUDE.md §2). It owns `Scene.characters_present`,
handed to it by `story-analyzer` §8. `backend/pipeline/segment.py` mints `s0` only today.
```

- [ ] **Step 6: Update `AGENTS.md`**

Two places. In *Project Context* → Architecture (around line 193), the sentence:

```markdown
  `generate_scene → consistency_check → compose` — linear, **zero conditional edges**. `input_gate`,
  `analyze`, `char_bible`, `consistency_check`, and `compose` are pass-through stubs; `segment` mints `s0`
  and writes `scenes[].caption`; `generate_scene` has real behavior. Fill the stubs in per
```

becomes:

```markdown
  `generate_scene → consistency_check → compose` — linear, **zero conditional edges**. `input_gate`,
  `char_bible`, `consistency_check`, and `compose` are pass-through stubs; `analyze` mints the entity
  roster; `segment` mints `s0` and writes `scenes[].caption`; `generate_scene` has real behavior. Fill the
  stubs in per
```

In *Validation Notes* (around line 353), the remaining-specs line:

```markdown
  Remaining Phase-1 specs: `story-analyzer`, `character-bible`, `consistency-check`,
  `regeneration-controller`, `compose` (pass-through stubs in the graph today).
```

becomes:

```markdown
  **`story-analyzer` is built (2026-07-29):** `pipeline/analyze.py` mints `characters[]` (≤3),
  `locations[]`, `objects[]`, `timeline[]`.
  Remaining Phase-1 specs: `scene-segmentation`, `character-bible`, `consistency-check`,
  `regeneration-controller`, `compose`.
```

Also check the *Contract-first* → "State of play" block (around line 104-107): if it says "Remaining Phase-1 nodes are pass-through stubs" without naming them, it is still true and needs no edit. If it names `analyze`, fix it.

- [ ] **Step 7: Update `docs/specs/story-memory-contract.md` §8**

Find the open refinement item naming `Location` / `StoryObject` / `TimelineEvent` as *"refined by the `story-analyzer` spec"* and mark it resolved:

```markdown
- ~~`Location` / `StoryObject` / `TimelineEvent` — refined by the `story-analyzer` spec~~
  → **Resolved 2026-07-29: no refinement.** `docs/specs/story-analyzer.md` decided the minimal shapes
  are sufficient for every Phase-1 consumer. No contract change, no `schema_version` bump.
```

Match the strike-through/resolution style the rest of that §8 already uses; if it uses a different convention, follow that instead of this one.

- [ ] **Step 8: Confirm `docs/MASTER_SPEC.md` §2**

Read the `analyze` row of the node-I/O table. Its inputs should read `input.redacted_text` and its outputs `characters[]`, `locations[]`, `objects[]`, `timeline[]`. **No edit is expected** (spec §9.5). If the row disagrees with what Task 3 built, stop and surface the conflict — MASTER_SPEC §2 is canonical and a disagreement is a finding, not a typo to patch.

- [ ] **Step 9: Confirm nothing was added to the status surface**

Spec §9.6: this change adds **no** new file to AGENTS.md's nine-file status table. Confirm `git status` shows only the files listed in this plan's File Structure, plus the plan itself.

- [ ] **Step 10: Final verify, shown not claimed**

```bash
cd backend && uv run ruff check . && uv run pytest
```

Paste the real output. Spec §9.3 requires it.

- [ ] **Step 11: Commit**

```bash
git add docs/ AGENTS.md
git commit -m "docs: mark story-analyzer built; close the story-memory-contract §8 refinement item"
```

- [ ] **Step 12: Delete this plan**

AGENTS.md *Artifact hygiene*: plans are disposable, specs are durable. `docs/specs/plans/` holds only in-flight work; git keeps the history.

```bash
git rm docs/specs/plans/2026-07-29-story-analyzer.md
git commit -m "chore(plans): retire the story-analyzer plan — module built, tests green, spec updated"
```

---

## Completion report

Per AGENTS.md *Definition of Done*, the report must state:

- **Commands run** and their real output: `uv run ruff check . && uv run pytest` from `backend/`.
- **Verified:** every §6 assertion — id minting, the 3-character cap keeping the *first* three, timeline re-indexing over gapped and duplicate `order` values, empty roster not raising, `redacted_text` preference with `raw_text` fallback, four-key partial return with `state` unmutated, the D-G no-id guard, the persisted type being `CharacterDescription`, boundary strictness on `species`, the contract unchanged, and the roster surviving the graph.
- **Not verified:** extraction *quality* — whether the model finds the characters a human reads, and ranks the protagonist first. That is Tier B (spec §7), measured offline on the story corpus, feeding Objective 3. It is deliberately absent from CI.
- **Residual risks, both recorded and neither closed:**
  - **CC-7** — `providers.structured_text` accepts no seed, so two runs of the same story can produce different rosters and different `char_id` assignments. Within-run and resume stability comes from checkpointing, which is all `story-memory-contract` §2.1 requires; a seeded re-run is not byte-identical.
  - **Filipino / Taglish extraction quality is unmeasured.** `qwen/qwen3-32b` has no published Filipino entity-extraction numbers and the respondents are Filipino children (ADR-017); a Taglish story may also yield Filipino descriptive labels that then flow into an English-prompted image model. Not a Phase-1 blocker — **flag it before Phase 2 hardening.**
  - **CC-2 is not satisfied end-to-end today.** This node is correct by construction, but `input_gate` is a pass-through stub and Presidio is not a dependency anywhere in `backend/`. The redaction this node depends on lands with `moderation-stack` (Phase 2).
- **Documented ceilings carried forward** (spec §4, none of them bugs): the same character named twice gets two `char_id`s and two of the three budget slots; character-vs-object ambiguity is resolved by whichever collection the model picks; `locations[]` / `objects[]` are uncapped; a model self-refusal is a hard job failure until `self-refusal-fallback` lands.

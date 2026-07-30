# Character Bible — Plan B (the node, the graph test, and the doc sweep)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the `char_bible` LangGraph node on top of Plan A's `mint_reference` helper — select at most two characters, mint their references, return the **full** roster and a copied-and-bumped `cost` — then prove it through the graph and close the spec's Definition of Done.

**Architecture:** The node body does **no I/O**. It selects, maps, bumps and partial-returns (ADR-024 — never mutate `state`). Every effect is behind `mint_reference`, which node and graph tests patch at a single point (MASTER_SPEC §6 rule 1). The acceptance loop stays node-internal: no conditional edge, no super-step, so ADR-003 and ADR-024 are unamended.

**Tech Stack:** Python 3.12, Pydantic v2, LangGraph, pytest + `unittest.mock`, ruff, uv.

**Spec:** `docs/specs/character-bible.md`. **Prerequisite: Plan A (`2026-07-30-character-bible-a-helper.md`) must be complete and green.** This plan consumes its `mint_reference` signature verbatim.

## Global Constraints

- **Run everything from `backend/`.** Verify command: `uv run ruff check . && uv run pytest`. `uv` only.
- **`backend/contracts/` MUST NOT be modified.**
- **The returned `characters` list must be COMPLETE.** `characters` carries **no reducer** — only `scenes[]` is `Annotated` with `upsert_scenes` (`contracts/story_memory.py:173`). A partial return of `{"characters": [...]}` **replaces** the list, so returning only the modified entries silently deletes the third character.
- **`cost` has no reducer either.** Copy it from `state.cost` and bump — never rebuild from zero, which would erase `regen_count` and `usd_estimate`.
- **At most 2 characters get a reference** (ADR-004): `characters[0]` and `characters[1]`, in the prominence order `analyze` minted. A third keeps `canonical_ref_image = None`.
- **Cap FIRST, then filter.** `characters[:2]` then drop the already-referenced. Filtering first slides the 2-slot window onto `c2` and mints a third canonical reference against ADR-004.
- **`ref_moderation_status` is NOT written here** — it is owned by the Phase-2 char-ref moderation node. Leave it `None`.
- **Nothing in §8's "hands off" list may be absorbed into this node** — the reveal/confirm step (D-I), scene-image `cost.image_count`, deterministic-path idempotency, character dedup, and the three-preset `style_presets` dict all belong to other owners. Naming them in a comment is correct; implementing them is a spec violation.
- Ruff: `line-length = 120`, default rules. `ruff format` is not adopted — do not reformat existing lines.

---

### Task 4: The `char_bible` node

**Files:**
- Modify: `backend/pipeline/char_bible.py` (replace the temporary `char_bible` stub from Plan A Task 2 Step 6)
- Test: `backend/tests/test_char_bible_node.py` (append)

**Interfaces:**
- Consumes: `mint_reference(description, name, style_fragment, story_id, char_id) -> tuple[str, RefVerdict | None, int]` (Plan A Task 3); `settings.default_style_fragment` (Plan A Task 1); `StoryMemory`, `Character`, `Cost` from `contracts.story_memory`.
- Produces: `char_bible(state: StoryMemory) -> dict` — returns `{}` when nothing to mint, otherwise exactly `{"characters": [...], "cost": Cost}`. Consumed by `pipeline/graph.py` (already wired) and by Task 5's graph test.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_char_bible_node.py`:

```python
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Character, Cost, Input, StoryMemory, Style
from pipeline.char_bible import char_bible


def _char(char_id: str, name: str, ref: str | None = None) -> Character:
    return Character(
        char_id=char_id,
        name=name,
        description=CharacterDescription(species="dog"),
        canonical_ref_image=ref,
    )


def _state(characters: list[Character], style: Style | None = None, cost: Cost | None = None) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="story-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="The dog ran.", redacted_text="The dog ran."),
        characters=characters,
        style=style or Style(),
        cost=cost or Cost(),
    )


def _minted(path: str = "story-1/ref.png", draws: int = 1):
    """A mint_reference stand-in: same 3-tuple shape, one accepted draw."""
    return (path, _verdict(True, ["dog"]), draws)


def test_char_bible_references_at_most_two_characters():
    """Invariant 1 (ADR-004: max 2 canonical refs, v1): a 3-character roster calls the helper
    exactly twice, for c0 and c1."""
    state = _state([_char("c0", "the dog"), _char("c1", "the cat"), _char("c2", "the bird")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(state)

    assert mint.call_count == 2
    assert [call.args[4] for call in mint.call_args_list] == ["c0", "c1"]


def test_char_bible_returns_the_complete_character_list():
    """Invariant 2 — THE REDUCER TRAP. `characters` has no reducer, so a partial return
    REPLACES the list. Returning only the two modified entries deletes c2 silently."""
    c2 = _char("c2", "the bird")
    state = _state([_char("c0", "the dog"), _char("c1", "the cat"), c2])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    assert len(result["characters"]) == 3
    assert result["characters"][2] == c2          # byte-identical to input
    assert result["characters"][2].canonical_ref_image is None
    assert [c.char_id for c in result["characters"]] == ["c0", "c1", "c2"]


def test_char_bible_writes_the_path_and_verdict_onto_the_referenced_characters():
    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted("story-1/ref-c0.png")):
        result = char_bible(state)

    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0.png"
    assert result["characters"][0].ref_verdict.matches_description is True


def test_char_bible_persists_a_failing_verdict_rather_than_failing_the_job():
    """ADR-010/ADR-028: a failed acceptance loop is loud, never a failed job, never a placeholder."""
    failing = ("story-1/ref-c0.png", _verdict(False, ["dog"]), 3)
    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=failing):
        result = char_bible(state)

    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0.png"
    assert result["characters"][0].ref_verdict.matches_description is False


def test_char_bible_accepts_a_null_verdict_from_a_degraded_judge():
    """Spec §4: ref_verdict=None is honest and distinguishable from a FAILED verdict."""
    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=("story-1/ref-c0.png", None, 1)):
        result = char_bible(state)

    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0.png"
    assert result["characters"][0].ref_verdict is None


def test_char_bible_bumps_image_count_by_the_draws_made_and_preserves_the_rest_of_cost():
    """Invariant 4: cost has no reducer, so it is COPIED and bumped — never rebuilt from zero,
    which would erase any field a future node has written."""
    state = _state(
        [_char("c0", "the dog"), _char("c1", "the cat")],
        cost=Cost(image_count=4, regen_count=2, usd_estimate=1.25),
    )

    with patch("pipeline.char_bible.mint_reference", side_effect=[_minted(draws=3), _minted(draws=2)]):
        result = char_bible(state)

    assert result["cost"].image_count == 4 + 3 + 2
    assert result["cost"].regen_count == 2
    assert result["cost"].usd_estimate == 1.25


def test_char_bible_on_an_empty_roster_returns_without_calling_the_helper():
    """Spec §4 edge case: zero characters → no refs, no cost change, and the node does NOT raise.
    Scenes generate unreferenced — a book with drifting art beats no book (ADR-010)."""
    with patch("pipeline.char_bible.mint_reference") as mint:
        result = char_bible(_state([]))

    mint.assert_not_called()
    assert result == {}


def test_char_bible_on_a_single_character_mints_exactly_one_reference():
    """Spec §4: the cap is a ceiling, not a quota."""
    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        result = char_bible(_state([_char("c0", "the dog")]))

    assert mint.call_count == 1
    assert len(result["characters"]) == 1


def test_char_bible_skips_a_character_that_already_has_a_reference():
    """Invariant 6 / CC-10: idempotent re-entry — zero draws, zero cost for an existing ref."""
    state = _state([_char("c0", "the dog", ref="story-1/ref-c0.png"), _char("c1", "the cat")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted(draws=1)) as mint:
        result = char_bible(state)

    assert mint.call_count == 1
    assert mint.call_args.args[4] == "c1"
    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0.png"


def test_char_bible_makes_zero_helper_calls_when_both_references_already_exist():
    """Invariant 6: full re-entry after success costs nothing."""
    state = _state([
        _char("c0", "the dog", ref="story-1/ref-c0.png"),
        _char("c1", "the cat", ref="story-1/ref-c1.png"),
    ])

    with patch("pipeline.char_bible.mint_reference") as mint:
        result = char_bible(state)

    mint.assert_not_called()
    assert result == {}


def test_char_bible_caps_before_it_filters():
    """Spec §4's trap. A 3-character roster where c0 is already referenced calls the helper
    ONCE, for c1 only — never for c2. Filtering before capping slides the 2-slot window onto c2
    and mints a THIRD canonical reference against ADR-004."""
    state = _state([
        _char("c0", "the dog", ref="story-1/ref-c0.png"),
        _char("c1", "the cat"),
        _char("c2", "the bird"),
    ])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        result = char_bible(state)

    assert mint.call_count == 1
    assert mint.call_args.args[4] == "c1"
    assert result["characters"][2].canonical_ref_image is None


def test_char_bible_leaves_ref_moderation_status_untouched():
    """Contract slice: ref_moderation_status is owned by the Phase-2 char-ref moderation node.
    CC-1 is NOT closed by this node completing (spec §5)."""
    state = _state([_char("c0", "the dog"), _char("c1", "the cat"), _char("c2", "the bird")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    for character in result["characters"]:
        assert character.ref_moderation_status is None


def test_char_bible_partial_returns_exactly_characters_and_cost_without_mutating_state():
    """ADR-024: partial-return, never mutate."""
    state = _state([_char("c0", "the dog")])
    before = state.model_dump()

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    assert set(result) == {"characters", "cost"}
    assert state.model_dump() == before


def test_char_bible_falls_back_to_the_default_style_fragment():
    """Spec §4: nothing writes `style` today, so the fallback is the NORMAL Phase-1 path."""
    from app.config import settings

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(_state([_char("c0", "the dog")], style=Style(prompt_fragment=None)))

    assert mint.call_args.args[2] == settings.default_style_fragment


def test_char_bible_prefers_the_state_style_fragment_when_set():
    """ADR-022: the style is frozen before the reference is drawn, and state wins over the default."""
    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(_state([_char("c0", "the dog")], style=Style(prompt_fragment="flat gouache storybook")))

    assert mint.call_args.args[2] == "flat gouache storybook"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_char_bible_node.py -v`
Expected: the 15 new tests FAIL. The first failures read `AssertionError` on `mint.call_count == 2` / `result == {}` passing trivially, because Plan A's placeholder `char_bible` returns `{}` unconditionally. Plan A's 17 tests still pass.

- [ ] **Step 3: Write the implementation**

In `backend/pipeline/char_bible.py`, add `StoryMemory` to the contracts import:

```python
from contracts.story_memory import CharacterDescription, RefVerdict, StoryMemory
```

and add the settings import beside the existing `app.db` one:

```python
from app.config import settings
```

Then replace the placeholder `char_bible` stub with:

```python
def char_bible(state: StoryMemory) -> dict:
    """Pure: select, map, bump, partial-return. Every effect is behind `mint_reference`.

    Linear in the graph — no conditional edge (ADR-003's two branch points are moderation
    pass/fail and consistency pass/fail, and this is neither).
    """
    # Cap FIRST (invariant 1, ADR-004), THEN filter (invariant 6). The order is load-bearing:
    # filtering first slides the 2-slot window onto c2 when c0 is already referenced, producing
    # three canonical references and breaking the cap.
    selected = [c for c in state.characters[:2] if c.canonical_ref_image is None]
    if not selected:
        return {}

    # Nothing writes `style` today, so this fallback is the normal Phase-1 path, not an error
    # path. The three-preset dict and `style_preset_id` resolution belong to `style-presets`.
    style_fragment = state.style.prompt_fragment or settings.default_style_fragment

    minted: dict[str, tuple[str, RefVerdict | None]] = {}
    draws_made = 0
    for character in selected:
        path, verdict, draws = mint_reference(
            character.description, character.name, style_fragment, state.story_id, character.char_id
        )
        minted[character.char_id] = (path, verdict)
        draws_made += draws

    # Invariant 2: `characters` has NO reducer, so a partial return REPLACES the list —
    # returning only the modified entries would silently delete every other character.
    characters = [
        c.model_copy(update={"canonical_ref_image": minted[c.char_id][0], "ref_verdict": minted[c.char_id][1]})
        if c.char_id in minted
        else c
        for c in state.characters
    ]
    # Invariant 4: `cost` has no reducer either — copy and bump, never rebuild from zero.
    # CC-3: this node's prelude bound is 6 (2 references x 3 draws). `image-generator` owns the
    # scene-image half of `image_count`; the breaker cannot trip until it writes its share.
    cost = state.cost.model_copy(update={"image_count": state.cost.image_count + draws_made})

    log.info("char_bible: minted %s in %d draws", sorted(minted), draws_made)
    return {"characters": characters, "cost": cost}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_char_bible_node.py -v`
Expected: 32 passed (17 from Plan A + 15 here).

- [ ] **Step 5: Run the full verify**

Run from `backend/`: `uv run ruff check . && uv run pytest`
Expected: `All checks passed!` and every test green. **Paste the output — do not claim it.**

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/char_bible.py backend/tests/test_char_bible_node.py
git commit -m "feat(char_bible): implement the node — 2-ref cap, full roster, cost bump"
```

---

### Task 5: Prove it through the graph

MASTER_SPEC §6 rule 1: **one patch point per node.** `test_graph_stub.py` already patches `extract_entities`, `segment_scenes` and `generate_and_store`; this adds `mint_reference` and asserts the references survive `input_gate → analyze → segment → char_bible`.

**Files:**
- Modify: `backend/tests/test_graph_stub.py`

**Interfaces:**
- Consumes: `char_bible` (Task 4) via the already-wired `pipeline/graph.py`. No production code changes in this task.

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_graph_stub.py`, add `RefVerdict` to the contracts import:

```python
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, RefVerdict, StoryMemory
```

Add the fourth patch point to `_mock_call_points`, after the `generate_and_store` one:

```python
    monkeypatch.setattr(
        "pipeline.char_bible.mint_reference",
        lambda description, name, style_fragment, story_id, char_id: (
            f"{story_id}/ref-{char_id}.png",
            RefVerdict(differences_observed="none", matches_description=True, attributes_present=["dog"]),
            2,
        ),
    )
```

Append this test at the end of the file:

```python
def test_char_bible_references_survive_the_graph(monkeypatch):
    """Spec §6: patch the single helper and assert the references survive
    input_gate → analyze → segment → char_bible. `characters` has no reducer, so a later node
    replacing the list shows up here and nowhere else."""
    _mock_call_points(monkeypatch)
    app_graph = build_graph()

    result = app_graph.invoke(
        _initial_state("test-job-4"), config={"configurable": {"thread_id": "test-job-4"}}
    )

    character, = result["characters"]
    assert character.canonical_ref_image == "test-job-4/ref-c0.png"
    assert character.ref_verdict.matches_description is True
    assert character.ref_moderation_status is None   # Phase-2 owner, not this node
    assert result["cost"].image_count == 2           # the draws mint_reference reported
```

- [ ] **Step 2: Run the test to verify it fails**

Before adding the patch point, running this test would call the real `mint_reference`. Add the test **first**, without the `_mock_call_points` addition, and run:

Run: `uv run pytest tests/test_graph_stub.py::test_char_bible_references_survive_the_graph -v`
Expected: FAIL — a real `text_to_image` / fal call is attempted and errors on the test key, or `AssertionError: assert None == 'test-job-4/ref-c0.png'`.

- [ ] **Step 3: Add the patch point**

Add the `mint_reference` `monkeypatch.setattr` block from Step 1 to `_mock_call_points`.

- [ ] **Step 4: Run the graph tests to verify they pass**

Run: `uv run pytest tests/test_graph_stub.py -v`
Expected: 4 passed. `test_analyze_roster_survives_the_graph` still passes — it asserts the roster's ids, name and species, none of which `char_bible` touches.

- [ ] **Step 5: Run the full verify**

Run from `backend/`: `uv run ruff check . && uv run pytest`
Expected: `All checks passed!`, everything green. **Paste the output.**

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_graph_stub.py
git commit -m "test(graph): assert char_bible references survive the run"
```

---

### Task 6: Close the Definition of Done — status flip and the finding-change grep

Spec §9 items 5 and 6. AGENTS.md's *Definition of Done*: a finding change has a wider blast radius than the module, and **one doc updated is not done**. The known surface is listed below; the grep is what proves it is the whole surface.

**Files:**
- Modify: `docs/specs/character-bible.md` (status line, line 3)
- Modify: `docs/product/DECISION_BACKLOG.md` (the `character-bible` checklist row ~line 116, and the *"Recommended next session"* block ~line 171)
- Modify: `docs/WORKFLOW.md` (§"Right now", ~line 106)
- Modify: `AGENTS.md` (*Project Context* stub list ~line 195, *Validation Notes* remaining-Phase-1 list ~line 358)
- Delete: both plan files in `docs/specs/plans/`

**Interfaces:** none — documentation only. **No new file may be added to AGENTS.md's nine-file status surface.** This spec points at `PHASE_05_RESULTS.md` and asserts no probe numbers of its own.

- [ ] **Step 1: Run the finding-change grep**

Run from the repo root:

```bash
grep -rn "char_bible\|character-bible" --include=*.md . | grep -v "docs/specs/plans/"
```

Expected: hits in `docs/specs/character-bible.md`, `docs/product/DECISION_BACKLOG.md`, `docs/WORKFLOW.md`, `AGENTS.md`, `docs/MASTER_SPEC.md`, `docs/specs/story-analyzer.md`, `docs/product/ROADMAP.md`. Every hit that asserts *"stub"*, *"draft"*, or *"next action"* must be fixed in this change. Hits that merely describe the node's behavior stay.

- [ ] **Step 2: Flip the spec status line**

In `docs/specs/character-bible.md` line 3, change `**Status:** draft` to `**Status:** built` and append the commit range from Tasks 1–5, e.g.:

```markdown
**Status:** built (2026-07-30, `<first-sha>..<last-sha>`) · **Phase:** 1 · **Owner node:** `backend/pipeline/char_bible.py`
```

Get the range with: `git log --oneline -6`

- [ ] **Step 3: Update `docs/product/DECISION_BACKLOG.md`**

Replace the `- [ ] character-bible` checklist row (~line 116) with:

```markdown
- [x] `character-bible`   *(spec **built 2026-07-30** — `docs/specs/character-bible.md`;
      `pipeline/char_bible.py` owns ADR-028's reference-acceptance loop — draw → judge vs
      `CharacterDescription` → re-roll, 3-draw cap, best-of by `attributes_present`. Caps references at
      **2** per ADR-004. Authored `settings.default_style_fragment` (ADR-022 `cel`); `contracts/`
      untouched. Opened **D-I**. Hands the reveal step to D-I, deterministic-path idempotency and
      scene-image `cost.image_count` to `image-generator`, and the preset dict to `style-presets`.)*
```

Replace the **Build `character-bible`** paragraph (~line 171) with:

```markdown
> ✅ **`character-bible` is built (2026-07-30).** See `docs/specs/character-bible.md`.

**Build `style-presets`** — ADR-022's three presets (`cel` / `comic` / `gouache`), `style_preset_id`
resolution and the picker UI. `char_bible` authored one default fragment and nothing else; the preset
dict and ADR-022's binding "must not read as generic AI art" acceptance condition are still unowned in
code. Write `docs/specs/style-presets.md` from `docs/specs/TEMPLATE.md` before any code (AGENTS.md).
```

Leave the **No open decision blocks Phase 1** paragraph and the D-I row untouched — D-I is still open and still non-blocking.

Update the trailing roadmap-order line to drop `character-bible`:

```markdown
After `style-presets`, in roadmap order: `prompt-optimizer`, `image-generator`, `consistency-checker`, `regeneration-controller`.
```

- [ ] **Step 4: Update `docs/WORKFLOW.md` §"Right now"**

Replace lines 106–108 (the **Next action: `character-bible` spec** paragraph) with:

```markdown
`character-bible` is **built** (2026-07-30): `backend/pipeline/char_bible.py` mints at most 2 canonical
references (ADR-004), judges each against its `CharacterDescription` and re-rolls up to 3 times
(ADR-028), persists the verdict — including a failing one — and bumps `cost.image_count`.

**Next action: `style-presets` spec** — write `docs/specs/style-presets.md` from
`docs/specs/TEMPLATE.md` before writing any code (AGENTS.md). `char_bible` authored
`settings.default_style_fragment` only; ADR-022's three-preset dict and picker are still unowned.
```

Also add a line to the "built" list above it, matching the existing entries' shape:

```markdown
`character-bible` is **built** (2026-07-30): `backend/pipeline/char_bible.py`.
```

- [ ] **Step 5: Update `AGENTS.md`**

In *Project Context* (~line 195), the sentence currently reads `` `input_gate`, `char_bible`, `consistency_check`, and `compose` are pass-through stubs ``. Change it to:

```markdown
  `input_gate`, `consistency_check`, and `compose` are pass-through stubs; `analyze` mints the entity
  roster; `segment` splits into scenes (≤15), maps names → char_ids, and sets `caption = text_excerpt`
  (ADR-013); `char_bible` mints ≤2 canonical references with ADR-028's 3-draw acceptance loop;
  `generate_scene` has real behavior.
```

In *Validation Notes* (~line 355), after the `scene-segmentation` entry, add:

```markdown
  **`character-bible` is built (2026-07-30):** `pipeline/char_bible.py` mints ≤2 canonical references
  (ADR-004), judges each against its `CharacterDescription` with a 3-draw cap and best-of fallback
  (ADR-028), persists `ref_verdict` — failing verdicts included — and bumps `cost.image_count`.
  Added `settings.default_style_fragment` (ADR-022 `cel`). CC-1 is **not** closed for the char-ref leg.
```

and change the last line to:

```markdown
  Remaining Phase-1 specs: `consistency-check`, `regeneration-controller`, `compose`.
```

- [ ] **Step 6: Confirm the two 2026-07-30 corrections still read true**

Spec §8 records that `docs/specs/story-analyzer.md` §5 and `docs/MASTER_SPEC.md` §2 were corrected when the spec was written. Confirm, no edit expected:

```bash
grep -n "reference draws" docs/specs/story-analyzer.md
grep -n -A2 "char_bible" docs/MASTER_SPEC.md
```

Expected: `story-analyzer` §5 shows the struck-through *"at most 9"* with **6** standing; the MASTER_SPEC `char_bible` row lists `canonical_ref_image`, `ref_verdict`, `cost.image_count` and **not** `ref_moderation_status`, with a separate row for the Phase-2 gate. If either has drifted, fix it here.

- [ ] **Step 7: Delete the plans**

AGENTS.md *Artifact hygiene*: specs are durable, plans are disposable — `docs/specs/plans/` holds only in-flight work, and git keeps the history.

```bash
git rm docs/specs/plans/2026-07-30-character-bible-a-helper.md docs/specs/plans/2026-07-30-character-bible-b-node.md
```

- [ ] **Step 8: Final verify**

Run from `backend/`: `uv run ruff check . && uv run pytest`
Expected: `All checks passed!` and all tests green. **Paste the output into the completion report — never claim it.**

- [ ] **Step 9: Commit**

```bash
git add docs AGENTS.md
git commit -m "docs(spec): mark character-bible built; close blast-radius sites"
```

---

## Definition of done (spec §9 — check every line before reporting)

1. `backend/pipeline/char_bible.py` implements §4: `reference_prompt` and `best_draw` (pure), the `mint_reference` effect helper, and a node that selects, maps, bumps `cost` and partial-returns. The `# ponytail: stub` comment and its spec pointer are gone.
2. `settings.default_style_fragment` exists in `backend/app/config.py` holding ADR-022's `cel` fragment, and `backend/.env.example` carries the override line.
3. Every §6 assertion exists and passes in `backend/tests/test_char_bible_node.py` (the §6 *graph* bullet lives in `test_graph_stub.py`, where the graph test already is — no parallel structures).
4. `uv run ruff check . && uv run pytest` is green from `backend/`, **with the output shown, not claimed**.
5. The spec's status line reads `built` with the commit range.
6. The finding-change grep was run and every hit fixed in the same change.
7. No new file was added to AGENTS.md's nine-file status surface.

**Not done if:** any §6 test is skipped; `backend/contracts/` was modified; the returned `characters` list is partial; `cost` was rebuilt rather than copied-and-bumped; the 2-reference cap is enforced only by prompt text; the reveal gap was silently implemented instead of left to `D-I`; or any §8 handoff was absorbed into this node instead of being left to its owner.

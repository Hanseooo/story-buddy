# Regeneration Controller — Part 2: The Retry Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/specs/regeneration-controller.md`
**Prerequisite:** `docs/specs/plans/2026-08-02-regeneration-controller-part-1-prerequisites.md` must be complete and green. Tasks 5 and 6 here call `generate_and_store` with `attempt_n` and `correct_prompt` with two booleans — neither exists until Part 1 lands.

**Goal:** Build ADR-010 in code — one corrected retry per failing scene, best-of between the two attempts, and never a broken page.

**Architecture:** Four changes that must land together. `consistency_check` stops finalizing unconditionally and gains a lexicographic best-of rule (Task 4). A new `regenerate` node redraws once from a corrected prompt (Task 5). A new pure router `route_after_check` sends a checked-and-failing scene to it (Task 6). Then the doc surface is swept (Task 7). Tasks 4 and 6 are deliberately in the same plan: between them there is a window where a checked failure no longer finalizes but nothing routes to `regenerate` yet, and a real failing judge would redraw with an **uncorrected** prompt — exactly the resample ADR-010 rejects. CI stays green through that window, so nothing would catch it. Do not merge Task 4 alone.

**Tech Stack:** Python 3.12, uv, pytest, ruff, Pydantic v2, LangGraph 1.2.8, Supabase Storage.

## Global Constraints

Copied verbatim from `AGENTS.md` and the spec. Every task's requirements implicitly include this section.

- **`backend/contracts/` must not be modified.** Every field this work writes already exists. The spec's *Not done* clause names this first.
- **`FailureReason` must not gain a value.** Frozen at 7 permanently (ADR-028).
- **`regenerate` appends exactly one `Attempt`, or raises. It never returns `{}`.** A `{}` return leaves state unchanged, so `consistency_check` re-judges the same attempt, reaches the same verdict, and `route_after_check` sends control straight back — an infinite loop bounded only by `recursion_limit`. The two guards are unreachable by construction and therefore **raise**.
- **`regenerate` never writes `final_image_ref`.** `consistency_check` remains its only writer.
- **`regenerate` never writes `scenes[].prompt`.** That field holds the original `build_prompt` output; per-attempt provenance is `Attempt.prompt`.
- **`regenerate` never writes `scenes[].regeneration_count`.** It equals `len(attempts) - 1`; a stored copy of a derived fact is a second source of truth a resume can desynchronise.
- **At most one regeneration per scene** (ADR-010). The budget is `len(scene.attempts)`, derived — there is no budget field.
- **`cost.regen_count` is incremented on every invocation; `cost.image_count` only when the image was actually paid for.** The asymmetry is deliberate — see Task 5.
- **All commands run from `backend/`.** Verify with `uv run ruff check . && uv run pytest`.
- **Deterministic tests mock every `providers.py` call.** Never assert on generated content.
- **`ruff format` is not adopted.** Only `ruff check`.
- **One module = one concern, one file per pipeline node.** `regenerate` gets its own file.
- Exact values from Part 1: `IMAGE_BUDGET = MAX_SCENES * 2 + 9` (= 39), `RECURSION_LIMIT = MAX_SCENES * 4 + 9` (= 69), Storage path `f"{story_id}/{scene_id}-{attempt_n}.png"`.

## File Structure

| File | Task | Responsibility after this plan |
|---|---|---|
| `backend/pipeline/consistency_check.py` | 4 | Gains `_rank`, the three-term `finalize` rule, and best-of selection. Stays the **only** writer of `final_image_ref`. |
| `backend/tests/test_consistency_check_node.py` | 4 | Best-of and finalization cases. Existing assertions stay green unedited. |
| `backend/pipeline/regenerate.py` | 5 | **New.** ADR-010's one corrected retry. Imports `generate_and_store` from `generate_scene` rather than restating the effect boundary — the fal upload cache, the Storage round-trip and the CC-10 skip exist once. |
| `backend/tests/test_regenerate_node.py` | 5 | **New.** The node seam, `generate_and_store` patched. |
| `backend/pipeline/graph.py` | 6 | Gains `route_after_check`, the `regenerate` node, the re-pointed `consistency_check` registration, and `add_edge("regenerate", "consistency_check")`. `route_next_scene` keeps its `char_bible` registration and is **called by** `route_after_check`, not replaced. |
| `backend/tests/test_graph_stub.py` | 6 | Loop-termination tests for retry-then-pass and both-fail. |
| `backend/tests/test_consistency_check_node.py` | 6 | `route_after_check` router cases (they live beside `route_next_scene`'s). |
| six doc files | 7 | The spec's DoD item 10 grep surface. |

---

### Task 4: Best-of and the three-term `finalize` rule

`consistency_check` currently finalizes unconditionally (`consistency_check.py:160`). It stops doing that:

```python
finalize = passed or verdict is None or len(scene.attempts) >= 2
```

The **`verdict is None` term is load-bearing**: an *unchecked* attempt finalizes, it does not retry. Without it a judge or Storage outage turns every scene into two paid draws with no signal to correct on — and a redraw chosen by an outage is exactly the uncorrected resample ADR-010 rejects. ADR-025's posture applies unchanged: the *check* failed, not the artifact. Only a real verdict that says *fail* buys a retry.

Three things about the ranking expression:

- **It runs over `updated`, not `scene.attempts`** — the attempt judged this pass must carry its own verdict into the comparison.
- **Reverse iteration is required.** Python's `max` returns the *first* maximal element, so ranking forward would keep attempt 1 on a tie. The rule is **tie → attempt 2**: on a genuine tie the corrected prompt is the better prior, and ADR-010 calls attempt 2 refinement rather than resampling.
- **No special case for a passing attempt.** A pass scores `(1, 1, 1, …)` and beats anything that gated, so `max` is correct uniformly.

**Unchecked sorts last** (`(0,0,0,0)`), so a checked failure beats an unjudged image. Promoting an unjudged image over a judged one would let a judge outage silently decide the page, contradicting invariant 4 (*unchecked is never a pass*).

> **One deliberate rendering difference from the spec.** The spec writes `max(reversed(updated), key=_rank).image_ref`. This plan ranks over `reversed(range(len(updated)))` instead and indexes in. Identical ordering rule, identical tie behaviour — but it yields the winner's **position**, which CC-5 needs in order to log `best_of=1`. Recovering the position from the winning `Attempt` afterwards would need `updated.index(winner)`, and `index` compares by value, so on a genuine tie between two byte-identical attempts it would report attempt 1 and contradict the rule the same line just implemented.

**Files:**
- Modify: `backend/pipeline/consistency_check.py` — insert `_rank` above `consistency_check`, rewrite the tail of the node (lines 141-164)
- Test: `backend/tests/test_consistency_check_node.py` (append)

**Interfaces:**
- Consumes: `Attempt` from `contracts.story_memory` — **must be added to the existing import** at `consistency_check.py:14`, which currently imports only `FailureReason, StoryMemory, VlmVerdict`.
- Produces: `_rank(a: Attempt) -> tuple[int, int, int, int]` — module-private, used by the node and asserted indirectly through it. No other module imports it.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_consistency_check_node.py`, immediately before the `# --- route_next_scene` section (i.e. before line 377):

```python
# --- ADR-010 best-of and the three-term finalize rule (regeneration-controller §4) ---

def _attempt(image_ref: str, *, same: bool | None = None, anatomy: bool = True, style: bool = True) -> Attempt:
    """An already-judged attempt. same=None means UNCHECKED (vlm_verdict is None)."""
    if same is None:
        return Attempt(image_ref=image_ref, prompt="p", passed=False)
    return Attempt(
        image_ref=image_ref,
        prompt="p",
        vlm_verdict=VlmVerdict(
            differences_observed="d", same_character=same, style_match=style, anatomy_intact=anatomy
        ),
        passed=same and anatomy,
    )


def _two_attempt_scene(first: Attempt, second: Attempt) -> Scene:
    return Scene(scene_id="s0", text_excerpt="x", characters_present=["c0"], attempts=[first, second])


def test_node_defers_finalization_when_a_single_attempt_fails_the_gate():
    """The whole point of the change: a checked FAILURE with one attempt is left unfinalized so
    route_after_check can send it to regenerate."""
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])
    result = _run(state, [_verdict(False)])

    assert result["scenes"][0].final_image_ref is None


def test_node_finalizes_a_single_unchecked_attempt_rather_than_retrying():
    """The `verdict is None` term is load-bearing. A judge or Storage outage must not buy a
    second paid draw with no signal to correct on — that redraw would be a pure resample."""
    state = _state([_scene_with_attempt(characters_present=[])])
    result = _run(state, [])

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_node_finalizes_a_single_passing_attempt():
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])
    result = _run(state, [_verdict(True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_best_of_prefers_the_attempt_that_wins_on_same_character():
    """Lexicographic: same_character is the first term and outranks everything below it."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=True, anatomy=False, style=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=True, style=True),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(False, anatomy=True, style=True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_best_of_prefers_the_attempt_that_wins_on_anatomy_when_identity_ties():
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, style=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=False, style=True),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(False, anatomy=False, style=True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_best_of_prefers_the_attempt_that_wins_on_style_when_the_first_two_terms_tie():
    """style_match does not GATE, but it is the third term of the ranking (ADR-028)."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, style=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=True, style=True),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(False, anatomy=True, style=True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-2.png"


def test_best_of_breaks_a_genuine_tie_in_favour_of_attempt_two():
    """Pinned explicitly: max returns the FIRST maximal element, so this only holds because the
    ranking iterates in reverse. On a tie the corrected prompt is the better prior — ADR-010
    calls attempt 2 refinement, not resampling."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, style=True),
        _attempt("job-1/s0-2.png", same=False, anatomy=True, style=True),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(False, anatomy=True, style=True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-2.png"


def test_best_of_ranks_a_checked_failure_above_an_unchecked_attempt():
    """Unchecked sorts last (0,0,0,0). Promoting an unjudged image over a judged one would let
    a judge outage silently decide the page — invariant 4 says unchecked is never a pass."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=False, style=False),
        _attempt("job-1/s0-2.png", same=None),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [])

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_two_attempts_always_finalize_even_when_both_fail():
    """ADR-010: at most one regeneration per scene, and never a broken page. A real image ships."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=False),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(False, anatomy=False)])

    finalized = result["scenes"][0]
    assert finalized.final_image_ref is not None
    assert all(a.passed is False for a in finalized.attempts)


def test_best_of_uses_the_verdict_written_this_pass_not_the_stale_one():
    """Ranking runs over `updated`, not scene.attempts. If it ranked the pre-fold list, attempt 2
    would carry no verdict, sort last, and attempt 1 would win every retry."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=False, style=False),
        Attempt(image_ref="job-1/s0-2.png", prompt="corrected", passed=False),   # unjudged going in
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(True, anatomy=True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-2.png"


def test_the_second_pass_never_rewrites_attempt_ones_verdict():
    """consistency-checker invariant 3: only the last attempt is judged and mutated."""
    first = _attempt("job-1/s0-1.png", same=False, anatomy=False, style=False)
    scene = _two_attempt_scene(first, Attempt(image_ref="job-1/s0-2.png", prompt="corrected"))
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(True)])

    assert result["scenes"][0].attempts[0] == first


def test_the_returned_attempt_list_replaces_rather_than_appends():
    """len(updated) == len(scene.attempts). Appending here would let a scene reach three attempts
    and break ADR-010's at-most-one-regeneration rule."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False),
        Attempt(image_ref="job-1/s0-2.png", prompt="corrected"),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(True)])

    assert len(result["scenes"][0].attempts) == 2
```

Update that file's contract import block (lines 9-20) to include `VlmVerdict`:

```python
from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Attempt,
    Character,
    CharacterDescription,
    Cost,
    FailureReason,
    Input,
    RefVerdict,
    Scene,
    StoryMemory,
    VlmVerdict,
)
```

and update `_scene_with_attempt`'s default `image_ref` (line 166) from `"job-1/s0.png"` to `"job-1/s0-1.png"`, plus the four other `"job-1/s0.png"` / `"job-1/s1.png"` literals in that file to their `-1` forms, so the fixtures match Part 1's Storage scheme. `test_node_sets_final_image_ref_to_the_last_attempts_image` keeps its distinct `"job-1/scene-abc.png"` — it is asserting identity, not the path scheme, so leave that one alone.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_consistency_check_node.py -v`
Expected: FAIL. `test_node_defers_finalization_when_a_single_attempt_fails_the_gate` fails with `assert 'job-1/s0-1.png' is None` — the node finalizes unconditionally today. The best-of tests fail because `final_image_ref` is always `attempts[-1].image_ref`.

- [ ] **Step 3: Add `_rank`**

In `backend/pipeline/consistency_check.py`, add `Attempt` to the contract import (line 14):

```python
from contracts.story_memory import Attempt, FailureReason, StoryMemory, VlmVerdict
```

and insert this function directly above `def consistency_check` (after line 80):

```python
def _rank(a: Attempt) -> tuple[int, int, int, int]:
    """ADR-028's lexicographic best-of signal, with unchecked sorting below every checked attempt.

    A pass scores (1, 1, 1, …) and beats anything that gated, so `max` needs no special case for
    it. Unchecked scores (0, 0, 0, 0): promoting an unjudged image over a judged one would let a
    judge outage silently decide the page, contradicting invariant 4 (unchecked is never a pass).
    """
    v = a.vlm_verdict
    return (0, 0, 0, 0) if v is None else (1, v.same_character, v.anatomy_intact, v.style_match)
```

- [ ] **Step 4: Replace the node's tail**

In `backend/pipeline/consistency_check.py`, replace everything from the CC-5 log comment through the end of the function (lines 139-164) with:

```python
    updated = [
        *scene.attempts[:-1],
        attempt.model_copy(
            update={"vlm_verdict": verdict, "failure_reasons": reasons, "passed": passed}
        ),
    ]

    # A pass finalizes; so does an UNCHECKED attempt — a judge or Storage outage must not buy a
    # second paid draw with no signal to correct on (that redraw would be the uncorrected
    # resample ADR-010 rejects; ADR-025: the CHECK failed, not the artifact). Only a real verdict
    # saying *fail* buys the one retry, and only the first time — ADR-010 caps it at one, and the
    # budget is len(attempts), derived, because ADR-024 rejected stored cursors.
    finalize = passed or verdict is None or len(scene.attempts) >= 2

    # ADR-028's best-of. Ranked over `updated`, not scene.attempts — the attempt judged THIS pass
    # must carry its own verdict into the comparison. Iterating in REVERSE is load-bearing: max
    # returns the FIRST maximal element, so ranking forward would keep attempt 1 on a tie, and the
    # rule is tie → attempt 2 (the corrected prompt is the better prior; ADR-010 calls attempt 2
    # refinement, not resampling). Indices rather than the Attempts themselves so CC-5 below can
    # log WHICH attempt won — `updated.index(winner)` compares by value and would report attempt 1
    # on exactly the tie this line exists to break.
    best = max(reversed(range(len(updated))), key=lambda i: _rank(updated[i])) if finalize else None

    # CC-5: a wrong character in the finished book traces to a scene, an attempt, and the verdict
    # that let it through. `best_of` is what tells a reader whether a retry ran and lost or never
    # ran at all — without it an off-character page gives no way to distinguish the two.
    log.info(
        "consistency_check: scene_id=%s attempt=%d/%d subjects=%d %s same_character=%s "
        "anatomy_intact=%s style_match=%s failure_reasons=%s passed=%s best_of=%s",
        scene.scene_id, len(updated), len(updated), len(subjects), "checked" if verdict else "unchecked",
        verdict and verdict.same_character, verdict and verdict.anatomy_intact,
        verdict and verdict.style_match, [r.value for r in reasons], passed,
        None if best is None else best + 1,
    )

    return {
        "scenes": [
            scene.model_copy(
                update={
                    "attempts": updated,
                    # Invariant 2: this node, and only this node, finalizes a scene.
                    "final_image_ref": None if best is None else updated[best].image_ref,
                }
            )
        ]
    }
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_consistency_check_node.py -v`
Expected: PASS — 13 new tests plus all 22 that were already there.

- [ ] **Step 6: Run the full backend verify**

Run: `uv run ruff check . && uv run pytest`
Expected: green. `test_graph_stub.py` still passes because its stub judge returns `[]` (unchecked), which finalizes on the `verdict is None` term.

- [ ] **Step 7: Commit**

```bash
git add backend/pipeline/consistency_check.py backend/tests/test_consistency_check_node.py
git commit -m "feat(consistency-check): ADR-028 best-of ranking and the three-term finalize rule"
```

---

### Task 5: The `regenerate` node

Its own file per AGENTS.md, importing `generate_scene.generate_and_store` rather than restating the effect boundary — the fal upload cache, the Storage round-trip and the CC-10 skip exist **once**.

**`regen_count` is not gated on `paid` — and that is not a bug.** It sits one line below `image_count`, which *is* gated, so the asymmetry looks like an oversight. On an ADR-025 resume the checkpoint predates this node's return, so both counters start from their pre-`regenerate` values: `image_count + 0` correctly records that the Storage skip meant no re-pay, and `regen_count + 1` correctly records the regeneration whose increment the lost checkpoint never persisted. Gating `regen_count` on `paid` would count it as zero.

**No prompt to correct → raise.** Unreachable today (`generate_scene` always sets both `Attempt.prompt` and `Scene.prompt`), and the alternative — drawing from correction clauses with no base prompt — is a guaranteed-garbage paid image. An ADR-025 hard failure is the honest outcome.

**Files:**
- Create: `backend/pipeline/regenerate.py`
- Test: `backend/tests/test_regenerate_node.py`

**Interfaces:**
- Consumes: `generate_and_store(prompt, story_id, scene_id, attempt_n, ref_paths) -> tuple[str, bool]` from `pipeline.generate_scene` (Part 1 Task 2); `correct_prompt(prompt, failure_reasons, characters, style_fragment, same_character=, anatomy_intact=) -> str` from `pipeline.prompt_optimizer` (Part 1 Task 3); `IMAGE_BUDGET` from `app.config`; `Attempt, StoryMemory` from `contracts.story_memory`.
- Produces: `regenerate(state: StoryMemory) -> dict` — a partial return with keys exactly `{"scenes", "cost"}`. Task 6 registers it as a graph node under the name `"regenerate"`.

- [ ] **Step 1: Write the failing test file**

Create `backend/tests/test_regenerate_node.py`:

```python
"""Deterministic tests for `regenerate` (spec `docs/specs/regeneration-controller.md` §6).

One seam (MASTER_SPEC §6): the node with `generate_and_store` patched. Everything else in this
node is pure — `correct_prompt` has no model call, and the selection rule is a list scan.
"""
import pytest
from unittest.mock import patch

from app.config import IMAGE_BUDGET
from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Attempt,
    Character,
    CharacterDescription,
    Cost,
    FailureReason,
    Input,
    Scene,
    StoryMemory,
    Style,
    VlmVerdict,
)
from pipeline.prompt_optimizer import ANATOMY_CLAUSE, IDENTITY_CLAUSE
from pipeline.regenerate import regenerate


def _char(char_id: str = "c0", name: str = "the dog", ref: str | None = "job-1/ref-c0.png") -> Character:
    return Character(
        char_id=char_id,
        name=name,
        description=CharacterDescription(species="dog", colours=["orange"]),
        canonical_ref_image=ref,
    )


def _verdict(*, same: bool = False, anatomy: bool = True, style: bool = True) -> VlmVerdict:
    return VlmVerdict(
        differences_observed="the face is wrong",
        same_character=same,
        style_match=style,
        anatomy_intact=anatomy,
    )


def _failed_attempt(
    *,
    verdict: VlmVerdict | None = None,
    reasons: list[FailureReason] | None = None,
    prompt: str | None = "the original prompt",
) -> Attempt:
    return Attempt(
        image_ref="job-1/s0-1.png",
        prompt=prompt,
        vlm_verdict=verdict if verdict is not None else _verdict(),
        failure_reasons=reasons or [],
        passed=False,
    )


def _state(
    scenes: list[Scene],
    characters: list[Character] | None = None,
    cost: Cost | None = None,
) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        characters=characters if characters is not None else [_char()],
        style=Style(prompt_fragment="flat cel-shaded cartoon"),
        scenes=scenes,
        cost=cost or Cost(),
    )


def _scene(attempts: list[Attempt] | None = None, **kwargs) -> Scene:
    return Scene(
        scene_id="s0",
        text_excerpt="The dog ran.",
        characters_present=["c0"],
        prompt="the original prompt",
        attempts=attempts if attempts is not None else [_failed_attempt()],
        **kwargs,
    )


def _run(state: StoryMemory, *, paid: bool = True):
    with patch(
        "pipeline.regenerate.generate_and_store", return_value=("job-1/s0-2.png", paid)
    ) as store:
        return regenerate(state), store


# --- the partial return (invariant 1) ---

def test_appends_exactly_one_attempt_and_returns_both_keys():
    result, _ = _run(_state([_scene()]))

    assert set(result) == {"scenes", "cost"}
    scene, = result["scenes"]
    assert len(scene.attempts) == 2
    assert scene.attempts[-1].image_ref == "job-1/s0-2.png"
    assert scene.attempts[-1].passed is False


def test_returns_the_pre_existing_attempt_byte_identical():
    """Only consistency_check judges and mutates attempts. This node appends and nothing else."""
    first = _failed_attempt()
    result, _ = _run(_state([_scene([first])]))

    assert result["scenes"][0].attempts[0] == first


def test_never_returns_an_empty_dict_on_any_reachable_path():
    """Invariant 1: `{}` leaves state unchanged, so consistency_check re-judges the same attempt,
    reaches the same verdict, and route_after_check sends control straight back — an infinite
    loop bounded only by recursion_limit."""
    result, _ = _run(_state([_scene()]))

    assert result != {}


# --- attempt_n (the per-attempt Storage path) ---

def test_passes_attempt_n_of_len_attempts_plus_one():
    _, store = _run(_state([_scene()]))

    assert store.call_args.args[3] == 2


def test_attempt_n_tracks_the_attempt_list_rather_than_a_stored_counter():
    """ADR-024 rejected a loop cursor for the same reason: derived beats stored."""
    scene = _scene([_failed_attempt(), Attempt(image_ref="job-1/s0-2.png", prompt="second")])
    _, store = _run(_state([scene]))

    assert store.call_args.args[3] == 3


# --- cost (invariant 6) ---

def test_bumps_image_count_and_regen_count_when_paid():
    result, _ = _run(_state([_scene()], cost=Cost(image_count=4, regen_count=1)), paid=True)

    assert result["cost"].image_count == 5
    assert result["cost"].regen_count == 2


def test_bumps_regen_count_but_not_image_count_when_the_asset_was_reused():
    """Resume mid-retry: the checkpoint predates this return, so both counters start from their
    pre-regenerate values. image_count + 0 records that the Storage skip meant no re-pay;
    regen_count + 1 records the regeneration the lost checkpoint never persisted. Gating
    regen_count on `paid` would count it as zero."""
    result, _ = _run(_state([_scene()], cost=Cost(image_count=4, regen_count=1)), paid=False)

    assert result["cost"].image_count == 4
    assert result["cost"].regen_count == 2


# --- what this node must NOT write (invariants 2, 3, 7) ---

def test_never_writes_final_image_ref():
    """Invariant 2: consistency_check remains its only writer."""
    result, _ = _run(_state([_scene()]))

    assert result["scenes"][0].final_image_ref is None


def test_never_writes_the_scene_prompt():
    """Invariant 3: scenes[].prompt holds the ORIGINAL build_prompt output. Per-attempt
    provenance is Attempt.prompt, which is what that field exists for (CC-5 tracing)."""
    result, _ = _run(_state([_scene()]))

    assert result["scenes"][0].prompt == "the original prompt"


def test_never_writes_regeneration_count():
    """Invariant 7: it equals len(attempts) - 1. A stored copy of a derived fact is a second
    source of truth that a resume can desynchronise."""
    result, _ = _run(_state([_scene()]))

    assert result["scenes"][0].regeneration_count == 0


def test_does_not_mutate_the_state_it_was_handed():
    state = _state([_scene()])
    before = state.model_dump()

    _run(state)

    assert state.model_dump() == before


# --- ref_paths (identical to generate_scene's loop) ---

def test_collects_refs_only_for_present_characters_carrying_a_canonical_image():
    cat = _char("c1", "the cat", ref=None)
    scene = _scene()
    scene = scene.model_copy(update={"characters_present": ["c0", "c1"]})
    _, store = _run(_state([scene], characters=[_char(), cat]))

    assert store.call_args.args[4] == ["job-1/ref-c0.png"]


def test_skips_an_unresolvable_char_id_without_raising():
    """This node may not extend the roster — identical posture to generate_scene."""
    scene = _scene().model_copy(update={"characters_present": ["c0", "ghost-id"]})
    _, store = _run(_state([scene], characters=[_char()]))

    assert store.call_args.args[4] == ["job-1/ref-c0.png"]


def test_falls_back_to_text_to_image_refs_when_the_scene_has_none():
    """ref_paths == [] → the same text_to_image branch generate_scene takes. The corrected
    prompt still applies."""
    scene = _scene().model_copy(update={"characters_present": []})
    _, store = _run(_state([scene]))

    assert store.call_args.args[4] == []


# --- invariant 5: the prompt is ALWAYS corrected, never resampled ---

def test_corrected_prompt_differs_from_the_previous_attempts_prompt_on_reasons():
    scene = _scene([_failed_attempt(reasons=[FailureReason.different_face])])
    _, store = _run(_state([scene]))

    sent = store.call_args.args[0]
    assert sent != "the original prompt"
    assert sent.startswith("the original prompt")
    assert "match the reference character's face exactly" in sent


def test_corrected_prompt_differs_on_an_anatomy_only_failure():
    """ADR-028 froze anatomy out of FailureReason, so without the boolean this retry would send
    a byte-identical prompt — a pure resample."""
    scene = _scene([_failed_attempt(verdict=_verdict(same=True, anatomy=False), reasons=[])])
    _, store = _run(_state([scene]))

    sent = store.call_args.args[0]
    assert sent != "the original prompt"
    assert ANATOMY_CLAUSE in sent


def test_corrected_prompt_differs_on_same_character_false_with_no_reasons():
    """The judge named the failure but gave no reason for it."""
    scene = _scene([_failed_attempt(verdict=_verdict(same=False), reasons=[])])
    _, store = _run(_state([scene]))

    sent = store.call_args.args[0]
    assert sent != "the original prompt"
    assert IDENTITY_CLAUSE in sent


def test_the_identity_clause_is_suppressed_when_the_judge_gave_a_reason():
    """No duplication with different_face."""
    scene = _scene([_failed_attempt(verdict=_verdict(same=False), reasons=[FailureReason.different_face])])
    _, store = _run(_state([scene]))

    assert IDENTITY_CLAUSE not in store.call_args.args[0]


def test_the_new_attempt_records_the_corrected_prompt_not_the_original():
    """CC-5: per-attempt provenance is the whole reason Attempt.prompt exists."""
    scene = _scene([_failed_attempt(reasons=[FailureReason.different_face])])
    result, store = _run(_state([scene]))

    assert result["scenes"][0].attempts[-1].prompt == store.call_args.args[0]


def test_corrects_from_the_scene_prompt_when_the_attempt_carries_none():
    scene = _scene([_failed_attempt(prompt=None, reasons=[FailureReason.different_face])])
    _, store = _run(_state([scene]))

    assert store.call_args.args[0].startswith("the original prompt")


def test_treats_a_missing_verdict_as_no_boolean_correction():
    """`v.same_character if v else True` — an attempt with no verdict cannot have failed on
    identity or anatomy, so neither boolean clause fires."""
    scene = _scene([_failed_attempt(verdict=None, reasons=[FailureReason.wrong_colour])])
    _, store = _run(_state([scene]))

    sent = store.call_args.args[0]
    assert IDENTITY_CLAUSE not in sent
    assert ANATOMY_CLAUSE not in sent


# --- the guards that raise (invariant 1, ADR-025 D4) ---

def test_raises_when_no_scene_is_unfinalized():
    state = _state([_scene(final_image_ref="job-1/s0-1.png")])

    with patch("pipeline.regenerate.generate_and_store") as store, pytest.raises(RuntimeError):
        regenerate(state)

    store.assert_not_called()


def test_raises_when_the_selected_scene_has_no_attempts():
    """A scene with no attempts belongs to generate_scene, and route_after_check says so.
    Returning {} here instead would ping-pong forever."""
    state = _state([_scene([])])

    with patch("pipeline.regenerate.generate_and_store") as store, pytest.raises(RuntimeError):
        regenerate(state)

    store.assert_not_called()


def test_raises_before_any_spend_when_the_image_budget_is_reached():
    """ADR-025 D4. A retry is not exempt from the breaker — same posture as generate_scene."""
    state = _state([_scene()], cost=Cost(image_count=IMAGE_BUDGET))

    with patch("pipeline.regenerate.generate_and_store") as store, pytest.raises(RuntimeError):
        regenerate(state)

    store.assert_not_called()


def test_raises_when_neither_the_attempt_nor_the_scene_carries_a_prompt():
    """Unreachable today. The alternative — drawing from correction clauses with no base prompt —
    is a guaranteed-garbage PAID image, so an ADR-025 hard failure is the honest outcome."""
    scene = _scene([_failed_attempt(prompt=None)]).model_copy(update={"prompt": None})
    state = _state([scene])

    with patch("pipeline.regenerate.generate_and_store") as store, pytest.raises(RuntimeError):
        regenerate(state)

    store.assert_not_called()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_regenerate_node.py -v`
Expected: FAIL at collection — `ModuleNotFoundError: No module named 'pipeline.regenerate'`.

- [ ] **Step 3: Write the node**

Create `backend/pipeline/regenerate.py`:

```python
"""ADR-010's one corrected retry (spec `docs/specs/regeneration-controller.md`).

The only place ADR-010 exists in code. When the judge fails a scene image, redraw it ONCE with a
prompt corrected from the failure reasons; `consistency_check` then keeps whichever attempt is
better. This node appends exactly one `Attempt` or raises — it never returns `{}`, because `{}`
leaves state unchanged, so `consistency_check` re-judges the same attempt, reaches the same
verdict, and `route_after_check` sends control straight back.

It imports `generate_and_store` rather than restating the effect boundary: the fal upload cache,
the Storage round-trip and the CC-10 exists-skip exist once, in `generate_scene`.
"""
import logging

from app.config import IMAGE_BUDGET
from contracts.story_memory import Attempt, StoryMemory
from pipeline.generate_scene import generate_and_store
from pipeline.prompt_optimizer import correct_prompt

log = logging.getLogger(__name__)


def regenerate(state: StoryMemory) -> dict:
    # ADR-024: the SAME selection rule generate_scene and consistency_check use — no cursor.
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is None or not scene.attempts:
        # Invariant 1: unreachable given route_after_check's guard, and therefore RAISES rather
        # than returning {} — a silent no-op here is an infinite check ⇄ regenerate loop.
        raise RuntimeError(
            "regenerate: no unfinalized scene with attempts — route_after_check should never "
            "have routed here (ADR-010, invariant 1)"
        )

    last = scene.attempts[-1]
    if last.prompt is None and scene.prompt is None:
        # Unreachable today: generate_scene always sets both. Drawing from correction clauses
        # with no base prompt is a guaranteed-garbage PAID image, so ADR-025 hard-fails instead.
        raise RuntimeError(f"regenerate: scene {scene.scene_id} has no prompt to correct (ADR-025)")

    # ADR-025 D4: breaker before any spend. A retry is not exempt.
    if state.cost.image_count >= IMAGE_BUDGET:
        raise RuntimeError(
            f"image budget exceeded: {state.cost.image_count} >= {IMAGE_BUDGET} (ADR-025)"
        )

    # Identical to generate_scene's loop — the retry is conditioned on the same references as the
    # original, or it would be measuring a different thing. This node may not extend the roster.
    by_id = {c.char_id: c for c in state.characters}
    ref_paths = []
    for char_id in scene.characters_present:
        c = by_id.get(char_id)
        if c is None:
            log.warning("regenerate: char_id %r in characters_present but absent from state.characters, skipped", char_id)
        elif c.canonical_ref_image:
            ref_paths.append(c.canonical_ref_image)

    # Invariant 5: every reachable path appends at least one clause. The two booleans cover the
    # holes the frozen 7 leave — anatomy is outside FailureReason entirely (ADR-028), and a
    # same_character failure can arrive with no reason named. A prompt identical to the previous
    # attempt's would be resampling, which ADR-010 rejects.
    v = last.vlm_verdict
    identity_clause = not (v.same_character if v else True) and not last.failure_reasons
    anatomy_clause = not (v.anatomy_intact if v else True)
    prompt = correct_prompt(
        last.prompt or scene.prompt,
        last.failure_reasons,
        state.characters,
        state.style.prompt_fragment,
        same_character=v.same_character if v else True,
        anatomy_intact=v.anatomy_intact if v else True,
    )

    attempt_n = len(scene.attempts) + 1
    path, paid = generate_and_store(
        prompt, state.story_id, scene.scene_id, attempt_n, ref_paths
    )

    # CC-5: one line per regeneration. Without the clause flags there is no way to tell a
    # correction that fired from one that silently appended nothing.
    log.info(
        "regenerate: scene_id=%s attempt_n=%d failure_reasons=%s same_character=%s "
        "anatomy_intact=%s identity_clause=%s anatomy_clause=%s paid=%s prompt_len=%d",
        scene.scene_id, attempt_n, [r.value for r in last.failure_reasons],
        v and v.same_character, v and v.anatomy_intact,
        identity_clause, anatomy_clause, paid, len(prompt),
    )

    return {
        "scenes": [
            scene.model_copy(
                update={
                    # Invariants 2, 3, 7: final_image_ref, scenes[].prompt and
                    # regeneration_count are all deliberately absent from this update.
                    "attempts": [*scene.attempts, Attempt(image_ref=path, prompt=prompt, passed=False)],
                }
            )
        ],
        # Invariant 6: image_count is gated on `paid`, regen_count is NOT. On an ADR-025 resume
        # the checkpoint predates this return, so both start from their pre-regenerate values:
        # +0 correctly records the Storage skip meant no re-pay, +1 correctly records the
        # regeneration whose increment the lost checkpoint never persisted.
        "cost": state.cost.model_copy(
            update={
                "image_count": state.cost.image_count + (1 if paid else 0),
                "regen_count": state.cost.regen_count + 1,
            }
        ),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_regenerate_node.py -v`
Expected: PASS — 26 tests.

- [ ] **Step 5: Run the full backend verify**

Run: `uv run ruff check . && uv run pytest`
Expected: green. Nothing calls `regenerate` yet — it is registered in Task 6.

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/regenerate.py backend/tests/test_regenerate_node.py
git commit -m "feat(pipeline): regenerate node — ADR-010's one corrected retry"
```

---

### Task 6: `route_after_check` and the graph wiring

`route_after_check` is pure and holds no policy (ADR-024 Decision 4) — it reads what the node wrote. The `scene.attempts` guard is load-bearing, not padding: it is what stops `consistency_check`'s "scene has no attempts → return `{}`" guard from becoming a `check ⇄ regenerate` ping-pong. A scene with no attempts belongs to `generate_scene`, and `route_next_scene` says so.

`route_next_scene` keeps its `char_bible` registration and is **called by** `route_after_check`, not replaced by it. ADR-003 is unamended — consistency pass/fail is one of the two branch points it sanctions, and this is that branch.

**The ADR-024 loop invariant survives.** Every entry into `generate_scene`…`consistency_check` still finalizes exactly one scene; it now takes at most two node visits instead of one, bounded by `len(attempts) >= 2`. The loop still terminates because each pass reduces the count of `final_image_ref is None` scenes by one.

> **The mock trap this task must not fall into.** `regenerate.py` does `from pipeline.generate_scene import generate_and_store`, which binds the function into `pipeline.regenerate`'s namespace at import time. Patching `pipeline.generate_scene.generate_and_store` alone leaves `regenerate` calling the **real** one — a live fal call and a live Supabase upload from a unit test. Both module paths must be patched.

**Files:**
- Modify: `backend/pipeline/graph.py` — add the import, `route_after_check`, the node, the re-pointed registration, the edge
- Test: `backend/tests/test_consistency_check_node.py` (router cases, appended beside `route_next_scene`'s), `backend/tests/test_graph_stub.py` (loop termination)

**Interfaces:**
- Consumes: `regenerate` from `pipeline.regenerate` (Task 5); `route_next_scene` (already in `graph.py:14`).
- Produces: `route_after_check(state: StoryMemory) -> str` returning one of `"regenerate"`, `"generate_scene"`, `"compose"` — all three are registered node names.

- [ ] **Step 1: Write the failing router tests**

Append to `backend/tests/test_consistency_check_node.py`, at the end of the file:

```python
# --- route_after_check (pure — no mocks) ---

def test_route_after_check_sends_a_checked_failing_scene_to_regenerate():
    state = _state([_scene_with_attempt(characters_present=["c0"])])
    assert route_after_check(state) == "regenerate"


def test_route_after_check_sends_a_scene_with_no_attempts_to_generate_scene():
    """The ping-pong guard. Without the `scene.attempts` term this returns "regenerate", which
    raises, or — if it returned {} instead — loops until recursion_limit. A scene with no
    attempts belongs to generate_scene, and route_next_scene says so."""
    state = _state([Scene(scene_id="s0", text_excerpt="0")])
    assert route_after_check(state) == "generate_scene"


def test_route_after_check_sends_a_fully_finalized_book_to_compose():
    state = _state([Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-1/s0-1.png")])
    assert route_after_check(state) == "compose"


def test_route_after_check_sends_an_empty_scene_list_to_compose():
    assert route_after_check(_state([])) == "compose"


def test_route_after_check_skips_finalized_scenes_when_selecting():
    """Same selection rule as every other node in the loop — the FIRST unfinalized scene."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-1/s0-1.png"),
        _scene_with_attempt("s1", "job-1/s1-1.png"),
    ])
    assert route_after_check(state) == "regenerate"
```

and change that file's graph import (line 22) to:

```python
from pipeline.graph import route_after_check, route_next_scene
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_consistency_check_node.py -v`
Expected: FAIL at collection — `ImportError: cannot import name 'route_after_check' from 'pipeline.graph'`.

- [ ] **Step 3: Wire the graph**

In `backend/pipeline/graph.py`, add the import after line 10:

```python
from pipeline.regenerate import regenerate
```

Replace the last paragraph of `route_next_scene`'s docstring (lines 22-24, the "`route_after_check` is deliberately NOT built" note) with:

```
    `route_after_check` below wraps it: this node no longer finalizes unconditionally, so the
    fail branch is real now. This router stays the loop head's registration and the fall-through
    of the tail's — it is called BY route_after_check, not replaced by it.
```

Add directly below `route_next_scene`:

```python
def route_after_check(state: StoryMemory) -> str:
    """Pure label-returning router (ADR-024 Decision 4) — ADR-003's consistency pass/fail branch.

    Holds no policy: it reads what `consistency_check` wrote. An unfinalized scene means the
    judge failed it and the retry budget is not spent, so ADR-010's one redraw is owed.

    The `scene.attempts` guard is load-bearing, not padding: it is what stops
    `consistency_check`'s "scene has no attempts → return {}" guard from becoming a
    check ⇄ regenerate ping-pong. A scene with no attempts belongs to `generate_scene`.
    """
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is not None and scene.attempts:
        return "regenerate"
    return route_next_scene(state)
```

In `build_graph`, add the node after line 36:

```python
    graph.add_node("regenerate", regenerate)
```

change line 45 from:

```python
    graph.add_conditional_edges("consistency_check", route_next_scene)
```

to:

```python
    graph.add_conditional_edges("consistency_check", route_after_check)
    graph.add_edge("regenerate", "consistency_check")
```

Leave line 43 (`add_conditional_edges("char_bible", route_next_scene)`) alone — the loop head is unchanged.

- [ ] **Step 4: Run the router tests to verify they pass**

Run: `uv run pytest tests/test_consistency_check_node.py -v`
Expected: PASS.

- [ ] **Step 5: Write the failing loop-termination tests**

In `backend/tests/test_graph_stub.py`, add to the imports at the top:

```python
from contracts.story_memory import CURRENT_SCHEMA_VERSION, FailureReason, Input, RefVerdict, StoryMemory
from pipeline.consistency_check import SceneVerdict
```

Inside `_mock_call_points`, add the second patch target directly below the existing `generate_and_store` one — **this is the mock trap above; without it the retry path makes a real fal call**:

```python
    # regenerate.py does `from ... import generate_and_store`, binding it into ITS namespace at
    # import time — patching only pipeline.generate_scene would leave the retry path live.
    monkeypatch.setattr(
        "pipeline.regenerate.generate_and_store",
        lambda prompt, story_id, scene_id, attempt_n, ref_paths: (f"stub/{scene_id}-{attempt_n}.png", True),
    )
```

Append these two tests to the end of the file:

```python
def _judge_returning(*, same: bool, anatomy: bool = True) -> SceneVerdict:
    return SceneVerdict(
        differences_observed="d",
        same_character=same,
        attributes_present=[],
        style_match=True,
        anatomy_intact=anatomy,
        failure_reasons=[FailureReason.different_face] if not same else [],
    )


def _two_scenes(monkeypatch):
    monkeypatch.setattr(
        "pipeline.segment.segment_scenes",
        lambda units, chars, timeline: SceneSegmentation(scenes=[
            ExtractedScene(start=0, end=0, characters_present=[]),
            ExtractedScene(start=1, end=len(units) - 1, characters_present=[]),
        ]),
    )


def test_a_failing_scene_retries_once_then_passes_and_the_run_reaches_compose(monkeypatch):
    """Spec §6: three attempts total, both scenes finalized, cost.regen_count == 1."""
    _mock_call_points(monkeypatch)
    _two_scenes(monkeypatch)

    # Keyed on the PATH, not a call counter: this test streams once and invokes once, so a
    # counter would carry across both runs and the second would never see a failure.
    monkeypatch.setattr(
        "pipeline.consistency_check.judge_attempt",
        lambda image_path, subjects: [_judge_returning(same=not image_path.endswith("s0-1.png"))],
    )
    app_graph = build_graph()

    ran = [
        next(iter(chunk))
        for chunk in app_graph.stream(
            _initial_state("test-job-retry"),
            config={"configurable": {"thread_id": "test-job-retry"}},
            stream_mode="updates",
        )
    ]
    result = app_graph.invoke(
        _initial_state("test-job-retry-2"),
        config={"configurable": {"thread_id": "test-job-retry-2"}},
    )

    assert ran == [
        "input_gate", "analyze", "segment", "char_bible",
        "generate_scene", "consistency_check", "regenerate", "consistency_check",
        "generate_scene", "consistency_check",
        "compose",
    ]
    assert sum(len(s.attempts) for s in result["scenes"]) == 3
    assert all(s.final_image_ref is not None for s in result["scenes"])
    assert result["scenes"][0].final_image_ref == "stub/s0-2.png"   # attempt 2 won on its own score
    assert result["cost"].regen_count == 1


def test_a_book_whose_every_judge_call_fails_still_reaches_compose(monkeypatch):
    """The ADR-010 best-of termination test: four attempts, both scenes finalized, never a
    broken page and never an infinite loop. `len(attempts) >= 2` is what bounds it."""
    _mock_call_points(monkeypatch)
    _two_scenes(monkeypatch)
    monkeypatch.setattr(
        "pipeline.consistency_check.judge_attempt",
        lambda image_path, subjects: [_judge_returning(same=False)],
    )
    app_graph = build_graph()

    result = app_graph.invoke(
        _initial_state("test-job-allfail"),
        config={"configurable": {"thread_id": "test-job-allfail"}},
    )

    assert sum(len(s.attempts) for s in result["scenes"]) == 4
    assert all(s.final_image_ref is not None for s in result["scenes"])
    assert all(a.passed is False for s in result["scenes"] for a in s.attempts)
    assert result["cost"].regen_count == 2
    # Tie on every ranking term → attempt 2, the `reversed` behaviour, end to end.
    assert [s.final_image_ref for s in result["scenes"]] == ["stub/s0-2.png", "stub/s1-2.png"]
```

- [ ] **Step 6: Run them to verify they pass**

Run: `uv run pytest tests/test_graph_stub.py -v`
Expected: PASS — 7 tests. The four pre-existing ones still pass because their stub judge returns `[]` (unchecked), which finalizes on the `verdict is None` term and never enters the retry branch.

- [ ] **Step 7: Run the full backend verify**

Run: `uv run ruff check . && uv run pytest`
Expected: all green, every file.

- [ ] **Step 8: Commit**

```bash
git add backend/pipeline/graph.py backend/tests/test_graph_stub.py backend/tests/test_consistency_check_node.py
git commit -m "feat(graph): route_after_check closes ADR-010's retry branch"
```

---

### Task 7: The finding-change sweep

The spec's DoD item 10 requires this and names the surface. **One doc updated is not done.** Run the greps, fix every hit, and do it in one commit so the docs and the code move together.

**Files:**
- Modify: `docs/specs/regeneration-controller.md` (status line)
- Modify: `docs/specs/consistency-checker.md`
- Modify: `docs/product/DECISION_BACKLOG.md`
- Modify: `docs/WORKFLOW.md`
- Modify: `AGENTS.md`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Run the grep and list every hit**

From the repo root:

```bash
grep -rn 'route_after_check\|regeneration-controller\|deliberately not built\|regenerate' docs/ AGENTS.md --include='*.md'
grep -rn 'compose.*only.*stub\|only remaining.*stub' docs/ AGENTS.md --include='*.md'
```

Write the hit list down before editing. Every one is either fixed or deliberately left with a reason.

- [ ] **Step 2: Fix `docs/specs/consistency-checker.md`**

Six places, per the spec's DoD:
- §2 invariants 1 and 2 — invariant 2 (`consistency_check` is the only writer of `final_image_ref`) is **unchanged and still true**; say so explicitly rather than leaving a reader to wonder. Invariant 1 gains: finalization is now conditional on `passed or verdict is None or len(attempts) >= 2`.
- §3 — "`route_after_check` deliberately not built" is now **built**; replace with a pointer to `regeneration-controller` §3.
- §4 edge table — the *"The attempt fails the gate"* row now defers to `regenerate`; *"Two attempts already exist"* now finalizes by best-of.
- The ⚠️ anatomy gap — **closed** by `ANATOMY_CLAUSE`. Point at `regeneration-controller` §4.
- §5 CC-3 — judge calls remain uncounted and a retried scene now costs up to 4 of them, not 2.
- §6 — the `final_image_ref == attempts[-1].image_ref` assertion is no longer universal; it is now `updated[best].image_ref`.
- §8 hand-offs and open items, and §9's *Not done* clause — the items handed to `regeneration-controller` are discharged.

- [ ] **Step 3: Fix `docs/product/DECISION_BACKLOG.md`**

Tick `regeneration-controller`. Then — this is the part that is easy to get wrong — **every row in the Phase-1 feature-spec list is now built, but `compose` is still a pass-through stub and has no row at all**; it was never added to that list. *"Recommended next session"* must say **`compose`**, not "Phase 1 finished".

- [ ] **Step 4: Fix `docs/WORKFLOW.md` §"Right now"**

Single next action → `compose`.

- [ ] **Step 5: Fix `AGENTS.md`**

Two sections:
- *Project Context* — the **"Built today"** graph line gains `regenerate` and `route_after_check`:
  `input_gate → analyze → segment → char_bible → [route_next_scene] → generate_scene → consistency_check → [route_after_check] → regenerate → … → compose`. The "`compose` is the only remaining pass-through stub" claim stays **true** — verify it before leaving it.
- *Validation Notes* — add the `regeneration-controller` built entry (dated 2026-08-02) naming: ADR-010's one corrected retry, best-of ranking, the per-attempt Storage path, `RECURSION_LIMIT`, and `correct_prompt`'s two booleans. Correct the `consistency-checker` entry's hand-off list — the anatomy gap and the ADR-010 branch are **discharged**; the CC-3 judge counter is **not**.

- [ ] **Step 6: Flip the spec's status line**

In `docs/specs/regeneration-controller.md` line 3, change `**Status:** draft` to `**Status:** built` with the commit range (MASTER_SPEC §7). Get the range with:

```bash
git log --oneline -8
```

- [ ] **Step 7: Verify the hand-offs were not silently absorbed**

The spec's *Not done* clause fails the work if any of these were quietly closed instead of handed on. Confirm all three are still recorded as **open** in `docs/specs/regeneration-controller.md` §8:
- A judge-call counter on `Cost` (CC-3) → unowned, a `contracts/` change.
- Surfacing a shipped-but-failing page to a teacher (CC-9) → `teacher-dashboard`, Phase 2.
- Seed control (CC-7, ADR-010's own clause) → blocked on Probe 2, which does not gate Phase 1.

- [ ] **Step 8: Final verify and commit**

Run: `uv run ruff check . && uv run pytest` from `backend/`. **Show the output; do not claim it.**

```bash
git add docs/ AGENTS.md
git commit -m "docs(spec): flip regeneration-controller to built, sweep the status surface"
```

---

## Definition of done (spec §9)

All ten hold:

1. `backend/pipeline/regenerate.py` implements §4: the guards that raise, the ADR-025 D4 breaker, the `correct_prompt` call with both new booleans, the `generate_and_store` call at `len(attempts) + 1`, and the partial return appending one `Attempt` plus both `cost` bumps.
2. `backend/pipeline/prompt_optimizer.py` has `same_character` / `anatomy_intact`, `IDENTITY_CLAUSE`, `ANATOMY_CLAUSE`. `FailureReason` **not** touched. *(Part 1 Task 3)*
3. `generate_and_store` takes `attempt_n` and writes `{story_id}/{scene_id}-{n}.png`; the node passes `len(scene.attempts) + 1`. *(Part 1 Task 2)*
4. `backend/pipeline/consistency_check.py` has `_rank`, the `finalize` rule, and reverse-ordered best-of selection. Its CC-5 line carries the winner.
5. `backend/pipeline/graph.py` has `route_after_check`, the `regenerate` node, the re-pointed `consistency_check` registration, and `add_edge("regenerate", "consistency_check")`.
6. `backend/app/config.py` defines `RECURSION_LIMIT`; `backend/worker/run_job.py` passes it to `invoke()`. *(Part 1 Task 1)*
7. Every §6 assertion exists and passes, in `backend/tests/test_regenerate_node.py` and the named existing files.
8. `uv run ruff check . && uv run pytest` from `backend/` is green and **its output is shown, not claimed**.
9. The spec's status line reads `built` with the commit range.
10. The finding-change grep ran and every hit is fixed in the same change.

**Not done if:** `backend/contracts/` is modified; `FailureReason` gains a value; `regenerate` returns `{}` on any path; `regenerate` writes `final_image_ref`, `scenes[].prompt`, or `scenes[].regeneration_count`; a scene can be regenerated twice; the Storage path is not per-attempt; `correct_prompt` can return its input unchanged on a path `regenerate` reaches; best-of promotes an unchecked attempt over a checked one; an unchecked attempt triggers a retry; `recursion_limit` is left unset; or the three hand-offs above are silently absorbed.

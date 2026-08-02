# compose Node Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `compose.py` pass-through stub with the terminal gate implementation described in `docs/specs/compose.md`.

**Architecture:** One pure function — no I/O, no provider calls, no helper. It asserts the book is non-empty and fully finalized, classifies each page by the attempt that won, then emits one per-book log line. It reads `StoryMemory` and returns `{}`.

**Tech Stack:** Python 3.11, Pydantic v2 (`StoryMemory` from `contracts/`), `logging`, `pytest` with `caplog`.

## Global Constraints

- No new dependency, no new helper, no new file beyond the two listed below (MASTER_SPEC §6 rule 1).
- `contracts/story_memory.py` is frozen — do not touch it (ADR-023, ADR-028).
- Tests run from the `backend/` directory: `cd backend && pytest tests/test_compose_node.py -v`.
- Tests must stay green: never assert on generated content; mock every provider boundary (there are none here, so no mocks needed at all).
- `compose` returns `{}` on every non-raising path (ADR-024 partial-return convention).
- Logger name is `pipeline.compose` — derived from `__name__` in `compose.py`.

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| **Modify** | `backend/pipeline/compose.py` | Replace 6-line stub with the full gate implementation from spec §4 |
| **Create** | `backend/tests/test_compose_node.py` | 5 deterministic tests from spec §6 — no mocks |

---

## Task 1: Write failing tests, implement the gate, verify everything passes

**Files:**
- Create: `backend/tests/test_compose_node.py`
- Modify: `backend/pipeline/compose.py`

**Interfaces:**
- Consumes: `compose(state: StoryMemory) -> dict` from `pipeline.compose`
- Produces: nothing (terminal node)

---

- [ ] **Step 1: Write the 5 failing tests**

Create `backend/tests/test_compose_node.py` with this exact content:

```python
"""Deterministic tests for `compose` (spec `docs/specs/compose.md` §6).

No mocks needed — the node has no effect boundary.
"""
import logging

import pytest

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Attempt,
    Cost,
    Input,
    Scene,
    StoryMemory,
    VlmVerdict,
)
from pipeline.compose import compose


# --- Fixture helpers ---

def _attempt(ref: str, *, passed: bool | None = None) -> Attempt:
    """Build an Attempt. `passed=None` → no verdict (unchecked); bool → verdict + passed flag."""
    if passed is None:
        return Attempt(image_ref=ref)
    verdict = VlmVerdict(differences_observed="none", same_character=passed)
    return Attempt(image_ref=ref, vlm_verdict=verdict, passed=passed)


def _scene(scene_id: str, final_ref: str | None, attempts: list[Attempt]) -> Scene:
    return Scene(scene_id=scene_id, text_excerpt="x", final_image_ref=final_ref, attempts=attempts)


def _mem(*scenes: Scene, image_count: int = 0, regen_count: int = 0) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="test",
        classroom_id="cls",
        profile_id="prof",
        input=Input(raw_text="once"),
        scenes=list(scenes),
        cost=Cost(image_count=image_count, regen_count=regen_count),
    )


# --- Tests ---

def test_zero_scenes_raises():
    """Spec §6 test 1: empty book → ValueError."""
    with pytest.raises(ValueError, match="no scenes"):
        compose(_mem())


def test_unfinalized_scene_raises_and_names_scene_id():
    """Spec §6 test 2: unfinished page → ValueError naming the offending scene_id."""
    scene = _scene("page-7", final_ref=None, attempts=[_attempt("path/p7-1.png", passed=True)])
    with pytest.raises(ValueError, match="page-7"):
        compose(_mem(scene))


def test_mixed_three_page_book_returns_empty_dict_and_logs(caplog):
    """Spec §6 test 3: one passed / one failing / one unchecked → {} + correct log line."""
    scenes = [
        _scene("s1", "p/s1-1.png", [_attempt("p/s1-1.png", passed=True)]),   # passed
        _scene("s2", "p/s2-1.png", [_attempt("p/s2-1.png", passed=False)]),  # failing
        _scene("s3", "p/s3-1.png", [_attempt("p/s3-1.png")]),                # unchecked (no verdict)
    ]
    state = _mem(*scenes, image_count=5, regen_count=2)

    with caplog.at_level(logging.INFO, logger="pipeline.compose"):
        result = compose(state)

    assert result == {}
    assert "pages=3" in caplog.text
    assert "passed=1" in caplog.text
    assert "failing=1" in caplog.text
    assert "unchecked=1" in caplog.text


def test_best_of_attempt_2_classified_by_attempt_2(caplog):
    """Spec §6 test 4: final_image_ref points at attempt 2 (which failed) → failing=1, passed=0.

    This is the assertion that breaks if _outcome ever regresses to attempts[-1] or attempts[0]
    instead of matching image_ref.
    """
    scene = _scene(
        "s1",
        final_ref="p/s1-2.png",
        attempts=[
            _attempt("p/s1-1.png", passed=True),   # passed but NOT the winner
            _attempt("p/s1-2.png", passed=False),  # failing, IS the winner
        ],
    )

    with caplog.at_level(logging.INFO, logger="pipeline.compose"):
        result = compose(_mem(scene))

    assert result == {}
    assert "failing=1" in caplog.text
    assert "passed=0" in caplog.text


def test_cost_reported_from_state(caplog):
    """Spec §6 test 5: image_count and regen_count come from state, not recomputed."""
    scene = _scene("s1", "p/s1-1.png", [_attempt("p/s1-1.png", passed=True)])

    with caplog.at_level(logging.INFO, logger="pipeline.compose"):
        compose(_mem(scene, image_count=7, regen_count=3))

    assert "image_count=7" in caplog.text
    assert "regen_count=3" in caplog.text
```

- [ ] **Step 2: Run the tests and confirm they all fail**

```bash
cd backend && pytest tests/test_compose_node.py -v
```

Expected: all 5 tests **FAIL**. Tests 1 and 2 fail because `compose` returns `{}` instead of raising. Tests 3–5 fail because `compose` produces no log output.

If any test passes unexpectedly, stop and investigate before continuing.

- [ ] **Step 3: Replace the stub in `compose.py` with the gate implementation**

Replace the entire content of `backend/pipeline/compose.py` with:

```python
"""The graph's terminal gate (spec `docs/specs/compose.md`).

No provider call, no I/O, no helper (MASTER_SPEC §6 rule 1) — the book IS `scenes[]` in
segmentation order, so there is nothing to assemble. What is left is the invariant no other
node is positioned to check, and the one per-book record the run emits.
"""
import logging

from contracts.story_memory import Scene, StoryMemory

log = logging.getLogger(__name__)


def _outcome(scene: Scene) -> str:
    """How the page that shipped got there: passed / failing / unchecked.

    Matched by `image_ref`, not by position: ADR-010's best-of may ship attempt 1 or attempt 2,
    and the Storage paths are per-attempt (`{story_id}/{scene_id}-{n}.png`), so the match is
    unique. A `final_image_ref` with no matching attempt cannot happen — `consistency_check`
    derives it from one — and counts as `unchecked`, because it carries no verdict either way.
    """
    winner = next((a for a in scene.attempts if a.image_ref == scene.final_image_ref), None)
    if winner is None or winner.vlm_verdict is None:
        return "unchecked"
    return "passed" if winner.passed else "failing"


def compose(state: StoryMemory) -> dict:
    if not state.scenes:
        raise ValueError("compose: no scenes — there is no book to compose")

    unfinalized = [s.scene_id for s in state.scenes if s.final_image_ref is None]
    if unfinalized:
        # Unreachable while `route_next_scene` is correct, and that is the point: a routing
        # regression fails the job HERE rather than shipping a book with a blank page.
        raise ValueError(f"compose: scenes not finalized: {unfinalized}")

    outcomes = [_outcome(s) for s in state.scenes]
    # CC-5: the only per-book terminal record the run produces.
    log.info(
        "compose: pages=%d passed=%d failing=%d unchecked=%d image_count=%d regen_count=%d",
        len(outcomes), outcomes.count("passed"), outcomes.count("failing"),
        outcomes.count("unchecked"), state.cost.image_count, state.cost.regen_count,
    )
    return {}
```

- [ ] **Step 4: Run the compose tests and confirm they all pass**

```bash
cd backend && pytest tests/test_compose_node.py -v
```

Expected: all 5 tests **PASS**.

- [ ] **Step 5: Run the full test suite including graph_stub**

```bash
cd backend && pytest tests/ -v
```

Expected: **all tests pass**. The graph_stub tests are the key check — they now run against a `compose` that can raise, and the spec calls this "coverage gained for free." If any graph_stub test fails, the scenes coming out of that path are not fully finalized; stop and debug before committing.

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/compose.py backend/tests/test_compose_node.py
git commit -m "feat(compose): implement terminal gate — assert non-empty fully-finalized book, log per-book summary"
```

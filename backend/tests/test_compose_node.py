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


def _scene(scene_id: str, final_ref: str | None, attempts: list[Attempt], caption: str | None = None) -> Scene:
    return Scene(scene_id=scene_id, text_excerpt="x", final_image_ref=final_ref, attempts=attempts, caption=caption)


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
        _scene("s1", "p/s1-1.png", [_attempt("p/s1-1.png", passed=True)], caption="c1"),   # passed
        _scene("s2", "p/s2-1.png", [_attempt("p/s2-1.png", passed=False)], caption="c2"),  # failing
        _scene("s3", "p/s3-1.png", [_attempt("p/s3-1.png")], caption="c3"),                # unchecked (no verdict)
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
        caption="c1",
    )

    with caplog.at_level(logging.INFO, logger="pipeline.compose"):
        result = compose(_mem(scene))

    assert result == {}
    assert "failing=1" in caplog.text
    assert "passed=0" in caplog.text


def test_uncaptioned_scene_raises_and_names_scene_id():
    """kid-flow-book-persistence spec §4.2: a page is an image plus a verbatim caption
    (ADR-013). A finalized scene with no caption must fail the job, not ship a blank page."""
    scene = _scene("page-3", final_ref="p/page-3-1.png", attempts=[_attempt("p/page-3-1.png", passed=True)])
    with pytest.raises(ValueError, match="page-3"):
        compose(_mem(scene))


def test_cost_reported_from_state(caplog):
    """Spec §6 test 5: image_count and regen_count come from state, not recomputed."""
    scene = _scene("s1", "p/s1-1.png", [_attempt("p/s1-1.png", passed=True)], caption="c1")

    with caplog.at_level(logging.INFO, logger="pipeline.compose"):
        compose(_mem(scene, image_count=7, regen_count=3))

    assert "image_count=7" in caplog.text
    assert "regen_count=3" in caplog.text

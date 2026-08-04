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

    uncaptioned = [s.scene_id for s in state.scenes if not s.caption]
    if uncaptioned:
        raise ValueError(f"compose: scenes without a caption: {uncaptioned}")

    outcomes = [_outcome(s) for s in state.scenes]
    # CC-5: the only per-book terminal record the run produces.
    log.info(
        "compose: pages=%d passed=%d failing=%d unchecked=%d image_count=%d regen_count=%d",
        len(outcomes), outcomes.count("passed"), outcomes.count("failing"),
        outcomes.count("unchecked"), state.cost.image_count, state.cost.regen_count,
    )
    return {}

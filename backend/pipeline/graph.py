from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from contracts.story_memory import StoryMemory
from pipeline.char_ref_mod import char_ref_mod
from pipeline.input_gate import input_gate
from pipeline.analyze import analyze
from pipeline.segment import segment
from pipeline.char_bible import char_bible
from pipeline.generate_scene import generate_scene
from pipeline.consistency_check import consistency_check
from pipeline.compose import compose
from pipeline.output_mod import output_mod
from pipeline.regenerate import regenerate
from pipeline.reveal import MAX_RETRY_TAPS, reveal


def moderation_router(state: StoryMemory) -> str:
    """Pure ADR-024 router: reads moderation state written by input_gate and char_ref_mod (spec §3).

    Called after input_gate (routes to analyze or raises) and after char_ref_mod (routes to the
    scene loop or raises). One function covers both: after input_gate state.scenes is empty;
    after char_ref_mod scenes exist.
    """
    mod = state.input.moderation
    if mod is not None and not mod.passed:
        if "moderation_error" in mod.categories:
            raise RuntimeError("moderation_error")
        raise RuntimeError("content_flagged")
    if any(c.ref_moderation_status == "flagged" for c in state.characters):
        raise RuntimeError("ref_flagged")
    if state.scenes:
        return "reveal"
    return "analyze"


def route_after_output_mod(state: StoryMemory) -> str:
    """Pure ADR-024 router: reads moderation_status written by output_mod (spec §3)."""
    if any(s.moderation_status == "failed" for s in state.scenes):
        raise RuntimeError("output_moderation_failed")
    return "compose"


def route_next_scene(state: StoryMemory) -> str:
    """Pure label-returning router (ADR-024 Decision 4) — the graph's scene-loop router.

    Used by route_after_check. Destination changed from "compose" to "output_mod" — compose is
    now reached only after output moderation passes.
    """
    return "generate_scene" if any(s.final_image_ref is None for s in state.scenes) else "output_mod"


def route_reveal(state: StoryMemory) -> str:
    """Pure ADR-024 router, holds no policy beyond the cap (spec §3). The cap is enforced HERE,
    not only in the UI: a resume payload arrives from a client and is a trust boundary.
    """
    if state.reference_retry is not None and state.cost.ref_retry_count < MAX_RETRY_TAPS:
        return "try_again"
    return route_next_scene(state)


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


def build_graph(checkpointer=None):
    graph = StateGraph(StoryMemory)
    graph.add_node("input_gate", input_gate)
    graph.add_node("analyze", analyze)
    graph.add_node("segment", segment)
    graph.add_node("char_bible", char_bible)
    graph.add_node("char_ref_mod", char_ref_mod)
    graph.add_node("reveal", reveal)
    graph.add_node("generate_scene", generate_scene)
    graph.add_node("consistency_check", consistency_check)
    graph.add_node("regenerate", regenerate)
    graph.add_node("output_mod", output_mod)
    graph.add_node("compose", compose)

    graph.set_entry_point("input_gate")
    graph.add_conditional_edges("input_gate", moderation_router)    # raises on fail; routes to analyze
    graph.add_edge("analyze", "segment")
    graph.add_edge("segment", "char_bible")
    graph.add_edge("char_bible", "char_ref_mod")                    # char_ref_mod writes status, never raises on flag
    graph.add_conditional_edges("char_ref_mod", moderation_router)  # raises on flag; routes to "reveal"
    graph.add_conditional_edges(
        "reveal", route_reveal, {"try_again": "char_bible", "generate_scene": "generate_scene", "output_mod": "output_mod"}
    )
    graph.add_edge("generate_scene", "consistency_check")
    graph.add_conditional_edges("consistency_check", route_after_check)
    graph.add_edge("regenerate", "consistency_check")
    graph.add_conditional_edges("output_mod", route_after_output_mod)  # raises on failed; routes to compose
    graph.add_edge("compose", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())

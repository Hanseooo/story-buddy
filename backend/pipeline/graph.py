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


def route_next_scene(state: StoryMemory) -> str:
    """Pure label-returning router (ADR-024 Decision 4) — the graph's first conditional edge.

    Registered on BOTH `char_ref_mod` (loop head) and `consistency_check` (loop back via
    route_after_check). Same selection rule: a scene with no `final_image_ref` is unfinished.
    Destination changed from "compose" to "output_mod" — compose is now reached only after
    output moderation passes.
    """
    return "generate_scene" if any(s.final_image_ref is None for s in state.scenes) else "output_mod"


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
    graph.add_node("generate_scene", generate_scene)
    graph.add_node("consistency_check", consistency_check)
    graph.add_node("regenerate", regenerate)
    graph.add_node("output_mod", output_mod)
    graph.add_node("compose", compose)

    graph.set_entry_point("input_gate")
    graph.add_edge("input_gate", "analyze")       # input_gate raises on fail; no conditional edge needed
    graph.add_edge("analyze", "segment")
    graph.add_edge("segment", "char_bible")
    graph.add_edge("char_bible", "char_ref_mod")  # char_ref_mod raises on fail
    graph.add_conditional_edges("char_ref_mod", route_next_scene)   # loop head (was char_bible)
    graph.add_edge("generate_scene", "consistency_check")
    graph.add_conditional_edges("consistency_check", route_after_check)
    graph.add_edge("regenerate", "consistency_check")
    graph.add_edge("output_mod", "compose")       # output_mod raises on fail
    graph.add_edge("compose", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())

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


def route_next_scene(state: StoryMemory) -> str:
    """Pure label-returning router (ADR-024 Decision 4) — the graph's first conditional edge.

    Registered on BOTH `char_bible` (loop head) and `consistency_check` (loop back). Same
    selection rule as the two nodes it brackets: a scene with no `final_image_ref` is unfinished.
    At the head it also covers ADR-024's empty-`scenes[]` case — segment produced none, so there
    is no loop to enter.

    `route_after_check` is deliberately NOT built: this node always finalizes, so that router
    would have exactly one outcome today. `regeneration-controller` introduces the branch and
    re-points the `consistency_check` registration below in the same change (spec §3).
    """
    return "generate_scene" if any(s.final_image_ref is None for s in state.scenes) else "compose"


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
    graph.add_conditional_edges("char_bible", route_next_scene)
    graph.add_edge("generate_scene", "consistency_check")
    graph.add_conditional_edges("consistency_check", route_next_scene)
    graph.add_edge("compose", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())

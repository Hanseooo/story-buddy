from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from contracts.job_state import JobState
from pipeline.analyze import analyze
from pipeline.segment import segment
from pipeline.char_bible import char_bible
from pipeline.generate_scene import generate_scene
from pipeline.consistency_check import consistency_check
from pipeline.compose import compose


def build_graph(checkpointer=None):
    graph = StateGraph(JobState)
    graph.add_node("analyze", analyze)
    graph.add_node("segment", segment)
    graph.add_node("char_bible", char_bible)
    graph.add_node("generate_scene", generate_scene)
    graph.add_node("consistency_check", consistency_check)
    graph.add_node("compose", compose)

    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "segment")
    graph.add_edge("segment", "char_bible")
    graph.add_edge("char_bible", "generate_scene")
    graph.add_edge("generate_scene", "consistency_check")
    graph.add_edge("consistency_check", "compose")
    graph.add_edge("compose", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())

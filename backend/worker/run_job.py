from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command

from app.config import RECURSION_LIMIT, STYLE_PRESETS, settings
from app.db import get_supabase_client
from app.length import word_count
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, Style, StoryMemory
from pipeline.graph import build_graph


_SCENE_NODES = {"generate_scene", "consistency_check", "regenerate", "output_mod"}


def _stage_string(node: str, latest: dict | None) -> str:
    scenes = (latest or {}).get("scenes") or []
    if node in _SCENE_NODES and scenes:
        done = sum(1 for s in scenes if s.final_image_ref is not None)
        return f"{node}:{min(done + 1, len(scenes))}/{len(scenes)}"
    return node


def _run_with_progress(supabase, job_id: str, app_graph, graph_input, config: dict) -> dict:
    """Drive app_graph.stream() in place of invoke(), writing current_stage on each new node.

    Returns a dict structurally identical to app_graph.invoke() — _finish is unchanged.
    """
    latest, interrupts, last_stage = None, [], None
    for chunk in app_graph.stream(graph_input, config, stream_mode=["updates", "values"]):
        # 2-tuple (mode, payload) for top-level; 3-tuple (ns, mode, payload) for subgraph nodes
        if len(chunk) == 3:
            _, mode, payload = chunk
        else:
            mode, payload = chunk

        if mode == "values":
            latest = payload
        else:  # "updates"
            if "__interrupt__" in payload:
                interrupts.extend(payload["__interrupt__"])
            node_name = next((k for k in payload if k != "__interrupt__"), None)
            if node_name:
                stage = _stage_string(node_name, latest)
                if stage != last_stage:
                    supabase.table("jobs").update(
                        {"current_stage": stage}
                    ).eq("id", job_id).execute()
                    last_stage = stage

    if interrupts:
        return {**(latest or {}), "__interrupt__": interrupts}
    return latest or {}


def _finish(supabase, job_id: str, result: dict) -> None:
    """The only writer of either `pages` or `reveal` (spec §4.8, invariant 1). Both worker
    entrypoints converge here so the terminal write happens exactly once per book, however many
    pauses intervened.
    """
    if "__interrupt__" in result:
        interrupts = result["__interrupt__"]
        value = interrupts[0].value if interrupts else None
        if not value:
            # A hard failure is the honest outcome (ADR-025 posture) — writing an empty `reveal`
            # would produce a row claiming to await a human in front of a screen with nothing on
            # it (spec §4.8).
            raise RuntimeError("reveal interrupt produced no usable payload")
        supabase.table("jobs").update(
            {"status": "awaiting_confirm", "current_stage": "reveal", "reveal": value}
        ).eq("id", job_id).execute()
        return

    # invoke() returns a dict; the values inside are model instances.
    # scenes[] insertion order IS page order (story_memory.py:129-131) — no page_index field.
    pages = [
        {"scene_id": s.scene_id, "caption": s.caption, "image_path": s.final_image_ref}
        for s in result["scenes"]
    ]
    supabase.table("jobs").update(
        {"status": "complete", "current_stage": "compose", "pages": pages}
    ).eq("id", job_id).execute()


def run_storybook_job(job_id: str) -> None:
    supabase = get_supabase_client()
    row = supabase.table("jobs").select("input_text, style_preset_id, truncated, profile_id, classroom_id").eq("id", job_id).single().execute()
    input_text = row.data["input_text"]
    preset_id = row.data.get("style_preset_id")
    truncated = row.data["truncated"]
    chosen_id = preset_id if preset_id is not None else "cel"

    supabase.table("jobs").update({"status": "running"}).eq("id", job_id).execute()

    initial_state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id=job_id,
        classroom_id=row.data["classroom_id"],
        profile_id=row.data["profile_id"],
        input=Input(raw_text=input_text, word_count=word_count(input_text), truncated=truncated),
        style=Style(style_preset_id=chosen_id, prompt_fragment=STYLE_PRESETS[chosen_id]),
    )

    try:
        with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
            checkpointer.setup()
            app_graph = build_graph(checkpointer=checkpointer)
            _config = {
                "configurable": {"thread_id": job_id},
                "recursion_limit": RECURSION_LIMIT,
            }
            result = _run_with_progress(supabase, job_id, app_graph, initial_state, _config)
        _finish(supabase, job_id, result)
    except Exception as exc:
        msg = str(exc)
        failure_reason = "child_text" if msg == "content_flagged" else "machine"
        supabase.table("jobs").update(
            {"status": "failed", "error": msg, "failure_reason": failure_reason}
        ).eq("id", job_id).execute()
        raise


def resume_storybook_job(job_id: str, payload: dict) -> None:
    """A second entrypoint that never constructs a `StoryMemory` — it structurally cannot rebuild
    and clobber a live checkpoint thread, the failure mode a single resume-aware
    `run_storybook_job(job_id, resume=None)` would leave one `if` away (spec §4.10).
    """
    supabase = get_supabase_client()
    supabase.table("jobs").update({"status": "running"}).eq("id", job_id).execute()

    try:
        with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
            checkpointer.setup()
            app_graph = build_graph(checkpointer=checkpointer)
            _config = {
                "configurable": {"thread_id": job_id},
                "recursion_limit": RECURSION_LIMIT,
            }
            result = _run_with_progress(
                supabase, job_id, app_graph, Command(resume=payload), _config
            )
        _finish(supabase, job_id, result)
    except Exception as exc:
        msg = str(exc)
        failure_reason = "child_text" if msg == "content_flagged" else "machine"
        supabase.table("jobs").update(
            {"status": "failed", "error": msg, "failure_reason": failure_reason}
        ).eq("id", job_id).execute()
        raise

from langgraph.checkpoint.postgres import PostgresSaver

from app.config import RECURSION_LIMIT, STYLE_PRESETS, settings
from app.db import get_supabase_client
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, Style, StoryMemory
from pipeline.graph import build_graph


def run_storybook_job(job_id: str) -> None:
    supabase = get_supabase_client()
    row = supabase.table("jobs").select("input_text, style_preset_id").eq("id", job_id).single().execute()
    input_text = row.data["input_text"]
    preset_id = row.data.get("style_preset_id")
    chosen_id = preset_id if preset_id is not None else "cel"

    supabase.table("jobs").update({"status": "running"}).eq("id", job_id).execute()

    # ADR-023 amendment 2026-07-22b: the worker is the supplier of durable provenance.
    # story_id = job_id (one job = one story). classroom/profile are Phase-1 dev sentinels;
    # `auth-and-classroom` swaps these two values here and changes nothing else.
    initial_state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id=job_id,
        classroom_id=settings.dev_classroom_id,
        profile_id=settings.dev_profile_id,
        input=Input(raw_text=input_text),
        style=Style(style_preset_id=chosen_id, prompt_fragment=STYLE_PRESETS[chosen_id]),
    )

    try:
        with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
            checkpointer.setup()
            app_graph = build_graph(checkpointer=checkpointer)
            result = app_graph.invoke(
                initial_state,
                config={
                    "configurable": {"thread_id": job_id},
                    "recursion_limit": RECURSION_LIMIT,
                },
            )
    except Exception as exc:
        supabase.table("jobs").update(
            {"status": "failed", "error": str(exc)}
        ).eq("id", job_id).execute()
        raise

    # invoke() returns a dict; the values inside are model instances.
    # Captions live at scenes[].caption, images at scenes[].final_image_ref — the old
    # top-level `caption` / `image_path` keys do not exist in StoryMemory.
    scenes = result["scenes"]
    first = scenes[0] if scenes else None

    supabase.table("jobs").update(
        {
            "status": "complete",
            "current_stage": "compose",
            "caption": first.caption if first else None,
            "image_path": first.final_image_ref if first else None,
        }
    ).eq("id", job_id).execute()

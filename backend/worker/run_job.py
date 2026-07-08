from langgraph.checkpoint.postgres import PostgresSaver

from app.config import settings
from app.db import get_supabase_client
from pipeline.graph import build_graph


def run_storybook_job(job_id: str) -> None:
    supabase = get_supabase_client()
    row = supabase.table("jobs").select("input_text").eq("id", job_id).single().execute()
    input_text = row.data["input_text"]

    supabase.table("jobs").update({"status": "running"}).eq("id", job_id).execute()

    initial_state = {
        "job_id": job_id,
        "input_text": input_text,
        "caption": None,
        "image_path": None,
        "stage": "queued",
    }

    try:
        with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
            checkpointer.setup()
            app_graph = build_graph(checkpointer=checkpointer)
            result = app_graph.invoke(
                initial_state, config={"configurable": {"thread_id": job_id}}
            )
    except Exception as exc:
        supabase.table("jobs").update(
            {"status": "failed", "error": str(exc)}
        ).eq("id", job_id).execute()
        raise

    supabase.table("jobs").update(
        {
            "status": "complete",
            "current_stage": "compose",
            "caption": result["caption"],
            "image_path": result["image_path"],
        }
    ).eq("id", job_id).execute()

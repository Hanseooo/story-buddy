from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command

from app.config import RECURSION_LIMIT, STYLE_PRESETS, settings
from app.db import get_supabase_client
from app.length import word_count
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Cost, Input, Style, StoryMemory
from pipeline.compose import outcome
from pipeline.graph import build_graph


_SCENE_NODES = {"generate_scene", "consistency_check", "regenerate", "output_mod"}


def _langfuse_handler(job_id: str) -> tuple[CallbackHandler, str]:
    host = settings.langfuse_host.rstrip("/")
    trace_id = job_id.replace("-", "")
    url = f"{host}/project/{settings.langfuse_project_id}/traces/{trace_id}"
    # CallbackHandler only *looks up* a client in LangfuseResourceManager._instances
    # (langfuse/_client/get_client.py:138-149) — it never constructs one. Without this line the
    # registry is empty, so every run logged "No Langfuse client with public key ... has been
    # initialized. Skipping tracing" and langfuse_trace_url pointed at a trace that never existed.
    # Langfuse is a singleton per public key, so re-calling it per job is free. Missing keys warn
    # and return a disabled client rather than raising (client.py:381-397), so tracing stays
    # strictly best-effort — a story never fails because observability is misconfigured.
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=host,
    )
    handler = CallbackHandler(
        public_key=settings.langfuse_public_key,
        trace_context={"trace_id": trace_id},
    )
    return handler, url


def _publish_trace(job_id: str) -> None:
    """Make the job's trace readable without a Langfuse login.

    /research/metrics is an unauthenticated page, so its "View trace" link has to open for a
    logged-out visitor. The LangChain CallbackHandler has no `langfuse_public` metadata key, so we
    attach a throwaway span carrying the flag (span.py:276-294; publishing any span publishes the
    whole trace).

    Must run *after* the graph, never before: Langfuse rebuilds the trace row from whichever root
    span ingested last, so a publish that lands ahead of the pipeline's own root span is silently
    reset to public=False. Verified against the live project — publish-first gave public=False,
    publish-last gave public=True.

    One-way door: a published trace cannot be unpublished via the SDK, and anyone with the URL sees
    every prompt and model output in it.
    ponytail: publish-everything; snapshot chosen metrics onto the job row instead if a trace ever
    carries something we would not hand a stranger.
    """
    try:
        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=settings.langfuse_host.rstrip("/"),
        )
        client.flush()  # land the pipeline's spans first so ours is the last root span
        client.start_observation(
            trace_context={"trace_id": job_id.replace("-", "")}, name="public-link"
        ).set_trace_as_public().end()
        client.flush()
    except Exception:
        # Tracing is strictly best-effort — a finished story never fails on observability.
        pass


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
    has_interrupt = False
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
                has_interrupt = True
                interrupts.extend(payload["__interrupt__"])
            node_name = next((k for k in payload if k != "__interrupt__"), None)
            if node_name:
                stage = _stage_string(node_name, latest)
                if stage != last_stage:
                    supabase.table("jobs").update(
                        {"current_stage": stage}
                    ).eq("id", job_id).execute()
                    last_stage = stage

    if has_interrupt:
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
    cost = result.get("cost") or Cost()
    scenes = result.get("scenes") or []
    outcomes = [outcome(s) for s in scenes]

    pages = [
        {"scene_id": s.scene_id, "caption": s.caption, "image_path": s.final_image_ref}
        for s in scenes
    ]
    supabase.table("jobs").update(
        {
            "status": "complete",
            "current_stage": "compose",
            "pages": pages,
            "image_count": cost.image_count,
            "regen_count": cost.regen_count,
            "ref_retry_count": cost.ref_retry_count,
            "scenes_total": len(scenes),
            "scenes_passed": outcomes.count("passed"),
            "scenes_failed": outcomes.count("failing"),
            "scenes_unchecked": outcomes.count("unchecked"),
            "usd_estimate": round(cost.image_count * 0.025, 4),
        }
    ).eq("id", job_id).execute()


def run_storybook_job(job_id: str) -> None:
    supabase = get_supabase_client()
    row = supabase.table("jobs").select("input_text, style_preset_id, truncated, classroom_id, profile_id").eq("id", job_id).single().execute()
    input_text = row.data["input_text"]
    preset_id = row.data.get("style_preset_id")
    truncated = row.data["truncated"]
    chosen_id = preset_id if preset_id is not None else "cel"

    supabase.table("jobs").update({"status": "running"}).eq("id", job_id).execute()

    handler, trace_url = _langfuse_handler(job_id)
    supabase.table("jobs").update({"langfuse_trace_url": trace_url}).eq("id", job_id).execute()

    # ADR-023 amendment 2026-07-22b: story_id = job_id (one job = one story).
    # classroom_id/profile_id come from the job row (0008 adds these columns as NOT NULL).
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
                "callbacks": [handler],
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
    finally:
        _publish_trace(job_id)


def resume_storybook_job(job_id: str, payload: dict) -> None:
    """A second entrypoint that never constructs a `StoryMemory` — it structurally cannot rebuild
    and clobber a live checkpoint thread, the failure mode a single resume-aware
    `run_storybook_job(job_id, resume=None)` would leave one `if` away (spec §4.10).
    """
    supabase = get_supabase_client()
    supabase.table("jobs").update({"status": "running"}).eq("id", job_id).execute()

    handler, trace_url = _langfuse_handler(job_id)
    supabase.table("jobs").update({"langfuse_trace_url": trace_url}).eq("id", job_id).execute()

    try:
        with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
            checkpointer.setup()
            app_graph = build_graph(checkpointer=checkpointer)
            _config = {
                "configurable": {"thread_id": job_id},
                "recursion_limit": RECURSION_LIMIT,
                "callbacks": [handler],
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
    finally:
        _publish_trace(job_id)


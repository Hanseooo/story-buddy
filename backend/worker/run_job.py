from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from datetime import datetime, timezone

from app.config import RECURSION_LIMIT, TEACHER_REVIEW_RECURSION_LIMIT, STYLE_PRESETS, settings
from app.db import get_supabase_client
from app.length import word_count
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Cost, Input, Style, StoryMemory
from pipeline.compose import outcome
from pipeline.graph import build_graph
from worker.failure_classifier import classify_failure_reason


_SCENE_NODES = {"generate_scene", "consistency_check", "regenerate", "output_mod"}


def run_review_storybook_job(job_id: str, payload: dict | None = None, expected_epoch: int | None = None,
                             review_id: str | None = None) -> None:
    """Serialized, fenced teacher-review work. Captured mode survives switch-off.

    Repair uses only a retained moderation checkpoint. It cannot restart classifiers
    or generation. The final marker is written after closing the checkpointer.
    """
    import providers
    from app.moderation_hold import (
        StaleGeneration, active_author, assert_current, connect, project_hold,
        review_subject_bytes, teacher_classroom, validate_review_checkpoint,
    )
    from contracts.story_memory import ModerationContext, ReviewContext

    with connect() as conn:
        # Session lock covers graph effects, projection and the final finish marker.
        # Control deliveries wait for any fenced provider call to finish before anchoring.
        if review_id is not None:
            conn.execute("select pg_advisory_lock(hashtextextended(%s,0))", (job_id,))
            locked = True
        else:
            locked = conn.execute("select pg_try_advisory_lock(hashtextextended(%s,0)) as locked", (job_id,)).fetchone()["locked"]
        if not locked:
            return
        epoch, started, hold_pending = None, False, False
        incurred = [0]
        initial_count = 0
        tokens = []
        try:
            with conn.transaction():
                job = conn.execute("select * from jobs where id=%s for update", (job_id,)).fetchone()
                if not job or job["moderation_mode"] != "teacher_review_v1":
                    return
                if expected_epoch is not None and expected_epoch != job["generation_epoch"]:
                    return
                withdrawal = conn.execute("""select * from job_moderation_reviews where job_id=%s
                  and decision is null and withdraws_review_id is not null""", (job_id,)).fetchone()
                if withdrawal and withdrawal["checkpoint_id"] is None and str(withdrawal["id"]) != review_id:
                    return
                if withdrawal and str(withdrawal["id"]) == review_id and withdrawal["checkpoint_id"] is not None:
                    epoch, started = job["generation_epoch"], True
                    if validate_review_checkpoint(conn, job_id, withdrawal) is None:
                        raise RuntimeError("checkpoint_unavailable")
                    conn.execute("update job_moderation_reviews set dispatch_state='consumed',dispatch_error_code=null where id=%s",
                                 (withdrawal["id"],))
                    return
                if withdrawal and str(withdrawal["id"]) == review_id and withdrawal["checkpoint_id"] is None:
                    epoch, started = job["generation_epoch"], True
                    with PostgresSaver.from_conn_string(settings.supabase_db_url) as saver:
                        graph = build_graph(checkpointer=saver)
                        config = {"configurable": {"thread_id": job_id}, "callbacks": []}
                        snapshot = graph.get_state(config)
                        retained = StoryMemory.model_validate(snapshot.values)
                        existing_review = retained.moderation_context.review
                        repairing = (existing_review is not None and existing_review.resolution is None
                                     and str(existing_review.review_id) == str(withdrawal["id"]))
                        if existing_review and existing_review.resolution is None and not repairing:
                            # A later allow can commit just before this withdrawal fences
                            # its queued worker. Apply only that pure decision node; never
                            # run its paid continuation while anchoring the new hold.
                            prior = conn.execute("""select * from job_moderation_reviews where id=%s and job_id=%s
                              and decision='allow' and decision_epoch<%s""", (existing_review.review_id, job_id, epoch)).fetchone()
                            if (snapshot.next != ("moderation_review",) or not prior
                                    or validate_review_checkpoint(conn, job_id, prior) is None
                                    or (job["image_count"] or 0) > retained.cost.image_count):
                                raise RuntimeError("checkpoint_not_resumable")
                            if not active_author(conn, job):
                                raise RuntimeError("account_unavailable")
                            teacher_classroom(conn, str(job["classroom_id"]), str(prior["actor_id"]))
                            import hashlib
                            if hashlib.sha256(review_subject_bytes(prior)).hexdigest() != prior["subject_version"]:
                                raise RuntimeError("moderation_subject_unavailable")
                            graph.invoke(Command(resume={"action": "allow", "review_id": str(prior["id"]),
                                "subject_version": prior["subject_version"], "generation_epoch": prior["decision_epoch"],
                                "policy_version": prior["decision_policy_version"]}),
                                config, interrupt_after=["moderation_review"])
                            snapshot = graph.get_state(config)
                            retained = StoryMemory.model_validate(snapshot.values)
                            existing_review = retained.moderation_context.review
                            conn.execute("update job_moderation_reviews set dispatch_state='consumed',dispatch_error_code=null where id=%s",
                                         (prior["id"],))
                        if (len(snapshot.next) > 1 or (existing_review
                                and existing_review.resolution is None and not repairing)
                                or (job["image_count"] or 0) > retained.cost.image_count):
                            raise RuntimeError("checkpoint_not_resumable")
                        return_node = existing_review.return_node if repairing else snapshot.next[0] if snapshot.next else "__end__"
                        if return_node not in ("analyze", "segment", "char_bible", "char_ref_mod", "output_mod", "generate_scene", "consistency_check", "reveal", "compose", "__end__"):
                            raise RuntimeError("checkpoint_not_resumable")
                        if withdrawal["kind"] == "story_text":
                            text = retained.input.redacted_text
                            if text is None or text != withdrawal["subject"].get("story_text"):
                                raise RuntimeError("moderation_subject_unavailable")
                            changes = {"input": retained.input.model_copy(update={"moderation_clearance": None})}
                        elif withdrawal["kind"] == "character_reference":
                            char = next(c for c in retained.characters if c.char_id == withdrawal["subject_id"])
                            path = char.canonical_ref_image
                            changes = {"characters": [c.model_copy(update={"ref_moderation_status": None})
                                       if c.char_id == char.char_id else c for c in retained.characters]}
                        else:
                            scene = next(s for s in retained.scenes if s.scene_id == withdrawal["subject_id"])
                            path = scene.final_image_ref
                            changes = {"scenes": [scene.model_copy(update={
                                "moderation_status": None, "attempts": [a.model_copy(update={"safety_eligibility": "unreviewed"})
                                    if a.image_ref == scene.final_image_ref else a for a in scene.attempts],
                            })]}
                        if withdrawal["kind"] != "story_text" and path != withdrawal["subject"]["image_path"]:
                            raise RuntimeError("moderation_subject_unavailable")
                        import hashlib
                        if hashlib.sha256(review_subject_bytes(withdrawal)).hexdigest() != withdrawal["subject_version"]:
                            raise RuntimeError("moderation_subject_unavailable")
                        context = retained.moderation_context.model_copy(update={"generation_epoch": epoch,
                            "review": ReviewContext(review_id=withdrawal["id"], kind=withdrawal["kind"], subject_id=withdrawal["subject_id"],
                                subject_version=withdrawal["subject_version"], criteria=withdrawal["criteria"], return_node=return_node)})
                        graph.update_state(config, {"moderation_context": context, **changes}, as_node="moderation_review")
                        graph.invoke(None, config)
                        anchored = graph.get_state(config)
                        conn.execute("""update job_moderation_reviews set checkpoint_id=%s,return_node=%s where id=%s""",
                            (anchored.config["configurable"]["checkpoint_id"], return_node, withdrawal["id"]))
                    conn.execute("update job_moderation_reviews set dispatch_state='consumed',dispatch_error_code=null where id=%s",
                                 (withdrawal["id"],))
                    return
                decision = conn.execute("""select * from job_moderation_reviews where job_id=%s
                  and decision_epoch=%s and dispatch_kind='resume'""", (job_id, job["generation_epoch"])).fetchone()
                if review_id is not None and (not decision or str(decision["id"]) != review_id):
                    return
                if decision and decision["dispatch_state"] == "consumed":
                    if payload is None:
                        return
                    # A later child reveal command shares the current epoch, but
                    # does not replay the teacher decision that reached reveal.
                    decision = None
                if job["status"] in ("awaiting_confirm", "complete", "stopped", "deleting"):
                    return
                if job["status"] == "awaiting_teacher" and job["worker_finished_at"] is not None:
                    return
                if job["status"] == "failed" and job["error"] not in ("hold_projection_failed", "worker_stopped"):
                    return
                epoch = job["generation_epoch"]
                initial_count = job["image_count"] or 0
                if not active_author(conn, job):
                    raise RuntimeError("account_unavailable")
                if decision:
                    teacher_classroom(conn, str(job["classroom_id"]), str(decision["actor_id"]))
                conn.execute("update jobs set worker_finished_at=null where id=%s", (job_id,))
                started = True

            def fence():
                assert_current(conn, job_id, epoch)

            def image_event(event):
                if event == "completed":
                    incurred[0] += 1

            tokens = [providers._generation_fence.set(fence), providers._fal_event_sink.set(image_event)]
            with PostgresSaver.from_conn_string(settings.supabase_db_url) as saver:
                saver.setup()
                graph = build_graph(checkpointer=saver)
                config = {"configurable": {"thread_id": job_id}, "recursion_limit": TEACHER_REVIEW_RECURSION_LIMIT, "callbacks": []}
                snapshot = graph.get_state(config)
                if snapshot.values:
                    retained = StoryMemory.model_validate(snapshot.values)
                    review = retained.moderation_context.review
                    if review and review.resolution is None and decision:
                        if (decision["decision"] not in ("allow", "replace") or validate_review_checkpoint(conn, job_id, decision) is None
                                or str(review.review_id) != str(decision["id"])
                                or snapshot.next != ("moderation_review",)):
                            raise RuntimeError("checkpoint_not_resumable")
                        contents = review_subject_bytes(decision)
                        import hashlib
                        if hashlib.sha256(contents).hexdigest() != decision["subject_version"]:
                            raise RuntimeError("moderation_subject_unavailable")
                        config["configurable"]["checkpoint_id"] = decision["checkpoint_id"]
                        graph_input = Command(resume={"action": decision["decision"], "review_id": str(decision["id"]),
                            "subject_version": decision["subject_version"], "generation_epoch": epoch,
                            "policy_version": decision["decision_policy_version"]})
                    elif review and review.resolution is None:
                        hold_pending = True
                        # Output evidence is durable even if the process died before interrupt.
                        if snapshot.next != ("moderation_review",):
                            raise RuntimeError("invalid_moderation_checkpoint")
                        if not any(task.interrupts for task in snapshot.tasks):
                            graph.invoke(None, config)
                            snapshot = graph.get_state(config)
                        epoch = project_hold(conn, job_id, retained, snapshot.config["configurable"]["checkpoint_id"])
                        return
                    elif (payload is None or snapshot.next != ("reveal",)
                            or retained.moderation_context.generation_epoch != epoch):
                        raise RuntimeError("checkpoint_not_resumable")
                    else:
                        graph_input = Command(resume=payload)
                else:
                    if job["status"] != "queued" or payload is not None or decision is not None or review_id is not None:
                        raise RuntimeError("checkpoint_unavailable")
                    captured = job["moderation_settings_snapshot"]
                    if not captured.get("policy_version"):
                        raise RuntimeError("moderation_config_unavailable")
                    chosen_id = job["style_preset_id"] or "cel"
                    graph_input = StoryMemory(
                        schema_version=CURRENT_SCHEMA_VERSION, story_id=job_id,
                        classroom_id=str(job["classroom_id"]), profile_id=str(job["profile_id"]),
                        input=Input(raw_text=job["input_text"], word_count=word_count(job["input_text"]), truncated=job["truncated"]),
                        style=Style(style_preset_id=chosen_id, prompt_fragment=STYLE_PRESETS[chosen_id]),
                        moderation_context=ModerationContext(mode="teacher_review_v1", generation_epoch=epoch, **captured),
                    )
                with conn.transaction():
                    assert_current(conn, job_id, epoch)
                    conn.execute("update jobs set status='running' where id=%s", (job_id,))
                # No callbacks, trace URL or public Langfuse publication in this mode.
                for mode, chunk in graph.stream(graph_input, config, stream_mode=["updates", "values"]):
                    fence()
                    if mode == "updates":
                        node = next((k for k in chunk if k != "__interrupt__"), None)
                        if node:
                            conn.execute("update jobs set current_stage=%s where id=%s and generation_epoch=%s",
                                         (node, job_id, epoch))
                # Read back the committed checkpoint, never trust an ephemeral stream event.
                config["configurable"].pop("checkpoint_id", None)
                snapshot = graph.get_state(config)
                state = StoryMemory.model_validate(snapshot.values)
                if state.moderation_context.review and state.moderation_context.review.resolution is None:
                    hold_pending = True
                    epoch = project_hold(conn, job_id, state, snapshot.config["configurable"]["checkpoint_id"])
                else:
                    from psycopg.types.json import Jsonb

                    with conn.transaction():
                        assert_current(conn, job_id, epoch)
                        interrupts = [i for t in snapshot.tasks for i in t.interrupts]
                        if interrupts:
                            value = interrupts[0].value
                            if snapshot.next != ("reveal",) or not isinstance(value, dict) or "characters" not in value:
                                raise RuntimeError("invalid_reveal_checkpoint")
                            conn.execute("update jobs set status='awaiting_confirm',current_stage='reveal',reveal=%s where id=%s",
                                         (Jsonb(value), job_id))
                        else:
                            if snapshot.next or any(s.moderation_status not in ("passed", "teacher_allowed") for s in state.scenes):
                                raise RuntimeError("incomplete_safety_checks")
                            pages = [{"scene_id": s.scene_id, "caption": s.caption, "image_path": s.final_image_ref} for s in state.scenes]
                            outcomes = [outcome(s) for s in state.scenes]
                            conn.execute("""update jobs set status='complete',current_stage='compose',pages=%s,
                              reveal='{}',image_count=%s,regen_count=%s,ref_retry_count=%s,scenes_total=%s,
                              scenes_passed=%s,scenes_failed=%s,scenes_unchecked=%s,usd_estimate=%s where id=%s""", (
                                Jsonb(pages), state.cost.image_count, state.cost.regen_count, state.cost.ref_retry_count,
                                len(state.scenes), outcomes.count("passed"), outcomes.count("failing"), outcomes.count("unchecked"),
                                round(state.cost.image_count * 0.025, 4), job_id,
                            ))
                        conn.execute("update jobs set image_count=%s where id=%s", (state.cost.image_count, job_id))
                if decision:
                    conn.execute("update job_moderation_reviews set dispatch_state='consumed',dispatch_error_code=null where id=%s",
                                 (decision["id"],))
        except StaleGeneration:
            pass  # The authoritative newer state wins. Never write a stale failure.
        except Exception as exc:
            if started and epoch is not None:
                # Projection failure preserves its checkpoint for explicit repair.
                code = "hold_projection_failed" if hold_pending else "generation_failed"
                conn.execute("""update jobs set status='failed',error=%s,failure_reason=%s
                  where id=%s and generation_epoch=%s and status in ('queued','running','failed','awaiting_teacher')""",
                             (code, classify_failure_reason(exc), job_id, epoch))
            raise
        finally:
            if tokens:
                providers._generation_fence.reset(tokens[0])
                providers._fal_event_sink.reset(tokens[1])
            if started and epoch is not None:
                conn.execute("""update jobs set image_count=greatest(coalesce(image_count,0),%s)
                  where id=%s and generation_epoch>=%s and status<>'deleting'""", (initial_count + incurred[0], job_id, epoch))
                # After every checkpoint/provider/tracing operation, including raised failures.
                conn.execute("""update jobs set worker_finished_at=now()
                  where id=%s and generation_epoch=%s""", (job_id, epoch))
            conn.execute("select pg_advisory_unlock(hashtextextended(%s,0))", (job_id,))


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
        if isinstance(value, dict) and value.get("kind") == "moderation_review":
            raise RuntimeError("moderation interrupt requires private durable projection")
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
    row = supabase.table("jobs").select("input_text, style_preset_id, truncated, classroom_id, profile_id, moderation_mode").eq("id", job_id).single().execute()
    if row.data.get("moderation_mode") == "teacher_review_v1":
        return run_review_storybook_job(job_id)
    input_text = row.data["input_text"]
    preset_id = row.data.get("style_preset_id")
    truncated = row.data["truncated"]
    chosen_id = preset_id if preset_id is not None else "cel"

    supabase.table("jobs").update({"status": "running", "worker_finished_at": None}).eq("id", job_id).execute()

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
        failure_reason = classify_failure_reason(exc)
        supabase.table("jobs").update(
            {"status": "failed", "error": msg, "failure_reason": failure_reason}
        ).eq("id", job_id).execute()
        raise
    finally:
        _publish_trace(job_id)
        supabase.table("jobs").update({"worker_finished_at": datetime.now(timezone.utc).isoformat()}).eq("id", job_id).execute()


def resume_storybook_job(job_id: str, payload: dict) -> None:
    """A second entrypoint that never constructs a `StoryMemory` — it structurally cannot rebuild
    and clobber a live checkpoint thread, the failure mode a single resume-aware
    `run_storybook_job(job_id, resume=None)` would leave one `if` away (spec §4.10).
    """
    supabase = get_supabase_client()
    mode_row = supabase.table("jobs").select("moderation_mode").eq("id", job_id).single().execute().data
    if mode_row.get("moderation_mode") == "teacher_review_v1":
        return run_review_storybook_job(job_id, payload)
    supabase.table("jobs").update({"status": "running", "worker_finished_at": None}).eq("id", job_id).execute()

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
        failure_reason = classify_failure_reason(exc)
        supabase.table("jobs").update(
            {"status": "failed", "error": msg, "failure_reason": failure_reason}
        ).eq("id", job_id).execute()
        raise
    finally:
        _publish_trace(job_id)
        supabase.table("jobs").update({"worker_finished_at": datetime.now(timezone.utc).isoformat()}).eq("id", job_id).execute()


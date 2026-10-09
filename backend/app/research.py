"""The run viewer's backend: one run's checkpoint history, projected (ADR-064).

Reads the LangGraph checkpoint thread (`thread_id = job_id`, ADR-033) and returns a projection, never
the checkpoint. `input.raw_text`, `profile_id` and `classroom_id` are dropped here; `jobs.input_text`
is never selected.
"""
import logging
from datetime import datetime
from typing import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from langgraph.checkpoint.postgres import PostgresSaver

from app.auth import require_researcher
from app.config import settings
from app.db import get_supabase_client
from contracts.story_memory import StoryMemory
from pipeline.graph import build_graph
from providers import get_signed_url

_log = logging.getLogger(__name__)

# ADR-064 rule 4: a page left open during a demo keeps its images.
SIGNED_URL_SECONDS = 3600

_ROW_FIELDS = (
    "id", "title", "status", "style_preset_id", "created_at", "failure_reason", "langfuse_trace_url",
    "usd_estimate", "image_count", "regen_count", "ref_retry_count", "scenes_total", "scenes_passed",
    "scenes_unchecked",
)
JOB_COLUMNS = ", ".join((*_ROW_FIELDS, "approved_at"))

# `complete` is absent on purpose: a finished run did not end on a node.
_ENDED_KIND = {"failed": "failed", "awaiting_confirm": "waiting", "queued": "running", "running": "running"}

_SCENE_FIELDS = {
    "scene_id", "text_excerpt", "caption", "visual_direction", "characters_present", "objects_present",
    "moderation_status", "regeneration_count",
}


def load_history(job_id: str) -> list:
    """Every checkpoint of one run, newest first. No `setup()`: the worker owns these tables."""
    with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
        graph = build_graph(checkpointer)
        return list(graph.get_state_history({"configurable": {"thread_id": job_id}}))


def sign(path: str | None) -> str | None:
    if not path:
        return None
    try:
        return get_signed_url(path, expires_in=SIGNED_URL_SECONDS)
    except Exception:
        # One missing object must not take the page down; the page shows a placeholder instead.
        _log.warning("run viewer could not sign a storage path")
        return None


def _duration_ms(start: str, end: str | None) -> int | None:
    if end is None:
        return None
    return round((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() * 1000)


def _steps(chronological: list) -> list[dict]:
    # `snapshot.next` is the node that ran after that checkpoint; the gap to the next checkpoint is its
    # duration. The last step of a failed or paused run has no next checkpoint, so no duration.
    steps = []
    for i, snap in enumerate(chronological):
        end = chronological[i + 1].created_at if i + 1 < len(chronological) else None
        for node in snap.next:
            if node != "__start__":
                steps.append({"node": node, "started_at": snap.created_at, "duration_ms": _duration_ms(snap.created_at, end)})
    return steps


def _state_parts(memory: StoryMemory, sign: Callable[[str | None], str | None]) -> dict:
    state = memory.model_dump(mode="json")
    state.pop("profile_id")
    state.pop("classroom_id")
    state["input"].pop("raw_text")
    scenes = []
    for scene in memory.scenes:
        shipped = next((i for i, a in enumerate(scene.attempts) if a.image_ref == scene.final_image_ref), None)
        scenes.append(scene.model_dump(mode="json", include=_SCENE_FIELDS) | {
            "shipped_attempt": shipped if scene.final_image_ref else None,
            "attempts": [a.model_dump(mode="json", exclude={"image_ref"}) | {"image_url": sign(a.image_ref)}
                         for a in scene.attempts],
        })
    moderation = memory.input.moderation
    return {
        "story": {"redacted_text": memory.input.redacted_text, "word_count": memory.input.word_count,
                  "truncated": memory.input.truncated},
        "moderation": {"input": moderation.model_dump(mode="json") if moderation else None},
        "characters": [c.model_dump(mode="json", exclude={"canonical_ref_image"})
                       | {"ref_image_url": sign(c.canonical_ref_image)} for c in memory.characters],
        "scenes": scenes,
        "cost": memory.cost.model_dump(mode="json"),
        "state": state,
    }


def project_run(job: dict, snapshots: list, sign: Callable[[str | None], str | None]) -> dict:
    """Pure. `snapshots` is `get_state_history` output, newest first."""
    out = {
        "job": {k: job.get(k) for k in _ROW_FIELDS} | {"approved": job.get("approved_at") is not None},
        "checkpointed": bool(snapshots),
        "story": None, "steps": [], "ended_on": None, "moderation": None,
        "characters": [], "scenes": [], "cost": None, "state": None,
    }
    if not snapshots:
        return out
    out["steps"] = _steps(list(reversed(snapshots)))
    kind = _ENDED_KIND.get(job["status"])
    ended = next((n for n in snapshots[0].next if n != "__start__"), None)
    if ended and kind:
        out["ended_on"] = {"node": ended, "kind": kind}
    # The `__start__` checkpoint has empty values; a thread that never got further has no state.
    latest = next((s for s in snapshots if s.values), None)
    if latest is not None:
        out |= _state_parts(StoryMemory.model_validate(latest.values), sign)
    return out


research_router = APIRouter()


@research_router.get("/research/runs/{job_id}")
def get_run(job_id: UUID, viewer: dict = Depends(require_researcher)) -> dict:
    rows = get_supabase_client().table("jobs").select(JOB_COLUMNS).eq("id", str(job_id)).execute().data
    if not rows:
        raise HTTPException(404, "not_found")
    job = rows[0]
    # ADR-064 rule 2: the adjudicator reads any run; every other researcher keeps 0008's approved-only rule.
    if not viewer["is_adjudicator"] and job["approved_at"] is None:
        raise HTTPException(403, "not_approved")
    return project_run(job, load_history(str(job_id)), sign)

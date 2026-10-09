# Research Runs A — Backend Run Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `GET /research/runs/{job_id}`, which returns one run's checkpoint history as a redacted projection for signed-in researchers.

**Architecture:** A new `backend/app/research.py` holds a pure `project_run(job, snapshots, sign)`, a thin `load_history(job_id)` over `PostgresSaver` + `build_graph`, and the route. Access lives in a new `require_researcher` dependency in `app/auth.py` plus one adjudicator check in the route. `providers.get_signed_url` gains an `expires_in` argument (default 300).

**Tech Stack:** Python 3.12, FastAPI, LangGraph 1.2.8 + langgraph-checkpoint-postgres 3.1.0, Pydantic `StoryMemory`, supabase-py, pytest, ruff (line length 120).

**Spec:** `docs/specs/research-run-browser.md` §2, §5.1. Decision record: ADR-064.

**Plan set:** A (this file) → B `2026-10-09-research-runs-b-shell.md` → C `2026-10-09-research-runs-c-run-list.md` → D `2026-10-09-research-runs-d-run-detail.md` → E `2026-10-09-research-runs-e-graph.md`. A has no dependency on B or C. D and E consume A's response shape. All five ship as one PR from branch `feat/research-run-browser`.

## Global Constraints

- Excluded from every response: `input.raw_text`, `profile_id`, `classroom_id`, `jobs.input_text` (never selected). The story shown is `input.redacted_text`; never fall back to `raw_text`.
- Access: signed out → 401; `role = 'researcher'` and `is_adjudicator = true` → any job; other researcher → only `approved_at is not null`, else 403; any other role → 403. RLS is not changed.
- Signed URLs for this route last 3600 s; every existing caller keeps 300 s.
- No migration, no `backend/contracts/` change, no `StoryMemory` change.
- `load_history` never calls `checkpointer.setup()`: the worker owns the checkpoint tables.
- Model IDs are not in the response (not recorded). Prompt versions only where recorded (`ref_verdict_prompt_version`).
- Never read `.env`. Tests mock Supabase and the checkpoint read; no network.
- Commits carry no `Co-Authored-By` or generated-by trailer.

## Review Focus

1. **A storage object that no longer exists.** One deleted image must not 500 the whole run; that image's URL is `null` and the page shows a placeholder. Pinned in Task 2 (`test_sign_returns_none_when_storage_fails`).
2. **A run blocked at the input gate.** The router raises, so `input_gate`'s writes are lost (checked on langgraph 1.2.8, 2026-10-09). The newest snapshot holds the initial state: `moderation.input` is `null`, `redacted_text` is `null`, and the projection must still not leak `raw_text`. Pinned in Task 2 (`test_blocked_at_input_gate_shows_nothing_unredacted`).
3. **A thread with only the `__start__` snapshot** (worker died before the first step). Its values are `{}`; validating them as `StoryMemory` would raise. Expect `checkpointed: true`, `steps: []`, `state: null`. Pinned in Task 2 (`test_thread_with_only_start_snapshot`).
4. **An id that is not a UUID** (`/research/runs/abc`). Postgres would reject it with a 500. Expect 422 from FastAPI path validation, which the page treats as "Run not found". Pinned in Task 3 (`test_malformed_id_is_422`).
5. **A run still in progress.** The newest snapshot's `next` names the running node; calling that "failed" would be wrong. Expect `ended_on.kind == "running"`. Pinned in Task 2 (`test_ended_on_kinds`).

---

## File map

| File | Responsibility |
|---|---|
| `backend/providers.py` (modify `get_signed_url`, line 568) | `expires_in` argument, default 300 |
| `backend/app/auth.py` (modify) | `require_researcher` dependency |
| `backend/app/research.py` (create) | `project_run`, `load_history`, `sign`, the route |
| `backend/app/main.py` (modify) | include `research_router` |
| `backend/tests/test_providers.py` (modify) | `get_signed_url` default and override |
| `backend/tests/test_research_runs.py` (create) | projection and access tests |
| `docs/specs/ROUTE_MAP.md` §8b (modify) | one row for the new backend route |

---

### Task 1: `get_signed_url` takes `expires_in`

**Files:**
- Modify: `backend/providers.py:568-570`
- Test: `backend/tests/test_providers.py` (append)

**Interfaces:**
- Produces: `get_signed_url(path: str, expires_in: int = 300) -> str`

- [ ] **Step 1: Write the failing test.** Append to `backend/tests/test_providers.py` (it already does `import providers` and `from unittest.mock import patch`; add the import if missing):

```python
def test_get_signed_url_defaults_to_300_seconds_and_accepts_an_override():
    with patch("providers.get_supabase_client") as client:
        bucket = client.return_value.storage.from_.return_value
        bucket.create_signed_url.return_value = {"signedURL": "https://signed/p.png"}

        assert providers.get_signed_url("p.png") == "https://signed/p.png"
        providers.get_signed_url("p.png", expires_in=3600)

    first, second = bucket.create_signed_url.call_args_list
    assert first.kwargs["expires_in"] == 300
    assert second.kwargs["expires_in"] == 3600
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `cd backend && uv run pytest tests/test_providers.py -k defaults_to_300 -v`
Expected: FAIL with `TypeError: get_signed_url() got an unexpected keyword argument 'expires_in'`.

- [ ] **Step 3: Implement.** Replace `backend/providers.py:568-570` with:

```python
def get_signed_url(path: str, expires_in: int = 300) -> str:
    resp = get_supabase_client().storage.from_(_STORAGE_BUCKET).create_signed_url(path, expires_in=expires_in)
    return resp["signedURL"]
```

- [ ] **Step 4: Run it and confirm it passes, and that existing callers still pass.**

Run: `cd backend && uv run pytest tests/test_providers.py tests/test_char_ref_mod_node.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit.**

```bash
git add backend/providers.py backend/tests/test_providers.py
git commit -m "feat(backend): get_signed_url takes expires_in (default 300)"
```

---

### Task 2: `project_run`, the pure projection

**Files:**
- Create: `backend/app/research.py`
- Test: `backend/tests/test_research_runs.py`

**Interfaces:**
- Consumes: `get_signed_url(path, expires_in)` from Task 1.
- Produces:
  - `project_run(job: dict, snapshots: list, sign: Callable[[str | None], str | None]) -> dict`. `snapshots` is `get_state_history` output, **newest first**; each item has `.next: tuple[str, ...]`, `.created_at: str` (ISO 8601), `.values: dict`.
  - `sign(path: str | None) -> str | None` (module function; `None` on a missing path or a storage error).
  - `SIGNED_URL_SECONDS = 3600`, `JOB_COLUMNS: str`.
  - Response shape (Plan D's `RunDetail` type mirrors this exactly):

```
job:          {id, title, status, style_preset_id, created_at, failure_reason, langfuse_trace_url,
               usd_estimate, image_count, regen_count, ref_retry_count, scenes_total, scenes_passed,
               scenes_unchecked, approved: bool}
checkpointed: bool
story:        {redacted_text: str|null, word_count: int, truncated: bool} | null
steps:        [{node: str, started_at: str, duration_ms: int|null}]
ended_on:     {node: str, kind: "failed"|"waiting"|"running"} | null
moderation:   {input: {passed: bool, categories: [str]} | null} | null
characters:   [{char_id, name, description{species, colours, body_features, clothing, notes, is_humanoid},
                ref_image_url, ref_moderation_status, ref_verdict{differences_observed, contradictions,
                matches_description, attributes_present, text_free}|null, ref_verdict_prompt_version}]
scenes:       [{scene_id, text_excerpt, caption, visual_direction, characters_present, objects_present,
                moderation_status, regeneration_count, shipped_attempt: int|null,
                attempts: [{image_url, prompt, passed, failure_reasons: [str], vlm_verdict{...}|null,
                            scene_contradictions: [str]|null}]}]
cost:         {image_count, regen_count, usd_estimate, ref_retry_count, ref_mod_retry_count} | null
state:        projected StoryMemory as JSON (raw_text, profile_id, classroom_id removed) | null
```

- [ ] **Step 1: Write the failing tests.** Create `backend/tests/test_research_runs.py`:

```python
"""GET /research/runs/{job_id} and its projection. Spec: docs/specs/research-run-browser.md §5.1, ADR-064."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app import research
from app.research import project_run
from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION, Attempt, Character, FailureReason, Input, ModerationResult, RefVerdict, Scene,
    StoryMemory,
)

JOB_ID = "3f9a1c2e-0000-4000-8000-000000000001"
RAW = "SENTINEL-RAW-7f3a"


def _memory(**overrides) -> StoryMemory:
    fields = dict(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id=JOB_ID,
        classroom_id="SENTINEL-CLASSROOM",
        profile_id="SENTINEL-PROFILE",
        input=Input(raw_text=RAW, redacted_text="Mia the fox found a red kite.", word_count=7,
                    moderation=ModerationResult(passed=True)),
        characters=[Character(
            char_id="c1", name="Mia", canonical_ref_image="refs/c1.png", ref_moderation_status="passed",
            ref_verdict=RefVerdict(differences_observed="none", matches_description=True),
            ref_verdict_prompt_version=3,
        )],
        scenes=[
            Scene(scene_id="s1", text_excerpt="Mia finds a kite.", regeneration_count=1, moderation_status="passed",
                  final_image_ref="pages/s1-a1.webp",
                  attempts=[Attempt(image_ref="pages/s1-a0.webp", passed=False,
                                    failure_reasons=[FailureReason.wrong_colour]),
                            Attempt(image_ref="pages/s1-a1.webp", passed=True)]),
            Scene(scene_id="s2", text_excerpt="The kite flies.", moderation_status="passed",
                  final_image_ref="pages/s2-a0.webp",
                  attempts=[Attempt(image_ref="pages/s2-a0.webp", passed=True)]),
        ],
    )
    fields.update(overrides)
    return StoryMemory(**fields)


def _job(status="complete", approved_at="2026-10-02T00:00:00+00:00"):
    return {"id": JOB_ID, "title": "The Red Kite", "status": status, "style_preset_id": "cel",
            "created_at": "2026-10-01T10:00:00+00:00", "failure_reason": None, "approved_at": approved_at,
            "langfuse_trace_url": None, "usd_estimate": 0.31, "image_count": 3, "regen_count": 1,
            "ref_retry_count": 0, "scenes_total": 2, "scenes_passed": 2, "scenes_unchecked": 0}


def _snap(next_, at, values):
    return SimpleNamespace(next=next_, created_at=at, values=values)


def _history(last_next, memory):
    """Newest first, the order get_state_history yields (checked on langgraph 1.2.8, 2026-10-09)."""
    v = dict(memory)  # live pydantic objects, the shape snapshot.values has
    chronological = [
        _snap(("__start__",), "2026-10-01T10:00:00+00:00", {}),
        _snap(("input_gate",), "2026-10-01T10:00:00+00:00", v),
        _snap(("analyze",), "2026-10-01T10:00:01.500000+00:00", v),
        _snap(("consistency_check",), "2026-10-01T10:00:04+00:00", v),
        _snap(("regenerate",), "2026-10-01T10:00:06+00:00", v),
        _snap(("consistency_check",), "2026-10-01T10:00:14+00:00", v),
        _snap(last_next, "2026-10-01T10:00:16+00:00", v),
    ]
    return list(reversed(chronological))


def _sign(path):
    return f"signed:{path}" if path else None


def test_steps_follow_history_order_with_durations():
    out = project_run(_job(), _history((), _memory()), _sign)

    assert out["checkpointed"] is True
    assert [(s["node"], s["duration_ms"]) for s in out["steps"]] == [
        ("input_gate", 1500), ("analyze", 2500), ("consistency_check", 2000),
        ("regenerate", 8000), ("consistency_check", 2000),
    ]
    assert out["steps"][0]["started_at"] == "2026-10-01T10:00:00+00:00"
    assert out["ended_on"] is None


def test_scenes_mark_the_shipped_attempt_and_sign_images():
    out = project_run(_job(), _history((), _memory()), _sign)

    assert [s["shipped_attempt"] for s in out["scenes"]] == [1, 0]
    assert out["scenes"][0]["attempts"][0]["image_url"] == "signed:pages/s1-a0.webp"
    assert out["scenes"][0]["attempts"][0]["failure_reasons"] == ["wrong_colour"]
    assert out["characters"][0]["ref_image_url"] == "signed:refs/c1.png"
    assert out["characters"][0]["ref_verdict_prompt_version"] == 3
    assert out["story"] == {"redacted_text": "Mia the fox found a red kite.", "word_count": 7, "truncated": False}


def test_ended_on_kinds():
    failed = project_run(_job(status="failed", approved_at=None), _history(("output_mod",), _memory()), _sign)
    waiting = project_run(_job(status="awaiting_confirm", approved_at=None), _history(("reveal",), _memory()), _sign)
    running = project_run(_job(status="running", approved_at=None), _history(("regenerate",), _memory()), _sign)

    assert failed["ended_on"] == {"node": "output_mod", "kind": "failed"}
    assert failed["steps"][-1] == {"node": "output_mod", "started_at": "2026-10-01T10:00:16+00:00",
                                   "duration_ms": None}
    assert waiting["ended_on"] == {"node": "reveal", "kind": "waiting"}
    assert running["ended_on"] == {"node": "regenerate", "kind": "running"}


def test_no_private_field_reaches_the_response():
    out = project_run(_job(), _history((), _memory()), _sign)
    body = json.dumps(out)

    for sentinel in (RAW, "SENTINEL-PROFILE", "SENTINEL-CLASSROOM"):
        assert sentinel not in body
    assert "raw_text" not in out["state"]["input"]


def test_blocked_at_input_gate_shows_nothing_unredacted():
    initial = _memory(input=Input(raw_text=RAW), characters=[], scenes=[])
    history = [_snap(("input_gate",), "2026-10-01T10:00:00+00:00", dict(initial)),
               _snap(("__start__",), "2026-10-01T10:00:00+00:00", {})]

    out = project_run(_job(status="failed", approved_at=None), history, _sign)

    assert out["ended_on"] == {"node": "input_gate", "kind": "failed"}
    assert out["moderation"] == {"input": None}
    assert out["story"]["redacted_text"] is None
    assert RAW not in json.dumps(out)


def test_thread_with_only_start_snapshot():
    out = project_run(_job(status="failed", approved_at=None),
                      [_snap(("__start__",), "2026-10-01T10:00:00+00:00", {})], _sign)

    assert out["checkpointed"] is True
    assert out["steps"] == []
    assert out["ended_on"] is None
    assert out["state"] is None and out["story"] is None and out["scenes"] == []


def test_no_checkpoint_thread():
    out = project_run(_job(), [], _sign)

    assert out["checkpointed"] is False
    assert out["job"]["title"] == "The Red Kite"
    assert out["job"]["approved"] is True
    assert out["steps"] == [] and out["state"] is None


def test_history_shape_matches_installed_langgraph():
    """Pins the newest-first order and the snapshot fields against the real library, not a stub."""
    graph = StateGraph(StoryMemory)
    graph.add_node("input_gate", lambda state: {})
    graph.add_node("analyze", lambda state: {})
    graph.set_entry_point("input_gate")
    graph.add_edge("input_gate", "analyze")
    graph.add_edge("analyze", END)
    compiled = graph.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": JOB_ID}}
    compiled.invoke(_memory(), config)

    out = project_run(_job(), list(compiled.get_state_history(config)), _sign)

    assert [s["node"] for s in out["steps"]] == ["input_gate", "analyze"]
    assert out["ended_on"] is None
    assert out["scenes"][0]["shipped_attempt"] == 1


def test_sign_returns_none_when_storage_fails():
    with patch("app.research.get_signed_url", side_effect=Exception("object not found")):
        assert research.sign("pages/gone.webp") is None
    assert research.sign(None) is None
```

- [ ] **Step 2: Run them and confirm they fail.**

Run: `cd backend && uv run pytest tests/test_research_runs.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'app.research'`.

- [ ] **Step 3: Implement.** Create `backend/app/research.py`:

```python
"""The run viewer's backend: one run's checkpoint history, projected (ADR-064).

Reads the LangGraph checkpoint thread (`thread_id = job_id`, ADR-033) and returns a projection, never
the checkpoint. `input.raw_text`, `profile_id` and `classroom_id` are dropped here; `jobs.input_text`
is never selected.
"""
import logging
from datetime import datetime
from typing import Callable

from langgraph.checkpoint.postgres import PostgresSaver

from app.config import settings
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
```

- [ ] **Step 4: Run them and confirm they pass.**

Run: `cd backend && uv run pytest tests/test_research_runs.py -v && uv run ruff check app/research.py tests/test_research_runs.py`
Expected: 9 passed; ruff `All checks passed!`. A `Deserializing unregistered type` warning from LangGraph is expected and out of scope (the worker uses the same default serializer).

- [ ] **Step 5: Break it on purpose.** In `_state_parts`, comment out `state["input"].pop("raw_text")`. Run `uv run pytest tests/test_research_runs.py -k private -v`. Expected: FAIL on the sentinel. Restore the line and re-run: PASS.

- [ ] **Step 6: Commit.**

```bash
git add backend/app/research.py backend/tests/test_research_runs.py
git commit -m "feat(backend): project a run's checkpoint history for the run viewer"
```

---

### Task 3: `require_researcher` and the route

**Files:**
- Modify: `backend/app/auth.py` (add after `require_teacher`)
- Modify: `backend/app/research.py` (add the router)
- Modify: `backend/app/main.py` (include the router after `app.include_router(teacher_router)`)
- Test: `backend/tests/test_research_runs.py` (append)
- Modify: `docs/specs/ROUTE_MAP.md` §8b table (append one row)

**Interfaces:**
- Consumes: `project_run`, `load_history`, `sign`, `JOB_COLUMNS` from Task 2.
- Produces:
  - `require_researcher(user=Depends(get_current_user)) -> dict` with keys `id, role, is_adjudicator`; raises `HTTPException(403, "researchers_only")`.
  - `GET /research/runs/{job_id}`: 200 with the Task 2 shape; 401 signed out; 403 with `detail` `"researchers_only"` or `"not_approved"`; 404 `"not_found"`; 422 on a non-UUID id. Plan D maps these `detail` codes to copy.
  - `research_router: APIRouter` in `app/research.py`.

- [ ] **Step 1: Write the failing tests.** Append to `backend/tests/test_research_runs.py`:

```python
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.auth import require_researcher
from app.main import app, get_current_user

client = TestClient(app)
ANNOTATOR = {"id": "r-1", "role": "researcher", "is_adjudicator": False}
ADJUDICATOR = {"id": "r-2", "role": "researcher", "is_adjudicator": True}


def _db(rows):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
    return db


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _get_as(profile, rows, job_id=JOB_ID):
    app.dependency_overrides[require_researcher] = lambda: profile
    db = _db(rows)
    with patch("app.research.get_supabase_client", return_value=db), \
         patch("app.research.load_history", return_value=[]):
        return client.get(f"/research/runs/{job_id}"), db


def test_signed_out_is_401():
    assert client.get(f"/research/runs/{JOB_ID}").status_code == 401


def test_teacher_is_403():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="t-1")
    with patch("app.auth.get_supabase_client",
               return_value=_db([{"id": "t-1", "role": "teacher", "is_adjudicator": False}])):
        response = client.get(f"/research/runs/{JOB_ID}")

    assert response.status_code == 403
    assert response.json()["detail"] == "researchers_only"


def test_annotator_cannot_open_an_unapproved_run():
    response, _ = _get_as(ANNOTATOR, [_job(status="failed", approved_at=None)])

    assert response.status_code == 403
    assert response.json()["detail"] == "not_approved"


def test_annotator_opens_an_approved_run_without_reading_input_text():
    response, db = _get_as(ANNOTATOR, [_job()])

    assert response.status_code == 200
    assert response.json()["job"]["title"] == "The Red Kite"
    assert "input_text" not in db.table.return_value.select.call_args.args[0]


def test_adjudicator_opens_an_unapproved_run():
    response, _ = _get_as(ADJUDICATOR, [_job(status="failed", approved_at=None)])

    assert response.status_code == 200
    assert response.json()["job"]["approved"] is False


def test_unknown_run_is_404():
    response, _ = _get_as(ADJUDICATOR, [])

    assert response.status_code == 404


def test_malformed_id_is_422():
    response, _ = _get_as(ADJUDICATOR, [_job()], job_id="abc")

    assert response.status_code == 422
```

Move the new imports to the top of the file with the others so ruff's import rule stays clean.

- [ ] **Step 2: Run them and confirm they fail.**

Run: `cd backend && uv run pytest tests/test_research_runs.py -v`
Expected: collection error `ImportError: cannot import name 'require_researcher' from 'app.auth'`.

- [ ] **Step 3: Implement the dependency.** In `backend/app/auth.py`, after `require_teacher`:

```python
def require_researcher(user=Depends(get_current_user)) -> dict:
    rows = (get_supabase_client().table("profiles")
            .select("id, role, is_adjudicator").eq("id", user.id).execute().data)
    if not rows or rows[0]["role"] != "researcher":
        raise HTTPException(403, "researchers_only")
    return rows[0]
```

- [ ] **Step 4: Implement the route.** In `backend/app/research.py`, extend the imports and append the router:

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_researcher
from app.db import get_supabase_client
```

```python
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
```

In `backend/app/main.py`, add `from app.research import research_router` beside the other `app.` imports and `app.include_router(research_router)` on the line after `app.include_router(teacher_router)`.

- [ ] **Step 5: Run the file, then the whole suite.**

Run: `cd backend && uv run pytest tests/test_research_runs.py -v && uv run pytest && uv run ruff check .`
Expected: 16 passed in the file; full suite green; ruff clean.

- [ ] **Step 6: Break it on purpose.** Delete the `if not viewer["is_adjudicator"] ...` check. Run `uv run pytest tests/test_research_runs.py -k unapproved -v`. Expected: `test_annotator_cannot_open_an_unapproved_run` FAILS (200 ≠ 403). Restore and re-run: PASS.

- [ ] **Step 7: Document the route.** Append to the table in `docs/specs/ROUTE_MAP.md` §8b:

```markdown
| `GET /research/runs/{job_id}` | Researcher (`require_researcher`); adjudicator any run, others approved runs only | Run viewer projection of the checkpoint history (ADR-064). 403 `researchers_only` / `not_approved`, 404 `not_found` |
```

- [ ] **Step 8: Commit.**

```bash
git add backend/app/auth.py backend/app/research.py backend/app/main.py backend/tests/test_research_runs.py docs/specs/ROUTE_MAP.md
git commit -m "feat(backend): GET /research/runs/{job_id} for researchers (ADR-064)"
```

---

## Not verified by this plan

- The real `PostgresSaver` read against production threads (size and latency per request). Plan E Task 5 times the endpoint on a real run.
- Whether production jobs have checkpoint threads at all. If none do, every run shows `checkpointed: false`; Plan D's browser check will show it.

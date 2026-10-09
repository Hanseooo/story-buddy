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

"""§5 — the synthetic corpus and the runner that turns it into images.

Two of these tests exist to stop a specific way of losing money: the spend cap (an unbounded
fal.ai bill) and the resume skip (paying twice for the same story). Everything else validates
that the checked-in corpus can actually reach the pipeline — a story that fails `clamp_story`
or the `POST /storybooks` minimum-length rule is a story you discover after paying for the
nineteen before it.

Every provider call is mocked. Nothing here draws an image.
"""
import hashlib
import json
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from app.config import MAX_STORY_WORDS, MIN_STORY_WORDS, STYLE_PRESETS
from app.length import clamp_story, word_count
from contracts.story_memory import Character, Cost, Scene
from finetune import build_corpus
from finetune.corpus_io import CorpusError, IntakeRecord, intake_sha256, load_completed_bundles


# --------------------------------------------------------------------------- corpus data


@pytest.fixture(scope="module")
def corpus():
    return build_corpus.load_corpus()


def test_corpus_has_thirty_stories_with_unique_ids(corpus):
    assert len(corpus) == 30
    assert len({s["story_id"] for s in corpus}) == 30


def test_every_story_clears_the_api_length_guard(corpus):
    """`POST /storybooks` rejects under MIN_STORY_WORDS with a 422 and `clamp_story` silently
    truncates over MAX_STORY_WORDS. Both would be discovered mid-run, after real spend."""
    for story in corpus:
        words = word_count(story["text"])
        assert words >= MIN_STORY_WORDS, story["story_id"]
        assert words <= MAX_STORY_WORDS, story["story_id"]
        text, truncated = clamp_story(story["text"])
        assert truncated is False, story["story_id"]
        assert text == story["text"], story["story_id"]


def test_every_story_carries_one_or_two_named_characters(corpus):
    """ADR-004 caps canonical references at 2 per story — a third named character can never
    get a reference image and so can never contribute a labelled pair."""
    for story in corpus:
        names = story["declared_characters"]
        assert 1 <= len(names) <= 2, story["story_id"]
        assert len(set(names)) == len(names), story["story_id"]
        assert set(story["declared_non_human"]) <= set(names), story["story_id"]
        for name in names:
            assert name in story["text"], (story["story_id"], name)


def test_character_names_are_distinct_across_the_whole_corpus(corpus):
    """§3.2 splits on character. Two stories sharing a name would land the same character on
    both sides of a split without the split guard ever seeing it."""
    names = [n for s in corpus for n in s["declared_characters"]]
    assert len(set(names)) == len(names)


def test_corpus_is_roughly_thirty_eight_characters_mostly_non_human(corpus):
    """§7.4 item 2 — the non-human slice is the research contribution and the least-powered
    slice, so the train corpus is deliberately weighted toward it."""
    names = [n for s in corpus for n in s["declared_characters"]]
    non_human = [n for s in corpus for n in s["declared_non_human"]]
    assert 36 <= len(names) <= 40
    assert 0.60 <= len(non_human) / len(names) <= 0.72


def test_corpus_file_is_static_data_not_a_generator(corpus):
    """CC-7 reproducibility: the corpus is byte-stable and hashable because it is checked in.
    A runtime-generated corpus would be neither."""
    raw = json.loads(build_corpus.CORPUS_PATH.read_text(encoding="utf-8"))
    assert raw == corpus


# --------------------------------------------------------------------------- runner harness


def _values(images: int, chars: int = 1, scenes: int = 0) -> dict:
    return {
        "cost": Cost(image_count=images),
        "characters": [
            Character(char_id=f"c{i}", name=f"c{i}", canonical_ref_image=f"story/ref-c{i}-1.png")
            for i in range(chars)
        ],
        "scenes": [
            Scene(scene_id=f"s{i}", text_excerpt="x", final_image_ref=f"story/s{i}-1.png")
            for i in range(scenes)
        ],
    }


class FakeGraph:
    """Stands in for the compiled LangGraph app. Records how far each stream was consumed so a
    test can prove the runner stopped pulling rather than merely stopped counting."""

    def __init__(self, per_story_images: int):
        self.per_story_images = per_story_images
        self.calls: list[str] = []
        self.consumed = 0

    def stream(self, graph_input, config, stream_mode=None):
        self.calls.append(config["configurable"]["thread_id"])
        for n in range(1, self.per_story_images + 1):
            sink = build_corpus._fal_event_sink.get()
            if sink:
                sink("attempted")
            self.consumed += 1
            if sink:
                sink("completed")
            values = graph_input.model_dump()
            values.update(
                cost=Cost(image_count=n),
                characters=[
                    Character(char_id="c0", name="c0", canonical_ref_image="story/ref-c0-1.png")
                ],
            )
            yield "values", values


class UncertainGraph:
    def __init__(self):
        self.calls = 0

    def stream(self, graph_input, config, stream_mode=None):
        self.calls += 1
        sink = build_corpus._fal_event_sink.get()
        sink("attempted")
        sink("failed_uncertain")
        raise TimeoutError("provider result unknown")
        yield


class RecoverableGraph(FakeGraph):
    def __init__(self, story, per_story_images):
        super().__init__(per_story_images)
        self.story = story

    def get_state(self, config):
        return SimpleNamespace(values=build_corpus._initial_state(self.story).model_dump())

    def stream(self, graph_input, config, stream_mode=None):
        for mode, values in super().stream(graph_input, config, stream_mode):
            values["characters"] = [
                Character(
                    char_id=f"c{i}",
                    name=name,
                    description={"is_humanoid": name not in self.story.declared_non_human},
                    canonical_ref_image=f"story/ref-c{i}-1.png",
                )
                for i, name in enumerate(self.story.declared_characters)
            ]
            yield mode, values


class FakeStorage:
    def __init__(self):
        self.downloads: list[str] = []

    def from_(self, bucket):
        return self

    def download(self, path):
        self.downloads.append(path)
        return image_bytes("PNG")


class FakeSupabase:
    def __init__(self):
        self.storage = FakeStorage()


def image_bytes(image_format):
    output = BytesIO()
    Image.new("RGB", (2, 3), "purple").save(output, format=image_format)
    return output.getvalue()


@pytest.fixture
def stories():
    return [
        IntakeRecord.model_validate(
            {
                "story_id": story_id,
                "text": "t",
                "declared_characters": ["c0"],
                "declared_non_human": [],
                "provenance": "synthetic",
                "split": "train",
                "candidate_role": "not_applicable",
                "style_preset_id": "cel",
            }
        )
        for story_id in ("a", "b", "c")
    ]


# --------------------------------------------------------------------------- the spend cap


def test_spend_policy_rounds_fractional_megapixels_up_for_each_call():
    policy = build_corpus.SpendPolicy(price_per_megapixel=Decimal("0.03"))

    assert policy.maximum_megapixels == Decimal("0.786432")
    assert policy.billable_megapixels == 1
    assert policy.conservative_call_usd == Decimal("0.03")


def test_operator_output_records_the_budget_basis(tmp_path, stories):
    policy = build_corpus.SpendPolicy(max_usd=Decimal("0.03"), price_per_megapixel=Decimal("0.03"))

    summary = build_corpus.build(
        stories[:1], FakeGraph(1), out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )
    [bundle] = load_completed_bundles(tmp_path)

    expected = {
        "image_size": "1024x768",
        "maximum_megapixels": "0.786432",
        "billable_megapixels": 1,
        "price_per_megapixel": "0.03",
        "authorized_usd": "0.03",
        "conservative_call_usd": "0.03",
    }
    assert expected.items() <= summary.items()
    assert expected.items() <= bundle.run_metadata.items()


def test_campaign_refuses_to_start_a_story_whose_maximum_draws_do_not_fit(tmp_path, stories):
    graph = FakeGraph(per_story_images=1)

    summary = build_corpus.build(
        stories,
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("1.92")),
    )

    assert graph.calls == []
    assert summary["halted"] is True
    assert summary["usd_high"] == "0.000"


def test_smoke_divides_affordable_draws_and_quarantines_at_the_ceiling(tmp_path, stories):
    graph = FakeGraph(per_story_images=20)

    summary = build_corpus.build(
        stories,
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("1.50")),
    )

    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert graph.calls == ["a"]
    assert graph.consumed == 14
    assert summary["images_spent"] == 14
    assert Decimal(summary["usd_high"]) == Decimal("0.490")
    assert state["a"]["reason_code"] == "budget_stopped"


def test_campaign_hard_cap_is_unconditionally_thirty_dollars():
    assert build_corpus.SpendPolicy(max_usd=Decimal("31.00")).authorized_usd == Decimal("30.00")


def test_exact_story_draw_limit_still_writes_a_completed_bundle(tmp_path, stories):
    graph = FakeGraph(per_story_images=2)
    policy = build_corpus.SpendPolicy(
        max_usd=Decimal("0.06"), price_per_megapixel=Decimal("0.03")
    )

    summary = build_corpus.build(
        stories[:1], graph, out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )

    assert summary["stories_run"] == 1
    assert summary["halted"] is False
    assert graph.consumed == 2
    assert load_completed_bundles(tmp_path)[0].memory.story_id == "a"


def test_next_call_past_story_limit_is_blocked_before_submission(tmp_path, stories):
    graph = FakeGraph(per_story_images=3)
    policy = build_corpus.SpendPolicy(
        max_usd=Decimal("0.06"), price_per_megapixel=Decimal("0.03")
    )

    summary = build_corpus.build(
        stories[:1], graph, out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert graph.consumed == 2
    assert summary["halted"] is True
    assert state["a"]["reason_code"] == "budget_stopped"
    assert load_completed_bundles(tmp_path) == []


def test_resume_exhaustion_is_quarantined_without_a_bundle(tmp_path, stories):
    class InterruptGraph:
        calls = 0

        def stream(self, graph_input, config, stream_mode=None):
            self.calls += 1
            yield "updates", {"__interrupt__": [object()]}

    graph = InterruptGraph()
    summary = build_corpus.build(
        stories[:1], graph, out_dir=tmp_path, supabase=FakeSupabase()
    )
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert graph.calls == build_corpus.MAX_RESUMES + 1
    assert summary["halted"] is True
    assert state["a"]["reason_code"] == "resume_exhausted"
    assert load_completed_bundles(tmp_path) == []


def test_campaign_reserves_completed_bundle_spend_across_invocations(tmp_path, stories):
    first_graph = FakeGraph(per_story_images=2)
    policy = build_corpus.SpendPolicy(max_usd=Decimal("1.95"))
    build_corpus.build(
        stories[:1], first_graph, out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )

    resumed_graph = FakeGraph(per_story_images=1)
    summary = build_corpus.build(
        stories[:2], resumed_graph, out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )

    assert resumed_graph.calls == []
    assert summary["halted"] is True
    assert Decimal(summary["usd_high"]) == Decimal("0.070")


def test_campaign_persists_failed_call_spend_before_restart(tmp_path, stories):
    class FailedGraph:
        def stream(self, graph_input, config, stream_mode=None):
            sink = build_corpus._fal_event_sink.get()
            sink("attempted")
            sink("failed")
            raise RuntimeError("known provider failure")
            yield

    policy = build_corpus.SpendPolicy(max_usd=Decimal("1.93"))
    with pytest.raises(RuntimeError, match="known provider failure"):
        build_corpus.build(
            stories[:1], FailedGraph(), out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
        )

    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert state["a"]["telemetry"]["attempted"] == 1
    resumed_graph = RecoverableGraph(stories[0], per_story_images=1)
    summary = build_corpus.build(
        stories[:1], resumed_graph, out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )
    assert resumed_graph.calls == []
    assert summary["halted"] is True
    assert Decimal(summary["usd_high"]) == Decimal("0.035")


def test_uncertain_billing_quarantines_and_stops_without_retry(tmp_path):
    graph = UncertainGraph()
    with pytest.raises(CorpusError, match="billing uncertain"):
        build_corpus.build([intake_story()], graph, out_dir=tmp_path, supabase=FakeSupabase())

    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert graph.calls == 1
    assert state["fixture-story"]["telemetry"] == {
        "attempted": 1,
        "completed": 0,
        "failed": 0,
        "uncertain": 1,
    }


def test_restart_quarantines_an_attempt_without_a_terminal_billing_event(tmp_path):
    story = intake_story()

    class CrashedGraph:
        def stream(self, graph_input, config, stream_mode=None):
            build_corpus._fal_event_sink.get()("attempted")
            raise SystemExit("process died")
            yield

    with pytest.raises(SystemExit, match="process died"):
        build_corpus.build([story], CrashedGraph(), out_dir=tmp_path, supabase=FakeSupabase())

    resumed = RecoverableGraph(story, per_story_images=1)
    with pytest.raises(CorpusError, match="billing uncertain"):
        build_corpus.build([story], resumed, out_dir=tmp_path, supabase=FakeSupabase())

    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert resumed.calls == []
    assert state[story.story_id]["reason_code"] == "billing_uncertain"


def test_budget_stop_requires_explicit_resume_and_preserves_telemetry(tmp_path, stories):
    smoke = build_corpus.SpendPolicy(max_usd=Decimal("0.07"))
    build_corpus.build(
        stories[:1], FakeGraph(3), out_dir=tmp_path, supabase=FakeSupabase(), policy=smoke
    )

    resumed = RecoverableGraph(stories[0], per_story_images=1)
    summary = build_corpus.build(
        stories[:1],
        resumed,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        resume_quarantined="a",
    )
    [bundle] = load_completed_bundles(tmp_path)

    assert summary["stories_run"] == 1
    assert bundle.run_metadata["attempted_calls"] == 3
    assert bundle.run_metadata["completed_calls"] == 3


def test_uncertain_billing_requires_matching_acknowledgment(tmp_path):
    story = intake_story()
    with pytest.raises(CorpusError, match="billing uncertain"):
        build_corpus.build(
            [story], UncertainGraph(), out_dir=tmp_path, supabase=FakeSupabase()
        )

    resumed = RecoverableGraph(story, per_story_images=1)
    with pytest.raises(CorpusError, match="acknowledge uncertain billing"):
        build_corpus.build(
            [story],
            resumed,
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            resume_quarantined=story.story_id,
        )
    assert resumed.calls == []


def test_uncertain_billing_acknowledgment_never_reduces_spend(tmp_path):
    story = intake_story()
    with pytest.raises(CorpusError):
        build_corpus.build(
            [story], UncertainGraph(), out_dir=tmp_path, supabase=FakeSupabase()
        )

    build_corpus.build(
        [story],
        RecoverableGraph(story, per_story_images=1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        resume_quarantined=story.story_id,
        acknowledge_uncertain_billing=story.story_id,
    )
    [bundle] = load_completed_bundles(tmp_path)

    assert bundle.run_metadata["attempted_calls"] == 2
    assert bundle.run_metadata["uncertain_calls"] == 1
    assert "billing_acknowledged_at" in bundle.run_metadata


def test_recovery_rejects_a_checkpoint_bound_to_different_intake(tmp_path):
    story = intake_story()
    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "telemetry": {"attempted": 1, "completed": 1, "failed": 0, "uncertain": 0},
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = RecoverableGraph(story, per_story_images=1)
    wrong = build_corpus._initial_state(story).model_copy(update={"story_id": "different-story"})
    graph.get_state = lambda config: SimpleNamespace(values=wrong.model_dump())

    with pytest.raises(CorpusError, match="checkpoint does not match intake"):
        build_corpus.build(
            [story],
            graph,
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            resume_quarantined=story.story_id,
        )
    assert graph.calls == []


def test_recovery_rejects_more_terminal_events_than_attempts(tmp_path):
    story = intake_story()
    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "telemetry": {"attempted": 0, "completed": 1, "failed": 0, "uncertain": 0},
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(CorpusError, match="invalid persisted billing telemetry"):
        build_corpus.build(
            [story],
            RecoverableGraph(story, per_story_images=1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            resume_quarantined=story.story_id,
        )


def test_restart_rejects_non_integer_billing_counters_as_corpus_error(tmp_path):
    story = intake_story()
    state = {
        story.story_id: {
            "in_progress": True,
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "telemetry": {"attempted": 1, "completed": "1", "failed": 0, "uncertain": 0},
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = RecoverableGraph(story, per_story_images=1)

    with pytest.raises(CorpusError, match="invalid persisted billing telemetry"):
        build_corpus.build([story], graph, out_dir=tmp_path, supabase=FakeSupabase())
    assert graph.calls == []


def test_restart_rejects_missing_billing_counters_before_graph_execution(tmp_path):
    story = intake_story()
    state = {
        story.story_id: {
            "in_progress": True,
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "telemetry": {"attempted": 1, "completed": 1, "failed": 0},
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = RecoverableGraph(story, per_story_images=1)

    with pytest.raises(CorpusError, match="invalid persisted billing telemetry"):
        build_corpus.build([story], graph, out_dir=tmp_path, supabase=FakeSupabase())
    assert graph.calls == []


def test_in_progress_restart_quarantines_an_intake_digest_mismatch(tmp_path):
    story = intake_story()
    state = {
        story.story_id: {
            "in_progress": True,
            "intake_sha256": "0" * 64,
            "conservative_call_usd": "0.035",
            "telemetry": {"attempted": 1, "completed": 1, "failed": 0, "uncertain": 0},
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = RecoverableGraph(story, per_story_images=1)

    with pytest.raises(CorpusError, match="intake digest differs"):
        build_corpus.build([story], graph, out_dir=tmp_path, supabase=FakeSupabase())

    saved = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert graph.calls == []
    assert saved[story.story_id]["reason_code"] == "intake_mismatch"


def test_in_progress_restart_quarantines_a_checkpoint_mismatch(tmp_path):
    story = intake_story()
    state = {
        story.story_id: {
            "in_progress": True,
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "telemetry": {"attempted": 1, "completed": 1, "failed": 0, "uncertain": 0},
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = RecoverableGraph(story, per_story_images=1)
    wrong = build_corpus._initial_state(story).model_copy(update={"story_id": "different-story"})
    graph.get_state = lambda config: SimpleNamespace(values=wrong.model_dump())

    with pytest.raises(CorpusError, match="checkpoint does not match intake"):
        build_corpus.build([story], graph, out_dir=tmp_path, supabase=FakeSupabase())

    saved = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert graph.calls == []
    assert saved[story.story_id]["reason_code"] == "invalid_terminal"


def test_billing_acknowledgment_survives_requarantine(tmp_path):
    story = intake_story()
    with pytest.raises(CorpusError, match="billing uncertain"):
        build_corpus.build([story], UncertainGraph(), out_dir=tmp_path, supabase=FakeSupabase())

    class InterruptGraph(RecoverableGraph):
        def stream(self, graph_input, config, stream_mode=None):
            yield "updates", {"__interrupt__": [object()]}

    summary = build_corpus.build(
        [story],
        InterruptGraph(story, per_story_images=0),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        resume_quarantined=story.story_id,
        acknowledge_uncertain_billing=story.story_id,
    )
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert summary["halted"] is True
    assert state[story.story_id]["reason_code"] == "resume_exhausted"
    assert state[story.story_id]["billing_acknowledged_at"].endswith("+00:00")


@pytest.mark.parametrize(
    ("reason_code", "include_digest", "resume_id"),
    [
        ("invalid_terminal", True, "fixture-story"),
        ("intake_mismatch", True, "fixture-story"),
        ("budget_stopped", False, "fixture-story"),
        ("budget_stopped", True, "different-story"),
    ],
)
def test_nonrecoverable_or_unbound_quarantine_cannot_resume(
    tmp_path, reason_code, include_digest, resume_id
):
    story = intake_story()
    entry = {
        "quarantined": reason_code.replace("_", " "),
        "reason_code": reason_code,
        "conservative_call_usd": "0.035",
        "telemetry": {"attempted": 1, "completed": 1, "failed": 0, "uncertain": 0},
    }
    if include_digest:
        entry["intake_sha256"] = intake_sha256(story)
    (tmp_path / "build_state.json").write_text(
        json.dumps({story.story_id: entry}), encoding="utf-8"
    )

    with pytest.raises(CorpusError):
        build_corpus.build(
            [story],
            RecoverableGraph(story, per_story_images=1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            resume_quarantined=resume_id,
        )
    assert load_completed_bundles(tmp_path) == []


def test_cli_reports_the_uncertain_billing_reconciliation_action(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(build_corpus, "load_intake", lambda path: [intake_story()])
    monkeypatch.setattr(
        build_corpus,
        "build",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            CorpusError("billing uncertain for fixture-story; reconcile before retry")
        ),
    )

    assert build_corpus.main(["--fixture", "--out", str(tmp_path)]) == 1
    assert "reconcile before retry" in capsys.readouterr().err


# --------------------------------------------------------------------------- the resume skip


def test_a_completed_story_is_never_resubmitted(tmp_path, stories):
    """A crash 20 stories in must not re-bill the first 20. `generate_scene`'s CC-10
    Storage-exists skip only makes a *re-executed* scene free — it does not stop the graph
    being re-entered, and `char_bible.mint_reference` has no such skip at all, so every
    canonical reference would be redrawn and paid for. The state file is the guard."""
    graph = FakeGraph(per_story_images=2)
    first = build_corpus.build(
        stories, graph, out_dir=tmp_path, supabase=FakeSupabase()
    )
    assert first["stories_run"] == 3
    assert graph.calls == ["a", "b", "c"]

    resumed = FakeGraph(per_story_images=2)
    second = build_corpus.build(
        stories, resumed, out_dir=tmp_path, supabase=FakeSupabase()
    )
    assert resumed.calls == []
    assert second["images_spent"] == 0
    assert second["stories_skipped"] == 3


# --------------------------------------------------------------------------- landing the images


def test_images_land_in_ref_and_scene_under_flattened_storage_paths(tmp_path):
    supabase = FakeSupabase()
    refs, scenes = build_corpus.download_images(_values(3, chars=2, scenes=2), tmp_path, supabase)
    assert refs == 2 and scenes == 2
    assert (tmp_path / "ref" / "story_ref-c0-1.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert (tmp_path / "scene" / "story_s1-1.png").read_bytes().startswith(b"RIFF")


def test_download_skips_a_file_already_on_disk(tmp_path):
    supabase = FakeSupabase()
    build_corpus.download_images(_values(1, chars=1, scenes=1), tmp_path, supabase)
    build_corpus.download_images(_values(1, chars=1, scenes=1), tmp_path, supabase)
    assert len(supabase.storage.downloads) == 2   # not 4


def test_download_rejects_invalid_reference_magic_bytes(tmp_path):
    class InvalidStorage(FakeStorage):
        def download(self, path):
            return b"not-an-image"

    supabase = FakeSupabase()
    supabase.storage = InvalidStorage()

    with pytest.raises(CorpusError, match="invalid image"):
        build_corpus.download_images(_values(1, chars=1), tmp_path, supabase)


# --------------------------------------------------------------------------- immutable fixture bundles


def intake_story(**changes):
    record = {
        "story_id": "fixture-story",
        "text": "A redacted fictional story.",
        "declared_characters": ["Moss"],
        "declared_non_human": ["Moss"],
        "provenance": "synthetic",
        "split": "train",
        "candidate_role": "not_applicable",
        "style_preset_id": "gouache",
    }
    record.update(changes)
    return IntakeRecord.model_validate(record)


def test_initial_state_uses_the_storys_frozen_style_preset():
    state = build_corpus._initial_state(intake_story(style_preset_id="cut_paper"))

    assert state.style.style_preset_id == "cut_paper"
    assert state.style.prompt_fragment == STYLE_PRESETS["cut_paper"]


def test_fixture_build_writes_a_complete_zero_cost_bundle_without_external_calls(tmp_path):
    graph = FakeGraph(per_story_images=4)
    supabase = FakeSupabase()

    first = build_corpus.build(
        [intake_story()], graph, out_dir=tmp_path, supabase=supabase, fixture=True
    )
    second = build_corpus.build(
        [intake_story()], graph, out_dir=tmp_path, supabase=supabase, fixture=True
    )

    [bundle] = load_completed_bundles(tmp_path)
    assert graph.calls == []
    assert supabase.storage.downloads == []
    assert bundle.memory.style.style_preset_id == "gouache"
    assert bundle.run_metadata["style_preset_id"] == "gouache"
    assert bundle.declared_characters == ["Moss"]
    assert bundle.declared_non_human == ["Moss"]
    assert {
        "code_commit",
        "schema_version",
        "text_model",
        "image_model",
        "image_edit_model",
        "judge_model",
        "moderation_primary_model",
        "moderation_primary_image_model",
        "moderation_backstop_model",
        "moderation_backstop_image_model",
        "extraction_prompt_version",
        "reference_judge_prompt_version",
        "scene_prompt_version",
        "judge_prompt_version",
        "scene_constraint_prompt_version",
        "image_budget",
        "recursion_limit",
    } <= bundle.run_metadata.keys()
    assert {asset.kind for asset in bundle.assets} == {"ref", "scene"}
    assert first["images_spent"] == second["images_spent"] == 0
    assert Decimal(first["usd_high"]) == Decimal(second["usd_high"]) == 0
    assert second["stories_skipped"] == 1
    assert bundle.run_metadata["intake_sha256"] == intake_sha256(intake_story())


def test_completed_bundle_rejects_changed_immutable_intake(tmp_path):
    story = intake_story()
    build_corpus.build(
        [story], FakeGraph(1), out_dir=tmp_path, supabase=FakeSupabase(), fixture=True
    )

    with pytest.raises(CorpusError, match="intake digest differs"):
        build_corpus.build(
            [story.model_copy(update={"text": "Changed redacted text."})],
            FakeGraph(1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            fixture=True,
        )


def test_fixture_inventory_matches_the_exact_emitted_image_bytes(tmp_path):
    build_corpus.build([intake_story()], FakeGraph(1), out_dir=tmp_path, supabase=FakeSupabase(), fixture=True)

    [bundle] = load_completed_bundles(tmp_path)
    for asset in bundle.assets:
        contents = (tmp_path / asset.local_path).read_bytes()
        with Image.open(BytesIO(contents)) as image:
            image.load()
            decoded_format = image.format
            decoded_size = image.size

        assert asset.sha256 == hashlib.sha256(contents).hexdigest()
        assert asset.byte_length == len(contents)
        assert (asset.width, asset.height) == decoded_size == (2, 2)
        if asset.kind == "ref":
            assert contents.startswith(b"\x89PNG\r\n\x1a\n")
            assert asset.mime_type == "image/png"
            assert decoded_format == "PNG"
        else:
            assert contents.startswith(b"RIFF") and contents[8:12] == b"WEBP"
            assert asset.mime_type == "image/webp"
            assert decoded_format == "WEBP"


def test_fixture_rerun_rejects_a_completed_asset_with_different_bytes(tmp_path):
    story = intake_story()
    build_corpus.build([story], FakeGraph(1), out_dir=tmp_path, supabase=FakeSupabase(), fixture=True)
    [bundle] = load_completed_bundles(tmp_path)
    asset_path = tmp_path / bundle.assets[0].local_path
    asset_path.write_bytes(b"changed")

    with pytest.raises(CorpusError, match="immutable bundle asset differs"):
        build_corpus.build([story], FakeGraph(1), out_dir=tmp_path, supabase=FakeSupabase(), fixture=True)


def test_build_quarantines_legacy_count_only_state(tmp_path):
    (tmp_path / "build_state.json").write_text('{"fixture-story": {"images": 1}}', encoding="utf-8")

    with pytest.raises(CorpusError, match="legacy build state quarantined"):
        build_corpus.build([intake_story()], FakeGraph(1), out_dir=tmp_path, supabase=FakeSupabase(), fixture=True)

    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert state["fixture-story"]["quarantined"] == "legacy count-only state; completed bundle required"


def test_build_revalidates_the_completed_graph_result(tmp_path):
    class InvalidGraph:
        def stream(self, graph_input, config, stream_mode=None):
            yield "values", {"story_id": "fixture-story"}

    with pytest.raises(CorpusError, match="invalid terminal state"):
        build_corpus.build(
            [intake_story()], InvalidGraph(), out_dir=tmp_path, supabase=FakeSupabase()
        )

    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert state["fixture-story"]["reason_code"] == "invalid_terminal"
    assert load_completed_bundles(tmp_path) == []


def test_build_quarantines_a_declared_roster_that_does_not_match_completion(tmp_path):
    with pytest.raises(CorpusError, match="declared roster"):
        build_corpus.build(
            [intake_story(declared_characters=["Moss"], declared_non_human=["Moss"])],
            FakeGraph(per_story_images=1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
        )


def test_build_quarantines_a_completion_with_duplicate_character_names(tmp_path):
    class DuplicateCharacterGraph:
        def stream(self, graph_input, config, stream_mode=None):
            values = graph_input.model_dump()
            values.update(
                cost=Cost(image_count=1),
                characters=[
                    Character(char_id="c1", name="Moss", canonical_ref_image="fixture-story/ref-c1.png"),
                    Character(char_id="c2", name="Moss", canonical_ref_image="fixture-story/ref-c2.png"),
                ],
            )
            yield "values", values

    with pytest.raises(CorpusError, match="declared roster"):
        build_corpus.build(
            [intake_story(declared_non_human=[])],
            DuplicateCharacterGraph(),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
        )


def test_build_quarantines_a_completion_with_extra_non_human_occurrences(tmp_path):
    class DuplicateNonHumanGraph:
        def stream(self, graph_input, config, stream_mode=None):
            values = graph_input.model_dump()
            values.update(
                cost=Cost(image_count=1),
                characters=[
                    Character(
                        char_id="c1",
                        name="Moss",
                        description={"is_humanoid": False},
                        canonical_ref_image="fixture-story/ref-c1.png",
                    ),
                    Character(
                        char_id="c2",
                        name="Moss",
                        description={"is_humanoid": False},
                        canonical_ref_image="fixture-story/ref-c2.png",
                    ),
                ],
            )
            yield "values", values

    with pytest.raises(CorpusError, match="declared roster"):
        build_corpus.build(
            [intake_story(declared_characters=["Moss", "Moss"], declared_non_human=["Moss"])],
            DuplicateNonHumanGraph(),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
        )


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--fixture", "--price-per-megapixel", "0.03"],
        ["--fixture", "--resume-quarantined", "fixture-story"],
        ["--acknowledge-uncertain-billing", "fixture-story"],
        [
            "--resume-quarantined",
            "fixture-story",
            "--acknowledge-uncertain-billing",
            "different-story",
        ],
    ],
)
def test_cli_rejects_unsafe_recovery_combinations(argv):
    with pytest.raises(SystemExit):
        build_corpus.main(argv)

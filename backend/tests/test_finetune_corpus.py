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
import pathlib
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from PIL import Image

from app.config import IMAGE_BUDGET, MAX_STORY_WORDS, MIN_STORY_WORDS, STYLE_PRESETS
from app.length import clamp_story, word_count
from contracts.story_memory import (
    Character,
    Cost,
    Location,
    RefVerdict,
    Scene,
    StoryMemory,
    StoryObject,
    TimelineEvent,
)
from finetune import build_corpus
from finetune.corpus_io import (
    CorpusError,
    IntakeRecord,
    intake_sha256,
    load_completed_bundles,
    reconcile_declared_roster,
)


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
        # A checkpoint stored under a thread always carries that thread as its `story_id` --
        # `_validated_checkpoint` rejects any other pairing -- and since threads became
        # campaign-scoped the bare story id is no longer the thread anything runs on.
        execution_story = self.story.model_copy(
            update={"story_id": config["configurable"]["thread_id"]}
        )
        return SimpleNamespace(values=build_corpus._initial_state(execution_story).model_dump())

    def stream(self, graph_input, config, stream_mode=None):
        graph_input = graph_input or build_corpus._initial_state(self.story)
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


class IsolatedRecoverableGraph(RecoverableGraph):
    def get_state(self, config):
        execution_story = self.story.model_copy(
            update={"story_id": config["configurable"]["thread_id"]}
        )
        return SimpleNamespace(values=build_corpus._initial_state(execution_story).model_dump())


def isolated_quarantine(story, reason_code="budget_stopped"):
    return {
        "quarantined": reason_code.replace("_", " "),
        "reason_code": reason_code,
        "intake_sha256": intake_sha256(story),
        "conservative_call_usd": "0.035",
        "max_calls_per_story": 20,
        "telemetry": {"attempted": 34, "completed": 33, "failed": 0, "uncertain": 1},
        "execution_id": f"{story.story_id}--restart-{'a' * 32}",
        "abandoned_execution_id": story.story_id,
        "restart_attempted_baseline": 14,
        "restarted_at": "2026-08-26T00:00:00+00:00",
    }


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
    policy = build_corpus.SpendPolicy(
        max_usd=Decimal("0.03"),
        price_per_megapixel=Decimal("0.03"),
        price_basis="https://fal.ai/models/example checked 2026-08-25",
    )

    summary = build_corpus.build(
        stories[:1], FakeGraph(1), out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )
    [bundle] = load_completed_bundles(tmp_path)

    expected = {
        "image_size": "1024x768",
        "maximum_megapixels": "0.786432",
        "billable_megapixels": 1,
        "price_per_megapixel": "0.03",
        "price_basis": "https://fal.ai/models/example checked 2026-08-25",
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
    assert graph.calls == [build_corpus._campaign_thread_id("a", tmp_path)]
    assert graph.consumed == 14
    assert summary["images_spent"] == 14
    assert Decimal(summary["usd_high"]) == Decimal("0.490")
    assert state["a"]["reason_code"] == "budget_stopped"


def test_campaign_hard_cap_is_unconditionally_thirty_dollars():
    assert build_corpus.SpendPolicy(max_usd=Decimal("31.00")).authorized_usd == Decimal("30.00")


def test_explicit_story_call_cap_overrides_the_smoke_budget_boundary():
    policy = build_corpus.SpendPolicy(
        max_usd=Decimal("2.59"),
        max_calls_per_story=20,
    )

    assert policy.story_draw_limit(3) == 20
    with pytest.raises(ValueError, match="max_calls_per_story"):
        build_corpus.SpendPolicy(max_calls_per_story=0)
    with pytest.raises(ValueError, match="max_calls_per_story"):
        build_corpus.SpendPolicy(max_calls_per_story=IMAGE_BUDGET + 1)


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


def test_run_story_continues_an_ordinary_checkpoint_without_overwriting_its_channels():
    story = intake_story()
    checkpointed = build_corpus._initial_state(story).model_copy(
        update={
            "characters": [
                Character(char_id="c1", name="Moss", description={"is_humanoid": False})
            ],
            "locations": [Location(loc_id="l1", name="Garden")],
            "objects": [StoryObject(obj_id="o1", name="Lantern")],
            "timeline": [TimelineEvent(order=1, summary="Moss finds the lantern")],
            "scenes": [Scene(scene_id="s1", text_excerpt="Moss finds the lantern.")],
            "cost": Cost(image_count=1),
        }
    )
    resumed = []

    def reveal(state):
        interrupt("confirm")
        resumed.append(state.story_id)
        return {}

    builder = StateGraph(build_corpus.StoryMemory)
    builder.add_node("reveal", reveal)
    builder.add_edge(START, "reveal")
    builder.add_edge("reveal", END)
    graph = builder.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": story.story_id}}
    list(graph.stream(checkpointed, config, stream_mode=["updates", "values"]))

    run = build_corpus.run_story(graph, story)
    memory = build_corpus.StoryMemory.model_validate(run.values)

    assert run.outcome == "completed"
    assert resumed == [story.story_id]
    assert memory.characters == checkpointed.characters
    assert memory.locations == checkpointed.locations
    assert memory.objects == checkpointed.objects
    assert memory.timeline == checkpointed.timeline
    assert memory.scenes == checkpointed.scenes
    assert memory.cost == checkpointed.cost


@pytest.mark.parametrize("prior_terminal", ["completed", "failed", "uncertain"])
def test_recovery_reserves_only_draws_not_already_attempted(tmp_path, prior_terminal):
    story = intake_story()
    policy = build_corpus.SpendPolicy(max_usd=Decimal("0.06"), price_per_megapixel=Decimal("0.03"))
    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.03",
            "telemetry": {"attempted": 1, "completed": 0, "failed": 0, "uncertain": 0},
        }
    }
    state[story.story_id]["telemetry"][prior_terminal] = 1
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")

    summary = build_corpus.build(
        [story],
        RecoverableGraph(story, per_story_images=1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=policy,
        resume_quarantined=story.story_id,
    )
    [bundle] = load_completed_bundles(tmp_path)

    assert summary["stories_run"] == 1
    assert Decimal(summary["usd_high"]) == Decimal("0.06")
    assert bundle.run_metadata["attempted_calls"] == 2
    assert bundle.run_metadata[f"{prior_terminal}_calls"] == {
        "completed": 2,
        "failed": 1,
        "uncertain": 1,
    }[prior_terminal]


def test_recovery_blocks_another_provider_attempt_at_the_prior_draw_limit(tmp_path):
    story = intake_story()
    policy = build_corpus.SpendPolicy(max_usd=Decimal("0.06"), price_per_megapixel=Decimal("0.03"))
    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.03",
            "telemetry": {"attempted": 2, "completed": 1, "failed": 1, "uncertain": 0},
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = RecoverableGraph(story, per_story_images=1)

    summary = build_corpus.build(
        [story],
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=policy,
        resume_quarantined=story.story_id,
    )
    saved = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert summary["halted"] is True
    assert graph.consumed == 0
    assert saved[story.story_id]["telemetry"] == state[story.story_id]["telemetry"]


def test_isolated_restart_preserves_prior_spend_and_uses_fresh_checkpoint_and_asset_identity(
    tmp_path,
):
    story = intake_story()
    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "telemetry": {"attempted": 14, "completed": 13, "failed": 0, "uncertain": 1},
            "billing_acknowledged_at": "2026-08-25T20:10:26+00:00",
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")

    class IsolatedGraph:
        def __init__(self):
            self.thread_ids = []
            self.input_story_ids = []

        def get_state(self, config):
            self.thread_ids.append(config["configurable"]["thread_id"])
            return SimpleNamespace(values={})

        def stream(self, graph_input, config, stream_mode=None):
            execution_id = graph_input.story_id
            self.input_story_ids.append(execution_id)
            sink = build_corpus._fal_event_sink.get()
            sink("attempted")
            sink("completed")
            values = graph_input.model_dump()
            values.update(
                cost=Cost(image_count=1),
                characters=[
                    Character(
                        char_id="c0",
                        name="Moss",
                        description={"is_humanoid": False},
                        canonical_ref_image=f"{execution_id}/ref-c0-1.png",
                    )
                ],
            )
            yield "values", values

    graph = IsolatedGraph()
    build_corpus.build(
        [story],
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("2.59"), max_calls_per_story=20),
        restart_quarantined=story.story_id,
    )
    [bundle] = load_completed_bundles(tmp_path)

    execution_id = graph.input_story_ids[0]
    assert execution_id.startswith(f"{story.story_id}--restart-")
    assert execution_id != story.story_id
    assert graph.thread_ids == [execution_id]
    assert bundle.memory.story_id == story.story_id
    assert bundle.assets[0].storage_path.startswith(f"{execution_id}/")
    assert bundle.run_metadata["attempted_calls"] == 15
    assert bundle.run_metadata["uncertain_calls"] == 1
    assert bundle.run_metadata["execution_id"] == execution_id
    assert bundle.run_metadata["abandoned_execution_id"] == build_corpus._campaign_thread_id(
        story.story_id, tmp_path
    )
    assert bundle.run_metadata["restart_attempted_baseline"] == 14
    assert bundle.run_metadata["max_calls_per_story"] == 20


def test_isolated_restart_call_cap_counts_new_execution_calls_not_abandoned_calls(tmp_path):
    story = intake_story(declared_characters=["c0"], declared_non_human=[])
    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "telemetry": {"attempted": 14, "completed": 13, "failed": 0, "uncertain": 1},
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = FakeGraph(per_story_images=21)

    summary = build_corpus.build(
        [story],
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("30.00"), max_calls_per_story=20),
        restart_quarantined=story.story_id,
    )
    saved = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert graph.consumed == 20
    assert summary["halted"] is True
    assert saved[story.story_id]["telemetry"]["attempted"] == 34
    assert saved[story.story_id]["restart_attempted_baseline"] == 14
    assert saved[story.story_id]["reason_code"] == "budget_stopped"


def test_budget_stopped_isolated_execution_can_extend_its_cap_once(tmp_path):
    story = intake_story()
    state = {story.story_id: isolated_quarantine(story)}
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")

    class ExtendedGraph(RecoverableGraph):
        def get_state(self, config):
            self.checked_thread_id = config["configurable"]["thread_id"]
            execution_story = self.story.model_copy(
                update={"story_id": state[story.story_id]["execution_id"]}
            )
            return SimpleNamespace(values=build_corpus._initial_state(execution_story).model_dump())

    graph = ExtendedGraph(story, per_story_images=1)
    build_corpus.build(
        [story],
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("3.12"), max_calls_per_story=25),
        resume_quarantined=story.story_id,
        extend_story_call_cap=story.story_id,
    )
    [bundle] = load_completed_bundles(tmp_path)

    assert graph.checked_thread_id == state[story.story_id]["execution_id"]
    assert graph.calls == [state[story.story_id]["execution_id"]]
    assert bundle.run_metadata["initial_max_calls_per_story"] == 20
    assert bundle.run_metadata["max_calls_per_story"] == 25
    assert bundle.run_metadata["attempted_calls"] == 35
    assert bundle.run_metadata["cap_extended_at"].endswith("+00:00")


def test_extended_cap_allows_only_five_more_calls_before_submission(tmp_path):
    story = intake_story()
    state = {story.story_id: isolated_quarantine(story)}
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = IsolatedRecoverableGraph(story, per_story_images=6)

    summary = build_corpus.build(
        [story],
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("3.12"), max_calls_per_story=25),
        resume_quarantined=story.story_id,
        extend_story_call_cap=story.story_id,
    )
    saved = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert graph.consumed == 5
    assert summary["halted"] is True
    assert saved[story.story_id]["telemetry"]["attempted"] == 39
    assert saved[story.story_id]["max_calls_per_story"] == 25
    assert saved[story.story_id]["initial_max_calls_per_story"] == 20


def test_call_cap_extension_requires_more_budget_before_it_is_persisted(tmp_path):
    story = intake_story()
    state = {story.story_id: isolated_quarantine(story)}
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")

    summary = build_corpus.build(
        [story],
        IsolatedRecoverableGraph(story, per_story_images=1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("1.20"), max_calls_per_story=25),
        resume_quarantined=story.story_id,
        extend_story_call_cap=story.story_id,
    )
    saved = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert summary["halted"] is True
    assert saved == state


def test_call_cap_extension_requires_an_existing_isolated_quarantine(tmp_path):
    story = intake_story()
    graph = RecoverableGraph(story, per_story_images=1)

    with pytest.raises(CorpusError, match="existing isolated quarantine"):
        build_corpus.build(
            [story],
            graph,
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("3.12"), max_calls_per_story=25),
            resume_quarantined=story.story_id,
            extend_story_call_cap=story.story_id,
        )
    assert graph.calls == []


@pytest.mark.parametrize(
    ("reason_code", "new_cap", "resume_id", "match"),
    [
        ("budget_stopped", 20, "fixture-story", "must increase"),
        ("billing_uncertain", 25, "fixture-story", "requires budget_stopped"),
        ("budget_stopped", 25, "different-story", "matching resume"),
    ],
)
def test_call_cap_extension_rejects_unsafe_requests(
    tmp_path, reason_code, new_cap, resume_id, match
):
    story = intake_story()
    state = {story.story_id: isolated_quarantine(story, reason_code)}
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = RecoverableGraph(story, per_story_images=1)

    with pytest.raises(CorpusError, match=match):
        build_corpus.build(
            [story],
            graph,
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(
                max_usd=Decimal("3.12"), max_calls_per_story=new_cap
            ),
            resume_quarantined=resume_id,
            extend_story_call_cap=story.story_id,
        )
    assert graph.calls == []


def test_isolated_restart_requires_existing_quarantine_and_explicit_call_cap(tmp_path):
    story = intake_story()

    with pytest.raises(CorpusError, match="existing quarantine"):
        build_corpus.build(
            [story],
            FakeGraph(1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("2.59"), max_calls_per_story=20),
            restart_quarantined=story.story_id,
        )

    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "telemetry": {"attempted": 14, "completed": 13, "failed": 0, "uncertain": 1},
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(CorpusError, match="explicit max_calls_per_story"):
        build_corpus.build(
            [story],
            FakeGraph(1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("2.59")),
            restart_quarantined=story.story_id,
        )


def test_resume_after_isolated_restart_reuses_its_execution_checkpoint(tmp_path):
    story = intake_story()
    execution_id = f"{story.story_id}--restart-{'a' * 32}"
    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "max_calls_per_story": 20,
            "telemetry": {"attempted": 15, "completed": 14, "failed": 0, "uncertain": 1},
            "execution_id": execution_id,
            "abandoned_execution_id": story.story_id,
            "restart_attempted_baseline": 14,
            "restarted_at": "2026-08-26T00:00:00+00:00",
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")

    class ResumedIsolatedGraph(RecoverableGraph):
        def get_state(self, config):
            self.checked_thread_id = config["configurable"]["thread_id"]
            execution_story = self.story.model_copy(update={"story_id": execution_id})
            return SimpleNamespace(values=build_corpus._initial_state(execution_story).model_dump())

    graph = ResumedIsolatedGraph(story, per_story_images=1)
    build_corpus.build(
        [story],
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("2.59"), max_calls_per_story=20),
        resume_quarantined=story.story_id,
    )

    assert graph.checked_thread_id == execution_id
    assert graph.calls == [execution_id]


@pytest.mark.parametrize("resumed_cap", [None, 21])
def test_resume_after_isolated_restart_rejects_call_cap_drift(tmp_path, resumed_cap):
    story = intake_story()
    execution_id = f"{story.story_id}--restart-{'a' * 32}"
    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "max_calls_per_story": 20,
            "telemetry": {"attempted": 15, "completed": 14, "failed": 0, "uncertain": 1},
            "execution_id": execution_id,
            "abandoned_execution_id": story.story_id,
            "restart_attempted_baseline": 14,
            "restarted_at": "2026-08-26T00:00:00+00:00",
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = RecoverableGraph(story, per_story_images=1)

    with pytest.raises(CorpusError, match="max_calls_per_story differs"):
        build_corpus.build(
            [story],
            graph,
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(
                max_usd=Decimal("2.59"), max_calls_per_story=resumed_cap
            ),
            resume_quarantined=story.story_id,
        )
    assert graph.calls == []


def test_isolated_restart_without_a_first_checkpoint_can_retry_the_same_identity(tmp_path):
    story = intake_story()
    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "telemetry": {"attempted": 14, "completed": 13, "failed": 0, "uncertain": 1},
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    first = build_corpus.build(
        [story],
        FakeGraph(1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("0.50"), max_calls_per_story=20),
        restart_quarantined=story.story_id,
    )
    restart_state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))[
        story.story_id
    ]

    class FreshRestartGraph:
        def __init__(self):
            self.thread_ids = []

        def get_state(self, config):
            self.thread_ids.append(config["configurable"]["thread_id"])
            return SimpleNamespace(values={})

        def stream(self, graph_input, config, stream_mode=None):
            sink = build_corpus._fal_event_sink.get()
            sink("attempted")
            sink("completed")
            values = graph_input.model_dump()
            values.update(
                cost=Cost(image_count=1),
                characters=[
                    Character(
                        char_id="c0",
                        name="Moss",
                        description={"is_humanoid": False},
                        canonical_ref_image=f"{graph_input.story_id}/ref-c0-1.png",
                    )
                ],
            )
            yield "values", values

    graph = FreshRestartGraph()
    second = build_corpus.build(
        [story],
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("2.59"), max_calls_per_story=20),
    )

    assert first["halted"] is True
    assert second["stories_run"] == 1
    assert graph.thread_ids == [restart_state["execution_id"], restart_state["execution_id"]]


def test_prior_uncertain_call_does_not_reclassify_a_later_known_failure(tmp_path):
    story = intake_story()
    execution_id = f"{story.story_id}--restart-{'a' * 32}"
    state = {
        story.story_id: {
            "in_progress": True,
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "max_calls_per_story": 20,
            "telemetry": {"attempted": 15, "completed": 14, "failed": 0, "uncertain": 1},
            "execution_id": execution_id,
            "abandoned_execution_id": story.story_id,
            "restart_attempted_baseline": 14,
            "restarted_at": "2026-08-26T00:00:00+00:00",
        }
    }
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")

    class KnownFailureGraph:
        def get_state(self, config):
            execution_story = story.model_copy(update={"story_id": execution_id})
            return SimpleNamespace(values=build_corpus._initial_state(execution_story).model_dump())

        def stream(self, graph_input, config, stream_mode=None):
            raise RuntimeError("known local failure")
            yield

    with pytest.raises(RuntimeError, match="known local failure"):
        build_corpus.build(
            [story],
            KnownFailureGraph(),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("2.59"), max_calls_per_story=20),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"execution_id": "../shared-prefix"},
        {"execution_id": "fixture-story--restart-fixed"},
        {"abandoned_execution_id": "another-story"},
        {"restarted_at": "not-a-timestamp"},
        {"restarted_at": "2026-08-26T00:00:00"},
    ],
)
def test_resume_rejects_an_unsafe_persisted_execution_identity(tmp_path, changes):
    story = intake_story()
    execution_id = f"{story.story_id}--restart-{'a' * 32}"
    state = {
        story.story_id: {
            "quarantined": "budget stopped",
            "reason_code": "budget_stopped",
            "intake_sha256": intake_sha256(story),
            "conservative_call_usd": "0.035",
            "max_calls_per_story": 20,
            "telemetry": {"attempted": 15, "completed": 14, "failed": 0, "uncertain": 1},
            "execution_id": execution_id,
            "abandoned_execution_id": story.story_id,
            "restart_attempted_baseline": 14,
            "restarted_at": "2026-08-26T00:00:00+00:00",
        }
    }
    state[story.story_id].update(changes)
    (tmp_path / "build_state.json").write_text(json.dumps(state), encoding="utf-8")
    graph = RecoverableGraph(story, per_story_images=1)

    with pytest.raises(CorpusError, match="invalid persisted execution identity"):
        build_corpus.build(
            [story],
            graph,
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("2.59"), max_calls_per_story=20),
            resume_quarantined=story.story_id,
        )
    assert graph.calls == []


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
    assert resumed_graph.calls == [build_corpus._campaign_thread_id("a", tmp_path)]
    assert summary["halted"] is False
    assert Decimal(summary["usd_high"]) == Decimal("0.070")


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
    ],
)
def test_invalid_quarantine_cannot_resume(
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
    assert graph.calls == [build_corpus._campaign_thread_id(s, tmp_path) for s in "abc"]

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


def test_code_commit_marks_a_dirty_working_tree():
    """A bare `git rev-parse HEAD` names code that may never have existed: an uncommitted edit
    ships under the last commit's id, and every number reported from that bundle traces to the
    wrong source. The suffix also makes the bundle unfreezable, since `freeze_dataset` requires
    every bundle to agree on `code_commit`."""
    def fake_run(cmd, **kwargs):
        out = "abc123\n" if cmd[1] == "rev-parse" else " M backend/pipeline/segment.py\n"
        return SimpleNamespace(stdout=out, stderr="", returncode=0)

    with patch("finetune.build_corpus.subprocess.run", side_effect=fake_run):
        assert build_corpus._code_commit() == "abc123-dirty"


def test_code_commit_is_bare_when_the_tree_is_clean():
    def fake_run(cmd, **kwargs):
        stdout = "abc123\n" if cmd[1] == "rev-parse" else ""
        return SimpleNamespace(stdout=stdout, stderr="", returncode=0)

    with patch("finetune.build_corpus.subprocess.run", side_effect=fake_run):
        assert build_corpus._code_commit() == "abc123"


def test_unchecked_references_counts_a_reference_that_shipped_without_a_verdict():
    """ADR-050 Decision 4. `ref_verdict: null` is reachable through exactly one path — the judge
    raised and `char_bible` accepted the draw unchecked — and on 2026-09-02 BOTH of `syn-001`'s
    references took it. The bundle recorded `ref_retry_count: 0`, which reads as "clean on draw
    one", and the defect was only found by opening PNGs by hand. A character with no reference at
    all (ADR-048 skips it) was never gated and is not a dropped check."""
    memory = StoryMemory(
        schema_version=1,
        story_id="s",
        profile_id="p",
        classroom_id="c",
        input={"raw_text": "a story"},
        characters=[
            Character(char_id="c0", name="Judged", canonical_ref_image="s/ref-c0-1.png",
                      ref_verdict=RefVerdict(differences_observed="", matches_description=True)),
            Character(char_id="c1", name="Unchecked", canonical_ref_image="s/ref-c1-1.png"),
            Character(char_id="c2", name="Unreferenced"),
        ],
    )

    assert build_corpus._unchecked_references(memory) == 1


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
        "segment_prompt_version",   # ADR-054 D2
        "image_budget",
        "recursion_limit",
        "unchecked_references",   # ADR-050 Decision 4
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
    summary = build_corpus.build(
        [intake_story(declared_characters=["Moss"], declared_non_human=["Moss"])],
        FakeGraph(per_story_images=1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
    )
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert summary["quarantined_story_ids"] == ["fixture-story"]
    assert state["fixture-story"]["reason_code"] == "invalid_terminal"
    assert "declared roster" in state["fixture-story"]["quarantined"]


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

    summary = build_corpus.build(
        [intake_story(declared_non_human=[])],
        DuplicateCharacterGraph(),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
    )
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert summary["quarantined_story_ids"] == ["fixture-story"]
    assert state["fixture-story"]["reason_code"] == "invalid_terminal"
    assert "declared roster" in state["fixture-story"]["quarantined"]


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

    summary = build_corpus.build(
        [intake_story(declared_characters=["Moss", "Moss"], declared_non_human=["Moss"])],
        DuplicateNonHumanGraph(),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
    )
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert summary["quarantined_story_ids"] == ["fixture-story"]
    assert state["fixture-story"]["reason_code"] == "invalid_terminal"
    assert "declared roster" in state["fixture-story"]["quarantined"]


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--price-per-megapixel", "0.03"],
        ["--fixture", "--price-per-megapixel", "0.03"],
        ["--fixture", "--price-basis", "official price checked today"],
        ["--fixture", "--resume-quarantined", "fixture-story"],
        ["--fixture", "--max-calls-per-story", "20"],
        ["--fixture", "--extend-story-call-cap", "fixture-story"],
        [
            "--max-usd",
            "2.59",
            "--price-per-megapixel",
            "0.035",
            "--price-basis",
            "checked",
            "--resume-quarantined",
            "fixture-story",
            "--restart-quarantined",
            "fixture-story",
        ],
        [
            "--max-usd",
            "2.59",
            "--price-per-megapixel",
            "0.035",
            "--price-basis",
            "checked",
            "--max-calls-per-story",
            "0",
        ],
        ["--acknowledge-uncertain-billing", "fixture-story"],
        [
            "--max-usd",
            "3.12",
            "--price-per-megapixel",
            "0.035",
            "--price-basis",
            "checked",
            "--resume-quarantined",
            "fixture-story",
            "--extend-story-call-cap",
            "different-story",
        ],
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


def test_run_story_quarantines_a_roster_mismatch_before_the_next_image():
    """A declared-roster mismatch is knowable from `analyze` alone, so it must cost one text
    call and not a whole story's image spend (syn-001 burned $1.33 discovering it at packaging)."""
    graph = FakeGraph(per_story_images=4)
    story = intake_story(declared_characters=["Moss"], declared_non_human=["Moss"])

    with pytest.raises(CorpusError, match="declared roster"):
        build_corpus.run_story(graph, story)

    assert graph.consumed == 1


def _memory_with(names_and_humanoid):
    return build_corpus.StoryMemory.model_validate(
        build_corpus._initial_state(intake_story()).model_copy(
            update={
                "characters": [
                    Character(
                        char_id=f"c{i}",
                        name=name,
                        description={"is_humanoid": humanoid},
                    )
                    for i, (name, humanoid) in enumerate(names_and_humanoid)
                ]
            }
        ).model_dump()
    )


def test_reconcile_tolerates_a_secondary_actor_the_declaration_did_not_list():
    """Whether a bit player has agency is a judgement the author and the model can legitimately
    read differently (`the goat`, `the family`). Equality made every such disagreement quarantine
    the story; only losing a declared character is a pipeline defect."""
    reconcile_declared_roster(["Moss"], ["Moss"], _memory_with([("Moss", False), ("the heron", False)]))


def test_reconcile_rejects_a_declared_character_pushed_out_of_the_reference_slice():
    """`char_bible` mints references for `characters[:2]` only, so a declared character ranked
    third silently loses its canonical reference — the corpus would measure consistency against
    an anchor that was never drawn."""
    with pytest.raises(CorpusError, match="declared roster"):
        reconcile_declared_roster(
            ["Moss"],
            ["Moss"],
            _memory_with([("the heron", False), ("the crow", False), ("Moss", False)]),
        )


def test_reconcile_still_rejects_a_differently_classified_declared_character():
    with pytest.raises(CorpusError, match="declared roster"):
        reconcile_declared_roster(["Moss"], [], _memory_with([("Moss", False)]))


def test_reconcile_rejects_an_empty_declared_roster():
    """An empty declaration passes vacuously against any roster, so a typo that empties the
    list silently disables the gate for that story."""
    with pytest.raises(CorpusError, match="declared roster is empty"):
        reconcile_declared_roster([], [], _memory_with([("Moss", False)]))


def test_reconcile_tolerates_whitespace_padded_declared_names():
    """Intake names are author-typed; a trailing space is not a roster defect."""
    reconcile_declared_roster([" Moss "], [" Moss "], _memory_with([("Moss", False)]))


def test_reconcile_failure_names_the_check_and_both_rosters():
    """The message is what lands in the quarantine record, so a failure must be diagnosable
    without re-running the graph."""
    with pytest.raises(CorpusError) as missing:
        reconcile_declared_roster(
            ["Moss"], ["Moss"], _memory_with([("the heron", False), ("the crow", False)])
        )
    assert "not in the reference slice" in str(missing.value)
    assert "declared=['Moss']" in str(missing.value)
    assert "the heron" in str(missing.value) and "the crow" in str(missing.value)

    with pytest.raises(CorpusError) as classified:
        reconcile_declared_roster(["Moss"], [], _memory_with([("Moss", False)]))
    assert "is_humanoid" in str(classified.value)
    assert "extracted=" in str(classified.value)

    with pytest.raises(CorpusError) as duplicate:
        reconcile_declared_roster(
            ["Moss"], ["Moss"], _memory_with([("Moss", False), ("Moss", False)])
        )
    assert "duplicate" in str(duplicate.value)
    assert "extracted=" in str(duplicate.value)


def _extracted(name: str, humanoid: bool = True) -> dict:
    return {
        "name": name,
        "description": {
            "species": "girl" if humanoid else "toad",
            "body_plan": "small upright body with two arms and two legs",
            "face_or_interface": "round face with two bright eyes",
            "is_humanoid": humanoid,
            "colours": ["warm brown skin"],
            "body_features": ["round face"],
            "clothing": ["yellow shirt"] if humanoid else [],
        },
    }


def _analysis_of(*names_and_humanoid):
    from pipeline.analyze import StoryAnalysis

    return StoryAnalysis.model_validate(
        {
            "characters": [_extracted(n, h) for n, h in names_and_humanoid],
            "locations": [{"name": "the pond", "description": "a shallow green pond in a valley"}],
            "objects": [{"name": "a flat rock", "materials": ["stone"], "colours": ["grey"], "form_features": ["wide flat slab"], "owner_name": None}],
            "timeline": [{"order": 0, "summary": "Something happens."}],
        }
    )


def test_check_rosters_passes_a_declaration_the_extraction_covers(tmp_path):
    story = intake_story(declared_characters=["Moss"], declared_non_human=["Moss"])

    with patch(
        "pipeline.analyze.extract_entities",
        return_value=_analysis_of(("Moss", False), ("the heron", False)),
    ):
        summary = build_corpus.check_rosters([story])

    assert summary["failures"] == []
    assert summary["checked"] == 1


def test_check_rosters_reports_a_lost_declared_character_without_any_image_call(tmp_path):
    """The pre-flight must reach the same verdict as a paid run, for one text call."""
    story = intake_story(declared_characters=["Moss"], declared_non_human=["Moss"])

    with patch(
        "pipeline.analyze.extract_entities",
        return_value=_analysis_of(("the heron", False), ("the crow", False)),
    ):
        summary = build_corpus.check_rosters([story])

    assert summary["checked"] == 1
    assert [f["story_id"] for f in summary["failures"]] == ["fixture-story"]
    assert "declared roster does not reconcile" in summary["failures"][0]["error"]


def test_readmit_clears_an_invalid_terminal_quarantine_into_a_fresh_isolated_execution(tmp_path):
    """An invalid_terminal verdict rendered by a defect that has since been fixed must be
    re-adjudicable without erasing the record of calls that were really paid for."""
    story = intake_story(declared_characters=["c0"], declared_non_human=[])
    entry = isolated_quarantine(story, reason_code="invalid_terminal")
    (tmp_path / "build_state.json").write_text(json.dumps({story.story_id: entry}), encoding="utf-8")
    graph = FakeGraph(per_story_images=2)

    build_corpus.build(
        [story],
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("30.00"), max_calls_per_story=20),
        readmit_quarantined=story.story_id,
        readmit_reason="cause fixed in 4f5fe44",
    )
    # the readmission is recorded in the immutable bundle, not left only in mutable build state
    metadata = load_completed_bundles(tmp_path)[0].run_metadata

    assert metadata["readmit_reason"] == "cause fixed in 4f5fe44"
    assert "readmitted_at" in metadata
    # the paid-call record survives the readmission rather than being reset
    assert metadata["attempted_calls"] == 34 + graph.consumed
    assert metadata["restart_attempted_baseline"] == 34
    assert metadata["abandoned_execution_id"] == entry["execution_id"]
    assert metadata["execution_id"].startswith(f"{story.story_id}--readmit-")


def test_readmit_refuses_a_quarantine_that_is_not_invalid_terminal(tmp_path):
    story = intake_story(declared_characters=["c0"], declared_non_human=[])
    (tmp_path / "build_state.json").write_text(
        json.dumps({story.story_id: isolated_quarantine(story)}), encoding="utf-8"
    )

    with pytest.raises(CorpusError, match="readmission requires invalid_terminal"):
        build_corpus.build(
            [story],
            FakeGraph(per_story_images=2),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("30.00"), max_calls_per_story=20),
            readmit_quarantined=story.story_id,
            readmit_reason="not applicable",
        )


def test_readmit_refuses_when_the_intake_digest_differs(tmp_path):
    story = intake_story(declared_characters=["c0"], declared_non_human=[])
    entry = isolated_quarantine(story, reason_code="invalid_terminal")
    entry["intake_sha256"] = "0" * 64
    (tmp_path / "build_state.json").write_text(json.dumps({story.story_id: entry}), encoding="utf-8")

    with pytest.raises(CorpusError, match="intake digest differs"):
        build_corpus.build(
            [story],
            FakeGraph(per_story_images=2),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("30.00"), max_calls_per_story=20),
            readmit_quarantined=story.story_id,
            readmit_reason="cause fixed",
        )


def test_initial_state_marks_synthetic_text_exempt_from_pseudonymization(tmp_path):
    """`input_gate` renamed the declared cast of 16 of the 30 synthetic records.

    Every node after the gate consumes `redacted_text`, so those stories would have been drawn,
    bundled and labelled under pool pseudonyms while `declared_characters` still named the
    author's cast -- scrambling the character identity the corpus is keyed on.
    """
    synthetic = intake_story(declared_characters=["c0"], declared_non_human=[])
    assert synthetic.provenance == "synthetic"
    assert build_corpus._initial_state(synthetic).input.synthetic_no_pii is True


def test_check_rosters_analyzes_the_same_text_the_paid_run_will_analyze(tmp_path):
    """The pre-flight used to read raw text while the graph always reads redacted text.

    That is why it reported 30 of 30 passing and the very next paid run failed to reconcile: the
    two were never looking at the same bytes. A gate that analyzes different input than the run
    it predicts is not a gate.
    """
    donated = donated_intake_story(declared_characters=["c0"], declared_non_human=[])
    seen: list[str] = []

    def fake_analyze(state):
        seen.append(state.input.redacted_text or state.input.raw_text)
        return {"characters": _extracted(["c0"], [False])}

    with patch.object(build_corpus, "redact_pii") as mock_redact, \
         patch.object(build_corpus, "analyze", side_effect=fake_analyze):
        build_corpus.check_rosters([donated])

    # Both sides now read the intake text verbatim: donated records are hand-redacted before
    # intake, so neither the pre-flight nor the graph runs the pseudonymizer over them.
    mock_redact.assert_not_called()
    assert seen == [donated.text]


def test_readmit_refuses_a_second_readmission_of_the_same_story(tmp_path):
    """Readmission grants a fresh full draw allowance, so an unbounded one is an unbounded spend.

    It also keeps a single `readmit_reason` slot, so a second override erases the justification
    for the first -- and the story never completed, so no bundle preserves it either.
    """
    story = intake_story(declared_characters=["c0"], declared_non_human=[])
    entry = isolated_quarantine(story, reason_code="invalid_terminal")
    entry["readmitted_at"] = "2026-08-26T00:00:00+00:00"
    entry["readmit_reason"] = "the first override"
    (tmp_path / "build_state.json").write_text(json.dumps({story.story_id: entry}), encoding="utf-8")

    with pytest.raises(build_corpus.CorpusError, match="already readmitted"):
        build_corpus.build(
            [story],
            FakeGraph(per_story_images=2),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("30.00"), max_calls_per_story=20),
            readmit_quarantined=story.story_id,
            readmit_reason="the second override",
        )


def test_readmit_requires_an_explicit_call_cap(tmp_path):
    """Readmitting without a cap wrote an `execution_id` that armed `_validate_restart_cap`.

    That guard runs ahead of every recovery branch, so the next invocation was refused for a cap
    mismatch while `--restart-quarantined` refused it for being `in_progress` rather than
    quarantined. No flag combination could recover it short of hand-editing the audit ledger.
    """
    story = intake_story(declared_characters=["c0"], declared_non_human=[])
    entry = isolated_quarantine(story, reason_code="invalid_terminal")
    del entry["max_calls_per_story"]
    del entry["execution_id"]
    del entry["abandoned_execution_id"]
    del entry["restarted_at"]
    (tmp_path / "build_state.json").write_text(json.dumps({story.story_id: entry}), encoding="utf-8")

    with pytest.raises(build_corpus.CorpusError, match="explicit max_calls_per_story"):
        build_corpus.build(
            [story],
            FakeGraph(per_story_images=2),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("30.00")),
            readmit_quarantined=story.story_id,
            readmit_reason="cause fixed",
        )


def test_scene_attempt_cap_is_recorded_in_every_bundle_budget_basis(
    tmp_path, stories, monkeypatch
):
    """Two bundles drawn under different caps are not the same experiment: at 3 the kept page is
    best-of-three, at 1 it is the only draw. That has to be readable off the bundle, or a corpus
    silently mixes the two distributions."""
    from app.config import settings

    monkeypatch.setattr(settings, "max_scene_attempts", 3)

    summary = build_corpus.build(
        stories,
        FakeGraph(per_story_images=1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(scene_attempts=1),
    )

    assert summary["scene_attempts"] == 1


def test_build_applies_the_policy_scene_attempt_cap_to_the_running_pipeline(
    tmp_path, stories, monkeypatch
):
    """`consistency_check` reads the cap off `settings` at call time, so setting the field on the
    policy alone would be inert — the pipeline would keep paying for three draws while the bundle
    claimed one."""
    from app.config import settings

    # `build` sets the field process-wide and does not restore it; monkeypatch is what keeps
    # a 1-attempt build here from silently capping every later test in the session.
    monkeypatch.setattr(settings, "max_scene_attempts", 3)

    build_corpus.build(
        stories,
        FakeGraph(per_story_images=1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(scene_attempts=1),
    )

    assert settings.max_scene_attempts == 1


@pytest.mark.parametrize("attempts", [0, -1, 4, 1.0])
def test_scene_attempt_cap_outside_the_graph_recursion_budget_is_rejected(attempts):
    """ADR-024 sizes the graph recursion limit at `max_scenes × 7`, which is three attempts per
    scene. A cap above that trades a paid GraphRecursionError for a config typo."""
    with pytest.raises(ValueError, match="scene_attempts"):
        build_corpus.SpendPolicy(scene_attempts=attempts)


def test_fixture_cli_run_honours_the_scene_attempt_cap(tmp_path, monkeypatch):
    """The fixture run is the mandated zero-cost rehearsal for a paid one (spec §6), so it has to
    rehearse the same cap. The first version of this flag reached only the paid branch, and the
    fixture summary reported the production 3 back while the operator had asked for 1."""
    captured = {}

    def fake_build(*args, **kwargs):
        captured["policy"] = kwargs["policy"]
        return {}

    monkeypatch.setattr(build_corpus, "build", fake_build)
    build_corpus.main(["--fixture", "--scene-attempts", "1", "--out", str(tmp_path)])

    assert captured["policy"].scene_attempts == 1


# ------------------------------------------------------- campaign-scoped graph identity


def test_a_fresh_campaign_directory_never_resumes_another_campaigns_checkpoint(tmp_path, stories):
    """Regression, corpus run 2026-08-27: a fresh `--out` was treated as a fresh run and it was
    not. `run_story` keys the graph on `thread_id = story.story_id` in Postgres, so the new
    campaign resumed the *original* abandoned `syn-001` thread — the one left with `characters=[]`
    — drew seven scene images against it with every `char_id` skipped, and then quarantined on a
    roster that had never been extracted. The ledger is scoped to the directory; the graph state
    was not. Two campaigns over the same story must not share a thread."""
    first, second = tmp_path / "one", tmp_path / "two"
    graph_one, graph_two = FakeGraph(1), FakeGraph(1)

    build_corpus.build(stories[:1], graph_one, out_dir=first, supabase=FakeSupabase())
    build_corpus.build(stories[:1], graph_two, out_dir=second, supabase=FakeSupabase())

    assert graph_one.calls != graph_two.calls
    assert stories[0].story_id not in graph_one.calls + graph_two.calls


def test_a_campaign_thread_is_stable_for_the_same_output_directory(tmp_path, stories):
    """Scoping the thread must not cost resumption: the same campaign has to land on the same
    thread every invocation, or a resumed story would silently start over and pay twice."""
    story_id = stories[0].story_id
    again = build_corpus._campaign_thread_id(story_id, tmp_path / "one")

    assert build_corpus._campaign_thread_id(story_id, tmp_path / "one") == again
    assert build_corpus._campaign_thread_id(story_id, tmp_path / "two") != again
    # `_validated_checkpoint` compares the thread against `StoryMemory.story_id`, and the
    # execution-identity checks reject anything with a path separator in it.
    assert again.startswith(f"{story_id}--")
    assert pathlib.Path(again).name == again


def test_a_persisted_isolated_execution_identity_still_beats_the_campaign_thread(stories):
    """A restart or readmission already owns the thread it minted. The campaign default applies
    only where no execution identity was ever persisted."""
    story = stories[0]
    entry = isolated_quarantine(story)

    assert build_corpus._execution_id(story, entry, campaign="ignored") == entry["execution_id"]


# ------------------------------------------------------- the roster gate on an empty roster


def test_run_story_quarantines_an_empty_extracted_roster_before_paying_for_images():
    """The early gate was guarded on a truthy roster:

        if not reconciled and payload.get("characters"):

    so a story whose extraction came back empty never tripped it — the one check that exists to
    catch a bad roster for a fraction of a cent silently switched itself off, and the failure
    surfaced at packaging after a full story's images. That is exactly how the 2026-08-27 run
    spent ~$0.245 on seven scenes drawn with no character anchor at all. An empty roster is a
    roster failure, not an absence of evidence."""
    class EmptyRosterGraph(FakeGraph):
        def stream(self, graph_input, config, stream_mode=None):
            self.calls.append(config["configurable"]["thread_id"])
            yield "updates", {"analyze": {"characters": []}}
            for mode, values in super().stream(graph_input, config, stream_mode):
                values["characters"] = []
                yield mode, values

    graph = EmptyRosterGraph(per_story_images=4)

    with pytest.raises(CorpusError, match="declared roster"):
        build_corpus.run_story(graph, intake_story())

    assert graph.consumed <= 1


# ------------------------------------------------- a halt the operator cannot miss


def test_budget_halt_records_the_authorization_that_would_have_finished_the_campaign(tmp_path):
    """A halted campaign is otherwise a single `true` in a JSON blob. The reserve check stops
    before a story whose worst case does not fit, so the operator's own arithmetic ("30 stories,
    $1.50 each") never explains the stop; the summary has to carry the counts and the figure."""
    stories = [
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
        for story_id in "abcdef"
    ]
    policy = build_corpus.SpendPolicy(max_usd=Decimal("1.50"), max_calls_per_story=10)

    summary = build_corpus.build(
        stories, FakeGraph(10), out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )

    assert summary["halted"] is True
    assert summary["halt_reason"] == "budget_reserve"
    assert summary["stories_requested"] == 6
    assert summary["stories_run"] == 4
    assert summary["stories_not_started"] == 2
    # 40 calls already charged at $0.035 = $1.400, plus two untouched stories at their
    # 10-draw worst case = $0.700.
    assert summary["required_max_usd"] == "2.10"


def test_a_completed_campaign_reports_no_halt_figures(tmp_path, stories):
    summary = build_corpus.build(
        stories[:1],
        FakeGraph(1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("1.95")),
    )

    assert summary["halted"] is False
    assert summary["stories_requested"] == 1
    assert "required_max_usd" not in summary
    assert "halt_reason" not in summary


def test_a_quarantine_halt_names_its_reason(tmp_path, stories):
    graph = FakeGraph(per_story_images=3)
    policy = build_corpus.SpendPolicy(max_usd=Decimal("0.06"), price_per_megapixel=Decimal("0.03"))

    summary = build_corpus.build(
        stories[:1], graph, out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )

    assert summary["halted"] is True
    assert summary["halt_reason"] == "budget_stopped"


def test_cli_exits_nonzero_and_names_the_shortfall_when_a_campaign_halts(
    monkeypatch, capsys, tmp_path
):
    monkeypatch.setattr(build_corpus, "load_intake", lambda path: [intake_story()])
    monkeypatch.setattr(
        build_corpus,
        "build",
        lambda *args, **kwargs: {
            "halted": True,
            "halt_reason": "budget_reserve",
            "stories_requested": 30,
            "stories_run": 26,
            "stories_skipped": 0,
            "stories_not_started": 4,
            "required_max_usd": "34.72",
            "usd_high": "25.000",
            "authorized_usd": "25.00",
        },
    )

    assert build_corpus.main(["--fixture", "--out", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert "campaign halted" in captured.err
    assert "26" in captured.err and "30" in captured.err
    assert "--max-usd 34.72" in captured.err
    # The machine-readable summary still reaches stdout for programmatic callers.
    assert json.loads(captured.out)["halted"] is True


def test_cli_exits_zero_when_the_campaign_completes(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(build_corpus, "load_intake", lambda path: [intake_story()])
    monkeypatch.setattr(
        build_corpus, "build", lambda *args, **kwargs: {"halted": False, "stories_requested": 1}
    )

    assert build_corpus.main(["--fixture", "--out", str(tmp_path)]) == 0
    assert capsys.readouterr().err == ""


# ------------------------------------------------- the standing campaign authorization


def test_raising_the_campaign_authorization_between_invocations_is_reported(tmp_path):
    """Cumulative spend is already charged against `authorized_usd` across invocations, but the
    authorization itself is whatever the current command line says. The ledger already records
    what each earlier run was authorized for, so an increase is detectable without a new file."""
    stories = [
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
        for story_id in "abcdef"
    ]
    build_corpus.build(
        stories,
        FakeGraph(10),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("1.50"), max_calls_per_story=10),
    )

    summary = build_corpus.build(
        stories,
        FakeGraph(10),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00"), max_calls_per_story=10),
    )

    assert summary["authorization_increased_from"] == "1.50"
    assert summary["authorized_usd"] == "25.00"


def test_an_unchanged_or_tightened_authorization_is_not_reported(tmp_path, stories):
    policy = build_corpus.SpendPolicy(max_usd=Decimal("1.95"))
    build_corpus.build(
        stories[:1], FakeGraph(1), out_dir=tmp_path, supabase=FakeSupabase(), policy=policy
    )

    summary = build_corpus.build(
        stories[:1],
        FakeGraph(1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("1.00")),
    )

    assert "authorization_increased_from" not in summary


def test_cli_announces_a_raised_campaign_authorization_on_stderr(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(build_corpus, "load_intake", lambda path: [intake_story()])
    monkeypatch.setattr(
        build_corpus,
        "build",
        lambda *args, **kwargs: {
            "halted": False,
            "stories_requested": 1,
            "authorized_usd": "25.00",
            "authorization_increased_from": "1.50",
        },
    )

    assert build_corpus.main(["--fixture", "--out", str(tmp_path)]) == 0
    assert "authorization raised" in capsys.readouterr().err


# ------------------------------------- a roster mismatch costs one story, not the campaign


def _roster_stories(*story_ids):
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
        for story_id in story_ids
    ]


def _extracted_character(name, ref=False):
    return Character(
        char_id="c0", name=name, canonical_ref_image="story/ref-c0-1.png" if ref else None
    )


class RosterGraph:
    """Emits the extraction roster before drawing anything, the way the real graph does.

    `build_graph` wires `input_gate -> analyze -> segment -> char_bible`, and `char_bible` is the
    first node that calls Fal, so the reconciliation `run_story` performs on the first roster it
    sees happens with zero image spend. A fake that drew first would prove the opposite of what
    these tests claim.
    """

    def __init__(self, extracted=None, per_story_images=1, final_extracted=None):
        self.extracted = extracted or {}
        self.final_extracted = final_extracted or {}
        self.per_story_images = per_story_images
        self.calls: list[str] = []
        self.consumed = 0

    def stream(self, graph_input, config, stream_mode=None):
        thread = config["configurable"]["thread_id"]
        self.calls.append(thread)
        story_id = thread.split("--")[0]
        values = graph_input.model_dump()
        values["characters"] = [_extracted_character(self.extracted.get(story_id, "c0"))]
        yield "values", values
        for n in range(1, self.per_story_images + 1):
            sink = build_corpus._fal_event_sink.get()
            sink("attempted")
            self.consumed += 1
            sink("completed")
            values = dict(
                values,
                cost=Cost(image_count=n),
                characters=[_extracted_character(self.extracted.get(story_id, "c0"), ref=True)],
            )
            yield "values", values
        if story_id in self.final_extracted:
            yield (
                "values",
                dict(
                    values,
                    characters=[_extracted_character(self.final_extracted[story_id], ref=True)],
                ),
            )


def test_a_roster_mismatch_quarantines_its_story_and_the_campaign_continues(tmp_path):
    """syn-007 and syn-017 declare two characters and have a third genuine actor the extractor
    can surface. An unlucky ranking pushes a declared name out of the reference slice, and the
    old behaviour re-raised -- stopping a 30-story campaign at story 7 with six paid bundles."""
    stories = _roster_stories("a", "b", "c")
    graph = RosterGraph(extracted={"b": "intruder"})

    summary = build_corpus.build(
        stories,
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00")),
    )
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert summary["stories_run"] == 2
    assert summary["halted"] is False
    assert "halt_reason" not in summary
    assert summary["stories_quarantined"] == 1
    assert summary["quarantined_story_ids"] == ["b"]
    assert sorted(bundle.memory.story_id for bundle in load_completed_bundles(tmp_path)) == [
        "a",
        "c",
    ]
    assert state["b"]["reason_code"] == "invalid_terminal"
    assert "declared roster does not reconcile" in state["b"]["quarantined"]


def test_a_roster_mismatch_costs_no_image_call(tmp_path):
    """The whole reason continuing is safe: reconciliation fires on the extraction roster, before
    `char_bible` draws. A mismatch that had already paid for a story's images would be a
    different decision."""
    stories = _roster_stories("a")
    graph = RosterGraph(extracted={"a": "intruder"})

    summary = build_corpus.build(
        stories,
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00")),
    )
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))

    assert graph.consumed == 0
    assert state["a"]["telemetry"] == {"attempted": 0, "completed": 0, "failed": 0, "uncertain": 0}
    assert summary["usd_high"] == "0.000"


def test_a_non_roster_corpus_error_still_stops_the_campaign(tmp_path):
    """Only the reconciliation path becomes non-fatal. A `CorpusError` raised for any other
    reason keeps the semantics it has today."""

    class BrokenGraph:
        def stream(self, graph_input, config, stream_mode=None):
            raise CorpusError("checkpoint is not resumable: a")
            yield

    stories = _roster_stories("a", "b")

    with pytest.raises(CorpusError, match="invalid terminal state for a"):
        build_corpus.build(
            stories,
            BrokenGraph(),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00")),
        )

    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert state["a"]["reason_code"] == "invalid_terminal"
    assert "b" not in state


def test_uncertain_billing_outranks_a_roster_mismatch(tmp_path):
    """An unknown provider result stops the campaign for reconciliation even when the story would
    also have failed its roster check -- the money question is decided first."""

    class UncertainRosterGraph:
        def stream(self, graph_input, config, stream_mode=None):
            sink = build_corpus._fal_event_sink.get()
            sink("attempted")
            sink("failed_uncertain")
            values = graph_input.model_dump()
            values["characters"] = [_extracted_character("intruder")]
            yield "values", values

    stories = _roster_stories("a", "b")

    with pytest.raises(CorpusError, match="billing uncertain for a"):
        build_corpus.build(
            stories,
            UncertainRosterGraph(),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00")),
        )

    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert state["a"]["reason_code"] == "billing_uncertain"
    assert "b" not in state


def test_a_packaging_roster_mismatch_still_stops_the_campaign(tmp_path):
    """Deliberate asymmetry. Continuing past a pre-draw mismatch is free; a mismatch discovered at
    packaging has already paid for that story's images and is the expensive surprise the operator
    must see immediately."""
    stories = _roster_stories("a", "b")
    graph = RosterGraph(final_extracted={"a": "intruder"})

    with pytest.raises(CorpusError, match="invalid terminal state for a"):
        build_corpus.build(
            stories,
            graph,
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00")),
        )

    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert state["a"]["reason_code"] == "invalid_terminal"
    assert "b" not in state


def test_a_roster_quarantine_stays_readmittable_after_the_campaign_continues(tmp_path):
    """The quarantine is not weakened by continuing: it is still `invalid_terminal`, so it still
    demands the documented human decision before that story runs again."""
    stories = _roster_stories("a")
    build_corpus.build(
        stories,
        RosterGraph(extracted={"a": "intruder"}),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00")),
    )

    summary = build_corpus.build(
        stories,
        RosterGraph(),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00"), max_calls_per_story=20),
        readmit_quarantined="a",
        readmit_reason="extraction ranking fixed",
    )

    assert summary["stories_run"] == 1
    assert summary["stories_quarantined"] == 0
    [bundle] = load_completed_bundles(tmp_path)
    assert bundle.run_metadata["readmit_reason"] == "extraction ranking fixed"


def test_a_clean_campaign_reports_no_quarantines(tmp_path, stories):
    summary = build_corpus.build(
        stories[:1],
        FakeGraph(1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("1.95")),
    )

    assert summary["stories_quarantined"] == 0
    assert summary["quarantined_story_ids"] == []


def test_cli_exits_nonzero_and_names_the_quarantined_stories(monkeypatch, capsys, tmp_path):
    """A run that quarantines is not halted, but it is not a clean run either, and the operator
    must not have to open the ledger to learn which stories still owe a decision."""
    monkeypatch.setattr(build_corpus, "load_intake", lambda path: [intake_story()])
    monkeypatch.setattr(
        build_corpus,
        "build",
        lambda *args, **kwargs: {
            "halted": False,
            "stories_requested": 30,
            "stories_run": 29,
            "stories_skipped": 0,
            "stories_quarantined": 1,
            "quarantined_story_ids": ["syn-007"],
        },
    )

    assert build_corpus.main(["--fixture", "--out", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert "1 of 30" in captured.err
    assert "syn-007" in captured.err
    assert json.loads(captured.out)["halted"] is False


# ------------------------------------- a pre-existing quarantine is "not this run", not a stop


def _seed_quarantine(tmp_path, story, reason_code, **extra):
    entry = {
        "quarantined": reason_code.replace("_", " "),
        "reason_code": reason_code,
        "intake_sha256": intake_sha256(story),
        "conservative_call_usd": "0.035",
        "telemetry": {"attempted": 1, "completed": 1, "failed": 0, "uncertain": 0},
        **extra,
    }
    (tmp_path / "build_state.json").write_text(
        json.dumps({story.story_id: entry}), encoding="utf-8"
    )


def test_a_pre_existing_quarantine_is_skipped_and_counted_on_a_rerun(tmp_path):
    """Run 1 leaves 2 bundles and a quarantine. Before this, run 2 died at the quarantined story
    -- so a campaign that had to be rerun (a budget halt, a re-authorization) could never get
    past its first bad story, which defeats the point of continuing past one in the first place.
    """
    first = _roster_stories("a", "b", "c")
    build_corpus.build(
        first,
        RosterGraph(extracted={"b": "intruder"}),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00")),
    )

    graph = RosterGraph()
    summary = build_corpus.build(
        _roster_stories("a", "b", "c", "d"),
        graph,
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00")),
    )

    assert summary["stories_requested"] == 4
    assert summary["stories_run"] == 1
    assert summary["stories_skipped"] == 2
    assert summary["stories_quarantined"] == 1
    assert summary["quarantined_story_ids"] == ["b"]
    assert summary["halted"] is False
    # Skipping is "not this run", not forgiveness: the story is never handed to the graph.
    assert graph.calls == [build_corpus._campaign_thread_id("d", tmp_path)]
    assert sorted(bundle.memory.story_id for bundle in load_completed_bundles(tmp_path)) == [
        "a",
        "c",
        "d",
    ]


def test_the_quarantine_count_is_stable_across_reruns(tmp_path):
    stories = _roster_stories("a", "b")
    first = build_corpus.build(
        stories,
        RosterGraph(extracted={"b": "intruder"}),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00")),
    )
    second = build_corpus.build(
        stories,
        RosterGraph(),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_usd=Decimal("25.00")),
    )

    assert first["stories_quarantined"] == second["stories_quarantined"] == 1
    assert first["quarantined_story_ids"] == second["quarantined_story_ids"] == ["b"]


def test_a_skipped_quarantine_still_needs_a_flag_and_still_fails_its_checks(tmp_path):
    """Skipping the story when nothing targets it must not make the targeted path permissive."""
    story = intake_story()
    _seed_quarantine(tmp_path, story, "budget_stopped")

    with pytest.raises(CorpusError, match="intake digest differs"):
        build_corpus.build(
            [intake_story(text="a different story entirely")],
            RecoverableGraph(story, per_story_images=1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            resume_quarantined=story.story_id,
        )


def test_an_unbound_resume_flag_skips_rather_than_stops(tmp_path):
    """A resume naming a different story does not unlock this one -- it is skipped, not run."""
    story = intake_story()
    (tmp_path / "build_state.json").write_text(
        json.dumps({story.story_id: isolated_quarantine(story)}), encoding="utf-8"
    )

    summary = build_corpus.build(
        [story],
        RecoverableGraph(story, per_story_images=1),
        out_dir=tmp_path,
        supabase=FakeSupabase(),
        policy=build_corpus.SpendPolicy(max_calls_per_story=15),
        resume_quarantined="different-story",
    )

    assert summary["quarantined_story_ids"] == [story.story_id]
    assert summary["stories_run"] == 0
    assert load_completed_bundles(tmp_path) == []


def test_an_uncertain_billing_quarantine_still_stops_a_rerun(tmp_path):
    """The one reason that is not a statement about a single story. Every other quarantine leaves
    the campaign total exactly known; uncertain billing means real money moved with an unknown
    outcome, so `usd_high` is a lower bound on a number nobody has. Spec section 10 stops before
    spending when billing is uncertain, and spending more against a total known to be wrong is
    what that forbids -- a line on stderr is not the same as refusing to spend."""
    story = intake_story()
    _seed_quarantine(
        tmp_path,
        story,
        "billing_uncertain",
        telemetry={"attempted": 2, "completed": 1, "failed": 0, "uncertain": 1},
    )

    with pytest.raises(CorpusError, match="billing uncertain"):
        build_corpus.build(
            [story],
            RecoverableGraph(story, per_story_images=1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
        )


def test_an_uncertain_billing_rerun_still_demands_acknowledgment(tmp_path):
    story = intake_story()
    _seed_quarantine(
        tmp_path,
        story,
        "billing_uncertain",
        telemetry={"attempted": 2, "completed": 1, "failed": 0, "uncertain": 1},
    )

    with pytest.raises(CorpusError, match="acknowledge uncertain billing"):
        build_corpus.build(
            [story],
            RecoverableGraph(story, per_story_images=1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
            resume_quarantined=story.story_id,
        )


@pytest.mark.parametrize("reason_code", [None, "unknown_reason"])
def test_a_malformed_quarantine_reason_still_stops_a_rerun(tmp_path, reason_code):
    story = intake_story()
    entry = {
        "quarantined": "malformed quarantine",
        "intake_sha256": intake_sha256(story),
        "conservative_call_usd": "0.035",
        "telemetry": {"attempted": 1, "completed": 1, "failed": 0, "uncertain": 0},
    }
    if reason_code is not None:
        entry["reason_code"] = reason_code
    (tmp_path / "build_state.json").write_text(
        json.dumps({story.story_id: entry}), encoding="utf-8"
    )

    with pytest.raises(CorpusError, match="malformed quarantine"):
        build_corpus.build(
            [story],
            RecoverableGraph(story, per_story_images=1),
            out_dir=tmp_path,
            supabase=FakeSupabase(),
        )


def test_a_fixture_run_still_refuses_to_pass_a_quarantine(tmp_path):
    """Fixture mode is the zero-cost rehearsal and has no recovery vocabulary at all, so a
    quarantine there is an unrehearsable state rather than work deferred to a later run."""
    story = intake_story()
    _seed_quarantine(tmp_path, story, "budget_stopped")

    with pytest.raises(CorpusError, match="budget stopped"):
        build_corpus.build([story], None, out_dir=tmp_path, supabase=None, fixture=True)


def test_a_rerun_that_only_skips_quarantines_still_exits_nonzero(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(build_corpus, "load_intake", lambda path: [intake_story()])
    monkeypatch.setattr(
        build_corpus,
        "build",
        lambda *args, **kwargs: {
            "halted": False,
            "stories_requested": 30,
            "stories_run": 0,
            "stories_skipped": 29,
            "stories_quarantined": 1,
            "quarantined_story_ids": ["syn-007"],
        },
    )

    assert build_corpus.main(["--fixture", "--out", str(tmp_path)]) == 2
    assert "syn-007" in capsys.readouterr().err


def donated_intake_story(**changes):
    """A donated record with the approvals `IntakeRecord` requires before it will load."""
    record = {
        "provenance": "donated",
        "split": "test",
        "candidate_role": "primary",
        "guardian_consent": True,
        "child_assent": True,
        "manual_pii_redaction": True,
        "independent_redaction_review": True,
        "withdrawal_state": "active",
        "selection_frozen_at": "2026-01-01T00:00:00+00:00",
    }
    record.update(changes)
    return intake_story(**record)


def test_donated_intake_counts_as_pii_already_handled():
    """`IntakeRecord` refuses to load a donated record unless both redaction attestations are
    true, so a record that exists at all has been hand-redacted and independently reviewed."""
    assert donated_intake_story().pii_already_handled is True
    assert intake_story().pii_already_handled is True


def test_initial_state_never_pseudonymizes_a_hand_redacted_donated_story():
    """Presidio pseudonymizes PERSON spans, renaming the cast `declared_characters` is keyed on.

    It cost 16 of the 30 synthetic records a declared name before `synthetic_no_pii` was added.
    Donated stories are hand-redacted and independently reviewed before intake, so a second
    automated pass buys nothing and does the same damage -- to real children's writing, whose
    declared roster the operator cannot restate under pool pseudonyms they cannot predict.
    """
    state = build_corpus._initial_state(donated_intake_story(declared_characters=["Marisol"],
                                                             declared_non_human=[]))

    assert state.input.synthetic_no_pii is True



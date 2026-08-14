"""§5 — the synthetic corpus and the runner that turns it into images.

Two of these tests exist to stop a specific way of losing money: the spend cap (an unbounded
fal.ai bill) and the resume skip (paying twice for the same story). Everything else validates
that the checked-in corpus can actually reach the pipeline — a story that fails `clamp_story`
or the `POST /storybooks` minimum-length rule is a story you discover after paying for the
nineteen before it.

Every provider call is mocked. Nothing here draws an image.
"""
import json

import pytest

from app.config import MAX_STORY_WORDS, MIN_STORY_WORDS
from app.length import clamp_story, word_count
from contracts.story_memory import Character, Cost, Scene
from finetune import build_corpus


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
        names = story["characters"]
        assert 1 <= len(names) <= 2, story["story_id"]
        assert len(set(names)) == len(names), story["story_id"]
        assert set(story["non_human"]) <= set(names), story["story_id"]
        for name in names:
            assert name in story["text"], (story["story_id"], name)


def test_character_names_are_distinct_across_the_whole_corpus(corpus):
    """§3.2 splits on character. Two stories sharing a name would land the same character on
    both sides of a split without the split guard ever seeing it."""
    names = [n for s in corpus for n in s["characters"]]
    assert len(set(names)) == len(names)


def test_corpus_is_roughly_thirty_eight_characters_mostly_non_human(corpus):
    """§7.4 item 2 — the non-human slice is the research contribution and the least-powered
    slice, so the train corpus is deliberately weighted toward it."""
    names = [n for s in corpus for n in s["characters"]]
    non_human = [n for s in corpus for n in s["non_human"]]
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
            self.consumed += 1
            yield "values", _values(n)


class FakeStorage:
    def __init__(self):
        self.downloads: list[str] = []

    def from_(self, bucket):
        return self

    def download(self, path):
        self.downloads.append(path)
        return b"png-bytes"


class FakeSupabase:
    def __init__(self):
        self.storage = FakeStorage()


@pytest.fixture
def stories():
    return [
        {"story_id": "a", "text": "t", "characters": ["A"], "non_human": []},
        {"story_id": "b", "text": "t", "characters": ["B"], "non_human": []},
        {"story_id": "c", "text": "t", "characters": ["C"], "non_human": []},
    ]


# --------------------------------------------------------------------------- the spend cap


def test_budget_cap_halts_mid_story_and_never_exceeds(tmp_path, stories):
    """THE test. Each story here wants 4 images; the cap is 5. Story `a` runs whole, story `b`
    is cut off after one image, story `c` is never started at all."""
    graph = FakeGraph(per_story_images=4)
    summary = build_corpus.build(
        stories, graph, budget=5, out_dir=tmp_path, supabase=FakeSupabase()
    )

    assert summary["images_spent"] == 5
    assert summary["images_spent"] <= 5
    assert graph.calls == ["a", "b"]          # `c` never submitted
    assert graph.consumed == 5                # `b`'s stream abandoned, not drained
    assert summary["halted"] is True
    assert summary["stories_run"] == 1        # only `a` completed


def test_budget_of_zero_submits_nothing(tmp_path, stories):
    graph = FakeGraph(per_story_images=4)
    summary = build_corpus.build(
        stories, graph, budget=0, out_dir=tmp_path, supabase=FakeSupabase()
    )
    assert graph.calls == []
    assert summary["images_spent"] == 0


def test_cost_estimate_brackets_the_fal_price_band(tmp_path, stories):
    graph = FakeGraph(per_story_images=2)
    summary = build_corpus.build(
        stories, graph, budget=100, out_dir=tmp_path, supabase=FakeSupabase()
    )
    assert summary["images_spent"] == 6
    assert summary["usd_low"] == pytest.approx(6 * 0.02)
    assert summary["usd_high"] == pytest.approx(6 * 0.035)


# --------------------------------------------------------------------------- the resume skip


def test_a_completed_story_is_never_resubmitted(tmp_path, stories):
    """A crash 20 stories in must not re-bill the first 20. `generate_scene`'s CC-10
    Storage-exists skip only makes a *re-executed* scene free — it does not stop the graph
    being re-entered, and `char_bible.mint_reference` has no such skip at all, so every
    canonical reference would be redrawn and paid for. The state file is the guard."""
    graph = FakeGraph(per_story_images=2)
    first = build_corpus.build(
        stories, graph, budget=100, out_dir=tmp_path, supabase=FakeSupabase()
    )
    assert first["stories_run"] == 3
    assert graph.calls == ["a", "b", "c"]

    resumed = FakeGraph(per_story_images=2)
    second = build_corpus.build(
        stories, resumed, budget=100, out_dir=tmp_path, supabase=FakeSupabase()
    )
    assert resumed.calls == []
    assert second["images_spent"] == 0
    assert second["stories_skipped"] == 3


def test_a_halted_story_is_not_marked_done(tmp_path, stories):
    graph = FakeGraph(per_story_images=4)
    build_corpus.build(stories, graph, budget=5, out_dir=tmp_path, supabase=FakeSupabase())
    state = json.loads((tmp_path / "build_state.json").read_text(encoding="utf-8"))
    assert list(state) == ["a"]


# --------------------------------------------------------------------------- landing the images


def test_images_land_in_ref_and_scene_under_flattened_storage_paths(tmp_path):
    supabase = FakeSupabase()
    refs, scenes = build_corpus.download_images(_values(3, chars=2, scenes=2), tmp_path, supabase)
    assert refs == 2 and scenes == 2
    assert (tmp_path / "ref" / "story_ref-c0-1.png").read_bytes() == b"png-bytes"
    assert (tmp_path / "scene" / "story_s1-1.png").exists()


def test_download_skips_a_file_already_on_disk(tmp_path):
    supabase = FakeSupabase()
    build_corpus.download_images(_values(1, chars=1, scenes=1), tmp_path, supabase)
    build_corpus.download_images(_values(1, chars=1, scenes=1), tmp_path, supabase)
    assert len(supabase.storage.downloads) == 2   # not 4

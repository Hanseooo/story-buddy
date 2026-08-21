"""§5.2 / §5.4 — pairing, annotation consensus, and the ONE polarity conversion.

`annotations.same_character` is `true` for *same*; the manuscript's positive class is
`label = not same_character` (annotation-surface §2.1). That inversion happens in
`build_dataset.py` and nowhere else, so it is asserted here and nowhere else.
"""
from unittest.mock import MagicMock, patch

import pytest

from contracts.story_memory import (
    Attempt,
    Character,
    CharacterDescription,
    Input,
    Scene,
    StoryMemory,
)
from finetune import build_dataset as bd
from finetune import evaluate as ev
from finetune.manifest import ManifestError


def memory() -> StoryMemory:
    return StoryMemory(
        schema_version=1,
        story_id="story_1",
        classroom_id="c1",
        profile_id="p1",
        input=Input(raw_text="once upon a time"),
        characters=[
            Character(
                char_id="quill_007",
                name="Quill",
                description=CharacterDescription(
                    species="hedgehog", colours=["cream chest"], body_features=["three amber eyes"],
                    clothing=["striped scarf"],
                ),
                canonical_ref_image="story_1/ref-quill.png",
            ),
            Character(char_id="noref_1", name="Ghost", canonical_ref_image=None),
        ],
        scenes=[
            Scene(
                scene_id="s1",
                text_excerpt="x",
                characters_present=["quill_007", "noref_1"],
                attempts=[Attempt(image_ref="story_1/s1-1.png"), Attempt(image_ref="story_1/s1-2.png")],
            ),
            Scene(scene_id="s2", text_excerpt="y", characters_present=[], attempts=[Attempt(image_ref="story_1/s2-1.png")]),
        ],
    )


# --- pairing -------------------------------------------------------------------------------

def test_pair_id_is_deterministic_and_opaque():
    a = bd.mint_pair_id("quill_007", "story_1/s1-1.png")
    assert a == bd.mint_pair_id("quill_007", "story_1/s1-1.png")
    assert a != bd.mint_pair_id("quill_007", "story_1/s1-2.png")
    assert "quill" not in a and ".png" not in a


def test_pairs_are_reference_first_one_per_attempt_and_skip_characters_without_a_reference():
    pairs = bd.pairs_from_memory(memory())
    assert [(p.char_id, p.ref_image, p.scene_image) for p in pairs] == [
        ("quill_007", "story_1/ref-quill.png", "story_1/s1-1.png"),
        ("quill_007", "story_1/ref-quill.png", "story_1/s1-2.png"),
    ]


# --- annotation consensus ------------------------------------------------------------------

def test_fetch_annotations_paginates_past_supabase_default_row_limit():
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.order.return_value = query
    first_page = MagicMock()
    first_page.execute.return_value.data = [{"pair_id": f"p{i}"} for i in range(1000)]
    second_page = MagicMock()
    second_page.execute.return_value.data = [{"pair_id": "p1000"}]
    query.range.side_effect = [first_page, second_page]

    with patch.object(bd, "get_supabase_client", return_value=client):
        result = bd.fetch_annotations()

    assert len(result) == 1001
    assert query.range.call_args_list == [((0, 999),), ((1000, 1999),)]

def rows(pair_id, *specs):
    out = []
    for i, spec in enumerate(specs):
        row = {"pair_id": pair_id, "annotator_id": f"a{i}", "failure_reasons": [],
               "anatomy_intact": True, "text_free": True}
        row.update(spec)
        out.append(row)
    return out


def test_consensus_is_majority_on_same_character():
    resolved = bd.resolve_annotations(
        rows("p1", {"same_character": True}, {"same_character": True}),
        set(), set(),
    )
    assert resolved["p1"].same_character is True
    assert resolved["p1"].adjudicated is False


def test_an_unadjudicated_tie_raises_manifest_error():
    with pytest.raises(ManifestError, match="unresolved conflict"):
        bd.resolve_annotations(
            rows("p1", {"same_character": True}, {"same_character": False}),
            set(), set(),
        )


def test_disagreeing_fields_goes_to_adjudication_and_is_exclusive():
    # If they agree on same_character but disagree on fields, it's a conflict and requires an adjudicator.
    # The adjudicator's row is used exclusively.
    resolved = bd.resolve_annotations(rows(
        "p1",
        {"annotator_id": "a1", "same_character": False, "failure_reasons": ["wrong_colour"], "anatomy_intact": False},
        {"annotator_id": "a2", "same_character": False, "failure_reasons": ["wrong_clothing"], "text_free": False},
        {"annotator_id": "adj1", "same_character": False, "failure_reasons": ["wrong_colour"], "anatomy_intact": True, "text_free": True},
    ), {"adj1"}, set())
    c = resolved["p1"]
    # Should exactly match adj1, no unioning
    assert c.anatomy_intact is True and c.text_free is True
    assert c.failure_reasons == ["wrong_colour"]


def test_missing_gating_columns_default_to_the_schema_defaults():
    resolved = bd.resolve_annotations(
        rows("p1", {"same_character": True}, {"same_character": True}),
        set(), set(),
    )
    assert resolved["p1"].anatomy_intact is True and resolved["p1"].text_free is True


def test_resolve_annotations_strict_rules():
    # >2 ordinary annotations -> hard fail
    with pytest.raises(ManifestError, match=">2 ordinary annotations"):
        bd.resolve_annotations(
            rows("p1", {"same_character": True}, {"same_character": True}, {"same_character": True}),
            set(), set(),
        )

    # <2 ordinary annotations -> hard fail
    with pytest.raises(ManifestError, match="<2 ordinary annotations"):
        bd.resolve_annotations(
            rows("p1", {"same_character": True}),
            set(), set(),
        )

    # duplicate annotator_ids -> hard fail
    with pytest.raises(ManifestError, match="duplicate annotator_ids"):
        bd.resolve_annotations(
            [
                {"pair_id": "p1", "annotator_id": "a1", "same_character": True},
                {"pair_id": "p1", "annotator_id": "a1", "same_character": True},
            ],
            set(), set(),
        )

    # 2 disagreeing ordinary rows + 1 adjudicator -> adjudicator decides
    res = bd.resolve_annotations(
        rows("p1",
            {"same_character": True, "annotator_id": "a1"},
            {"same_character": False, "annotator_id": "a2"},
            {"same_character": False, "annotator_id": "adj1", "failure_reasons": ["wrong_colour"]},
        ),
        {"adj1"}, set(),
    )
    assert res["p1"].same_character is False
    assert res["p1"].adjudicated is True
    assert res["p1"].failure_reasons == ["wrong_colour"]

    # 2 disagreeing ordinary rows + >1 adjudicators -> hard fail
    with pytest.raises(ManifestError, match="multiple adjudicator rows"):
        bd.resolve_annotations(
            rows("p1",
                {"same_character": True, "annotator_id": "a1"},
                {"same_character": False, "annotator_id": "a2"},
                {"same_character": False, "annotator_id": "adj1"},
                {"same_character": True, "annotator_id": "adj2"},
            ),
            {"adj1", "adj2"}, set(),
        )

    # 2 agreeing ordinary rows + adjudicator present -> hard fail
    with pytest.raises(ManifestError, match="ordinary annotators agreed, but adjudicator row exists"):
        bd.resolve_annotations(
            rows("p1",
                {"same_character": True, "annotator_id": "a1"},
                {"same_character": True, "annotator_id": "a2"},
                {"same_character": False, "annotator_id": "adj1"},
            ),
            {"adj1"}, set(),
        )

    # Pilot pairs are silently excluded from resolution
    assert bd.resolve_annotations(
        rows("pilot_1", {"same_character": True}),
        set(), {"pilot_1"},
    ) == {}


# --- polarity ------------------------------------------------------------------------------

@pytest.mark.parametrize("same_character", [True, False])
def test_label_is_the_inverse_of_same_character_and_is_converted_only_here(same_character):
    consensus = bd.resolve_annotations(
        rows("x", {"same_character": same_character}, {"same_character": same_character}),
        set(), set(),
    )
    pairs = bd.pairs_from_memory(memory())
    keyed = {pairs[0].pair_id: consensus["x"]}
    records = bd.build_records(memory(), "train", "synthetic", keyed, {pairs[1].pair_id})

    assert len(records) == 1
    assert records[0].same_character is same_character
    assert records[0].label is (not same_character)


def test_unannotated_pairs_hard_fail_if_not_pilot():
    with pytest.raises(ManifestError, match="<2 annotations"):
        bd.build_records(memory(), "train", "synthetic", {}, set())


def test_pilot_pairs_are_dropped():
    pairs = bd.pairs_from_memory(memory())
    pilot_pairs = {p.pair_id for p in pairs}
    assert bd.build_records(memory(), "train", "synthetic", {}, pilot_pairs) == []


def test_build_records_carries_the_gating_booleans_and_the_split_metadata():
    pairs = bd.pairs_from_memory(memory())
    keyed = {
        pairs[0].pair_id: bd.Consensus(
            same_character=False, failure_reasons=["wrong_colour"], anatomy_intact=False, text_free=False,
        ),
        pairs[1].pair_id: bd.Consensus(
            same_character=True, failure_reasons=[], anatomy_intact=True, text_free=True,
        ),
    }
    rec1, rec2 = bd.build_records(memory(), "test", "donated", keyed, set())
    assert (rec1.split, rec1.provenance, rec1.pair_type) == ("test", "donated", "pipeline")
    assert rec1.anatomy_intact is False and rec1.text_free is False
    assert rec1.failure_reasons == ["wrong_colour"]
    # Local dataset paths, NOT the raw Storage paths — LLaMA-Factory resolves `images` against
    # the filesystem and `build_corpus` writes the flattened name (manifest.local_image_path).
    assert rec1.images == ["data/judge/ref/story_1_ref-quill.png", "data/judge/scene/story_1_s1-1.png"]
    assert rec2.same_character is True
    assert rec2.label is False


# --- rationale template --------------------------------------------------------------------

def test_positive_rationale_lists_the_attributes_rather_than_being_blank():
    text = bd.render_rationale(True, [], ["three amber eyes", "striped scarf"])
    assert text and "three amber eyes" in text and "striped scarf" in text


def test_negative_rationale_is_one_deterministic_sentence_per_ticked_reason():
    text = bd.render_rationale(False, ["wrong_body_feature", "wrong_clothing"], ["three amber eyes"])
    assert text == bd.render_rationale(False, ["wrong_body_feature", "wrong_clothing"], ["three amber eyes"])
    assert text.count(".") >= 2
    assert "three amber eyes" in text


def test_negative_with_no_ticked_reason_still_renders_prose():
    assert bd.render_rationale(False, [], []).strip()


# --- constructed negatives -----------------------------------------------------------------

def test_constructed_negatives_are_train_only_cross_character_and_labelled_different():
    pipeline_records = [
        bd.ManifestRecord(
            pair_id=f"p{i}", char_id=cid, split="train", provenance="synthetic", pair_type="pipeline",
            images=[f"ref/{cid}.png", f"scene/{cid}.png"], differences_observed="ok",
            same_character=True, label=False, failure_reasons=[],
        )
        for i, cid in enumerate(["a", "b", "c"])
    ]
    made = bd.constructed_records(pipeline_records)
    assert made
    for rec in made:
        assert rec.split == "train" and rec.pair_type == "constructed"
        assert rec.same_character is False and rec.label is True
        assert rec.char_id in rec.images[0]          # the reference decides the split owner
        assert rec.char_id not in rec.images[1]      # the scene came from a different character


def test_constructed_negatives_ignore_val_and_test_records():
    recs = [
        bd.ManifestRecord(
            pair_id=f"p{i}", char_id=cid, split=split, provenance=prov, pair_type="pipeline",
            images=[f"ref/{cid}.png", f"scene/{cid}.png"], differences_observed="ok",
            same_character=True, label=False, failure_reasons=[],
        )
        for i, (cid, split, prov) in enumerate([("a", "val", "synthetic"), ("b", "test", "donated")])
    ]
    assert bd.constructed_records(recs) == []


# --- the supabase seam ---------------------------------------------------------------------

def test_fetch_annotations_reads_the_annotations_table_through_the_existing_client_seam():
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.order.return_value = query
    query.range.return_value.execute.return_value.data = [{"pair_id": "p1"}]
    with patch("finetune.build_dataset.get_supabase_client", return_value=client):
        assert bd.fetch_annotations() == [{"pair_id": "p1"}]
    client.table.assert_called_once_with("annotations")


def test_fetch_adjudicator_ids_reads_profiles_table():
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": "a1"}]
    with patch("finetune.build_dataset.get_supabase_client", return_value=client):
        assert bd.fetch_adjudicator_ids() == {"a1"}
    client.table.assert_called_with("profiles")


def test_fetch_pilot_pairs_reads_research_pairs_table():
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": "p1"}]
    with patch("finetune.build_dataset.get_supabase_client", return_value=client):
        assert bd.fetch_pilot_pairs() == {"p1"}
    client.table.assert_called_with("research_pairs")


# --- evaluate.py metrics -------------------------------------------------------------------

def test_prf1_scores_the_different_character_class():
    #                 labels                     predictions
    labels = [True, True, True, False, False]
    preds = [True, True, False, True, False]
    p, r, f1 = ev.prf1(labels, preds)
    assert p == pytest.approx(2 / 3)
    assert r == pytest.approx(2 / 3)
    assert f1 == pytest.approx(2 / 3)


def test_prf1_is_zero_rather_than_undefined_when_nothing_is_predicted_positive():
    assert ev.prf1([True, False], [False, False]) == (0.0, 0.0, 0.0)


def test_bootstrap_resamples_by_char_id_not_by_pair():
    labels = [True] * 4 + [False] * 4
    preds = [True] * 4 + [False] * 4
    char_ids = ["a", "a", "a", "a", "b", "b", "b", "b"]
    lo, hi = ev.bootstrap_f1_ci(labels, preds, char_ids, resamples=50, seed=0)
    assert 0.0 <= lo <= hi <= 1.0


# --- build_dataset manifest & stats --------------------------------------------------------

def test_build_dataset_creates_manifest_and_stats(tmp_path):
    import json
    out = tmp_path / "manifest.jsonl"
    with patch("finetune.build_dataset.fetch_annotations", return_value=[]), \
         patch("finetune.build_dataset.fetch_adjudicator_ids", return_value=set()), \
         patch("finetune.build_dataset.fetch_pilot_pairs", return_value=set()):
        records = bd.build_dataset([], out_path=out, add_constructed=False)

    assert out.exists()
    assert records == []
    stats_out = tmp_path / "dataset_manifest.json"
    assert stats_out.exists()
    stats = json.loads(stats_out.read_text(encoding="utf-8"))
    assert stats["overall"]["total_pairs"] == 0
    assert stats["overall"]["characters"] == 0
    assert stats["overall"]["natural_pairs"] == 0
    assert stats["overall"]["constructed_pairs"] == 0
    assert "splits" in stats
    assert set(stats["splits"].keys()) == {"train", "val", "test"}
    assert "class_balance" in stats
    assert "failure_reasons" in stats
    assert "adjudication_rate" in stats
    assert "dataset_sha256" in stats


def test_build_dataset_computes_accurate_statistics(tmp_path):
    import json
    out = tmp_path / "manifest.jsonl"
    mem = memory()
    pairs = bd.pairs_from_memory(mem)
    pair1, pair2 = pairs[0], pairs[1]

    # pair1: 2 annotators disagree (a1=True, a2=False), adj1=False (adjudicated)
    # pair2: 2 annotators agree (a1=True, a2=True)
    raw_annotations = [
        {"pair_id": pair1.pair_id, "annotator_id": "a1", "same_character": True, "failure_reasons": []},
        {"pair_id": pair1.pair_id, "annotator_id": "a2", "same_character": False, "failure_reasons": ["wrong_colour"]},
        {"pair_id": pair1.pair_id, "annotator_id": "adj1", "same_character": False, "failure_reasons": ["wrong_colour"]},
        {"pair_id": pair2.pair_id, "annotator_id": "a1", "same_character": True, "failure_reasons": []},
        {"pair_id": pair2.pair_id, "annotator_id": "a2", "same_character": True, "failure_reasons": []},
    ]
    with patch("finetune.build_dataset.fetch_annotations", return_value=raw_annotations), \
         patch("finetune.build_dataset.fetch_adjudicator_ids", return_value={"adj1"}), \
         patch("finetune.build_dataset.fetch_pilot_pairs", return_value=set()):
        records = bd.build_dataset([(mem, "train", "synthetic")], out_path=out, add_constructed=False)

    assert len(records) == 2
    stats_out = tmp_path / "dataset_manifest.json"
    stats = json.loads(stats_out.read_text(encoding="utf-8"))
    assert stats["overall"]["characters"] == 1
    assert stats["overall"]["natural_pairs"] == 2
    assert stats["overall"]["constructed_pairs"] == 0
    assert stats["overall"]["total_pairs"] == 2
    assert stats["class_balance"]["same_character"] == 1
    assert stats["class_balance"]["different_character"] == 1
    assert stats["failure_reasons"] == {"wrong_colour": 1}
    assert stats["adjudication_rate"] == 0.5
    assert len(stats["dataset_sha256"]) == 64

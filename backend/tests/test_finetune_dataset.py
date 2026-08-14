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
        rows("p1", {"same_character": True}, {"same_character": False}, {"same_character": True})
    )
    assert resolved["p1"].same_character is True


def test_an_unadjudicated_tie_is_dropped():
    resolved = bd.resolve_annotations(rows("p1", {"same_character": True}, {"same_character": False}))
    assert resolved == {}


def test_gating_booleans_fold_worst_wins_and_reasons_union():
    resolved = bd.resolve_annotations(rows(
        "p1",
        {"same_character": False, "failure_reasons": ["wrong_colour"], "anatomy_intact": False},
        {"same_character": False, "failure_reasons": ["wrong_clothing"], "text_free": False},
    ))
    c = resolved["p1"]
    assert c.anatomy_intact is False and c.text_free is False
    assert c.failure_reasons == ["wrong_colour", "wrong_clothing"]


def test_missing_gating_columns_default_to_the_schema_defaults():
    resolved = bd.resolve_annotations([{"pair_id": "p1", "annotator_id": "a", "same_character": True}])
    assert resolved["p1"].anatomy_intact is True and resolved["p1"].text_free is True


# --- polarity ------------------------------------------------------------------------------

@pytest.mark.parametrize("same_character", [True, False])
def test_label_is_the_inverse_of_same_character_and_is_converted_only_here(same_character):
    consensus = bd.resolve_annotations(
        rows("x", {"same_character": same_character}, {"same_character": same_character})
    )
    pairs = bd.pairs_from_memory(memory())
    keyed = {pairs[0].pair_id: consensus["x"]}
    records = bd.build_records(memory(), "train", "synthetic", keyed)

    assert len(records) == 1
    assert records[0].same_character is same_character
    assert records[0].label is (not same_character)


def test_unannotated_pairs_are_dropped():
    assert bd.build_records(memory(), "train", "synthetic", {}) == []


def test_build_records_carries_the_gating_booleans_and_the_split_metadata():
    pairs = bd.pairs_from_memory(memory())
    keyed = {pairs[0].pair_id: bd.Consensus(
        same_character=False, failure_reasons=["wrong_colour"], anatomy_intact=False, text_free=False,
    )}
    (rec,) = bd.build_records(memory(), "test", "donated", keyed)
    assert (rec.split, rec.provenance, rec.pair_type) == ("test", "donated", "pipeline")
    assert rec.anatomy_intact is False and rec.text_free is False
    assert rec.failure_reasons == ["wrong_colour"]
    # Local dataset paths, NOT the raw Storage paths — LLaMA-Factory resolves `images` against
    # the filesystem and `build_corpus` writes the flattened name (manifest.local_image_path).
    assert rec.images == ["data/judge/ref/story_1_ref-quill.png", "data/judge/scene/story_1_s1-1.png"]


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
    client.table.return_value.select.return_value.execute.return_value.data = [{"pair_id": "p1"}]
    with patch("finetune.build_dataset.get_supabase_client", return_value=client):
        assert bd.fetch_annotations() == [{"pair_id": "p1"}]
    client.table.assert_called_once_with("annotations")


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

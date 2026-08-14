"""§6.1 / §10 — the sharegpt build artifact.

Two rules, both silent when broken: the `<image>` token count must equal `len(images)`, and the
`gpt` turn must be byte-identical to what the production verdict schema serializes — otherwise
the model is trained to emit something `providers.judge()` cannot read.
"""
import json

from contracts.story_memory import VlmVerdict
from finetune.manifest import ManifestRecord
from finetune.to_llamafactory import DATASET_INFO, QUESTION, to_sharegpt, write_dataset
from pipeline.consistency_check import SceneVerdict


def record(**overrides) -> ManifestRecord:
    base = dict(
        pair_id="p0",
        char_id="quill_007",
        split="train",
        provenance="synthetic",
        pair_type="pipeline",
        images=["data/judge/ref/quill_007.png", "data/judge/scene/quill_007_s03_a1.png"],
        differences_observed="Two eyes rather than three; the scarf is unstriped.",
        same_character=False,
        label=True,
        anatomy_intact=True,
        text_free=True,
        failure_reasons=["wrong_body_feature", "wrong_clothing"],
    )
    base.update(overrides)
    return ManifestRecord(**base)


def test_image_token_count_equals_the_number_of_images():
    example = to_sharegpt(record())
    human = example["conversations"][0]["value"]
    assert human.count("<image>") == len(example["images"]) == 2
    assert human.startswith("<image><image>")
    assert human.endswith(QUESTION)


def test_bookkeeping_fields_never_reach_the_training_text():
    example = to_sharegpt(record())
    blob = json.dumps(example)
    assert "quill_007" not in example["conversations"][0]["value"]
    assert "split" not in blob and "provenance" not in blob and "pair_type" not in blob


def test_gpt_turn_round_trips_through_the_production_verdict_schema():
    gpt = to_sharegpt(record())["conversations"][1]["value"]

    verdict = VlmVerdict.model_validate_json(gpt)
    assert verdict.same_character is False
    assert verdict.differences_observed == record().differences_observed
    assert verdict.anatomy_intact is True and verdict.text_free is True

    # The wire shape `providers.judge` actually parses in production is the node-local
    # `SceneVerdict` — `VlmVerdict`'s fields in declaration order, then `failure_reasons`.
    scene_verdict = SceneVerdict.model_validate_json(gpt)
    assert [r.value for r in scene_verdict.failure_reasons] == ["wrong_body_feature", "wrong_clothing"]
    assert json.dumps(scene_verdict.model_dump(mode="json")) == gpt


def test_non_gating_fields_take_their_schema_defaults():
    gpt = json.loads(to_sharegpt(record())["conversations"][1]["value"])
    assert gpt["subjects_unique"] is VlmVerdict.model_fields["subjects_unique"].default
    assert gpt["style_match"] is VlmVerdict.model_fields["style_match"].default


def test_write_dataset_emits_one_file_per_split_plus_dataset_info(tmp_path):
    records = [
        record(pair_id="p1", char_id="a", split="train"),
        record(pair_id="p2", char_id="b", split="val", provenance="synthetic", pair_type="pipeline"),
        record(pair_id="p3", char_id="c", split="test", provenance="donated", pair_type="pipeline"),
    ]
    write_dataset(records, tmp_path)

    assert json.loads((tmp_path / "dataset_info.json").read_text(encoding="utf-8")) == DATASET_INFO
    for split, count in [("train", 1), ("val", 1), ("test", 1)]:
        rows = json.loads((tmp_path / f"{split}.json").read_text(encoding="utf-8"))
        assert len(rows) == count
        assert rows[0]["images"] == records[0].images


def test_dataset_info_names_the_files_write_dataset_produces():
    for key, entry in DATASET_INFO.items():
        assert key.startswith("storybuddy_judge_")
        assert entry["formatting"] == "sharegpt"
        assert entry["columns"] == {"messages": "conversations", "images": "images"}

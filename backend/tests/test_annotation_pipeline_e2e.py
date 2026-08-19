import json
from pathlib import Path
from unittest.mock import patch

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
from finetune.manifest import ManifestError
from finetune.to_llamafactory import write_dataset


def mock_memory() -> StoryMemory:
    return StoryMemory(
        schema_version=1,
        story_id="story_e2e",
        classroom_id="c1",
        profile_id="p1",
        input=Input(raw_text="hello world"),
        characters=[
            Character(
                char_id="char_1",
                name="Hero",
                description=CharacterDescription(
                    species="dog", colours=["brown"], body_features=[], clothing=[]
                ),
                canonical_ref_image="ref-1.png",
            )
        ],
        scenes=[
            Scene(
                scene_id="s1",
                text_excerpt="x",
                characters_present=["char_1"],
                attempts=[Attempt(image_ref="scene-1.png")],
            )
        ],
    )


def pair_id() -> str:
    return bd.mint_pair_id("char_1", "scene-1.png")


def assert_sharegpt_valid(tmp_path: Path, expected_label: bool) -> None:
    # Verify dataset_info
    dataset_info = json.loads((tmp_path / "dataset_info.json").read_text(encoding="utf-8"))
    assert "storybuddy_judge_train" in dataset_info

    # Verify train.json
    train_data = json.loads((tmp_path / "train.json").read_text(encoding="utf-8"))
    assert len(train_data) > 0
    record = train_data[0]

    # Verify formatting
    assert "conversations" in record
    assert "images" in record
    assert len(record["images"]) == 2
    assert record["conversations"][0]["value"].startswith("<image><image>")

    # Verify correct label serialized (ShareGPT JSON)
    gpt_turn = json.loads(record["conversations"][1]["value"])
    assert gpt_turn["same_character"] is expected_label


def test_fixture_a_unanimous_agreement(tmp_path: Path) -> None:
    """Fixture A: Annotator A and B submit identical labels.

    - Pair resolves automatically to agreed label.
    - Exported to manifest.
    - ShareGPT contains agreed label.
    """
    mem = mock_memory()
    pid = pair_id()

    annotations = [
        {"pair_id": pid, "annotator_id": "anno_1", "same_character": True, "failure_reasons": []},
        {"pair_id": pid, "annotator_id": "anno_2", "same_character": True, "failure_reasons": []},
    ]

    with patch("finetune.build_dataset.fetch_annotations", return_value=annotations), \
         patch("finetune.build_dataset.fetch_adjudicator_ids", return_value=set()), \
         patch("finetune.build_dataset.fetch_pilot_pairs", return_value=set()):

        manifest_out = tmp_path / "manifest.jsonl"
        records = bd.build_dataset([(mem, "train", "synthetic")], out_path=manifest_out, add_constructed=False)

        # Verify Manifest
        assert len(records) == 1
        assert records[0].same_character is True
        assert records[0].label is False

        # ShareGPT Serialization
        write_dataset(records, tmp_path)
        assert_sharegpt_valid(tmp_path, expected_label=True)


def test_fixture_b_disagreement_and_adjudication(tmp_path: Path) -> None:
    """Fixture B: Annotator A and B submit conflicting labels.

    - Adjudicator submits a 3rd row resolving the conflict.
    - Dataset compilation uses adjudicator label.
    """
    mem = mock_memory()
    pid = pair_id()

    annotations = [
        {"pair_id": pid, "annotator_id": "anno_1", "same_character": True, "failure_reasons": []},
        {"pair_id": pid, "annotator_id": "anno_2", "same_character": False, "failure_reasons": ["wrong_colour"]},
        {"pair_id": pid, "annotator_id": "adj_1", "same_character": False, "failure_reasons": ["wrong_colour"]},
    ]

    with patch("finetune.build_dataset.fetch_annotations", return_value=annotations), \
         patch("finetune.build_dataset.fetch_adjudicator_ids", return_value={"adj_1"}), \
         patch("finetune.build_dataset.fetch_pilot_pairs", return_value=set()):

        manifest_out = tmp_path / "manifest.jsonl"
        records = bd.build_dataset([(mem, "train", "synthetic")], out_path=manifest_out, add_constructed=False)

        # Verify Manifest
        assert len(records) == 1
        assert records[0].same_character is False
        assert records[0].label is True
        assert records[0].failure_reasons == ["wrong_colour"]

        # ShareGPT Serialization
        write_dataset(records, tmp_path)
        assert_sharegpt_valid(tmp_path, expected_label=False)


def test_fixture_c_unresolved_failure(tmp_path: Path) -> None:
    """Fixture C: Annotator A and B submit conflicting labels. NO Adjudicator row.

    - build_dataset.py strictly raises ManifestError and aborts.
    """
    mem = mock_memory()
    pid = pair_id()

    annotations = [
        {"pair_id": pid, "annotator_id": "anno_1", "same_character": True, "failure_reasons": []},
        {"pair_id": pid, "annotator_id": "anno_2", "same_character": False, "failure_reasons": ["wrong_colour"]},
    ]

    with patch("finetune.build_dataset.fetch_annotations", return_value=annotations), \
         patch("finetune.build_dataset.fetch_adjudicator_ids", return_value=set()), \
         patch("finetune.build_dataset.fetch_pilot_pairs", return_value=set()):

        manifest_out = tmp_path / "manifest.jsonl"

        with pytest.raises(ManifestError, match="unresolved conflict"):
            bd.build_dataset([(mem, "train", "synthetic")], out_path=manifest_out, add_constructed=False)

        assert not manifest_out.exists()

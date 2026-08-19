"""Cross-cutting research integrity test suite (Ticket 05 / #49).

Asserts methodological invariants from `judge-finetune.md`:
1. Character-disjoint splits across train/val/test.
2. Test set integrity: 100% donated real-child stories, 0 constructed negatives.
3. Constructed negatives reside strictly in the train split.
4. Data completeness and manifest reconciliation against dataset_manifest.json.
5. Prompt and serialized ShareGPT blinding (no leaked identifiers or split tokens).
"""
import json
from pathlib import Path
import re
from typing import Any

import pytest

from finetune.manifest import (
    ManifestRecord,
    read_manifest,
)

DATA_DIR = Path("data/judge")


# --- Invariant Assertions ---

def assert_character_disjoint_splits(manifest: list[ManifestRecord]) -> None:
    """Assert zero overlap of char_id across train, val, and test splits."""
    splits: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    for r in manifest:
        splits[r.split].add(r.char_id)

    assert splits["train"].isdisjoint(splits["val"]), (
        f"Train and val splits share characters: {splits['train'] & splits['val']}"
    )
    assert splits["train"].isdisjoint(splits["test"]), (
        f"Train and test splits share characters: {splits['train'] & splits['test']}"
    )
    assert splits["val"].isdisjoint(splits["test"]), (
        f"Val and test splits share characters: {splits['val'] & splits['test']}"
    )


def assert_test_set_integrity(manifest: list[ManifestRecord]) -> None:
    """Assert test split contains ONLY real-child donated stories and zero constructed negatives."""
    for r in manifest:
        if r.split == "test":
            assert r.provenance == "donated", (
                f"Test set contains non-donated record {r.pair_id} with provenance={r.provenance!r}"
            )
            assert r.pair_type != "constructed", (
                f"Test set contains constructed negative: {r.pair_id}"
            )


def assert_constructed_negatives_only_in_train(manifest: list[ManifestRecord]) -> None:
    """Assert constructed negatives exist ONLY in train (split == 'train')."""
    for r in manifest:
        if r.pair_type == "constructed":
            assert r.split == "train", (
                f"Constructed negative {r.pair_id} found in {r.split!r} split"
            )


def assert_manifest_reconciliation(manifest: list[ManifestRecord], stats: dict[str, Any]) -> None:
    """Assert manifest records reconcile exactly with dataset_manifest.json stats."""
    overall = stats.get("overall", {})
    assert len(manifest) == overall.get("total_pairs"), (
        f"Manifest total pairs ({len(manifest)}) != stats overall total_pairs ({overall.get('total_pairs')})"
    )
    assert len(set(r.char_id for r in manifest)) == overall.get("characters"), (
        f"Unique characters ({len(set(r.char_id for r in manifest))}) != stats overall characters ({overall.get('characters')})"
    )
    assert sum(1 for r in manifest if r.pair_type == "pipeline") == overall.get("natural_pairs"), (
        "Pipeline natural pairs count mismatch with stats"
    )
    assert sum(1 for r in manifest if r.pair_type == "constructed") == overall.get("constructed_pairs"), (
        "Constructed pairs count mismatch with stats"
    )

    splits_stats = stats.get("splits", {})
    for split in ["train", "val", "test"]:
        split_records = [r for r in manifest if r.split == split]
        split_stat = splits_stats.get(split, {})
        if not split_stat and not split_records:
            continue

        assert len(set(r.char_id for r in split_records)) == split_stat.get("characters"), (
            f"Split {split} character count mismatch"
        )
        assert sum(1 for r in split_records if r.pair_type == "pipeline") == split_stat.get("natural_pairs"), (
            f"Split {split} natural pairs count mismatch"
        )
        assert sum(1 for r in split_records if r.pair_type == "constructed") == split_stat.get("constructed_pairs"), (
            f"Split {split} constructed pairs count mismatch"
        )


def assert_all_records_have_ground_truth(manifest: list[ManifestRecord]) -> None:
    """Assert every record has verified ground truth booleans and failure reasons if negative."""
    for r in manifest:
        assert isinstance(r.same_character, bool), f"Record {r.pair_id} same_character is not bool"
        assert isinstance(r.label, bool), f"Record {r.pair_id} label is not bool"
        assert r.label == (not r.same_character), (
            f"Record {r.pair_id} label is not inverse of same_character"
        )
        if not r.same_character:
            assert isinstance(r.failure_reasons, list), (
                f"Record {r.pair_id} failure_reasons is not list"
            )
            assert len(r.failure_reasons) > 0, (
                f"Record {r.pair_id} is a negative but has no failure reasons."
            )


def assert_sharegpt_blinding(
    manifest: list[ManifestRecord],
    sharegpt: dict[str, list[dict[str, Any]]],
) -> None:
    """Assert serialized ShareGPT prompt conversations contain NO leaked IDs, names, or split tokens."""
    forbidden_ids = set()
    for r in manifest:
        forbidden_ids.add(r.char_id)
        forbidden_ids.add(r.pair_id)

    forbidden_keys = {"split", "provenance", "pair_type", "char_id", "pair_id", "story_id"}

    for split, data in sharegpt.items():
        for item in data:
            for turn in item.get("conversations", []):
                content = turn.get("value", "")

                for forbidden in forbidden_ids:
                    assert forbidden not in content, (
                        f"Leakage: ID {forbidden} found in ShareGPT text ({split})"
                    )

                # Check that bookkeeping metadata keys don't leak into the JSON content
                if turn.get("from") == "gpt":
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, dict):
                            for key in forbidden_keys:
                                assert key not in parsed, (
                                    f"Leakage: bookkeeping key {key!r} found in GPT verdict payload"
                                )
                    except json.JSONDecodeError:
                        pass

                # Check for split identifiers in prompt
                if turn.get("from") == "human":
                    words = re.findall(r"\b\w+\b", content.lower())
                    assert "train" not in words, "Leakage: 'train' identifier found in prompt"
                    assert "val" not in words, "Leakage: 'val' identifier found in prompt"
                    assert "test" not in words, "Leakage: 'test' identifier found in prompt"


# --- Session Fixture for Generated Dataset Artifacts ---

@pytest.fixture(scope="session")
def dataset_artifacts():
    if not (DATA_DIR / "manifest.jsonl").exists():
        pytest.skip("Dataset artifacts not found. Run dataset export first.")

    manifest = read_manifest(DATA_DIR / "manifest.jsonl")
    stats = json.loads((DATA_DIR / "dataset_manifest.json").read_text(encoding="utf-8"))

    sharegpt: dict[str, list[dict[str, Any]]] = {}
    for split in ["train", "val", "test"]:
        path = DATA_DIR / f"{split}.json"
        if path.exists():
            sharegpt[split] = json.loads(path.read_text(encoding="utf-8"))

    return {
        "manifest": manifest,
        "stats": stats,
        "sharegpt": sharegpt,
    }


# --- Artifact Integrity Integration Tests ---

def test_fixture_loads(dataset_artifacts):
    assert "manifest" in dataset_artifacts
    assert "stats" in dataset_artifacts
    assert "sharegpt" in dataset_artifacts


def test_character_disjoint_splits(dataset_artifacts):
    assert_character_disjoint_splits(dataset_artifacts["manifest"])


def test_test_set_integrity(dataset_artifacts):
    assert_test_set_integrity(dataset_artifacts["manifest"])


def test_constructed_negatives_only_in_train(dataset_artifacts):
    assert_constructed_negatives_only_in_train(dataset_artifacts["manifest"])


def test_manifest_reconciliation(dataset_artifacts):
    assert_manifest_reconciliation(dataset_artifacts["manifest"], dataset_artifacts["stats"])


def test_all_records_have_ground_truth(dataset_artifacts):
    assert_all_records_have_ground_truth(dataset_artifacts["manifest"])


def test_sharegpt_blinding(dataset_artifacts):
    assert_sharegpt_blinding(dataset_artifacts["manifest"], dataset_artifacts["sharegpt"])


# --- Unit Tests with Synthetic Fixtures (Exercised in CI) ---

def _sample_record(**overrides) -> ManifestRecord:
    base = dict(
        pair_id="p1",
        char_id="char_a",
        split="train",
        provenance="synthetic",
        pair_type="pipeline",
        images=["data/judge/ref/char_a.png", "data/judge/scene/char_a_s1.png"],
        differences_observed="Attribute match.",
        same_character=True,
        label=False,
        anatomy_intact=True,
        text_free=True,
        failure_reasons=[],
    )
    base.update(overrides)
    return ManifestRecord(**base)


def test_unit_character_disjoint_splits():
    valid = [
        _sample_record(pair_id="p1", char_id="char_1", split="train"),
        _sample_record(pair_id="p2", char_id="char_2", split="val"),
        _sample_record(pair_id="p3", char_id="char_3", split="test", provenance="donated"),
    ]
    assert_character_disjoint_splits(valid)

    invalid = [
        _sample_record(pair_id="p1", char_id="char_overlap", split="train"),
        _sample_record(pair_id="p2", char_id="char_overlap", split="val"),
    ]
    with pytest.raises(AssertionError, match="share characters"):
        assert_character_disjoint_splits(invalid)


def test_unit_test_set_integrity():
    valid = [
        _sample_record(pair_id="p1", char_id="char_1", split="test", provenance="donated"),
    ]
    assert_test_set_integrity(valid)

    invalid_synthetic = [
        _sample_record(pair_id="p1", char_id="char_1", split="test", provenance="synthetic"),
    ]
    with pytest.raises(AssertionError, match="non-donated"):
        assert_test_set_integrity(invalid_synthetic)

    invalid_constructed = [
        _sample_record(pair_id="p1", char_id="char_1", split="test", provenance="donated", pair_type="constructed"),
    ]
    with pytest.raises(AssertionError, match="constructed negative"):
        assert_test_set_integrity(invalid_constructed)


def test_unit_constructed_negatives_only_in_train():
    valid = [
        _sample_record(pair_id="p1", char_id="char_1", split="train", pair_type="constructed"),
        _sample_record(pair_id="p2", char_id="char_2", split="val", pair_type="pipeline"),
    ]
    assert_constructed_negatives_only_in_train(valid)

    invalid_val = [
        _sample_record(pair_id="p1", char_id="char_1", split="val", pair_type="constructed"),
    ]
    with pytest.raises(AssertionError, match="Constructed negative"):
        assert_constructed_negatives_only_in_train(invalid_val)


def test_unit_manifest_reconciliation():
    recs = [
        _sample_record(pair_id="p1", char_id="c1", split="train", pair_type="pipeline"),
        _sample_record(pair_id="p2", char_id="c1", split="train", pair_type="constructed"),
        _sample_record(pair_id="p3", char_id="c2", split="val", pair_type="pipeline"),
        _sample_record(pair_id="p4", char_id="c3", split="test", provenance="donated", pair_type="pipeline"),
    ]
    stats = {
        "overall": {
            "total_pairs": 4,
            "characters": 3,
            "natural_pairs": 3,
            "constructed_pairs": 1,
        },
        "splits": {
            "train": {"characters": 1, "natural_pairs": 1, "constructed_pairs": 1},
            "val": {"characters": 1, "natural_pairs": 1, "constructed_pairs": 0},
            "test": {"characters": 1, "natural_pairs": 1, "constructed_pairs": 0},
        },
    }
    assert_manifest_reconciliation(recs, stats)

    # Mismatch in total pairs
    bad_stats = dict(stats, overall=dict(stats["overall"], total_pairs=99))
    with pytest.raises(AssertionError, match="Manifest total pairs"):
        assert_manifest_reconciliation(recs, bad_stats)


def test_unit_all_records_have_ground_truth():
    valid = [
        _sample_record(pair_id="p1", same_character=True, label=False, failure_reasons=[]),
        _sample_record(pair_id="p2", same_character=False, label=True, failure_reasons=["wrong_colour"]),
    ]
    assert_all_records_have_ground_truth(valid)

    # Negative without failure reasons
    invalid = [
        _sample_record(pair_id="p2", same_character=False, label=True, failure_reasons=[]),
    ]
    with pytest.raises(AssertionError, match="has no failure reasons"):
        assert_all_records_have_ground_truth(invalid)


def test_unit_sharegpt_blinding():
    recs = [_sample_record(pair_id="pair_abc123", char_id="char_xyz789")]
    clean_sharegpt = {
        "train": [
            {
                "conversations": [
                    {"from": "human", "value": "<image><image>Is this the same character?"},
                    {
                        "from": "gpt",
                        "value": json.dumps({
                            "differences_observed": "Attribute match.",
                            "same_character": True,
                            "anatomy_intact": True,
                            "text_free": True,
                            "subjects_unique": True,
                            "style_match": True,
                            "failure_reasons": [],
                        }),
                    },
                ],
                "images": ["ref.png", "scene.png"],
            }
        ]
    }
    assert_sharegpt_blinding(recs, clean_sharegpt)

    # Leaked char_id in human prompt
    leaked_char = {
        "train": [
            {
                "conversations": [
                    {"from": "human", "value": "Check character char_xyz789"},
                    {"from": "gpt", "value": "{}"},
                ]
            }
        ]
    }
    with pytest.raises(AssertionError, match="Leakage: ID char_xyz789"):
        assert_sharegpt_blinding(recs, leaked_char)

    # Leaked metadata key in gpt turn
    leaked_meta = {
        "train": [
            {
                "conversations": [
                    {"from": "human", "value": "<image>Question"},
                    {"from": "gpt", "value": json.dumps({"split": "train", "same_character": True})},
                ]
            }
        ]
    }
    with pytest.raises(AssertionError, match="bookkeeping key 'split'"):
        assert_sharegpt_blinding(recs, leaked_meta)

    # Leaked split token in human prompt
    leaked_split = {
        "train": [
            {
                "conversations": [
                    {"from": "human", "value": "<image> This is for the train split"},
                    {"from": "gpt", "value": "{}"},
                ]
            }
        ]
    }
    with pytest.raises(AssertionError, match="Leakage: 'train' identifier found in prompt"):
        assert_sharegpt_blinding(recs, leaked_split)


def test_end_to_end_research_integrity_pipeline(tmp_path):
    """Generate complete dataset artifacts via build_dataset + to_llamafactory and assert integrity."""
    from unittest.mock import patch
    from contracts.story_memory import (
        Attempt,
        Character,
        CharacterDescription,
        Input,
        Scene,
        StoryMemory,
    )
    from finetune.build_dataset import build_dataset, pairs_from_memory
    from finetune.to_llamafactory import write_dataset

    # Create 3 memories with disjoint characters: c1 (train), c2 (train), c3 (val), c4 (test)
    mem_train = StoryMemory(
        schema_version=1,
        story_id="story_train",
        classroom_id="c1",
        profile_id="p1",
        input=Input(raw_text="train story"),
        characters=[
            Character(
                char_id="char_train_1",
                name="TrainChar1",
                description=CharacterDescription(species="dog", colours=["brown"], body_features=["floppy ears"], clothing=["red vest"]),
                canonical_ref_image="story_train/ref1.png",
            ),
            Character(
                char_id="char_train_2",
                name="TrainChar2",
                description=CharacterDescription(species="cat", colours=["white"], body_features=["green eyes"], clothing=["blue bow"]),
                canonical_ref_image="story_train/ref2.png",
            ),
        ],
        scenes=[
            Scene(scene_id="s1", text_excerpt="s1", characters_present=["char_train_1"], attempts=[Attempt(image_ref="story_train/s1.png")]),
            Scene(scene_id="s2", text_excerpt="s2", characters_present=["char_train_2"], attempts=[Attempt(image_ref="story_train/s2.png")]),
        ],
    )

    mem_val = StoryMemory(
        schema_version=1,
        story_id="story_val",
        classroom_id="c1",
        profile_id="p1",
        input=Input(raw_text="val story"),
        characters=[
            Character(
                char_id="char_val_1",
                name="ValChar1",
                description=CharacterDescription(species="bear", colours=["black"], body_features=["round ears"], clothing=["yellow scarf"]),
                canonical_ref_image="story_val/ref1.png",
            ),
        ],
        scenes=[
            Scene(scene_id="s1", text_excerpt="s1", characters_present=["char_val_1"], attempts=[Attempt(image_ref="story_val/s1.png")]),
        ],
    )

    mem_test = StoryMemory(
        schema_version=1,
        story_id="story_test",
        classroom_id="c1",
        profile_id="p1",
        input=Input(raw_text="test story"),
        characters=[
            Character(
                char_id="char_test_1",
                name="TestChar1",
                description=CharacterDescription(species="fox", colours=["orange"], body_features=["bushy tail"], clothing=["green cap"]),
                canonical_ref_image="story_test/ref1.png",
            ),
        ],
        scenes=[
            Scene(scene_id="s1", text_excerpt="s1", characters_present=["char_test_1"], attempts=[Attempt(image_ref="story_test/s1.png")]),
        ],
    )

    # Collect pairs and generate valid annotations
    train_pairs = pairs_from_memory(mem_train)
    val_pairs = pairs_from_memory(mem_val)
    test_pairs = pairs_from_memory(mem_test)

    annotations = [
        # train_pairs[0]: agreeing same
        {"pair_id": train_pairs[0].pair_id, "annotator_id": "a1", "same_character": True, "failure_reasons": []},
        {"pair_id": train_pairs[0].pair_id, "annotator_id": "a2", "same_character": True, "failure_reasons": []},
        # train_pairs[1]: disagreeing + adjudicated negative
        {"pair_id": train_pairs[1].pair_id, "annotator_id": "a1", "same_character": True, "failure_reasons": []},
        {"pair_id": train_pairs[1].pair_id, "annotator_id": "a2", "same_character": False, "failure_reasons": ["wrong_colour"]},
        {"pair_id": train_pairs[1].pair_id, "annotator_id": "adj1", "same_character": False, "failure_reasons": ["wrong_colour"]},
        # val_pairs[0]: agreeing same
        {"pair_id": val_pairs[0].pair_id, "annotator_id": "a1", "same_character": True, "failure_reasons": []},
        {"pair_id": val_pairs[0].pair_id, "annotator_id": "a2", "same_character": True, "failure_reasons": []},
        # test_pairs[0]: agreeing negative
        {"pair_id": test_pairs[0].pair_id, "annotator_id": "a1", "same_character": False, "failure_reasons": ["wrong_clothing"]},
        {"pair_id": test_pairs[0].pair_id, "annotator_id": "a2", "same_character": False, "failure_reasons": ["wrong_clothing"]},
    ]

    corpus = [
        (mem_train, "train", "synthetic"),
        (mem_val, "val", "synthetic"),
        (mem_test, "test", "donated"),
    ]

    manifest_path = tmp_path / "manifest.jsonl"
    with patch("finetune.build_dataset.fetch_annotations", return_value=annotations), \
         patch("finetune.build_dataset.fetch_adjudicator_ids", return_value={"adj1"}), \
         patch("finetune.build_dataset.fetch_pilot_pairs", return_value=set()):
        records = build_dataset(corpus, out_path=manifest_path, add_constructed=True)

    write_dataset(records, tmp_path)

    # Load artifacts and verify every invariant
    manifest = read_manifest(manifest_path)
    stats = json.loads((tmp_path / "dataset_manifest.json").read_text(encoding="utf-8"))
    sharegpt = {
        split: json.loads((tmp_path / f"{split}.json").read_text(encoding="utf-8"))
        for split in ["train", "val", "test"]
    }

    assert_character_disjoint_splits(manifest)
    assert_test_set_integrity(manifest)
    assert_constructed_negatives_only_in_train(manifest)
    assert_manifest_reconciliation(manifest, stats)
    assert_all_records_have_ground_truth(manifest)
    assert_sharegpt_blinding(manifest, sharegpt)


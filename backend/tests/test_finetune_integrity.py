"""Integrity guards for Objective-4 training, validation, and evaluation pipeline."""
from pathlib import Path
import pytest
import yaml

from finetune import evaluate as ev
from finetune import train as tr
from finetune.manifest import ManifestError, ManifestRecord


def test_train_yaml_pins_match_frozen_pre_registration():
    yaml_path = Path(__file__).resolve().parent.parent / "finetune" / "train_qlora.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    assert data["model_name_or_path"] == "Qwen/Qwen2.5-VL-7B-Instruct"
    assert data["model_revision"] == "cc594898137f460bfe9f0759e9844b3ce807cfb5"
    assert data["cutoff_len"] == 2048
    assert data["template"] == "qwen2_vl"
    assert data["lora_rank"] == 16
    assert data["lora_alpha"] == 32
    assert data["report_to"] == "none"


def test_constants_match_across_train_and_evaluate():
    assert tr.BASE_MODEL == ev.BASE_MODEL == "Qwen/Qwen2.5-VL-7B-Instruct"
    assert tr.BASE_REVISION == ev.BASE_REVISION == "cc594898137f460bfe9f0759e9844b3ce807cfb5"
    assert tr.LLAMAFACTORY_VERSION == ev.LLAMAFACTORY_VERSION == "v0.9.5"
    assert tr.LLAMAFACTORY_COMMIT == ev.LLAMAFACTORY_COMMIT == "7af909522a951e3ad9f022ea6f88b6755257eaa5"
    assert tr.SEEDS == ev.SEEDS == (0, 1, 2)


def test_split_isolation_and_no_leakage(tmp_path, monkeypatch):
    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    for f in ("manifest.jsonl", "manifest.train.jsonl", "manifest.val.jsonl", "manifest.test.jsonl",
              "train.json", "val.json", "dataset_info.json", "dataset_manifest.json", "freeze_report.json"):
        (freeze_dir / f).write_text("{}", encoding="utf-8")

    monkeypatch.setattr("finetune.train._validate_freeze", lambda f: {"dataset_sha256": "abc"})

    yaml_path = tmp_path / "train.yaml"
    yaml_path.write_text(yaml.safe_dump(tr.FIXED_CONFIG_PINS), encoding="utf-8")

    # Training preparation only references train_llamafactory.json and train split
    plan = tr.prepare(freeze=freeze_dir, run_root=tmp_path / "runs", config=yaml_path)
    for run in plan["runs"]:
        cmd_str = " ".join(run["command"])
        assert "manifest.test.jsonl" not in cmd_str



def test_heldout_fails_closed_if_test_manifest_modified_after_lock(tmp_path):
    import json
    import hashlib

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()
    r_test = ManifestRecord(
        pair_id="p_test",
        char_id="c1",
        split="test",
        provenance="donated",
        pair_type="pipeline",
        images=["a.png", "b.png"],
        differences_observed="none",
        same_character=True,
        label=False,
        failure_reasons=[],
    )
    test_mf = freeze_dir / "manifest.test.jsonl"
    test_mf.write_text(json.dumps(r_test.model_dump(mode="json")) + "\n", encoding="utf-8")
    for split in ("train", "val"):
        (freeze_dir / f"manifest.{split}.jsonl").write_text("", encoding="utf-8")

    valid_lock = {
        "schema_version": 1,
        "bootstrap_seed": 0,
        "base_model": "Qwen/Qwen2.5-VL-7B-Instruct",
        "base_revision": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
        "llamafactory_version": "v0.9.5",
        "llamafactory_commit": "7af909522a951e3ad9f022ea6f88b6755257eaa5",
        "deployment_seed": 0,
        "seeds": [0, 1, 2],
        "selected_checkpoints": {
            f"seed_{s}": {
                "checkpoint_id": "checkpoint-050",
                "step": 50,
                "path": f"runs/seed-{s}/output/checkpoint-050",
                "sha256": "a" * 64,
                "val_f1": 0.85,
            }
            for s in (0, 1, 2)
        },
        "controls": {
            "clip_cosine": {"threshold": 0.75, "val_f1": 0.65},
            "dinov2_cosine": {"threshold": 0.80, "val_f1": 0.70},
        },
        "manifest_hashes": {
            "manifest.train.jsonl": "1" * 64,
            "manifest.val.jsonl": "2" * 64,
            "manifest.test.jsonl": hashlib.sha256(test_mf.read_bytes()).hexdigest(),
        },
        "prompt_version": "4",
        "vlm_judge_model": "google/gemma-3-27b-it",
    }

    lock_path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    ledger_path = tmp_path / "access_ledger.json"

    # Modify test manifest after lock was created with a different valid record
    r_test_mod = r_test.model_copy(update={"pair_id": "p_test_2"})
    test_mf.write_text(json.dumps(r_test_mod.model_dump(mode="json")) + "\n", encoding="utf-8")

    with pytest.raises(ManifestError, match="mismatch against evaluation lock"):
        ev.run_heldout(
            freeze_dir=freeze_dir,
            lock_path=lock_path,
            ledger_path=ledger_path,
            run_id="run-1",
            approver="Hanseooo",
            purpose="test",
            predictions_dir=tmp_path / "preds",
            predict_fn=lambda j, r: ev.JudgeObservation(prediction=True, confidence=0.9, latency_ms=10),
        )


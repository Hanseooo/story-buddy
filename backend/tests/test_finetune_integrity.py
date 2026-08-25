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
    hardware = {"gpu": "gpu", "torch": "torch", "cuda": "cuda", "bitsandbytes": "bnb"}
    monkeypatch.setattr("finetune.train._validate_qualification", lambda p: {"hardware": hardware})

    yaml_path = tmp_path / "train.yaml"
    yaml_path.write_text(yaml.safe_dump(tr.FIXED_CONFIG_PINS | {
        "dataset_dir": tr.DATASET_DIR_SENTINEL,
    }), encoding="utf-8")
    (tmp_path / "qualification.json").write_text("{}", encoding="utf-8")

    # Training preparation only references train_llamafactory.json and train split
    plan = tr.prepare(
        freeze=freeze_dir, run_root=tmp_path / "runs", config=yaml_path,
        qualification=tmp_path / "qualification.json",
    )
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

    checkpoints = {}
    for seed in (0, 1, 2):
        checkpoint = tmp_path / "runs" / f"seed-{seed}" / "output" / "checkpoint-50"
        checkpoint.mkdir(parents=True)
        (checkpoint / "adapter_model.safetensors").write_bytes(f"seed-{seed}".encode())
        checkpoints[seed] = checkpoint

    valid_lock = {
        "schema_version": ev.PREDICTION_SCHEMA_VERSION,
        "bootstrap_seed": 0,
        "base_model": "Qwen/Qwen2.5-VL-7B-Instruct",
        "base_revision": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
        "llamafactory_version": "v0.9.5",
        "llamafactory_commit": "7af909522a951e3ad9f022ea6f88b6755257eaa5",
        "deployment_seed": 0,
        "seeds": [0, 1, 2],
        "selected_checkpoints": {
                f"seed_{s}": {
                    "model_id": f"seed{s}_checkpoint50",
                    "checkpoint_id": "checkpoint-50",
                    "step": 50,
                    "path": str(checkpoints[s]),
                    "sha256": ev._hash_directory(checkpoints[s]),
                "val_f1": 0.85,
            }
            for s in (0, 1, 2)
        },
        "controls": {
            "clip_cosine": {"threshold": 0.75, "val_f1": 0.65, "selected_on": "manifest.val.jsonl"},
            "dinov2_cosine": {"threshold": 0.80, "val_f1": 0.70, "selected_on": "manifest.val.jsonl"},
        },
        "manifest_hashes": {
            "manifest.train.jsonl": "1" * 64,
            "manifest.val.jsonl": "2" * 64,
            "manifest.test.jsonl": hashlib.sha256(test_mf.read_bytes()).hexdigest(),
        },
        "report_artifact_hashes": {
            "annotation_agreement.jsonl": "4" * 64,
            "character_slices.json": "5" * 64,
        },
        "prompt_version": "4",
        "vlm_judge_model": "google/gemma-3-27b-it",
    }

    lock_path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(lock_path, valid_lock)
    ledger_path = tmp_path / "access_ledger.json"
    signoff_path = tmp_path / "evaluation_signoff.json"
    signoff_path.write_text(json.dumps({
        "evaluation_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "approved_by": "Hanseooo",
        "approved_at": "2026-08-25T12:00:00+08:00",
    }), encoding="utf-8")

    # Modify test manifest after lock was created with a different valid record
    r_test_mod = r_test.model_copy(update={"pair_id": "p_test_2"})
    test_mf.write_text(json.dumps(r_test_mod.model_dump(mode="json")) + "\n", encoding="utf-8")

    with pytest.raises(ManifestError, match="mismatch against evaluation lock"):
        ev.run_heldout(
                freeze_dir=freeze_dir,
                lock_path=lock_path,
                signoff_path=signoff_path,
                ledger_path=ledger_path,
                run_id="run-1",
                predictions_dir=tmp_path / "preds",
                report_path=tmp_path / "report.json",
            predict_fn=lambda j, r: ev.JudgeObservation(prediction=True, confidence=0.9, latency_ms=10),
        )

"""Tests for pinned three-seed training runner and preflight."""
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from finetune import train
from finetune.manifest import ManifestError

CONFIG = Path(__file__).resolve().parent.parent / "finetune" / "train_qlora.yaml"


def make_record(pair_id: str, split: str) -> dict:
    return {
        "pair_id": pair_id,
        "char_id": "story:char",
        "split": split,
        "provenance": "synthetic",
        "pair_type": "pipeline",
        "images": ["ref.png", "scene.webp"],
        "differences_observed": "none",
        "same_character": True,
        "label": False,
        "failure_reasons": [],
    }


def frozen_fixture(tmp_path: Path) -> Path:
    freeze = tmp_path / "freeze"
    freeze.mkdir(parents=True, exist_ok=True)
    r1 = make_record("p1", "train")
    r2 = make_record("p2", "val")
    (freeze / "manifest.jsonl").write_text(json.dumps(r1) + "\n" + json.dumps(r2) + "\n", encoding="utf-8")
    (freeze / "manifest.train.jsonl").write_text(json.dumps(r1) + "\n", encoding="utf-8")
    (freeze / "manifest.val.jsonl").write_text(json.dumps(r2) + "\n", encoding="utf-8")
    (freeze / "train.json").write_bytes(b'[]\n')
    (freeze / "val.json").write_bytes(b'[]\n')
    (freeze / "dataset_info.json").write_bytes(b'{}\n')
    (freeze / "dataset_manifest.json").write_bytes(b'{}\n')
    report = {
        "dataset_sha256": hashlib.sha256((freeze / "manifest.jsonl").read_bytes()).hexdigest(),
        "counts": {},
        "adjudication_rate": 0.0,
        "exclusions": [],
        "pinned_versions": {},
        "artifact_sha256": {
            "manifest.train.jsonl": hashlib.sha256((freeze / "manifest.train.jsonl").read_bytes()).hexdigest(),
            "manifest.val.jsonl": hashlib.sha256((freeze / "manifest.val.jsonl").read_bytes()).hexdigest(),
            "manifest.test.jsonl": "0" * 64,
            "annotation_agreement.jsonl": "0" * 64,
            "character_slices.json": "0" * 64,
        },
    }
    (freeze / "freeze_report.json").write_text(json.dumps(report), encoding="utf-8")
    return freeze



def qualified_inventory() -> dict[str, str]:
    return {
        "os": "Linux-x86_64",
        "python": "3.12.10",
        "gpu": "NVIDIA A10G, 24576 MiB, 555.42.02",
        "torch": "2.5.1+cu124",
        "cuda": "12.4",
        "bitsandbytes": "0.45.0",
    }


def test_prepare_records_exactly_three_seed_commands_without_execution(tmp_path, monkeypatch):
    freeze = frozen_fixture(tmp_path)
    run_root = tmp_path / "runs"
    called = []

    def record(command, **kwargs):
        called.append(command)
        output = "a" * 40 if command[:2] == ["git", "rev-parse"] else "fixture"
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr(train.subprocess, "run", record)

    plan = train.prepare(freeze, run_root, CONFIG, report_to="none")

    assert not any(command[0] == "llamafactory-cli" for command in called)
    assert [item["seed"] for item in plan["runs"]] == [0, 1, 2]
    for seed, item in enumerate(plan["runs"]):
        command = item["command"]
        assert command[:3] == ["llamafactory-cli", "train", str(CONFIG)]
        assert f"seed={seed}" in command
        assert f"run_name=judge-qlora-seed{seed}" in command
        assert "report_to=none" in command
        assert not any("test" in value for value in command if not value.startswith("output_dir="))


def test_prepare_rejects_placeholder_revision_and_test_dataset(tmp_path):
    freeze = frozen_fixture(tmp_path)
    bad = tmp_path / "bad.yaml"
    bad.write_text(CONFIG.read_text().replace(
        train.BASE_REVISION, "PIN_THE_EXACT_COMMIT_HASH"
    ).replace("eval_dataset: storybuddy_judge_val", "eval_dataset: storybuddy_judge_test"))
    with pytest.raises(ManifestError, match="model_revision"):
        train.prepare(freeze, tmp_path / "runs", bad, report_to="none")


def test_execute_rejects_unqualified_hardware_before_child_process(tmp_path, monkeypatch):
    freeze = frozen_fixture(tmp_path)
    run_root = tmp_path / "runs"
    train.prepare(freeze, run_root, CONFIG, report_to="none")
    monkeypatch.setattr(train, "hardware_inventory", lambda: {
        "torch": "", "cuda": "", "bitsandbytes": "", "gpu": ""
    })
    with pytest.raises(ManifestError, match="hardware qualification"):
        train.execute(freeze, run_root, CONFIG, report_to="none", spend_alarm_confirmed=True)


def test_execute_requires_explicit_spend_alarm_confirmation(tmp_path):
    with pytest.raises(ManifestError, match="spend alarm"):
        train.execute(frozen_fixture(tmp_path), tmp_path / "runs", CONFIG, "none", False)


def test_execute_runs_seeds_in_order_and_stops_on_first_failure(tmp_path, monkeypatch):
    freeze = frozen_fixture(tmp_path)
    run_root = tmp_path / "runs"
    monkeypatch.setattr(train, "hardware_inventory", qualified_inventory)
    commands = []

    def fake_run(command, **kwargs):
        if command[0] == "nvidia-smi":
            return subprocess.CompletedProcess(command, 0, "GPU, 24 GiB, 555", "")
        if command[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(command, 0, "a" * 40, "")
        if command[:2] == ["llamafactory-cli", "version"]:
            return subprocess.CompletedProcess(command, 0, "v0.9.5", "")
        commands.append(command)
        if "seed=1" in command:
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(train.subprocess, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        train.execute(freeze, run_root, CONFIG, report_to="none", spend_alarm_confirmed=True)
    assert [next(value for value in command if value.startswith("seed=")) for command in commands] == [
        "seed=0", "seed=1"
    ]


def test_prepare_rejects_mutated_fixed_yaml_keys(tmp_path):
    freeze = frozen_fixture(tmp_path)
    bad = tmp_path / "bad.yaml"
    bad.write_text(CONFIG.read_text().replace("lora_rank: 16", "lora_rank: 32"))
    with pytest.raises(ManifestError, match="lora_rank"):
        train.prepare(freeze, tmp_path / "runs", bad, report_to="none")


def test_prepare_rejects_mutated_existing_run_plan(tmp_path, monkeypatch):
    freeze = frozen_fixture(tmp_path)
    run_root = tmp_path / "runs"

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, "a" * 40, "")

    monkeypatch.setattr(train.subprocess, "run", fake_run)
    train.prepare(freeze, run_root, CONFIG, report_to="none")
    plan_path = run_root / "seed-0" / "run_plan.json"
    plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_data["seed"] = 99
    plan_path.write_text(json.dumps(plan_data), encoding="utf-8")
    with pytest.raises(ManifestError, match="immutable run plan differs"):
        train.prepare(freeze, run_root, CONFIG, report_to="none")

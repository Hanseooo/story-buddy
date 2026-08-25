"""Pinned three-seed training preflight and runner for Objective-4 QLoRA."""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import yaml

from finetune.manifest import ManifestError, read_manifest

BASE_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"
BASE_REVISION = "cc594898137f460bfe9f0759e9844b3ce807cfb5"
LLAMAFACTORY_VERSION = "v0.9.5"
LLAMAFACTORY_COMMIT = "7af909522a951e3ad9f022ea6f88b6755257eaa5"
SEEDS = (0, 1, 2)
ALLOWED_OVERRIDES = {"seed", "output_dir", "run_name", "report_to"}
DATASET_DIR_SENTINEL = "__SELECTED_FREEZE__"
TRAINING_ARTIFACTS = (
    "manifest.jsonl", "manifest.train.jsonl", "manifest.val.jsonl",
    "train.json", "val.json", "dataset_info.json", "dataset_manifest.json",
)

FIXED_CONFIG_PINS = {
    "model_name_or_path": BASE_MODEL,
    "model_revision": BASE_REVISION,
    "stage": "sft",
    "do_train": True,
    "finetuning_type": "lora",
    "lora_rank": 16,
    "lora_alpha": 32,
    "lora_target": "all",
    "quantization_bit": 4,
    "quantization_method": "bnb",
    "dataset": "storybuddy_judge_train",
    "eval_dataset": "storybuddy_judge_val",
    "template": "qwen2_vl",
    "cutoff_len": 2048,
    "image_max_pixels": 262144,
    "per_device_train_batch_size": 1,
    "gradient_accumulation_steps": 8,
    "learning_rate": 1.0e-4,
    "num_train_epochs": 3.0,
    "lr_scheduler_type": "cosine",
    "warmup_ratio": 0.1,
    "bf16": True,
    "gradient_checkpointing": True,
    "eval_strategy": "steps",
    "eval_steps": 50,
    "load_best_model_at_end": True,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hardware_inventory() -> dict[str, str]:
    gpu_info = ""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            check=False, capture_output=True, text=True,
        )
        if result.returncode == 0:
            gpu_info = result.stdout.strip()
    except (FileNotFoundError, PermissionError):
        pass

    versions = {"torch": "", "cuda": "", "bitsandbytes": ""}
    try:
        import torch
        import bitsandbytes
        versions = {
            "torch": getattr(torch, "__version__", ""),
            "cuda": str(getattr(getattr(torch, "version", None), "cuda", "") or ""),
            "bitsandbytes": getattr(bitsandbytes, "__version__", ""),
        }
    except ImportError:
        pass
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "gpu": gpu_info,
        **versions,
    }


def installed_llamafactory_commit() -> str:
    tool_root = Path(subprocess.run(
        ["uv", "tool", "dir"], capture_output=True, text=True, check=True,
    ).stdout.strip()) / "llamafactory"
    records = [
        path for path in tool_root.rglob("direct_url.json")
        if path.parent.name.startswith("llamafactory-")
    ]
    if len(records) != 1:
        raise ManifestError(f"cannot locate installed LLaMA-Factory provenance under {tool_root}")
    direct_url = json.loads(records[0].read_text(encoding="utf-8"))
    return str(direct_url.get("vcs_info", {}).get("commit_id", ""))


def command_for(config: Path, freeze: Path, seed: int, seed_dir: Path, report_to: str) -> list[str]:
    return [
        "llamafactory-cli", "train", str(config),
        f"dataset_dir={freeze.resolve()}",
        f"seed={seed}",
        f"output_dir={seed_dir / 'output'}",
        f"run_name=judge-qlora-seed{seed}",
        f"report_to={report_to}",
    ]


def _validate_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise ManifestError(f"config file not found: {config_path}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ManifestError(f"invalid config YAML: {config_path}")

    for key, expected in FIXED_CONFIG_PINS.items():
        actual = raw.get(key)
        if actual != expected:
            raise ManifestError(f"config key {key} differs from fixed pin: expected {expected!r}, got {actual!r}")

    eval_dataset = raw.get("eval_dataset", "")
    if eval_dataset != "storybuddy_judge_val" or "test" in eval_dataset:
        raise ManifestError(f"invalid eval_dataset in config: {eval_dataset}")
    if "test" in raw.get("dataset", ""):
        raise ManifestError(f"test dataset forbidden in training config: {raw.get('dataset')}")
    if raw.get("dataset_dir") != DATASET_DIR_SENTINEL:
        raise ManifestError(f"dataset_dir must be {DATASET_DIR_SENTINEL!r}; got {raw.get('dataset_dir')!r}")

    return raw



def _validate_freeze(freeze: Path) -> dict:
    if not freeze.exists():
        raise ManifestError(f"freeze directory not found: {freeze}")
    manifest_path = freeze / "manifest.jsonl"
    if not manifest_path.exists():
        raise ManifestError(f"manifest.jsonl not found in freeze: {freeze}")

    freeze_report_path = freeze / "freeze_report.json"
    if not freeze_report_path.exists():
        raise ManifestError(f"freeze_report.json not found in freeze: {freeze}")

    freeze_report = json.loads(freeze_report_path.read_text(encoding="utf-8"))
    artifact_hashes = freeze_report.get("artifact_sha256", {})

    for required_file in TRAINING_ARTIFACTS:
        artifact = freeze / required_file
        if not artifact.exists():
            raise ManifestError(f"required dataset artifact missing: {required_file}")
        recorded = freeze_report.get("dataset_sha256") if required_file == "manifest.jsonl" else artifact_hashes.get(required_file)
        if sha256(artifact) != recorded:
            raise ManifestError(f"{required_file} hash does not match freeze_report.json")

    # Read train and val manifest records to ensure validity
    read_manifest(freeze / "manifest.train.jsonl")
    read_manifest(freeze / "manifest.val.jsonl")

    return freeze_report


def _validate_qualification(path: Path) -> dict:
    if not path.exists():
        raise ManifestError(f"training qualification not found: {path}")
    record = json.loads(path.read_text(encoding="utf-8"))
    pins = {
        "base_model": BASE_MODEL,
        "base_revision": BASE_REVISION,
        "llamafactory_version": LLAMAFACTORY_VERSION,
        "llamafactory_commit": LLAMAFACTORY_COMMIT,
    }
    for key, expected in pins.items():
        if record.get(key) != expected:
            raise ManifestError(f"qualification {key} differs from fixed pin: expected {expected!r}, got {record.get(key)!r}")
    installed_commit = installed_llamafactory_commit()
    if installed_commit != LLAMAFACTORY_COMMIT:
        raise ManifestError(
            f"installed LLaMA-Factory commit differs from fixed pin: expected {LLAMAFACTORY_COMMIT}, "
            f"got {installed_commit or '<missing>'}"
        )
    approved = record.get("hardware")
    live = hardware_inventory()
    if not isinstance(approved, dict) or approved != live or any(not approved.get(key) for key in ("gpu", "torch", "cuda", "bitsandbytes")):
        raise ManifestError(f"hardware does not match approved qualification: approved={approved}, live={live}")
    return record


def prepare(freeze: Path, run_root: Path, config: Path, qualification: Path, report_to: str = "none") -> dict:
    freeze, run_root, config, qualification = map(Path, (freeze, run_root, config, qualification))
    _validate_config(config)
    freeze_report = _validate_freeze(freeze)
    qualification_record = _validate_qualification(qualification)
    freeze_sha = freeze_report.get("dataset_sha256") or sha256(freeze / "manifest.jsonl")

    try:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        git_commit = "unknown"

    run_root.mkdir(parents=True, exist_ok=True)
    runs = []

    for seed in SEEDS:
        seed_dir = run_root / f"seed-{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        command = command_for(config, freeze, seed, seed_dir, report_to)
        run_plan = {
            "seed": seed,
            "base_model": BASE_MODEL,
            "base_revision": BASE_REVISION,
            "llamafactory_version": LLAMAFACTORY_VERSION,
            "llamafactory_commit": LLAMAFACTORY_COMMIT,
            "uv_install_command": (
                f"uv tool install --python 3.12 \"llamafactory @ "
                f"git+https://github.com/hiyouga/LLaMA-Factory.git@{LLAMAFACTORY_COMMIT}\""
            ),
            "git_commit": git_commit,
            "freeze_path": str(freeze),
            "freeze_dataset_sha256": freeze_sha,
            "config_path": str(config),
            "config_sha256": sha256(config),
            "qualification_path": str(qualification),
            "qualification_sha256": sha256(qualification),
            "hardware": qualification_record["hardware"],
            "command": command,
        }
        plan_file = seed_dir / "run_plan.json"
        plan_text = json.dumps(run_plan, indent=2, sort_keys=True) + "\n"
        if plan_file.exists():
            existing_text = plan_file.read_text(encoding="utf-8")
            if json.loads(existing_text) != json.loads(plan_text):
                raise ManifestError(f"immutable run plan differs in {seed_dir}")
        else:
            plan_file.write_text(plan_text, encoding="utf-8")

        runs.append(run_plan)

    return {
        "freeze": str(freeze),
        "run_root": str(run_root),
        "runs": runs,
    }


def execute(
    freeze: Path,
    run_root: Path,
    config: Path,
    qualification: Path,
    report_to: str = "none",
    spend_alarm_confirmed: bool = False,
) -> dict:
    if not spend_alarm_confirmed:
        raise ManifestError("explicit spend alarm confirmation is required before training execution")

    plan = prepare(freeze, run_root, config, qualification, report_to=report_to)
    hardware = hardware_inventory()

    for key in ("gpu", "torch", "cuda", "bitsandbytes"):
        if not hardware.get(key):
            raise ManifestError(f"hardware qualification failed: {key} is unpopulated ({hardware})")

    version_proc = subprocess.run(
        ["llamafactory-cli", "version"],
        capture_output=True, text=True, check=True,
    )
    version_output = version_proc.stdout.strip()
    if LLAMAFACTORY_VERSION not in version_output:
        raise ManifestError(
            f"LLaMA-Factory version mismatch: expected {LLAMAFACTORY_VERSION}, got {version_output}"
        )

    for item in plan["runs"]:
        seed = item["seed"]
        seed_dir = Path(run_root) / f"seed-{seed}"
        hw_file = seed_dir / "hardware.json"
        hw_text = json.dumps(hardware, indent=2, sort_keys=True) + "\n"
        if hw_file.exists():
            if json.loads(hw_file.read_text(encoding="utf-8")) != json.loads(hw_text):
                raise ManifestError(f"immutable hardware record differs in {seed_dir}")
        else:
            hw_file.write_text(hw_text, encoding="utf-8")

        log_path = seed_dir / "stdout.log"
        command = item["command"]
        with open(log_path, "a", encoding="utf-8") as log_file:
            subprocess.run(command, stdout=log_file, stderr=subprocess.STDOUT, check=True)

    return {"status": "completed", "plan": plan, "hardware": hardware}


def main():
    parser = argparse.ArgumentParser(description="Three-seed QLoRA training runner for Objective-4")
    parser.add_argument("--freeze", required=True, type=Path, help="Path to frozen dataset directory")
    parser.add_argument("--run-root", required=True, type=Path, help="Path to training runs directory")
    parser.add_argument(
        "--config", type=Path,
        default=Path(__file__).resolve().parent / "train_qlora.yaml",
        help="Path to training config YAML",
    )
    parser.add_argument("--qualification", required=True, type=Path, help="Approved toolchain and hardware record")
    parser.add_argument("--report-to", choices=["none", "wandb"], default="none", help="Experiment reporting target")

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--prepare", action="store_true", help="Preflight and write immutable run plans")
    mode_group.add_argument("--execute", action="store_true", help="Execute three seed training runs sequentially")

    parser.add_argument("--spend-alarm-confirmed", action="store_true", help="Confirm spend alarm active")

    args = parser.parse_args()

    if args.prepare:
        plan = prepare(args.freeze, args.run_root, args.config, args.qualification, report_to=args.report_to)
        print(json.dumps(plan, indent=2, sort_keys=True))
    elif args.execute:
        result = execute(
            args.freeze, args.run_root, args.config, args.qualification,
            report_to=args.report_to, spend_alarm_confirmed=args.spend_alarm_confirmed,
        )
        print(f"Executed training successfully: {result['status']}")


if __name__ == "__main__":
    main()

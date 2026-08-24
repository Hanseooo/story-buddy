# Objective-4 Training and Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the zero-cost controls and offline commands needed to train three pinned consistency-judge adapters, select only on validation, and run one auditable held-out evaluation with the preregistered statistics.

**Architecture:** Keep the combined frozen manifest authoritative while adding deterministic split projections and de-identified evaluation evidence. A small repository-native runner validates and records three LLaMA-Factory invocations; the offline evaluator captures immutable predictions, uses standard-library statistics, locks validation choices before test access, and reserves held-out reads in an append-only file ledger. Production `providers.judge()` remains unchanged; only an additive metadata-returning provider seam is introduced.

**Tech Stack:** Python 3.12 standard library, existing Pydantic and PyYAML installations, pytest, existing OpenAI client, LLaMA-Factory `v0.9.5` at `7af909522a951e3ad9f022ea6f88b6755257eaa5`, Qwen2.5-VL revision `cc594898137f460bfe9f0759e9844b3ce807cfb5`.

**Spec:** `docs/specs/judge-finetune.md`, `docs/specs/research-corpus-operations.md`, and `docs/product/PREREGISTRATION_OBJ4.md`

## Global Constraints

- Do not read `.env`, real donated inputs, `manifest.test.jsonl`, or `test.json` while implementing or testing.
- Deterministic tests mock every model and child-process call; real model evaluation remains Tier B and outside CI.
- Do not add Torch, Transformers, bitsandbytes, LLaMA-Factory, scipy, numpy, or statsmodels to the production backend environment.
- Keep `providers.judge(prompt, image_urls, schema, model=None) -> T` unchanged.
- Base model is `Qwen/Qwen2.5-VL-7B-Instruct` at revision `cc594898137f460bfe9f0759e9844b3ce807cfb5`.
- LLaMA-Factory is `v0.9.5` at commit `7af909522a951e3ad9f022ea6f88b6755257eaa5`.
- Training seeds are `0`, `1`, and `2`; bootstrap seed is `0`; evaluation temperature is `0`.
- Only `seed`, `output_dir`, `run_name`, and `report_to` may vary between training invocations.
- W&B is optional; immutable local files are the canonical evidence.
- `manifest.jsonl` stays the hashed source of truth. Training reads `manifest.train.jsonl`; selection reads `manifest.val.jsonl`; only the guarded held-out command reads `manifest.test.jsonl`.
- Select checkpoints, the deployment seed, and CLIP/DINOv2 thresholds on validation only. Never select or tune from test results.
- A first held-out run evaluates three selected seed checkpoints plus zero-shot Qwen, prompted Gemma, CLIP, and DINOv2. Only a completed Rung-D report plus a dated deviation permits one second read; a third read is always rejected.
- Scope ends at in-domain Objective-4 results. DreamBench++, Objective-3 downstream evaluation, data-scaling ablation, and deployment are excluded.

---

## File Map

- Modify `backend/finetune/freeze_dataset.py`: emit and hash split manifests, agreement labels, and character slices.
- Modify `backend/finetune/train_qlora.yaml`: replace placeholders and make local reporting the default.
- Create `backend/finetune/train.py`: preflight, run evidence, and the three controlled LLaMA-Factory invocations.
- Create `backend/finetune/evaluation_metrics.py`: pure standard-library metrics.
- Modify `backend/providers.py`: additive rich judge result and logprob/latency call.
- Replace the orchestration in `backend/finetune/evaluate.py`: prediction evidence, validation selection, evaluation lock, access ledger, result aggregation, and CLI.
- Modify `backend/tests/test_finetune_dataset.py`: frozen-artifact contract tests.
- Create `backend/tests/test_finetune_train.py`: runner preflight and invocation tests.
- Create `backend/tests/test_finetune_evaluation_metrics.py`: known-value and degenerate metric tests.
- Create `backend/tests/test_finetune_evaluate.py`: prediction, selection, lock, held-out access, and report tests.
- Modify `backend/tests/test_providers.py`: metadata-seam tests without real calls.
- Modify `backend/tests/test_research_integrity.py`: static guards against combined/test-manifest access outside the approved boundaries.
- Modify `docs/capstone/research_runbook.md`: exact operator sequence and sign-off boundaries.
- Delete this plan after all tasks pass and the owning specs remain accurate.

---

### Task 1: Freeze Evaluation Projections and De-identified Evidence

**Files:**
- Modify: `backend/finetune/freeze_dataset.py:39-51,148-247`
- Modify: `backend/tests/test_finetune_dataset.py:699-750`

**Interfaces:**
- Consumes: `records: list[ManifestRecord]`, selected `RunBundle` values, annotation rows, adjudicator IDs, and ignored pilot/exclusion pair IDs already present inside `freeze_dataset()`.
- Produces: `manifest.{train,val,test}.jsonl`, `annotation_agreement.jsonl`, `character_slices.json`, and `FreezeReport.artifact_sha256: dict[str, str]`.
- Agreement row shape: `{"pair_id": str, "labels": [bool, bool]}` in combined-manifest order for natural annotated pairs.
- Slice shape: one sorted JSON object mapping qualified `char_id` to `"human"` or `"non_human"`.

- [ ] **Step 1: Write the failing freeze-artifact test**

Extend `test_freeze_dataset_writes_complete_immutable_artifacts_from_annotation_truth` and add a focused test that uses three fixture records ordered train, val, test. Assert exact projection bytes, de-identification, slice coverage, and recorded hashes:

```python
def test_freeze_writes_hashed_evaluation_projections_without_identity_fields(tmp_path):
    data_dir = tmp_path / "corpus"
    bundle = freeze_bundle(data_dir)
    pair_id = bd.pairs_from_memory(bundle.memory)[0].pair_id
    annotations = rows(
        pair_id,
        {"same_character": True},
        {"same_character": False},
        {"same_character": True, "annotator_id": "adjudicator"},
    )
    out_dir = tmp_path / "freeze"

    with (
        patch.object(fd, "fetch_annotations", return_value=annotations),
        patch.object(fd, "fetch_adjudicator_ids", return_value={"adjudicator"}),
        patch.object(fd, "fetch_pilot_pairs", return_value=set()),
    ):
        report = fd.freeze_dataset(data_dir, out_dir)

    combined = (out_dir / "manifest.jsonl").read_bytes()
    assert (out_dir / "manifest.train.jsonl").read_bytes() == combined
    assert (out_dir / "manifest.val.jsonl").read_bytes() == b""
    assert (out_dir / "manifest.test.jsonl").read_bytes() == b""
    agreement = [json.loads(line) for line in (out_dir / "annotation_agreement.jsonl").read_text().splitlines()]
    assert agreement == [{"pair_id": pair_id, "labels": [True, False]}]
    assert "annotator_id" not in (out_dir / "annotation_agreement.jsonl").read_text()
    assert json.loads((out_dir / "character_slices.json").read_text()) == {
        "story-freeze:char-freeze": "human"
    }
    for name in (
        "manifest.train.jsonl",
        "manifest.val.jsonl",
        "manifest.test.jsonl",
        "annotation_agreement.jsonl",
        "character_slices.json",
    ):
        assert report.artifact_sha256[name] == hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
```

Keep the test helper’s ordinary annotator IDs stable by allowing `rows()` to accept an explicit `annotator_id` override.

- [ ] **Step 2: Run the test and confirm RED**

Run from `backend/`:

```powershell
uv run pytest tests/test_finetune_dataset.py -k "evaluation_projections or complete_immutable_artifacts" -v
```

Expected: FAIL because the five new files and `FreezeReport.artifact_sha256` do not exist.

- [ ] **Step 3: Implement the minimal freeze evidence writer**

Add one helper in `freeze_dataset.py` and call it after `build_dataset()` but before constructing `FreezeReport`:

```python
EVALUATION_ARTIFACTS = (
    "manifest.train.jsonl",
    "manifest.val.jsonl",
    "manifest.test.jsonl",
    "annotation_agreement.jsonl",
    "character_slices.json",
)


def _write_evaluation_artifacts(
    staged: Path,
    records: list[ManifestRecord],
    bundles: list[RunBundle],
    annotations: list[dict],
    adjudicator_ids: set[str],
    ignored_pair_ids: set[str],
) -> dict[str, str]:
    from finetune.build_dataset import lineage_id
    from finetune.manifest import write_manifest

    for split in ("train", "val", "test"):
        write_manifest(staged / f"manifest.{split}.jsonl", [r for r in records if r.split == split])
    projected = b"".join((staged / f"manifest.{split}.jsonl").read_bytes() for split in ("train", "val", "test"))
    if projected != (staged / "manifest.jsonl").read_bytes():
        raise ManifestError("split manifest projections differ from combined manifest order")

    rows_by_pair: dict[str, list[dict]] = {}
    for row in annotations:
        if row["pair_id"] not in ignored_pair_ids:
            rows_by_pair.setdefault(row["pair_id"], []).append(row)
    agreement = []
    for record in records:
        if record.pair_type != "pipeline":
            continue
        ordinary = [
            row for row in rows_by_pair.get(record.pair_id, [])
            if row.get("annotator_id") not in adjudicator_ids
        ]
        if len(ordinary) != 2:
            raise ManifestError(f"{record.pair_id}: agreement evidence requires two ordinary labels")
        agreement.append({"pair_id": record.pair_id, "labels": [bool(row["same_character"]) for row in ordinary]})
    (staged / "annotation_agreement.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in agreement), encoding="utf-8"
    )

    slices = {}
    for bundle in bundles:
        non_human = {name.casefold() for name in bundle.declared_non_human or []}
        for character in bundle.memory.characters:
            slices[lineage_id(bundle.memory.story_id, character.char_id)] = (
                "non_human" if character.name.casefold() in non_human else "human"
            )
    if set(slices) != {record.char_id for record in records}:
        raise ManifestError("character slice keys differ from manifest characters")
    (staged / "character_slices.json").write_text(
        json.dumps(dict(sorted(slices.items())), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        name: hashlib.sha256((staged / name).read_bytes()).hexdigest()
        for name in EVALUATION_ARTIFACTS
    }
```

Add `artifact_sha256: dict[str, str] = Field(default_factory=dict)` to `FreezeReport`, pass the helper result into the report, and include the five filenames in the existing complete-artifact assertion.

- [ ] **Step 4: Run focused and existing freeze tests**

```powershell
uv run pytest tests/test_finetune_dataset.py tests/test_finetune_llamafactory.py -v
```

Expected: PASS. If the production ordering test exposes a non-grouped combined manifest, change `build_dataset()` sorting only enough to make the canonical order train, val, test while preserving the within-split order, then update its existing ordering assertion in the same TDD cycle.

- [ ] **Step 5: Commit the independently reviewable freeze contract**

```powershell
git add backend/finetune/freeze_dataset.py backend/finetune/build_dataset.py backend/tests/test_finetune_dataset.py
git commit -m "feat(research): freeze evaluation projections"
```

Only add `build_dataset.py` if Step 4 proved the ordering change necessary.

---

### Task 2: Pinned Three-seed Training Preflight and Runner

**Files:**
- Modify: `backend/finetune/train_qlora.yaml:1-52`
- Create: `backend/finetune/train.py`
- Create: `backend/tests/test_finetune_train.py`

**Interfaces:**
- Produces `prepare(freeze: Path, run_root: Path, config: Path, report_to: str) -> dict` and `execute(freeze: Path, run_root: Path, config: Path, report_to: str, spend_alarm_confirmed: bool) -> dict`.
- Each seed directory contains `run_plan.json`, `hardware.json`, `stdout.log`, and the configured `output/` directory.
- `run_plan.json` records freeze/config/artifact hashes, git commit, fixed pins, seed, and the exact command list.
- CLI: `python -m finetune.train --freeze PATH --run-root PATH --prepare [--report-to none|wandb]`; replace `--prepare` with `--execute --spend-alarm-confirmed` only after hardware qualification and spend-alarm sign-off.

- [ ] **Step 1: Write failing config and preflight tests**

Create `test_finetune_train.py` with a minimal frozen directory fixture and these cases:

```python
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
        assert not any("test" in value for value in command)


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
```

`frozen_fixture()` writes byte-consistent `manifest.jsonl`, `manifest.train.jsonl`, `manifest.val.jsonl`, `train.json`, `val.json`, `dataset_info.json`, `dataset_manifest.json`, and `freeze_report.json`; it never creates a test projection with real records.

- [ ] **Step 2: Run the new test file and confirm RED**

```powershell
uv run pytest tests/test_finetune_train.py -v
```

Expected: collection FAIL because `finetune.train` does not exist.

- [ ] **Step 3: Pin the checked-in YAML**

Change only these YAML values:

```yaml
model_revision: cc594898137f460bfe9f0759e9844b3ce807cfb5
report_to: none
```

Keep the existing model, dataset, rank/alpha, quantization, image pixels, schedule, and seed-0 defaults unchanged.

- [ ] **Step 4: Implement preflight, inventory, and immutable run plans**

Use `argparse`, `hashlib`, `json`, `platform`, `subprocess`, and the already-installed `yaml.safe_load`. Define these exact constants and functions:

```python
BASE_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"
BASE_REVISION = "cc594898137f460bfe9f0759e9844b3ce807cfb5"
LLAMAFACTORY_VERSION = "v0.9.5"
LLAMAFACTORY_COMMIT = "7af909522a951e3ad9f022ea6f88b6755257eaa5"
SEEDS = (0, 1, 2)
ALLOWED_OVERRIDES = {"seed", "output_dir", "run_name", "report_to"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hardware_inventory() -> dict[str, str]:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
        check=False, capture_output=True, text=True,
    )
    versions = {"torch": "", "cuda": "", "bitsandbytes": ""}
    try:
        import torch
        import bitsandbytes
        versions = {
            "torch": torch.__version__,
            "cuda": str(torch.version.cuda or ""),
            "bitsandbytes": bitsandbytes.__version__,
        }
    except ImportError:
        pass
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "gpu": result.stdout.strip(),
        **versions,
    }
```

`prepare()` must:

1. parse YAML and compare all fixed scientific values to the spec;
2. reject an `eval_dataset` other than `storybuddy_judge_val` and any dataset name containing `test`;
3. hash but not parse `manifest.jsonl`;
4. parse only `manifest.train.jsonl` and `manifest.val.jsonl` and verify their hashes against `freeze_report.json`;
5. verify `train.json`, `val.json`, `dataset_info.json`, and `dataset_manifest.json` exist;
6. build commands with only the four allowed overrides;
7. create each seed directory with exclusive creation and write byte-identical `run_plan.json` on a repeated prepare, rejecting any difference.

The command builder is:

```python
def command_for(config: Path, seed: int, seed_dir: Path, report_to: str) -> list[str]:
    return [
        "llamafactory-cli", "train", str(config),
        f"seed={seed}",
        f"output_dir={seed_dir / 'output'}",
        f"run_name=judge-qlora-seed{seed}",
        f"report_to={report_to}",
    ]
```

`execute()` repeats `prepare()`, rejects a false spend-alarm confirmation, rejects blank `gpu`, `torch`, `cuda`, or `bitsandbytes`, writes the exact `hardware.json`, and runs the three commands sequentially with `check=True`, `stdout` and `stderr` merged into each seed’s `stdout.log`. It also records the output of `llamafactory-cli version`, rejects any version other than `v0.9.5`, and records the exact commit-pinned `uv tool install` command in `run_plan.json`. A non-zero child exits immediately and leaves prior evidence intact.

- [ ] **Step 5: Add deterministic execution and drift tests**

Add tests proving:

```python
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
```

Also mutate one fixed YAML key and assert preflight rejection, and mutate an existing `run_plan.json` and assert immutable-run rejection.

- [ ] **Step 6: Run runner tests and Ruff**

```powershell
uv run pytest tests/test_finetune_train.py -v
uv run ruff check finetune/train.py tests/test_finetune_train.py
```

Expected: PASS and `All checks passed!`.

- [ ] **Step 7: Commit the runner**

```powershell
git add backend/finetune/train.py backend/finetune/train_qlora.yaml backend/tests/test_finetune_train.py
git commit -m "feat(research): add pinned judge training runner"
```

---

### Task 3: Standard-library Evaluation Metrics

**Files:**
- Create: `backend/finetune/evaluation_metrics.py`
- Create: `backend/tests/test_finetune_evaluation_metrics.py`
- Modify: `backend/finetune/evaluate.py:20-86` after the new module passes
- Modify: `backend/tests/test_finetune_dataset.py:644-668` to remove metric tests moved to the focused file

**Interfaces:**
- Produces `prf1`, `clustered_f1_ci`, `clustered_delta_f1_ci`, `mcnemar_exact`, `auroc`, `cohen_kappa`, `calibration`, and `mean_sample_std`.
- Every unavailable metric returns `{"value": None, "reason": str}` rather than raising for an empty slice, one-class AUROC, or zero-variance kappa.
- Bootstrap defaults: `resamples=10_000`, `seed=0`, `alpha=0.05`.

- [ ] **Step 1: Write known-value failing tests**

```python
def test_exact_metrics_match_small_hand_checked_examples():
    assert metrics.prf1([True, True, False, False], [True, False, True, False]) == pytest.approx(
        (0.5, 0.5, 0.5)
    )
    assert metrics.mcnemar_exact([True, True, False, False], [True, False, True, False], [False, False, True, False]) == pytest.approx(1.0)
    assert metrics.auroc([True, False, True, False], [0.9, 0.8, 0.8, 0.1]) == {"value": pytest.approx(0.875), "reason": None}
    assert metrics.cohen_kappa([True, True, False, False], [True, False, True, False]) == {"value": pytest.approx(0.0), "reason": None}


def test_degenerate_metrics_report_unavailable_reasons():
    assert metrics.auroc([], [])["reason"] == "empty slice"
    assert metrics.auroc([True, True], [0.8, 0.9])["reason"] == "AUROC requires both classes"
    assert metrics.cohen_kappa([True, True], [True, True])["reason"] == "kappa expected agreement is one"


def test_cluster_bootstrap_is_character_grouped_and_seeded():
    labels = [True, False, True, False]
    tuned = [True, False, True, False]
    base = [False, False, False, False]
    chars = ["a", "a", "b", "b"]
    first = metrics.clustered_delta_f1_ci(labels, tuned, base, chars, resamples=100, seed=0)
    second = metrics.clustered_delta_f1_ci(labels, tuned, base, chars, resamples=100, seed=0)
    assert first == second
    assert first[0] == pytest.approx(1.0)
```

Add calibration checks for Brier score `0.125` on labels `[True, False]` with confidences `[0.5, 0.0]`, exactly ten bins, and unavailable output when any confidence is missing.

- [ ] **Step 2: Run and confirm RED**

```powershell
uv run pytest tests/test_finetune_evaluation_metrics.py -v
```

Expected: collection FAIL because `evaluation_metrics.py` does not exist.

- [ ] **Step 3: Implement the pure functions**

Use `math.comb`, `random.Random`, `statistics.mean`, and `statistics.stdev`. The exact McNemar implementation is:

```python
def mcnemar_exact(labels, left, right) -> float:
    left_only = sum(a == y and b != y for y, a, b in zip(labels, left, right))
    right_only = sum(a != y and b == y for y, a, b in zip(labels, left, right))
    discordant = left_only + right_only
    if discordant == 0:
        return 1.0
    tail = sum(comb(discordant, k) for k in range(min(left_only, right_only) + 1)) / (2 ** discordant)
    return min(1.0, 2 * tail)
```

Implement tied AUROC by assigning average ranks to equal confidence values and applying the Mann-Whitney rank formula. Implement kappa from observed agreement and marginal expected agreement. Bootstrap whole sorted character clusters with replacement; when a character is drawn twice, include all its rows twice. For calibration, convert confidence in the predicted verdict into probability of `different_character` (`confidence` when prediction is true, `1-confidence` otherwise), use the ten intervals from `[0, 0.1)` through `[0.9, 1.0]`, and report `count`, mean probability, and positive rate for each bin.

- [ ] **Step 4: Move old metric callers to the new module**

Import the functions into `evaluate.py`; delete its old `prf1`, `bootstrap_f1_ci`, and `score` definitions. Move the three existing metric tests from `test_finetune_dataset.py` to the new focused test file so there is one owner.

- [ ] **Step 5: Run metric and evaluator-adjacent tests**

```powershell
uv run pytest tests/test_finetune_evaluation_metrics.py tests/test_finetune_dataset.py -v
uv run ruff check finetune/evaluation_metrics.py finetune/evaluate.py tests/test_finetune_evaluation_metrics.py
```

Expected: PASS and `All checks passed!`.

- [ ] **Step 6: Commit pure metrics**

```powershell
git add backend/finetune/evaluation_metrics.py backend/finetune/evaluate.py backend/tests/test_finetune_evaluation_metrics.py backend/tests/test_finetune_dataset.py
git commit -m "feat(research): add preregistered evaluation metrics"
```

---

### Task 4: Evaluation-only Provider Metadata and Prediction Evidence

**Files:**
- Modify: `backend/providers.py:99-213`
- Modify: `backend/tests/test_providers.py:16-150`
- Modify: `backend/finetune/evaluate.py`
- Create: `backend/tests/test_finetune_evaluate.py`

**Interfaces:**
- Produces `EvaluationJudgeResult[T]` with `verdict: T`, `confidence: float | None`, and `latency_ms: int`.
- Produces `judge_with_metadata(prompt, image_urls, schema, model=None, *, route="judge") -> EvaluationJudgeResult[T]`, where `route` is `"judge"` for the Qwen/vLLM endpoint or `"openrouter"` for prompted Gemma. Endpoint selection and API keys remain inside `providers.py`.
- Production `judge()` retains its existing signature and return type.
- `PredictionRecord` fields are `pair_id`, `char_id`, `split`, `judge_id`, `prediction`, `confidence`, `score`, `latency_ms`, `parse_status`, `model_id`, `adapter_id`, `prompt_version`, `threshold_id`, and `checkpoint_id`. `confidence` is the emitted verdict-token probability; `score` is oriented toward the positive `different_character` class and may be an uncalibrated embedding score.

- [ ] **Step 1: Write failing provider tests**

```python
def test_judge_with_metadata_returns_verdict_confidence_and_latency_without_changing_judge(monkeypatch):
    parsed = _Verdict(differences_observed="none", same_character=True)
    completion = _fake_completion(parsed, '{"differences_observed":"none","same_character":true}')
    completion.choices[0].logprobs.content = [
        MagicMock(token='"same_character"', logprob=-0.01),
        MagicMock(token="true", logprob=math.log(0.8)),
    ]
    with patch("providers.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.parse.return_value = completion
        rich = providers.judge_with_metadata("compare", ["https://ref", "https://scene"], _Verdict)
        plain = providers.judge("compare", ["https://ref", "https://scene"], _Verdict)

    assert rich.verdict == parsed
    assert rich.confidence == pytest.approx(0.8)
    assert rich.latency_ms >= 0
    assert plain == parsed
```

Assert the rich request sends `logprobs=True` and `top_logprobs=5`, and add a case where `choices[0].logprobs` is absent and confidence is `None`.

- [ ] **Step 2: Run provider tests and confirm RED**

```powershell
uv run pytest tests/test_providers.py -k "judge_with_metadata" -v
```

Expected: FAIL because the additive function and result type do not exist.

- [ ] **Step 3: Implement the additive provider seam with shared request logic**

Add:

```python
@dataclass(frozen=True)
class EvaluationJudgeResult(Generic[T]):
    verdict: T
    confidence: float | None
    latency_ms: int


def _same_character_confidence(completion) -> float | None:
    content = getattr(getattr(completion.choices[0], "logprobs", None), "content", None)
    seen_field = False
    for item in content or []:
        token = item.token.strip().lower()
        seen_field = seen_field or "same_character" in token
        if seen_field and ("true" in token or "false" in token):
            return math.exp(item.logprob)
    return None
```

Extract the existing OpenAI completion creation into one private helper that accepts `include_logprobs: bool` and `temperature: float | None`. Both `_one_answer()` and the new evaluation function call it, so retry, provider-routing, timeout, Pydantic validation, and field-order behavior stay identical. Production `judge()` passes no temperature override; `judge_with_metadata()` passes `temperature=0`, measures `time.perf_counter_ns()`, requests logprobs, calls `_assert_field_order`, and returns milliseconds rounded to an integer. For `route="judge"`, use the existing `settings.judge_base_url` and judge key; for `route="openrouter"`, use `OPENROUTER_BASE_URL`, the OpenRouter key, and normal OpenRouter provider preferences. Reject any other route. Do not add model-specific behavior to production call sites.

- [ ] **Step 4: Write failing prediction evidence tests**

```python
def test_capture_predictions_is_ordered_and_scores_malformed_output_as_a_miss(manifest_record):
    records = [manifest_record("p1"), manifest_record("p2")]

    def predict(record):
        if record.pair_id == "p2":
            raise ValueError("broken JSON")
        return ev.JudgeObservation(prediction=True, confidence=0.8, latency_ms=12)

    rows = ev.capture_predictions(records, "zero_shot_base", predict, model_id="qwen", prompt_version="4")
    assert [row.pair_id for row in rows] == ["p1", "p2"]
    assert rows[0].parse_status == "parsed"
    assert rows[1].prediction is False
    assert rows[1].confidence is None
    assert rows[1].parse_status == "malformed"
```

Add `write_predictions(path, rows)` tests proving exclusive creation, byte-identical retry acceptance, and rejection of duplicate, missing, reordered, or unknown pair IDs through `validate_prediction_alignment(records, rows)`.

- [ ] **Step 5: Implement prediction types and immutable JSONL**

Use Pydantic models in `evaluate.py`:

```python
class JudgeObservation(BaseModel):
    prediction: bool
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    score: float | None = None
    latency_ms: int = Field(ge=0)


class PredictionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pair_id: str
    char_id: str
    split: Literal["val", "test"]
    judge_id: str
    prediction: bool
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    score: float | None = None
    latency_ms: int = Field(ge=0)
    parse_status: Literal["parsed", "malformed"]
    model_id: str
    adapter_id: str | None = None
    prompt_version: str
    threshold_id: str | None = None
    checkpoint_id: str | None = None
```

The VLM predictor wraps `providers.judge_with_metadata`. It converts emitted-verdict confidence to a positive-class score: use `confidence` when `prediction=True`, otherwise `1-confidence`. Embedding controls store negative cosine similarity as the positive-oriented `score`, leave `confidence=None`, and apply the already-locked validation threshold. `write_predictions()` writes JSONL to a temporary sibling and installs it with exclusive create; an existing byte-identical file is accepted, while different bytes raise `ManifestError`.

- [ ] **Step 6: Run focused tests**

```powershell
uv run pytest tests/test_providers.py tests/test_finetune_evaluate.py -v
uv run ruff check providers.py finetune/evaluate.py tests/test_providers.py tests/test_finetune_evaluate.py
```

Expected: PASS and `All checks passed!`.

- [ ] **Step 7: Commit metadata capture**

```powershell
git add backend/providers.py backend/finetune/evaluate.py backend/tests/test_providers.py backend/tests/test_finetune_evaluate.py
git commit -m "feat(research): capture immutable judge predictions"
```

---

### Task 5: Validation-only Selection and Immutable Evaluation Lock

**Files:**
- Modify: `backend/finetune/evaluate.py`
- Modify: `backend/tests/test_finetune_evaluate.py`

**Interfaces:**
- Produces `inventory_checkpoints(runs, out) -> dict`, `select_checkpoint(candidates, records) -> dict`, `select_threshold(scores, records) -> dict`, and `write_evaluation_lock(path, payload) -> dict`.
- `evaluation_lock.json` contains the three checkpoint paths/hashes and validation F1 values, deployment seed, CLIP and DINOv2 thresholds, prompt/model/tool pins, manifest projection hashes, bootstrap seed, and prediction schema version.
- CLI: `python -m finetune.evaluate validation-inventory --runs PATH --out PATH`, followed by `python -m finetune.evaluate validate --freeze PATH --candidates PATH --predictions PATH --out PATH`.

- [ ] **Step 1: Write failing validation-selection tests**

```python
def test_checkpoint_selection_uses_val_f1_and_breaks_ties_by_earlier_step(val_records):
    selected = ev.select_checkpoint({
        "checkpoint-100": predictions(val_records, [True, False]),
        "checkpoint-050": predictions(val_records, [True, False]),
        "checkpoint-150": predictions(val_records, [False, False]),
    }, val_records)
    assert selected["checkpoint_id"] == "checkpoint-050"


def test_threshold_selection_maximizes_val_f1_then_prefers_lower_threshold(val_records):
    selected = ev.select_threshold([0.9, 0.4], val_records)
    assert selected["threshold"] in {0.4, 0.9}
    assert selected["selected_on"] == "manifest.val.jsonl"


def test_evaluation_lock_is_immutable_and_contains_all_required_pins(tmp_path, valid_lock):
    path = tmp_path / "evaluation_lock.json"
    ev.write_evaluation_lock(path, valid_lock)
    ev.write_evaluation_lock(path, valid_lock)
    with pytest.raises(ManifestError, match="evaluation lock differs"):
        ev.write_evaluation_lock(path, {**valid_lock, "bootstrap_seed": 1})
```

Also patch `finetune.evaluate.read_manifest` and assert validation opens only `manifest.val.jsonl`; opening `manifest.jsonl` or `manifest.test.jsonl` fails the test immediately.

- [ ] **Step 2: Run selection tests and confirm RED**

```powershell
uv run pytest tests/test_finetune_evaluate.py -k "selection or evaluation_lock or validation_opens" -v
```

Expected: FAIL because selection and lock functions do not exist.

- [ ] **Step 3: Implement deterministic selection**

Checkpoint selection computes positive-class F1 from aligned validation predictions and sorts by `(-f1, training_step)`. Threshold selection considers the sorted unique observed cosine values plus the two outside boundaries; predict `different_character` when similarity is below the candidate threshold; sort by `(-f1, threshold)`. This makes ties deterministic without consulting test.

Choose the deployment seed by `(-validation_f1, seed)`. Record all three seeds; do not discard the other two.

- [ ] **Step 4: Inventory real checkpoints and define the validation-serving boundary**

`prepare()` names run directories `seed-0`, `seed-1`, and `seed-2`. `inventory_checkpoints()` discovers only `seed-*/output/checkpoint-[0-9]+` directories beneath that immutable run root, hashes each directory by sorted relative filename plus file bytes, and assigns model IDs `seed{seed}_checkpoint{step}`. It writes `validation_candidates.json` containing every path/hash/model ID and an exact `vllm_command` array:

```python
[
    "vllm", "serve", BASE_MODEL, "--revision", BASE_REVISION,
    "--enable-lora", "--max-lora-rank", "16", "--lora-modules",
    *[f"{item['model_id']}={item['path']}" for item in candidates],
]
```

The operator runs that generated command in the qualified GPU environment. `validate` then uses the model IDs from the inventory against `route="judge"`, writes one immutable validation prediction JSONL per checkpoint, records raw CLIP/DINOv2 scores, selects checkpoints and thresholds, and uses `route="openrouter"` only for prompted Gemma. It opens `manifest.val.jsonl` and no other manifest projection.

- [ ] **Step 5: Implement lock validation and exclusive write**

Define `EvaluationLock` as a Pydantic model with `extra="forbid"`. Validate 64-character lowercase SHA-256 values, seeds exactly `[0, 1, 2]`, base/LLaMA-Factory pins exactly equal to the global constants, bootstrap seed `0`, prediction schema version `1`, and nonblank prompt version/model/adapter/checkpoint values. Verify every path/hash before writing. Install with the same byte-identical-or-reject rule used for predictions.

- [ ] **Step 6: Add the validation CLI without a split argument**

Use `argparse` subparsers. `validation-inventory` never reads a manifest. The `validate` subcommand derives `freeze / "manifest.val.jsonl"`; there is no public `--split` option and no code path that filters the combined manifest.

- [ ] **Step 7: Run focused tests and commit**

```powershell
uv run pytest tests/test_finetune_evaluate.py -v
uv run ruff check finetune/evaluate.py tests/test_finetune_evaluate.py
git add backend/finetune/evaluate.py backend/tests/test_finetune_evaluate.py
git commit -m "feat(research): lock validation-only model selection"
```

Expected: tests PASS, Ruff reports `All checks passed!`, and the commit contains no generated predictions or model artifacts.

---

### Task 6: Fail-closed Held-out Access Ledger and Resume Rules

**Files:**
- Modify: `backend/finetune/evaluate.py`
- Modify: `backend/tests/test_finetune_evaluate.py`

**Interfaces:**
- Produces `reserve_test_read(ledger, run_id, lock_hash, first_report=None, deviation=None) -> AccessReservation`.
- Ledger is append-only JSONL with `reserved`, `resumed`, and `completed` events; each event records UTC timestamp, run ID, evaluation-lock hash, manifest-test hash, and ordinal read number.
- CLI: `python -m finetune.evaluate heldout --freeze PATH --lock PATH --signoff PATH --ledger PATH --run-id ID --out PATH [--deviation PATH]`.

- [ ] **Step 1: Write the four required failing access tests**

```python
def test_first_read_is_reserved_before_test_manifest_opens(tmp_path, monkeypatch, valid_lock):
    events = []
    ledger = tmp_path / "access.jsonl"

    def guarded_read(path):
        assert json.loads(ledger.read_text().splitlines()[0])["event"] == "reserved"
        events.append(Path(path).name)
        return []

    monkeypatch.setattr(ev, "read_manifest", guarded_read)
    lock = lock_file(tmp_path, valid_lock)
    signoff = signoff_file(tmp_path, lock)
    ev.run_heldout(freeze_fixture(tmp_path), lock, signoff, ledger, "run-1", tmp_path / "result")
    assert events == ["manifest.test.jsonl"]


def test_crash_resume_requires_same_run_id_and_hashes(tmp_path, reserved_ledger, valid_lock):
    assert ev.reserve_test_read(reserved_ledger, "run-1", lock_hash(valid_lock)).ordinal == 1
    with pytest.raises(ManifestError, match="unfinished held-out run"):
        ev.reserve_test_read(reserved_ledger, "run-other", lock_hash(valid_lock))


def test_second_read_requires_completed_rung_d_and_bound_deviation(tmp_path, completed_rung_d):
    deviation = write_deviation(tmp_path, completed_rung_d, fix_commit="a" * 40)
    reservation = ev.reserve_test_read(completed_rung_d.ledger, "run-2", completed_rung_d.lock_hash, deviation=deviation)
    assert reservation.ordinal == 2


def test_third_read_is_always_rejected(tmp_path, two_completed_reads):
    with pytest.raises(ManifestError, match="third held-out read is prohibited"):
        ev.reserve_test_read(two_completed_reads.ledger, "run-3", two_completed_reads.lock_hash)


def test_heldout_rejects_missing_or_mismatched_signoff(tmp_path, valid_lock):
    lock = lock_file(tmp_path, valid_lock)
    with pytest.raises(ManifestError, match="sign-off"):
        ev.run_heldout(freeze_fixture(tmp_path), lock, tmp_path / "missing.json", tmp_path / "ledger", "run-1", tmp_path / "result")
    wrong = signoff_file(tmp_path, lock, evaluation_lock_sha256="0" * 64)
    with pytest.raises(ManifestError, match="sign-off hash"):
        ev.run_heldout(freeze_fixture(tmp_path), lock, wrong, tmp_path / "ledger", "run-1", tmp_path / "result")
```

Add rejection cases for changed evaluation-lock hash, changed test-manifest hash, non-Rung-D first report, missing first-report hash, missing defect description, missing fix commit, and missing train/validation-only debugging-evidence hashes.

- [ ] **Step 2: Run and confirm RED**

```powershell
uv run pytest tests/test_finetune_evaluate.py -k "read or resume or rung_d or third" -v
```

Expected: FAIL because the ledger state machine does not exist.

- [ ] **Step 3: Implement atomic reservation before file access**

Use an adjacent `ledger.with_suffix(".lock")` created with `os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)`. While holding it, parse and validate every prior JSONL event, decide whether the action is first read, same-run resume, or authorized second read, append and `fsync()` the reservation, then remove the lock in `finally`. Never open `manifest.test.jsonl` before reservation returns.

Same-run resume does not increment the read ordinal and requires identical evaluation-lock and test-manifest hashes. A second read requires a deviation JSON object with:

```json
{
  "first_report_sha256": "64 lowercase hex characters",
  "defect": "nonblank confirmed evaluation-code defect",
  "fix_commit": "40 lowercase hex characters",
  "debug_evidence_sha256": ["64 lowercase hex characters"],
  "debug_splits": ["train", "val"],
  "approved_at": "ISO-8601 timestamp"
}
```

Reject any `debug_splits` value other than exactly `train` and `val`.

- [ ] **Step 4: Require a separate lock sign-off artifact**

Before reservation, validate a controlled JSON file with this exact shape:

```json
{
  "evaluation_lock_sha256": "64 lowercase hex characters",
  "approved_by": "nonblank owner or adviser identifier",
  "approved_at": "ISO-8601 timestamp"
}
```

Reject a missing sign-off, a hash that differs from the immutable `evaluation_lock.json`, a blank approver, or a timestamp without a timezone. The sign-off is never written automatically by evaluation code.

- [ ] **Step 5: Implement one guarded held-out entry point**

`run_heldout()` validates and hashes the signed-off `evaluation_lock.json`, hashes `manifest.test.jsonl` as bytes without parsing it, reserves access, then calls `read_manifest()` exactly once. It requires output prediction files for all seven judge IDs:

```python
REQUIRED_JUDGES = (
    "finetuned_seed0", "finetuned_seed1", "finetuned_seed2",
    "zero_shot_base", "prompted_gemma", "clip_cosine", "dinov2_cosine",
)
```

On interruption, rerunning the same `run_id` reuses byte-identical completed prediction files and creates only missing ones. Append `completed` only after predictions and final report are installed.

- [ ] **Step 6: Remove the unsafe old evaluator entry point**

Delete `main(manifest: Path, split: str, judges: dict[str, Judge], out: Path | None = None) -> dict`, because it permits validation code to parse the combined manifest and request test directly. Keep explicit `validation-inventory`, `validate`, and `heldout` subcommands only.

- [ ] **Step 7: Run access tests and commit**

```powershell
uv run pytest tests/test_finetune_evaluate.py -v
uv run ruff check finetune/evaluate.py tests/test_finetune_evaluate.py
git add backend/finetune/evaluate.py backend/tests/test_finetune_evaluate.py
git commit -m "feat(research): guard held-out evaluation access"
```

Expected: PASS, `All checks passed!`, and no real held-out file is opened.

---

### Task 7: Complete Objective-4 Result Aggregation and Rung Output

**Files:**
- Modify: `backend/finetune/evaluate.py`
- Modify: `backend/tests/test_finetune_evaluate.py`

**Interfaces:**
- Produces `build_report(records, prediction_sets, agreement, slices, evaluation_lock) -> dict`.
- Produces immutable `objective4_results.json` with individual judges, fine-tune seed summary, primary comparison, Gemma comparison, slices, inter-rater agreement, calibration diagnostics, drift, and deployment rung.
- Rung uses the deployment seed selected and frozen on validation; test results never choose a seed.

- [ ] **Step 1: Write a failing complete-report test**

```python
def test_report_contains_every_preregistered_result_and_uses_locked_deployment_seed(
    test_records, aligned_predictions, evaluation_lock, agreement_rows, character_slices
):
    report = ev.build_report(
        test_records, aligned_predictions, agreement_rows, character_slices, evaluation_lock
    )
    assert set(report["judges"]) == set(ev.REQUIRED_JUDGES)
    assert report["fine_tuned_seeds"]["deployment_seed"] == evaluation_lock["deployment_seed"]
    assert set(report["fine_tuned_seeds"]["individual"]) == {"0", "1", "2"}
    assert set(report["fine_tuned_seeds"]["summary"]["f1"]) == {"mean", "sample_std"}
    assert set(report["slices"]) == {"human", "non_human"}
    assert "mcnemar_exact_p" in report["primary_comparison"]
    assert "clustered_delta_f1_ci95" in report["primary_comparison"]
    assert "ordinary_annotator_kappa" in report["agreement"]
    assert report["calibration"]["status"] == "exploratory"
    assert report["deployment"]["rung"] in {"A", "B", "C", "D"}
```

Add degenerate fixtures asserting unavailable reasons propagate into the JSON rather than crashing, and a confidence-missing fixture asserting AUROC and calibration are unavailable while F1 remains available.

- [ ] **Step 2: Run report tests and confirm RED**

```powershell
uv run pytest tests/test_finetune_evaluate.py -k "report or unavailable or confidence" -v
```

Expected: FAIL because complete aggregation is absent.

- [ ] **Step 3: Implement per-judge and per-slice reporting**

For every aligned judge prediction set, report:

- `n`, positive-label prevalence, predicted-positive rate and their difference;
- precision, recall, F1 and character-clustered 95% F1 interval;
- tied-rank AUROC from the positive-oriented `score` when it exists;
- Cohen’s kappa against adjudicated truth overall, human, and non-human;
- median and mean latency plus malformed count/rate;
- exploratory ten-bin reliability table and Brier score.

Inter-rater kappa uses the two ordered values in each frozen `annotation_agreement.jsonl` row and is reported overall, human, and non-human. Slice membership comes only from `character_slices.json`; reject unknown or missing keys.

- [ ] **Step 4: Implement paired comparisons and three-seed summary**

For the locked deployment seed against zero-shot Qwen and prompted Gemma, report exact McNemar and 10,000-resample character-clustered paired delta-F1 intervals. Report seeds 0/1/2 individually and use `statistics.mean` plus sample `statistics.stdev` for F1, precision, recall, and latency.

- [ ] **Step 5: Implement the frozen deployment ladder**

Use the validation-selected deployment seed. `beats_base` means the paired delta-F1 interval lower bound is greater than zero. Then:

```python
def deployment_rung(tuned, base, gemma, delta_ci) -> str:
    if delta_ci[0] <= 0:
        return "D"
    if tuned["f1"] > gemma["f1"]:
        return "A"
    if gemma["f1"] - tuned["f1"] <= 0.03 and tuned["recall"] >= gemma["recall"]:
        return "B"
    return "C"
```

The report labels this as an engineering deployment conclusion, separate from Objective 4’s absolute F1 result.

- [ ] **Step 6: Write immutable report and complete ledger**

Serialize with sorted keys and a trailing newline. Accept a byte-identical rerun under the same run ID; reject replacement. Hash the installed report, then append the ledger’s `completed` event with rung and report hash.

- [ ] **Step 7: Run focused tests and commit**

```powershell
uv run pytest tests/test_finetune_evaluation_metrics.py tests/test_finetune_evaluate.py -v
uv run ruff check finetune/evaluation_metrics.py finetune/evaluate.py tests/test_finetune_evaluation_metrics.py tests/test_finetune_evaluate.py
git add backend/finetune/evaluate.py backend/tests/test_finetune_evaluate.py
git commit -m "feat(research): report objective four evaluation"
```

Expected: PASS and `All checks passed!`.

---

### Task 8: Operator Runbook, Integrity Guards, and Full Verification

**Files:**
- Modify: `docs/capstone/research_runbook.md:70-85`
- Modify: `backend/tests/test_research_integrity.py`
- Modify: `tasks/todo.md`
- Delete after verification: `docs/specs/plans/2026-08-25-objective-4-training-evaluation.md`

**Interfaces:**
- Produces the sole operator flow from immutable freeze through result artifact.
- Adds static guards ensuring no validation/training module opens `manifest.test.jsonl` and only `evaluate.run_heldout()` may parse it.

- [ ] **Step 1: Write failing research-integrity guards**

Add AST/source checks:

```python
def test_only_guarded_evaluator_names_the_test_manifest():
    allowed = {Path("finetune/freeze_dataset.py"), Path("finetune/evaluate.py")}
    offenders = []
    for path in Path("finetune").glob("*.py"):
        if "manifest.test.jsonl" in path.read_text(encoding="utf-8") and path not in allowed:
            offenders.append(path.as_posix())
    assert offenders == []


def test_training_runner_never_parses_combined_or_test_manifest():
    source = Path("finetune/train.py").read_text(encoding="utf-8")
    assert 'read_manifest(freeze / "manifest.jsonl")' not in source
    assert 'read_manifest(freeze / "manifest.test.jsonl")' not in source
    assert 'read_manifest(freeze / "manifest.train.jsonl")' in source
    assert 'read_manifest(freeze / "manifest.val.jsonl")' in source
```

- [ ] **Step 2: Run integrity tests and confirm any missing guard fails**

```powershell
uv run pytest tests/test_research_integrity.py -v
```

Expected before the final guard edits: at least one new assertion fails if an unsafe path remains; otherwise the new tests pass immediately because earlier tasks already removed it.

- [ ] **Step 3: Write the exact runbook sequence**

Add these commands, with a warning that commands after preparation run only after annotation/freeze/adviser sign-off:

```powershell
cd backend
uv run python -m finetune.train --freeze data/judge/freezes/obj4-v1 --run-root data/judge/training/obj4-v1 --prepare --report-to none

# In the separately qualified GPU uv environment, after exact Torch/CUDA/bitsandbytes versions are recorded and the spend alarm is active:
uv run python -m finetune.train --freeze data/judge/freezes/obj4-v1 --run-root data/judge/training/obj4-v1 --execute --report-to none --spend-alarm-confirmed

# Inventory every saved checkpoint and obtain the exact generated vLLM command:
uv run python -m finetune.evaluate validation-inventory --runs data/judge/training/obj4-v1 --out data/judge/evaluations/obj4-v1/validation_candidates.json

# In the qualified GPU environment, run the vllm_command array recorded above, then score validation and lock all choices:
uv run python -m finetune.evaluate validate --freeze data/judge/freezes/obj4-v1 --candidates data/judge/evaluations/obj4-v1/validation_candidates.json --predictions data/judge/evaluations/obj4-v1/validation --out data/judge/evaluations/obj4-v1/evaluation_lock.json

# Stop for owner/adviser creation of evaluation_signoff.json before this command:
uv run python -m finetune.evaluate heldout --freeze data/judge/freezes/obj4-v1 --lock data/judge/evaluations/obj4-v1/evaluation_lock.json --signoff data/judge/evaluations/obj4-v1/evaluation_signoff.json --ledger data/judge/evaluations/obj4-v1/test_access.jsonl --run-id obj4-heldout-1 --out data/judge/evaluations/obj4-v1/heldout-1
```

Document that a second held-out command additionally requires `--deviation PATH`, is legal only after Rung D, and uses a new run ID. State plainly that there is no third-read command and no automatic deployment.

- [ ] **Step 4: Run the complete deterministic verification**

From `backend/`:

```powershell
uv run pytest tests/test_finetune_dataset.py tests/test_finetune_llamafactory.py tests/test_finetune_train.py tests/test_finetune_evaluation_metrics.py tests/test_finetune_evaluate.py tests/test_providers.py tests/test_research_integrity.py -v
uv run ruff check .
uv run pytest
```

Expected: all deterministic tests PASS; only documented live-Supabase/provider skips remain; Ruff reports `All checks passed!`. Do not run smoke tests because Batch 3 implementation changes no production model ID or provider route and the new provider function is evaluation-only.

- [ ] **Step 5: Verify repository hygiene and spec coverage**

From the repository root:

```powershell
git diff --check
rg -n "PIN_THE_EXACT_COMMIT_HASH|model_revision:[[:space:]]*(main|master)" backend/finetune backend/tests docs/capstone/research_runbook.md
git status --short
```

Expected: `git diff --check` is silent; the placeholder scan finds no Batch-3 placeholder; status shows only intended files plus the owner’s pre-existing unrelated changes.

- [ ] **Step 6: Request two-axis code review and address findings**

Use `superpowers:requesting-code-review` against the pre-Batch-3 implementation commit. Review standards and the three governing specs. Fix only confirmed Batch-3 findings, rerun the smallest affected test, then rerun Step 4.

- [ ] **Step 7: Record outcome, remove the disposable plan, and commit closure**

Add a Batch-3 outcome section to `tasks/todo.md` containing commands, pass/skip counts, verified boundaries, and residual operational risks (hardware qualification, paid GPU execution, real provider reachability, and unopened held-out data). Mark Batch 3 implemented only after Step 4 is green. Then:

```powershell
git rm docs/specs/plans/2026-08-25-objective-4-training-evaluation.md
git add docs/capstone/research_runbook.md backend/tests/test_research_integrity.py tasks/todo.md
git commit -m "docs(research): close objective four execution safeguards"
```

The plan deletion is intentional project hygiene: specs are durable; completed plans remain in Git history.

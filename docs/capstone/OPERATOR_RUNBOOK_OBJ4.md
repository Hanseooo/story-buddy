# Objective 4 Operator Runbook: Training, Validation Selection, and Held-out Evaluation

This runbook documents the exact, reproducible execution procedure for fine-tuning the consistency judge model (Objective 4), performing validation-only model/threshold selection, creating the immutable evaluation lock, and executing the held-out evaluation protocol under pre-registration guards.

---

## 1. Environment & Hardware Preflight

### 1.1 Python Environment
All commands run within the `backend/` directory using `uv`:
```bash
cd backend
uv sync
```

### 1.2 Training Environment & Dependencies
Training and local embedding control evaluation require the GPU training environment:
```bash
pip install "llamafactory==0.9.5" "torch>=2.4.0" "transformers>=4.45.0"
```

Verify hardware and fixed pin compliance before launching training:
```bash
uv run python -m finetune.train preflight \
  --yaml finetune/train_qlora.yaml \
  --freeze-dir <PATH_TO_FREEZE_DIR> \
  --min-vram-gb 40.0
```

---

## 2. Dataset Freeze & Integrity Verification

To generate the immutable dataset freeze from annotated ground truth:
```bash
uv run python -m finetune.freeze_dataset freeze \
  --bundle <PATH_TO_REMOTE_ANNOTATIONS_BUNDLE.json> \
  --assets <PATH_TO_ASSETS_DIR> \
  --out data/freeze_20260825 \
  --allow-unannotated-drop
```
This produces:
- `manifest.jsonl`, `manifest.train.jsonl`, `manifest.val.jsonl`, `manifest.test.jsonl`
- `train_llamafactory.json`
- `annotation_agreement.jsonl`
- `character_slices.json`
- `freeze_report.json` (containing SHA-256 hashes of all artifacts)

---

## 3. Pinned Three-seed Training

### 3.1 Prepare Run Plan
Generate pinned execution commands and seed directories:
```bash
uv run python -m finetune.train prepare \
  --yaml finetune/train_qlora.yaml \
  --freeze-dir data/freeze_20260825 \
  --runs-root runs/objective4_runs
```

### 3.2 Execute Training
Run the three training seeds (0, 1, 2) sequentially with fail-fast execution:
```bash
uv run python -m finetune.train execute \
  --runs-root runs/objective4_runs
```

---

## 4. Checkpoint Inventory & Multi-LoRA Serving

Inventory all saved checkpoints across the 3 runs:
```bash
uv run python -m finetune.evaluate validation-inventory \
  --runs runs/objective4_runs \
  --out runs/objective4_runs/validation_candidates.json
```

Start the vLLM server with all candidate LoRA modules enabled (command recorded in `validation_candidates.json`):
```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --revision cc594898137f460bfe9f0759e9844b3ce807cfb5 \
  --enable-lora \
  --max-lora-rank 16 \
  --lora-modules <MODULE_MAP>
```

---

## 5. Validation Selection & Evaluation Lock

Run validation predictions for all checkpoint candidates, select the top checkpoint per seed and the deployment candidate on `manifest.val.jsonl`, tune cosine thresholds for CLIP/DINOv2, and create the immutable `evaluation_lock.json`:
```bash
uv run python -m finetune.evaluate validate \
  --freeze data/freeze_20260825 \
  --candidates runs/objective4_runs/validation_candidates.json \
  --predictions data/val_predictions \
  --out data/evaluation_lock.json
```

---

## 6. Held-out Test Split Access & Evaluation

⚠️ **The held-out test split is evaluated exactly once.**
Any access requires formal sign-off in the access ledger.

### 6.1 Reserve Test Access
```bash
uv run python -m finetune.evaluate reserve-test \
  --ledger data/heldout_ledger.json \
  --lock data/evaluation_lock.json \
  --freeze data/freeze_20260825 \
  --run-id run-20260825-final \
  --approver Hanseooo \
  --purpose "Objective-4 final held-out benchmark"
```

### 6.2 Execute Held-out Evaluation
```bash
uv run python -m finetune.evaluate run-heldout \
  --freeze data/freeze_20260825 \
  --lock data/evaluation_lock.json \
  --ledger data/heldout_ledger.json \
  --run-id run-20260825-final \
  --approver Hanseooo \
  --purpose "Objective-4 final held-out benchmark" \
  --predictions data/heldout_predictions
```

---

## 7. Results Aggregation & Deployment Decision

Aggregate final held-out metrics, bootstrap confidence intervals, slice metrics, and evaluate the §7.2 product deployment rung:
```bash
uv run python -m finetune.evaluate aggregate \
  --freeze data/freeze_20260825 \
  --lock data/evaluation_lock.json \
  --predictions data/heldout_predictions \
  --out data/objective4_results.json
```

The output report in `objective4_results.json` contains:
- 3 tuned seed F1 scores, mean, and sample standard deviation
- Benchmark comparisons vs `zero_shot_base`, `prompted_gemma`, `clip_cosine`, `dinov2_cosine`
- Non-human character slice evaluation
- Final deployment gate verdict (`"pass"` / `"fail"`) and recommended model ID.

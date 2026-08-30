# 03 — Bind training to the selected immutable freeze

**What to build:** A training launch can only consume the exact immutable freeze that passed preflight. The generated LLaMA-Factory invocation uses that selected dataset directory, verifies every required frozen artifact and toolchain pin, and rejects mismatched or altered inputs before allocating GPU work.

**Blocked by:** 02 — Reconcile the Batch 3 implementation baseline.

**Status:** completed
**Labels:** `criticality:critical`, `complexity:high`

- [x] The dataset directory passed to LLaMA-Factory is derived from the same freeze selected by the training command; a hardcoded alternate directory cannot win.
- [x] Preflight verifies the recorded hash of the combined manifest and the hashes of all train, validation, dataset-info, and dataset-manifest artifacts required by training.
- [x] Preflight validates the frozen base-model revision, LLaMA-Factory commit, and declared hardware evidence rather than accepting non-empty placeholders.
- [x] The already-used YAML parser is declared as a direct backend dependency through `uv`, with no bare package installation instructions.
- [x] Failure tests cover a mismatched dataset path, changed artifact, missing artifact, wrong toolchain revision, and hardware evidence that does not match the approved record.
- [x] A successful dry-run prints an auditable three-seed command plan without starting GPU training or opening held-out data.
- [x] Training specs and operator instructions use the same freeze-binding and preflight contract.


## Verification (2026-08-28)

Criteria confirmed against committed code, not self-reported. Implementing commit: `5071096`
"fix(obj4): bind training to selected freeze" (2026-08-25, 9 files, +216/-56).

| Criterion | Evidence |
|---|---|
| Freeze-derived dataset directory wins over any hardcoded one | `train_qlora.yaml:29` is `dataset_dir: __SELECTED_FREEZE__`; `train.py:107` emits `dataset_dir={freeze.resolve()}` as a CLI override |
| Hashes of all required frozen artifacts verified | `train.py:139-165` `_validate_freeze` over the artifact list at `train.py:21-22`, against `freeze_report.json` |
| Base revision, LLaMA-Factory commit and hardware validated, not merely non-empty | `train.py:174-190` vs `installed_llamafactory_commit()` (`train.py:90`) and `hardware_inventory()` |
| YAML parser declared as a direct `uv` dependency | `pyproject.toml:44` `pyyaml>=6.0`, added in the same commit |
| Failure tests for path, changed artifact, missing artifact, toolchain, hardware | `test_finetune_train.py:131, 142, 149, 156, 166, 172` |
| Dry-run prints a three-seed plan without GPU work or held-out access | `test_finetune_train.py:94` |
| Specs and operator instructions carry the same contract | `docs/specs/judge-finetune.md`, `docs/capstone/research_runbook.md`, both touched by `5071096` |

The boxes were previously unticked while the implementation was complete; this reconciles the
record. No code changed for this ticket.

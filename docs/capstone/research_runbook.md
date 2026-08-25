# Objective-4 research runbook

> **Stop gate:** This runbook does not authorize donor contact, donated-story intake, generation, annotation
> or training. The consent/assent draft remains **DRAFT — DO NOT ADMINISTER** until its remaining blanks,
> retention schedule and Filipino/Tagalog translation are institutionally approved.

## Governance record before any donated intake

- [ ] Adviser approves the final study wording and operational process.
- [ ] HCDC/ethics approval covers consent, assent, retention, withdrawal and third-party processing.
- [ ] The participating school approves recruitment, contact and administration.
- [ ] The final consent/assent version, approval dates and approvers are recorded outside the dataset.
- [ ] The identity-to-receipt ledger is stored only in the ethics-approved restricted location outside
      StoryBuddy, its repository, Supabase research storage, logs, checkpoints and model artifacts.

## Sanitized intake and selection freeze

- [ ] Receive the source material through the approved process; do not place the raw submission, names,
      contacts or receipt code in the controlled JSON intake.
- [ ] Manually redact PII, then obtain an independent second-person redaction review before creating the
      donated `story_id` record.
- [ ] Record affirmative guardian consent, child assent, manual-redaction and independent-review approvals.
- [ ] Freeze 10 primary and 5 backup held-out candidates before generation or judge outcomes: five candidates
      per style; primaries are 4 Gouache, 3 Cel and 3 Cut-paper; backups are 1 Gouache, 2 Cel and 2 Cut-paper.
- [ ] Keep each candidate's frozen style and role outcome-blind. A replacement may fill only the same-style
      slot after withdrawal, unusable/de-identification failure, terminal pipeline failure or inadequate
      character yield under the recorded rule.
- [ ] After selection freeze, restrict changes to the controlled intake file and record every approved
      same-style replacement in the restricted study record. The loader validates the completed freeze timestamp
      and exact batch allocation, but the approved record shape cannot reconstruct whether a role or style was
      edited after that timestamp.

## Withdrawal and stop rules

- [ ] Locate a withdrawal only through the restricted receipt ledger; mark the sanitized record withdrawn and
      exclude its story, assets, labels and dataset records before freeze under the approved retention process.
- [ ] After freeze, exclude a withdrawal from future training and evaluation and disclose that an already
      trained model cannot selectively unlearn one example.
- [ ] Stop before spending or advancing if an approval is missing, redaction is uncertain, a candidate is
      withdrawn, the selection is not frozen, or the approved retention/translation wording is incomplete.

## Execution pipeline sequence

Run all commands from `backend/`. Angle-bracket values (`<...>`) are operator inputs, not copy-ready literals.
Before a paid run, record the official Fal price URL, lookup date, authorized USD, pinned `1024x768` size,
raw maximum `0.786432` MP, Fal's `ceil(MP)` billing rule, and the resulting per-call ceiling. Supply the
current highest applicable rate for the two configured image endpoints as `<current-usd-per-megapixel>` and
pass the source plus lookup date as `<official-price-url-and-date>`.

```powershell
# 1. Zero-cost verification on temporary fixture directory
uv run python -m finetune.build_corpus --fixture --limit 1 --out <temporary-fixture-directory>

# 2. Paid synthetic smoke run (3 stories, conservative budget cap)
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --limit 3 --max-usd 1.50 --price-per-megapixel <current-usd-per-megapixel> --price-basis "<official-price-url-and-date>"

# 3. Full synthetic generation (24 train + 6 val stories)
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --max-usd 25 --price-per-megapixel <same-current-usd-per-megapixel> --price-basis "<same-official-price-url-and-date>"

# 4. Full donated generation (15 candidate stories: 10 primary + 5 backup)
uv run python -m finetune.build_corpus --corpus ../data/judge/intake/donated.json --out ../data/judge/corpus --max-usd 25 --price-per-megapixel <same-current-usd-per-megapixel> --price-basis "<same-official-price-url-and-date>"

# 5. Read-only candidate inspection for hard negative selection
uv run python -m finetune.build_dataset --candidate-report --data ../data/judge/corpus

# 6. Upload immutable assets and seed research pair queue
uv run python -m finetune.materialize_pairs --data ../data/judge/corpus --donated-intake ../data/judge/intake/donated.json --selection ../data/judge/intake/dataset_selection.json

# 7. Check annotation progress / reconcile pair queue
uv run python -m finetune.build_dataset --reconcile-only

# 8. Install immutable training dataset freeze
uv run python -m finetune.build_dataset --freeze --data ../data/judge/corpus --donated-intake ../data/judge/intake/donated.json --selection ../data/judge/intake/dataset_selection.json --out ../data/judge/freezes/obj4-v1

# 9. Install the exact training tool in the qualified GPU environment
uv tool install "llamafactory @ git+https://github.com/hiyouga/LlamaFactory.git@7af909522a951e3ad9f022ea6f88b6755257eaa5"

# 10. On the qualified host, have the operator record the approved base/tool pins and exact
# hardware_inventory() output in ../data/judge/training_qualification.json. Verify that record and
# installed uv-tool commit provenance, and every training artifact hash; then print/write immutable
# plans for seeds 0, 1 and 2 (zero-cost).
uv run python -m finetune.train --freeze ../data/judge/freezes/obj4-v1 --qualification ../data/judge/training_qualification.json --run-root ../data/judge/runs/obj4-v1 --prepare

# 11. After recording the qualified hardware and activating the external spend alarm, train all seeds
uv run python -m finetune.train --freeze ../data/judge/freezes/obj4-v1 --qualification ../data/judge/training_qualification.json --run-root ../data/judge/runs/obj4-v1 --execute --spend-alarm-confirmed

# 12. Inventory every checkpoint and obtain the exact generated vLLM command
uv run python -m finetune.evaluate validation-inventory --runs ../data/judge/runs/obj4-v1 --out ../data/judge/evaluations/obj4-v1/validation_candidates.json

# 13. Start the generated vllm_command, point JUDGE_BASE_URL/JUDGE_API_KEY at it, then capture validation evidence
uv run python -m finetune.evaluate capture-validation --freeze ../data/judge/freezes/obj4-v1 --candidates ../data/judge/evaluations/obj4-v1/validation_candidates.json --predictions ../data/judge/evaluations/obj4-v1/validation

# 14. Select checkpoints and cosine thresholds using validation only; write the immutable lock
uv run python -m finetune.evaluate validate --freeze ../data/judge/freezes/obj4-v1 --candidates ../data/judge/evaluations/obj4-v1/validation_candidates.json --predictions ../data/judge/evaluations/obj4-v1/validation --out ../data/judge/evaluations/obj4-v1/evaluation_lock.json

# 15. After an owner/adviser independently writes evaluation_signoff.json, run the one guarded evaluation
uv run python -m finetune.evaluate heldout --freeze ../data/judge/freezes/obj4-v1 --lock ../data/judge/evaluations/obj4-v1/evaluation_lock.json --signoff ../data/judge/evaluations/obj4-v1/evaluation_signoff.json --ledger ../data/judge/evaluations/obj4-v1/test_access.jsonl --run-id obj4-heldout-1 --predictions ../data/judge/evaluations/obj4-v1/heldout-1/predictions --out ../data/judge/evaluations/obj4-v1/heldout-1/objective4_results.json
```

`evaluation_signoff.json` is written by the approver, never by evaluation code. It contains exactly the
SHA-256 of `evaluation_lock.json`, a nonblank `approved_by`, and a timezone-bearing `approved_at`. A second
`heldout` invocation is legal only after a completed Rung-D report and additionally requires
`--deviation <PATH>` with the preregistered report hash, defect, fix commit, train/validation-only evidence,
and approval timestamp. There is no third-read command and no automatic deployment.

Steps 11 and 13 run in the qualified GPU environment whose exact PyTorch, CUDA, bitsandbytes and transformers
versions are recorded with the run evidence. Install those hardware-specific versions with `uv`, never bare
`pip`; they deliberately remain outside the deployed backend dependency set.

### Operational invariants and integrity gates

- **Visual comparison dimensions:** Hard negative candidate inspection evaluates five dimensions: body shape/structure, key colours, prominent facial/body features, clothing/accessories, and rendered art style.
- **Hard negative freeze-before-annotation gate:** All cross-character hard negative matches in `dataset_selection.json` must be frozen with a timestamp preceding all non-pilot annotations in Supabase.
- **Replacement evidence rule:** Any primary donor withdrawal/failure replacement requires documented evidence in `dataset_selection.json` satisfying the exact same style preset and leaving exactly 10 primaries (4 Gouache, 3 Cel, 3 Cut-paper).
- **Immutable freeze directories:** `data/judge/freezes/obj4-v1` is strictly immutable. Any legitimate pre-training modification must produce a new named directory (e.g. `obj4-v2`); `finetune.train --freeze` is the sole dataset-directory selection and is injected into every generated command after hash preflight.
- **Qualified training host:** `training_qualification.json` records the approved base revision, exact LLaMA-Factory commit/version, and full hardware inventory. Preparation and execution fail unless the live host matches it exactly.
- **Test-unopened rule:** The test split (`test.json` in the freeze) is held-out and must never be inspected, browsed, or evaluated during model development.
- **Three-seed validation-only development:** Checkpoint selection and hyperparameter exploration use only `train.json` and `val.json` over 3 random seeds (0, 1, 2).
- **Held-out evaluation:** The final selected model checkpoint is evaluated once on the held-out test split at study conclusion. Only preregistration §7's Rung-D defect exception permits exactly one second read after debugging exclusively on train/validation; both readings and the deviation must then be reported, and no third read is allowed.

## Evidence to retain outside intake data

Record approval references, finalized consent/assent version, selection-freeze timestamp, withdrawal actions
and deviations in the restricted study record. The JSON intake contains only the validated de-identified
research fields accepted by `finetune.corpus_io`.

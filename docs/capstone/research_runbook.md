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

```powershell
# 1. Zero-cost verification on temporary fixture directory
uv run python -m finetune.build_corpus --fixture --limit 1 --out <temporary-fixture-directory>

# 2. Paid synthetic smoke run (3 stories, conservative budget cap)
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --limit 3 --max-usd 1.50 --price-per-call <pinned-conservative-price>

# 3. Full synthetic generation (24 train + 6 val stories)
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --max-usd 25 --price-per-call <same-pinned-price>

# 4. Full donated generation (15 candidate stories: 10 primary + 5 backup)
uv run python -m finetune.build_corpus --corpus ../data/judge/intake/donated.json --out ../data/judge/corpus --max-usd 25 --price-per-call <same-pinned-price>

# 5. Read-only candidate inspection for hard negative selection
uv run python -m finetune.build_dataset --candidate-report --data ../data/judge/corpus

# 6. Upload immutable assets and seed research pair queue
uv run python -m finetune.materialize_pairs --data ../data/judge/corpus --donated-intake ../data/judge/intake/donated.json --selection ../data/judge/intake/dataset_selection.json

# 7. Check annotation progress / reconcile pair queue
uv run python -m finetune.build_dataset --reconcile-only

# 8. Install immutable training dataset freeze
uv run python -m finetune.build_dataset --freeze --data ../data/judge/corpus --donated-intake ../data/judge/intake/donated.json --selection ../data/judge/intake/dataset_selection.json --out ../data/judge/freezes/obj4-v1
```

### Operational invariants and integrity gates

- **Visual comparison dimensions:** Hard negative candidate inspection evaluates five dimensions: body shape/structure, key colours, prominent facial/body features, clothing/accessories, and rendered art style.
- **Hard negative freeze-before-annotation gate:** All cross-character hard negative matches in `dataset_selection.json` must be frozen with a timestamp preceding all non-pilot annotations in Supabase.
- **Replacement evidence rule:** Any primary donor withdrawal/failure replacement requires documented evidence in `dataset_selection.json` satisfying the exact same style preset and leaving exactly 10 primaries (4 Gouache, 3 Cel, 3 Cut-paper).
- **Immutable freeze directories:** `data/judge/freezes/obj4-v1` is strictly immutable. Any legitimate pre-training modification must produce a new named directory (e.g. `obj4-v2`) and a deliberate configuration update.
- **Test-unopened rule:** The test split (`test.json` in the freeze) is held-out and must never be inspected, browsed, or evaluated during model development.
- **Three-seed validation-only development:** Checkpoint selection and hyperparameter exploration use only `train.json` and `val.json` over 3 random seeds (0, 1, 2).
- **One-time held-out evaluation:** The final selected model checkpoint is evaluated exactly once on the held-out test split at study conclusion.

## Evidence to retain outside intake data

Record approval references, finalized consent/assent version, selection-freeze timestamp, withdrawal actions
and deviations in the restricted study record. The JSON intake contains only the validated de-identified
research fields accepted by `finetune.corpus_io`.

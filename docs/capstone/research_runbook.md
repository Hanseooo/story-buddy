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

## Dataset handoff (2026-09-30)

The registered `data/judge/freezes/obj4-v1` freeze is installed: manifest SHA-256
`9faa7b3217466c8b8aec074e6e3f36df4cedb1a0a489f196c2da402cae2a1d0b`, with
484 train, 86 validation and 329 held-out test pairs. The separate exploratory
`data/judge/freezes/obj4-exploratory-qc-v2` freeze has manifest SHA-256
`646b795e26f865f62ea45fc4c12e6b83b343f33b47014f84f7925f70b4f40ad3`, with
468 train, 86 validation and 329 test pairs. Its 16 exclusions are synthetic training
pairs only. No retained natural or constructed training pair uses one of their scene
images; validation and test manifests and the validation payload match the registered
freeze byte for byte. The training runner's hash and manifest preflight passed for both.
The ten AI-assisted audit labels and their protocol deviation are recorded in
`PREREGISTRATION_OBJ4.md` and `adjudication-notes-2026-09.md`.

### What the registered freeze contains (counted 2026-10-10)

Counted from `data/judge/freezes/obj4-v1/manifest.jsonl` and checked against `freeze_report.json`.
Both are local and git-ignored, so this table is the public source for these totals. The
`/research/dataset` page cites it (ADR-065).

| Split | Stories | Characters | Pairs | Same | Different | Constructed pairs |
|---|---|---|---|---|---|---|
| Train (synthetic) | 24 | 44 | 484 | 327 | 157 | 104 |
| Validation (synthetic) | 6 | 11 | 86 | 82 | 4 | 0 |
| Held-out test (donated) | 12 | 24 | 329 | 282 | 47 | 0 |
| All | 42 | 79 | 899 | 691 | 208 | 104 |

No story or character is in more than one split. A constructed pair sets one character's reference
against another character's page, so it is Different by construction and was not shown to the
raters. The other 795 pairs came out of the pipeline and are the ones the two raters labelled.
All 104 constructed pairs carry the one reason `different_face` and the one sentence in
`CONSTRUCTED_RATIONALE` (`backend/finetune/build_dataset.py`). No rater wrote either.

**Two constructed pairs contradict a rated pair (found 2026-10-11).** `constructed_records` in
`backend/finetune/build_dataset.py` pairs a reference with every page its matched character has a
pipeline pair for. `dataset_selection.json` holds 14 frozen matches. Twelve pair a character with
one from another story. The other two match `syn-020:c0` and `syn-020:c1` to each other inside one
story, and one page of that story (`s1-1`) shows both of them. So the builder made `e16ef0eee299d1ae` (c0's reference, that page)
and `3f5380f572b0730b` (c1's reference, that page) as Different, while the raters had labelled the
same two image pairs Same (`a130ca522d1ebb36`, `83fec61200a0dfc0`). `train.json` therefore holds two
image pairs with both answers: 2 of the 104 constructed pairs, 4 of the 484 training records. The
other 102 constructed pairs share no image pair with a rated pair (checked over all 899 records).
The freeze is registered and is not changed. No validation or test pair is affected. Whether a
constructed page happens to show the reference character without a rated pair saying so was not
checked by eye.

Drift reasons on the 208 Different pairs. A pair can carry more than one, so they sum to 236:

| Reason | Pairs |
|---|---|
| Different Face | 141 |
| Wrong Body Feature | 50 |
| Character Absent | 18 |
| Wrong Clothing/Accessories | 12 |
| Wrong Color | 9 |
| Wrong Style | 4 |
| Wrong Species | 2 |

The two artifact checkboxes, on all 899 pairs: Broken Anatomy on 32, Text Visible on 3.

Next: qualify a rented GPU host, install the pinned LLaMA-Factory tool and host-specific
PyTorch/CUDA/bitsandbytes versions, record `training_qualification.json`, then run steps
10–11 below under the accepted
[ADR-061](../product/adr/ADR-061-qwen3-5-9b-as-the-objective-4-judge-base.md) and the
[dated protocol amendment](../product/PREREGISTRATION_OBJ4.md). The training/evaluation code now
uses the amended pins. Qualify both images, an actual
QLoRA step and measured peak GPU memory; the old 7B memory estimate does not qualify 9B.
The owner rented Vast.ai instance 53678415 on 2026-10-01 for the initial USD 2-capped
qualification session. Session evidence and capture status belong in
`data/judge/qualification/vast-53678415/capture_notes.md`; this is not a passed qualification.
The owner reported on
2026-09-30 that third-party Vast.ai processing is approved; keep the approval reference
in the restricted study record and verify the remaining governance entries above before
upload. Compare the live on-demand offer's GPU memory, reliability, compute, storage and
bandwidth charges. [Vast.ai pricing](https://github.com/vast-ai/docs/blob/main/guides/pricing.mdx)
notes that storage billing continues while an instance is stopped; download the run
evidence and delete the instance when finished. The registered freeze is the input to
the registered run; use the exploratory freeze only for an explicitly named exploratory
run with a separate run directory.

## Held-out resume context (2026-10-07)

This section records the latest owner conversation and local artifact checks. Earlier qualification
and preparation notes below describe their own stages, not the current execution state.

**Training and validation selection are complete. The owner confirmed the reporting scope as
untuned Qwen versus fine-tuned Qwen and requested documentation with verification references.
The partial held-out comparison is saved; all four Qwen and both embedding-control captures are
verified locally. The owner reported destroying the remaining rentals and cannot fund another
top-up. Paid evaluation has stopped. Prompted Gemma failed authentication and the full registered
report remains incomplete. Preserve that failed attempt as infrastructure evidence, not a quality
result. The next workstream is the existing pipeline, with the production judge unchanged.**

The [signed evaluation lock](../../data/judge/evaluations/obj4-v1/evaluation_lock.json) and
[owner sign-off](../../data/judge/evaluations/obj4-v1/evaluation_signoff.json) remain authoritative.
Keep their checkpoint choices, prompts, thresholds and 256-token generation cap unchanged.
The validation precision, recall and F1 in the
[validation score report](../../data/judge/evaluations/obj4-v1/validation_scores.json) are selection
results, not final test results. That table compares the three selected fine-tuned seeds with CLIP
and DINO. It does not contain untuned Qwen or prompted Gemma.

### Saved progress and safe resume

- Run ID: `obj4-heldout-1`. The [access ledger](../../data/judge/evaluations/obj4-v1/test_access.jsonl)
  contains one `reserved` event at `2026-10-06T19:34:56.305412Z`, with no completed report event.
- In `data/judge/evaluations/obj4-v1/heldout-1/predictions/`, `seed_0.jsonl` and `seed_1.jsonl`
  each contain 329 rows. Both checksum sidecars passed a fresh local SHA256 check for this handoff.
  At the original pause, seed 2 had not published a complete prediction file.
- The resumed run saved `seed_2.jsonl` and `zero_shot_base.jsonl`, each with 329 rows and matching
  checksum sidecars. All four GPU-dependent comparator files are now complete and locally verified.
- `prompted_gemma.jsonl` has 329 malformed entries and zero parsed entries following the owner's
  reported HTTP 401 `User not found` errors. Preserve the file and sidecar as the failed attempt.
  A Vast credit top-up does not repair OpenRouter authentication. The exact credential/account
  cause is unconfirmed; credentials must be entered by the owner at the hidden prompt only.
- Both held-out embedding controls now contain 329 parsed rows. Fresh local checks verified both
  checksum sidecars and the owner supplied successful alignment output from the recovery helper.
  `heldout-1/objective4_results.json` does not exist. The partial Qwen results below are available;
  a final Objective-4 claim-ladder/product-gate decision has not been calculated.
  A final report including the failed Gemma capture would misrepresent authentication as model quality.
- Resume the same run ID with identical signed hashes and the existing ledger. Preserve complete
  files and sidecars. The evaluator reuses complete verified comparator files; an unfinished
  comparator repeats its capture. This is not per-request resume. Do not delete or manually reset
  the ledger to create another first evaluation.

The original full Windows checkpoint directories are still needed for the signed hash guards.
Compact serving adapters do not replace them. The [operator handoff](../../data/judge/evaluations/obj4-v1/heldout-1/OPERATOR.md)
owns commands and the existing local guarded launcher. No raw held-out examples should be browsed
for development or used to tune the failed outputs.

### Partial untuned versus fine-tuned comparison (2026-10-08)

The owner requested this comparison after confirming destruction of the rentals. The reproducible
[partial result](../../data/judge/evaluations/obj4-v1/heldout-1/qwen_comparison.partial.json) is the source
of its numbers. The [screenshot table](../../data/judge/evaluations/obj4-v1/heldout-1/qwen_comparison.partial.html)
labels the comparison as partial and shows every selected seed, the untuned baseline, precision,
recall, F1, intervals and malformed counts. Run `heldout-1/score_qwen_comparison.py` through the
existing backend `uv run --frozen` environment to reproduce it.

On the frozen held-out pairs, untuned Qwen has higher observed F1 than each selected fine-tune.
The validation-preselected seed 1 gains precision but loses recall; its character-clustered paired
F1-difference interval includes zero. These results do not demonstrate a positive fine-tuning effect
under the evaluated dataset, training and inference constraints. This is not evidence that fine-tuning
is infeasible in general. Technical training feasibility and improved judge performance are separate
findings. The source contains the registered 10,000-resample interval, exact McNemar result and seed
mean/sample standard deviation. No seed or checkpoint was reselected using these results.

The analysis verified signed checkpoint identities, prediction sidecars and ordered pair coverage,
then used the existing metric functions under the same ledgered run ID. All thirteen
launcher/transport/recovery/partial-analysis tests and relevant lint passed after the new aggregation
tests first failed on real validation evidence. The final seven-comparator report and completed ledger
event remain absent. Gemma's authentication failure is excluded from this quality comparison;
the captured CLIP/DINO controls are outside this requested Qwen-only table. Prompts, caps and
thresholds remain fixed. Further model changes cannot be justified using inspection of these test outputs.

#### Exact values of the partial comparison (copied 2026-10-11)

Copied from `qwen_comparison.partial.json`, which is local and git-ignored, so this table is the
public source for these values. The `/research/results` page cites it (ADR-066). Test slice: 329
pairs, 47 Different and 282 Same. "Caught" is a Different pair the judge called Different, a "false
alarm" is a Same pair it called Different, and an unreadable answer is scored as Same.

| Judge | F1 | F1 95% interval | Precision | Recall | Caught (of 47) | Missed (of 47) | False alarms (of 282) | Correct Same (of 282) | Unreadable (of 329) |
|---|---|---|---|---|---|---|---|---|---|
| Untuned Qwen3.5-9B | 0.472 | 0.236 to 0.629 | 0.382 | 0.617 | 29 | 18 | 47 | 235 | 3 |
| Seed 1 (preselected) | 0.310 | 0.000 to 0.491 | 0.818 | 0.191 | 9 | 38 | 2 | 280 | 40 |
| Seed 0 | 0.361 | 0.000 to 0.586 | 0.786 | 0.234 | 11 | 36 | 3 | 279 | 44 |
| Seed 2 | 0.417 | 0.214 to 0.566 | 0.353 | 0.511 | 24 | 23 | 44 | 238 | 8 |

- Seed 1 minus untuned: ΔF1 −0.161, 95% character-clustered interval −0.358 to +0.003, exact
  McNemar p = 0.0035. Intervals use 10,000 resamples clustered by character.
- The three seeds: mean F1 0.363, sample SD 0.054.
- Selected checkpoint and its validation F1: seed 0 `checkpoint-40` 0.333, seed 1 `checkpoint-40`
  0.444, seed 2 `checkpoint-140` 0.364. The validation split has 4 Different pairs out of 86, so
  these three numbers each rest on four pairs.

Derived from the table, not stored in the source: the untuned model called 76 pairs Different and
was wrong on 65 pairs (47 false alarms, 18 misses). Seed 1 called 11 pairs Different and was wrong on
40 (2 false alarms, 38 misses). McNemar's test compares which pairs each judge got right, so its
small p goes with seed 1 being wrong on 25 fewer pairs. It does not say seed 1 is the better
detector: F1, the registered primary metric, is lower for seed 1 because it misses 38 of the 47
Different pairs. A judge that answered Same every time would be right on 282 of 329 pairs and catch
none.

#### Registered training settings (copied 2026-10-11)

Copied from `backend/finetune/train_qlora.yaml`, which last changed on 2026-10-02, before the
three-seed run. The `/research/results` page cites this table (ADR-066 amendment (a)). Between the
three runs the runner varies only `seed`, `output_dir`, `run_name` and `report_to`
(`docs/specs/judge-finetune.md` §6.4).

| Setting | Value |
|---|---|
| `model_name_or_path` | Qwen/Qwen3.5-9B |
| `finetuning_type` | lora |
| `quantization_bit` | 4 |
| `lora_rank` | 16 |
| `lora_alpha` | 32 |
| `image_max_pixels` | 262144 |
| `num_train_epochs` | 3.0 |
| `per_device_train_batch_size` | 1 |
| `gradient_accumulation_steps` | 8 |
| `learning_rate` | 1.0e-4 |
| `lr_scheduler_type` | cosine |
| `warmup_ratio` | 0.1 |
| `save_steps` | 10 |

- Training length: 61 updates per epoch, 183 per seed, on the 484 training records. The arithmetic
  is under "Full-run readiness and cost assessment (2026-10-02)" below.
- Derived from the table, not stored in a source: `checkpoint-40` is 40 of the 183 updates, before
  the first epoch ends at update 61. `checkpoint-140` is in the third epoch, which starts after
  update 122.
- A judge's answer at evaluation is capped at 256 tokens ("Held-out resume context" above).

### Verification sources for the accepted comparison

Paths below are relative to the repository root unless linked. The machine-readable result owns
the reported numbers; screenshots supplement it. These artifacts remain local research evidence,
not a public dataset or a second source of truth for study status.

| What to verify | Source / proof | Verification purpose |
|---|---|---|
| Reported metrics and uncertainty | [qwen_comparison.partial.json](../../data/judge/evaluations/obj4-v1/heldout-1/qwen_comparison.partial.json) | Four Qwen summaries, confusion counts, preselected seed 1 versus base, paired character-clustered interval, McNemar result, seed mean/SD, input hashes and limitations. |
| Screenshot for the manuscript | [qwen_comparison.partial.html](../../data/judge/evaluations/obj4-v1/heldout-1/qwen_comparison.partial.html) | Human-readable display of the same partial result. |
| Immutable captured decisions | [untuned](../../data/judge/evaluations/obj4-v1/heldout-1/predictions/zero_shot_base.jsonl), [seed 0](../../data/judge/evaluations/obj4-v1/heldout-1/predictions/seed_0.jsonl), [seed 1](../../data/judge/evaluations/obj4-v1/heldout-1/predictions/seed_1.jsonl), [seed 2](../../data/judge/evaluations/obj4-v1/heldout-1/predictions/seed_2.jsonl) | Each file has 329 ordered rows and an adjacent `.jsonl.sha256` sidecar; the result also records each digest. |
| Choices fixed before test reporting | [evaluation_lock.json](../../data/judge/evaluations/obj4-v1/evaluation_lock.json), [evaluation_signoff.json](../../data/judge/evaluations/obj4-v1/evaluation_signoff.json), [validation_scores.json](../../data/judge/evaluations/obj4-v1/validation_scores.json) | Base revision, selected checkpoint paths/digests, candidate seed, prompts, thresholds, manifest hashes and owner approval. Validation scores explain selection, not test effectiveness. |
| Frozen ground truth and coverage | [manifest.test.jsonl](../../data/judge/freezes/obj4-v1/manifest.test.jsonl), [freeze_report.json](../../data/judge/freezes/obj4-v1/freeze_report.json) | Manifest identity is checked against the signed lock. Reproduction uses the guarded analysis below; test examples are not debugging or tuning inputs. |
| Original read and resumptions | [test_access.jsonl](../../data/judge/evaluations/obj4-v1/test_access.jsonl) | Same run ID `obj4-heldout-1`, unchanged signed hashes, original reservation and resumptions. No completed full-report event exists. |
| Reproducible calculation | [score_qwen_comparison.py](../../data/judge/evaluations/obj4-v1/heldout-1/score_qwen_comparison.py), [evaluate.py](../../backend/finetune/evaluate.py), [evaluation_metrics.py](../../backend/finetune/evaluation_metrics.py) | Guards, ordered evidence checks, existing metric definitions, 10,000-resample character bootstrap and fixed RNG seed. No model call is made. |
| Regression and verification record | [test_score_qwen_comparison.py](../../data/judge/evaluations/obj4-v1/heldout-1/test_score_qwen_comparison.py), [preparation-verification.json](../../data/judge/evaluations/obj4-v1/heldout-1/preparation-verification.json) | Real validation fixtures test aggregate counts and refusal of reordered rows. Receipt records tests, partial-result/script hashes, saved progress and exclusions. |
| Training feasibility | [verified-extracted training runs](../../data/judge/qualification/vast-54113001/registered-training/verified-extracted/storybuddy/data/judge/runs/obj4-v1/), [qualification notes](../../data/judge/qualification/vast-54113001/capture_notes.md) | For each `seed-0`, `seed-1`, `seed-2`: `stdout.log`, `run_plan.json`, `hardware.json`, `output/trainer_state.json`, `output/train_results.json` and `output/eval_results.json`. Selected adapter locations/hashes are in the signed lock. Training success is separate from classification improvement. |
| Original study commitments | [PREREGISTRATION_OBJ4.md](../product/PREREGISTRATION_OBJ4.md) §§5, 7, 9; [judge-finetune.md](../specs/judge-finetune.md) §7 | Registered metrics, test-access policy and comparator requirements. The budget-limited partial comparison does not replace these commitments. |

To reproduce the saved comparison without paid calls, from the repository's `backend/` directory:

```powershell
uv run --frozen python ../data/judge/evaluations/obj4-v1/heldout-1/score_qwen_comparison.py
Start-Process ../data/judge/evaluations/obj4-v1/heldout-1/qwen_comparison.partial.html
```

The script verifies the signed lock and original checkpoint directories, resumes the same ledgered
run, checks frozen manifest and prediction hashes/identities, and reproduces the existing partial
outputs exclusively/idempotently. It neither overwrites predictions nor publishes the full report.
Keep the referenced original checkpoint directories available for these checks. For a checksum-only
audit, compare `Get-FileHash -Algorithm SHA256` against the adjacent prediction sidecars and the
result's `prediction_sha256` map; this does not read test labels or reserve another access.

### Registered agreement and sensitivity analyses (2026-10-09)

These are the 2026-09-23 amendment's items 2, 3 and 5 (`PREREGISTRATION_OBJ4.md` §12), run on the
saved predictions and frozen labels only. No model call, no reselection, no label change. The
[result](../../data/judge/evaluations/obj4-v1/heldout-1/sensitivity_and_agreement.json) owns the
numbers; [score_sensitivity.py](../../data/judge/evaluations/obj4-v1/heldout-1/score_sensitivity.py)
reproduces it. It resumed run `obj4-heldout-1` once more (new resumed event in `test_access.jsonl`,
2026-10-08T23:28:48Z). Label timestamps came from a read-only fetch of the `annotations` table
(`annotation_times_2026-10-09.json`, 1772 rows); the script refuses to run unless the database labels
equal the freeze labels on every pair. Agreement treats "different character" as the positive
class, as `evaluate.py` does. All files are local and git-ignored.

**Inter-rater agreement on `same_character`** (raters `c4f346f6` and `d9a03bf8`):

| Slice | n | Cohen's κ | Agreement |
|---|---|---|---|
| Test slice (registered number) | 329 | 0.634 | 89.7% |
| Test, human characters | 304 | 0.636 | |
| Test, non-human characters | 25 | 0.000 | 96.0% |
| All 795 pairs (labelled as such) | 795 | 0.659 | 89.3% |

The non-human κ of 0 is a prevalence artifact, checked: 24 of 25 pairs were Same for both raters,
and on the one disagreement only one rater said Different, so the other rater has no Different
label and κ cannot rise above 0. Report it with the raw counts, not as "no agreement".

The amendment's 78.4% agreement (172 conflicted pairs) is a different measure. The labelling app
marks a pair conflicted unless both raters match on `same_character`, `anatomy_intact`,
`text_free` and the set of failure reasons (`frontend/app/(research)/_shared/validation.ts`,
`isConsensus`). Only 85 of 795 pairs disagree on `same_character`. The 182 adjudication rows match
the 172 conflicts plus the ten AI-assisted audit labels (inferred from the counts). The 172 was not recounted here; the
timestamp fetch held only `same_character`.

**Before and after the guide fix** (deploy `757a406`, 2026-09-21 09:31:50 UTC). Labels before the
boundary: 324 and 318, matching the amendment. A pair counts as before or after only when both
labels fall on that side; most pairs straddle because the raters worked in different orders.

| Pairs | All: n | All: κ | Test: n | Test: κ |
|---|---|---|---|---|
| Both before | 42 | 0.419 | 11 | 1.000 |
| Straddling | 558 | 0.683 | 228 | 0.662 |
| Both after | 195 | 0.630 | 90 | 0.483 |

The groups are small and self-selected by labelling order, so this shows no clear guide effect
either way. It is not evidence that the guide fix helped or hurt.

**Secondary sensitivity analysis** (ambiguous-reference list from
[`ambiguous-references-2026-09.md`](ambiguous-references-2026-09.md): `don-005:c1`, `syn-028:c0`,
`syn-030:c0`). Only `don-005:c1` is in the test slice, so 20 pairs were dropped: n = 309, 41
Different, 268 Same.

| Judge | F1 | Precision | Recall |
|---|---|---|---|
| Untuned | 0.476 | 0.391 | 0.610 |
| Seed 1 (preselected) | 0.346 | 0.818 | 0.220 |
| Seed 0 | 0.400 | 0.786 | 0.268 |
| Seed 2 | 0.438 | 0.382 | 0.512 |

Seed 1 minus untuned: ΔF1 −0.130, 95% character-clustered CI −0.333 to +0.053, exact McNemar
p = 0.0075. Inter-rater κ on the kept test pairs: 0.709. The direction matches the primary analysis.
The primary analysis (every pair) stands; this secondary never replaces it and decides no claim rung.

**Limitations.** Both raters are group members briefed by the owner, who adjudicates; κ cannot
detect a shared misunderstanding. The comparison remains partial (no prompted Gemma).

```powershell
uv run --frozen python ../data/judge/evaluations/obj4-v1/heldout-1/score_sensitivity.py
```

Run from `backend/`. Each run adds a resumed event to the ledger. The publish step is exclusive: identical
output is accepted, and any changed output raises instead of overwriting.

### Owner decisions and confirmed scope

The owner explicitly requested **untuned Qwen next**, then consideration of a documented research
finding and a return to pipeline work if fine-tuning performs weakly. Untuned Qwen is already a
registered comparator (`zero_shot_base`, the same pinned Qwen3.5-9B without an adapter).
The local runner now verifies saved seed evidence, captures missing untuned Qwen predictions first,
then resumes missing selected seeds and the other registered comparators. The existing resume test
first failed because `seed_0` ran before `zero_shot_base`; after the ordering change all 46 evaluator
tests and relevant lint passed. The test also removes the saved baseline while tampering with a saved
seed to require refusal before any new prediction. Existing complete baseline and seed files are reused.
This is an operational capture-order change, not a change to the signed research choices or coverage.

The owner confirmed that "normal Qwen" meant the trained fine-tune: report **untuned versus
fine-tuned Qwen**, document the finding and proof locations, and stop further paid evaluation because
another top-up is not possible. Seed 1 remains the validation-preselected primary comparison;
all three selected seeds remain in the table and original evidence. This budget-limited scope leaves
the registered seven-comparator study incomplete. It does not amend the frozen requirements or
permit a complete-report/production-swap claim. CLIP/DINO captures remain preserved as auxiliary
evidence; the invalid Gemma attempt remains excluded from quality comparisons.

Three completed training runs establish technical feasibility in this setup. They do not establish
improved judgment. If the completed registered comparison supports it, a bounded finding could be:
"Under the evaluated dataset, training settings and inference constraints, fine-tuning did not
demonstrate a reliable improvement over the untuned baseline." Do not generalize that conclusion
to fine-tuning in all settings, or use validation selection scores to support it. Preserve malformed
outputs as registered failures rather than changing the cap after seeing test behavior.
Further training, a production judge swap and changes to the frozen research design have not been
approved by this discussion. Keep the production Gemma judge and existing pipeline decisions.

### Infrastructure and budget handoff

The owner's latest observations, not a fresh API check, were:

- Retained instance **54471883**, host `361582`, machine `124820`, was inactive after an attempt
  to restart showed `Scheduling` because its GPU was in use. Files were retained. Last SSH endpoint
  was `122.183.60.28:41180`; obtain the current endpoint before reconnecting. Stopping released
  the GPU reservation, so restarting is not guaranteed. Its displayed storage charge was
  `$0.038/hour`, and running base cost `$0.438/hour`, excluding bandwidth.
- Replacement **54633938**, host `86680`, machine `149573`, IP `129.153.115.129`, had only been
  reported as creating. No SSH endpoint, runtime qualification or transfer was completed. Its
  stopped/destroyed status was unconfirmed. The latest all-instances page no longer lists it.
- Replacement **54645099**, host `314882`, machine `51579`, IP `72.83.150.152`, remained
  `Connecting` at 16 minutes with a displayed running rate of `$0.515/hour`. Its proxy endpoint
  was `ssh7.vast.ai:10679`. Both SCP and plain SSH with configuration disabled failed before
  authentication: `banner exchange: Connection to UNKNOWN port -1: Connection refused`.
  TCP connected before the plain SSH failure. No direct-port check or container log was available,
  so the root cause remains undiagnosed. The operating guide could not be downloaded; no study
  payload was uploaded. The owner subsequently reported deleting this instance.
  Offer **54647728** then appeared on the same host/machine. Avoid retrying that machine for the
  next attempt without evidence that its connectivity issue has been resolved.
- The owner nevertheless rented **54649859** on host `314882`, machine `51579`, IP
  `72.83.150.152`. At 53 seconds it showed `Loading` and "Successfully loaded vastai/pytorch:cuda-12.8.1-auto".
  Its direct SSH endpoint is now `72.83.150.152:52502`. The owner connected, downloaded its
  operating guide (read locally), uploaded both compact recovery packets and reported pinned
  installation, CUDA computation and media import passed. The owner subsequently reported pinned
  Qwen caching and SHA256 verification of both public control weights passed. Remote log evidence
  is not yet downloaded.
- A fresh local recovery check verified the full compact selected-serving archive hash and every
  member, located the original Linux evaluator snapshot matching the qualified hash in the prior
  validation packet, and rechecked both complete seed prediction sidecars. New-host installation,
  model caching and validation-only control qualification are still required.
- The verified [fresh-host support packet](../../data/judge/evaluations/obj4-v1/heldout-1/serving/fresh-host-support-v1.zip)
  contains the qualified Linux source, 69 validation images, their original preparation metadata
  and both saved validation controls. Its 88 payload members total an 11,658,451-byte ZIP, with
  SHA256 `46255907a6fe7f38e10275661d56ef2d159a1c20a1211e5b596dbf29c30b00d1`.
  It complements the existing selected-serving adapter packet; neither contains held-out records.
  Both archives passed member/hash checks. The owner reported installation and public model
  downloads passed. The owner then reported all six validation scores and frozen decisions passed
  over live SSH on the new host, followed by HTTP health 200 and exact base/adapter inventory checks.
- The SSH control transport now explicitly sets the original qualified 14 CPU threads, rather
  than depending on the new machine's CPU allocation. Its regression test failed when those
  settings were absent, then all nine launcher tests and targeted lint passed after the adjustment.
  The original immutable Linux proof remains the expected reference. It does not establish that
  this new host passes. The owner subsequently supplied passing output for the six live validation
  scores on the replacement. This check made no additional held-out access or ledger reservation.
- Last reported balance was **$1.61**, not a live balance. The owner prefers manual top-ups and
  asked to avoid repeated balance/time questions. Previous extensions do not authorize unlimited
  spending or a new top-up. Preserve the approved limits and allow for backup/transfer charges.

Before paid capture on any replacement host, read its operating guide, verify its runtime, qualify
the Linux controls using validation only, check private serving health and the exact base/adapter
inventory, and pass the local signed-input guards. The retained-host wrapper assumes cached model
weights; a fresh host needs verified public weights first. Do not blindly reuse offline startup
commands on an empty cache. Existing preparation receipts record the fixes for manifest collisions,
TorchCodec imports and Linux control compatibility.

**Next action:** the confirmed comparison and verification references are documented above. Return
to the existing pipeline workstream after consulting its current backlog/spec. No
further paid evaluation or top-up is authorized by the latest request. The owner reported destroying
the remaining rentals after both CPU controls passed local verification; this is not an independent
billing API check. All GPU and CPU comparator files are saved locally. Gemma recovery is outstanding
but no longer the active paid task. Preserve its failed file/sidecar. If completing the full study is
later authorized, recover authentication and capture Gemma under the same run and signed choices.
Do not rerun the ordinary launcher as-is:
it would reuse the invalid all-malformed Gemma file and still require an unnecessary Linux host.
The observed 401 payload
reproduced the runner swallowing authentication errors as malformed model answers. The minimal fix
propagates HTTP 401 before publishing a comparator file, while preserving the malformed-output scoring
rule. Recovery must not overwrite existing evidence or reset the ledger. The requested partial Qwen
comparison is saved above; completing the full study still requires the valid prompted Gemma capture.
Do not present the partial result as the complete registered report. No new training is needed.

## Qwen35 host qualification

Registered three-seed training and backups are complete; validation checkpoint selection and control
thresholds are locked. See [held-out resume context](#held-out-resume-context-2026-10-07) for current progress.
The owner confirmed hosts 54113001 and 54261178 destroyed after verified local backups.
See the [validation runtime benchmark](#validation-runtime-benchmark-2026-10-05) before budgeting further scoring. Its independently
verified qualification evidence and operator acceptance are recorded in
[`vast-54113001/capture_notes.md`](../../data/judge/qualification/vast-54113001/capture_notes.md).
The earlier checks below span separate qualification sessions. Installation/runtime and
registered preprocessing checks passed on the initial rented host. Its one-step GPU execution logged zero learning
rate and saved zero LoRA B tensors; retain it as training-path evidence only. The later guarded
two-step retry produced a nonzero weight update, verified directly against the saved initial
adapter. Its logs, trainer states, measured peak memory and complete final adapter are locally
verified and backed up. The later inference result is recorded below.
See the session evidence above for raw results and
capture status. Those earlier qualification sessions did not start registered study training.
The owner confirmed this qualification instance destroyed on 2026-10-02 Manila time after
local backups were verified. See the session capture notes for final billing and restore artifacts;
a future training host needs fresh runtime checks and an operator-approved qualification record.
The replacement inference-only instance 53813406 was also destroyed after its downloaded
evidence and the prior adapter backup passed local hash checks. Its isolated vLLM server
started after replacing an incompatible TorchCodec CUDA build with the same-version CPU
build. Base/adapter inventory passed, but the preprocessing guard failed before any judge
request. The raw evidence receipt and diagnosis are in
[`vast-53813406/capture_notes.md`](../../data/judge/qualification/vast-53813406/capture_notes.md).
This is a failed inference qualification, not a quality result or proof of adapter execution.
The local CPU replay identifies a missing LLaMA-Factory image preparation step in serving
inputs. Matching the numeric pixel cap alone does not match the training preprocessing.
The owner approved the local correction under ADR-061. Qualification and Qwen evaluation now
share `finetune/image_preprocessing.py`, using the unchanged trainer resize semantics and
existing Pillow dependency. The Qwen observer requires embedded image data so remote URLs
cannot silently bypass preparation. Gemma retains original inputs. Local verification matches
the pinned trainer's prepared RGB pixels for every synthetic transfer asset and all recorded
train/validation image grids. Those checks do not qualify actual model inference.
The corrected bundle was restore-verified and tested on inference-only instance 53867285.
Its four preselected synthetic base/adapter requests passed strict verdict-field and raw-type
checks, returned the requested model names, and matched the qualified training image grids.
The downloaded archive, every retained file hash, original input/profile bytes and raw responses
were independently verified locally. The server warned about unsupported visual LoRA wrappers;
inspection of the saved adapter tensor header confirmed that it contains only language-model
tensors, so those warnings did not omit trained visual adapter weights. All four confidence
values were unavailable; retain that limitation rather than inventing probabilities.
The owner confirmed the instance destroyed after backup verification. This is a synthetic
contract result, not quality improvement, a production deployment qualification or completed
study training. Evidence, billing and pending screenshots are recorded in
[`vast-53867285/capture_notes.md`](../../data/judge/qualification/vast-53867285/capture_notes.md),
with the machine-readable integrity receipt beside it. The current training-host attempt is
recorded in [`vast-54113001/capture_notes.md`](../../data/judge/qualification/vast-54113001/capture_notes.md).
Its raw-file backup verification and operator acceptance passed. The owner reported matching
immutable three-seed plans and sufficient live GPU/disk resources. Registered seed 0 started
under the existing budget and confirmed spend alert; the completed three-seed evidence is retained locally.
The first execution attempt stopped before any trainer child because the runner compared the
CLI's `version 0.9.5` banner with the literal `v0.9.5` Git tag. A locally tested correction
compares the complete version value while preserving the commit and recipe pins. See the
current capture notes for the failed launch, patch hashes and successful retry's progress.
The laptop's observed RTX 3050 Ti has 4 GB VRAM. Do not run steps 10–11 or upload the
donated held-out split while preparing or qualifying the toolchain.

1. Select a short **on-demand, single-GPU offer with at least 24 GB VRAM**. Compare verified-host
   status, reliability, system RAM, free disk, driver and network throughput as well as compute,
   storage and transfer charges. A 24 GB offer is a starting candidate, not a measured fit.
   Record the offer/host ID, template, approved qualification USD cap, deadline and active external
   spend alarm before rental. Vast's [official pricing guide](https://github.com/vast-ai/docs/blob/main/guides/pricing.mdx)
   describes live offers and separate storage/bandwidth charges. Preserve the governance approvals
   in the restricted study record. Qualification needs only synthetic train/validation assets.
   Prepare `data/judge/qualification/registered-train-val` as a temporary transfer package with
   byte-identical `train.json`, `val.json`, `dataset_info.json`, `manifest.train.jsonl`,
   `manifest.val.jsonl`, `freeze_report.json` and only the assets named by those two split manifests.
   Preserve their freeze-relative paths. Do not copy `test.json`, `manifest.test.jsonl`, the combined
   `manifest.jsonl`, or donated assets. This package is not a replacement freeze or a study run.
2. Install the exact LLaMA-Factory commit in the separate GPU research environment. Record the
   resolved Python, Torch, CUDA, Transformers, PEFT, bitsandbytes, torchvision and trainer versions
   and installation provenance. The pinned trainer has `qwen3_5_nothink`, but the resolved
   Transformers build must actually load this pinned Qwen3.5 model. The research environment
   running `finetune.train.hardware_inventory()` must see the qualified Torch/CUDA/bitsandbytes
   installation. Installing them only into an isolated uv tool does not make them visible to the
   backend interpreter. Keep all these packages out of the deployed backend dependencies.
3. On synthetic train/validation only, inspect the **actual pinned processor**, not `main`.
   Save its configuration and hashes, effective resize/min/max-pixel settings, patch/merge sizes,
   reference-then-scene order, two image grids and expanded token counts. Run the pinned
   LLaMA-Factory preprocessing on all train/validation rows and report retained/dropped counts,
   maximum input/target lengths and any truncation. At `image_max_pixels=262144` and
   `cutoff_len=2048`, both images and the complete supervised JSON target must survive.
   Check the longest encoded pair and both image aspect ratios. Do not adjust image resolution,
   cutoff, template, dataset membership or base revision to make a failed qualification pass.
4. Run a bounded optimizer probe with the checked-in recipe, eight accumulated microbatches,
   the qualified host and a separate qualification output directory. Keep the registered freeze
   immutable. The approved retry's **qualification-only overrides** stop at two steps to get past
   zero-rate warmup, avoid validation selection and save a disposable adapter. They are never
   arguments to the registered runner:

   The first one-step probe stopped in zero-rate warmup and saved unchanged LoRA B weights.
   The owner approved a two-step qualification retry on 2026-10-01, preserving the registered
   hyperparameters and using a fresh output directory. The guarded session probe is
   `data/judge/qualification/qualification_update.py`; keep the original `qualification_step.py`
   and its failed learned-update evidence intact. The retry compares checkpoint-1 and checkpoint-2
   LoRA B tensors, rejects unchanged/zero/nonfinite tensors, and requires finite gradients/loss and
   a positive logged learning rate. Do not use this disposable adapter as a study checkpoint.

   Run the verified probe from `backend/` in the isolated qualified research interpreter:

   ```bash
   PYTHONPATH="$PWD" HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
   uv run --no-project --python "$(uv tool dir)/llamafactory/bin/python" \
     python ../data/judge/qualification/qualification_update.py
   ```
   Use a fresh output directory per attempt. Record the resolved command/config, finite loss,
   successful optimizer update, adapter hash, wall time and **in-process**
   `torch.cuda.max_memory_allocated()` / `max_memory_reserved()` after synchronization.
   The wrapper captures those counters in the training process. A separate Python process cannot
   read them. Sample `nvidia-smi` concurrently
   for total device use, but label that as a sampled maximum rather than an exact peak. If the
   recipe OOMs or fails, retain the log and stop for an owner decision under ADR-061.
5. Qualify structured inference from the pinned base and that disposable adapter on the **same**
   preselected synthetic two-image pairs. Record the vLLM version and resolved server command,
   processor configuration, non-thinking mode, temperature zero, raw output, and strict
   `VlmVerdict` validation including rationale-before-verdict field order. Confirm the adapter
   is loaded and named correctly. The two arms must differ only by adapter. The generated
   `validation-inventory` command supplies the revision, two-image count and non-thinking
   defaults. [vLLM's CLI reference](https://docs.vllm.ai/en/stable/cli/serve/) documents these
   switches; their presence does not establish runtime model/adapter support. Processor limits
   need explicit verification on this host. This is a contract check, not a quality result or
   checkpoint-selection run. Training fit does not imply vLLM serving fit on the same GPU.
   The disposable `data/judge/qualification/qualification_inference.py` probe reuses
   `providers.judge_with_metadata`, retains raw responses and strictly checks all verdict fields
   in declaration order. It preselects two synthetic training pairs before requests and refuses
   importing settings beside a `.env` file. Preparation and local safety tests do not pass this
   stage; retain the actual server command, processor settings, adapter-loading evidence and
   remote response report before approving it.
   The original `data/judge/qualification/inference-next-host.zip` and its SHA-256 receipt
   preserve the failed attempt's synthetic train/validation data, allowlisted source,
   disposable adapter and inference setup. Its dependency lock and probe are not a corrected
   next-session package. Use the corrected `inference-next-host-v2.zip` only after its local
   restore verification passes. Follow
   [the next-session commands](../../data/judge/qualification/next-session-commands.md)
   one stage at a time under a newly approved rental cap. The probe requires a fresh session
   name, checks serving image grids against prior preprocessing and preserves earlier evidence.
6. Retain this evidence beside the approved `training_qualification.json` described in
   `judge-finetune.md` §6.6. Its existing preflight checks pins, installed trainer provenance and
   hardware identity, **not** the measured step or inference results. The operator must approve
   the record only after all checks above pass. The full three-seed run still requires the
   remaining governance checks and spend alarm. Never fabricate an approved qualification
   record from package imports alone. Keep the disposable adapter out of study checkpoint
   selection. Before a later held-out run, freeze the serving command and effective processor/
   decoding settings with the signed evaluation evidence.

## Full-run readiness and cost assessment (2026-10-02)

The owner reported on 2026-10-03 that consent is now good. Keep the final consent version
and approval references in the restricted study record. This owner update does not supply
the separate live training-host qualification or authorize a full-run spending budget.

For the next session, follow the local
[training operator handoff](../../data/judge/qualification/training-session-commands.md)
one stage at a time. Its [transfer receipt](../../data/judge/qualification/training-transfer-verification.json)
records source/config hashes and archive verification. Synthetic qualification data is separate
from the opaque combined-manifest integrity files; keep the latter local until host qualification
passes. Local package verification does not supply the approved live-host record.

Local read-only checks passed for the registered training configuration and the hashed training
artifacts in `obj4-v1`: 484 training and 86 validation rows. They did not open the held-out test
payload, run a model or execute training. The approved live-host record is now retained in
`data/judge/training_qualification.json`; see the current session capture notes above for the
evidence, acceptance and confirmed spend alert. Registered training and raw-file backup
verification are now complete; see those notes for the retained evidence.

For one GPU, batch size 1, accumulation 8 and three epochs, the pinned
[Transformers 5.6.0 trainer](https://github.com/huggingface/transformers/blob/v5.6.0/src/transformers/trainer.py)
uses `ceil(484 / 8) = 61` updates per epoch: **183 updates per seed**, or 549 across three seeds.
The checked-in ten-step save schedule implies **18 regular checkpoints per seed**, or 54 total.
The actual saved inventory is authoritative; an additional final-step checkpoint would increase
this count. `capture_validation` evaluates every candidate sequentially on all 86 validation
pairs, so those regular checkpoints alone require **4,644 generated verdicts**. In-training
validation loss is a separate workload, also scheduled every ten updates. There is no configured
early-stopping callback; `load_best_model_at_end` reloads the loss-selected checkpoint.

The following are **linear budgeting scenarios, not a qualified full-run forecast**. The rate
is the ended rental's $0.447/hour including its 100 GB disk, not a current offer. Refresh the
live offer before spending; [Vast's pricing guide](https://docs.vast.ai/guides/instances/pricing)
separates compute, continuing storage charges and usage-based transfer.

| Work | Saved observation and calculation | Scenario at the historical rate |
|---|---|---|
| Training updates only, all three seeds | `vast-53678415/update2.log` reports 47.59 seconds for two updates; `549 × 47.59 / 2` | 3.63 hours, $1.62 |
| Regular checkpoint validation | The two adapter requests in `vast-53867285-inference1/inference-contract.json`, inside the verified backup archive, took 21.915 and 46.647 seconds; apply each to 4,644 sequential requests | 28.27–60.17 hours, $12.64–26.90 |

The two-request mean gives 44.22 hours/$19.77 for checkpoint validation alone. This tiny sample
includes warmup effects and a disposable two-step adapter, not a trained study model. Request
lengths, caching and later checkpoint behavior can change runtime substantially. The training
probe disabled evaluation and saved every step. Neither scenario includes installation, downloads,
in-training validation loss, preprocessing, serving startup, extra final checkpoints, embedding
controls, failures/retries, held-out comparisons or transfer. Do not present their sum as a total
study quote or retain the old $5–15 estimate as an approved budget.

The owner reported $0.96 remaining after destroying the latest instance. That is about 2.15
running hours at the historical rate before transfer, shorter than even the training-only
projection. No new rental or top-up is authorized by this assessment.

Before another paid session, obtain the remaining governance status, approve an explicit budget
covering training **and** checkpoint validation, activate an external spend alarm, and prepare the
transfer/backup procedure locally. On the actual target host, verify the pinned trainer and full
hardware inventory, qualify the registered evaluation-loss path, and obtain the operator-approved
training record before `--prepare`/`--execute`. Serving many checkpoint adapters has not been
qualified by the one-adapter probe; check capacity against the actual inventory before starting
validation. Preserve the registered save schedule and all candidates. A cheaper schedule or
scientific recipe change needs a separately recorded decision, not a silent cost workaround.

### Validation runtime benchmark (2026-10-05)

The October 2 scenarios above are historical planning evidence. Registered training has since
completed on all three seeds. Verified backups contain **19 checkpoints per seed, 57 total**,
including the final step 183. Evaluating each against all **86 validation pairs** requires
**4,902 generated verdicts**, before embedding controls and held-out comparisons. The validation
split contains only four `different_character` positives; checkpoint-selection F1 is therefore
particularly sensitive to individual verdicts. Preserve the frozen split and report this limitation.

Instance 54261178 measured seed 0 checkpoint 10, chosen before looking at validation F1.
The locally hash-verified archive retained **81 completed-call timings: 80 parsed and one failed**.
The 79 warm parsed calls averaged **21.615 seconds**, giving a provisional sequential extrapolation
of **29.43 hours**, or **$13.16 at the historical $0.447/hour**. This excludes startup, checkpoint
switching, failed-call overhead, embedding controls, held-out evaluation, transfers and backups.
One checkpoint and a partial capture do not establish a reliable upper bound for the study.

The failed response reached the 256-completion-token limit and could not be parsed. The bounded
capture produced no final prediction file or native summary, so it is timing evidence only,
not a completed validation result or checkpoint selection. The server log records SIGTERM
shutdown. Archive SHA256, call identities, package versions and owner-confirmed destruction are in
[`benchmark-backup-verification.json`](../../data/judge/qualification/vast-54261178/benchmark-backup-verification.json).
Raw logs remain in that protected directory's verified archive. No held-out data was accessed.

The server explicitly disabled compilation and CUDA graphs with `--enforce-eager`, allowed only
one active sequence, and received sequential requests. Its active-request logging intervals had
a median generation throughput of 4.6 tokens/second; these interval aggregates are not individual
request decode rates. The adapter header contains 496 language-model tensors and no trained
vision tensors, so the ignored visual-module warnings do not identify omitted visual adapter weights.
The pinned [vLLM 0.26.0 compilation documentation](https://github.com/vllm-project/vllm/blob/v0.26.0/docs/design/debug_vllm_compile.md)
confirms the execution-mode flag disables those optimizations. This motivated the bounded
comparison below; the original benchmark alone did not establish a speedup or explain all latency.

Local diagnosis and an **unqualified experimental profile** are recorded in
[`runtime-diagnosis.json`](../../data/judge/qualification/vast-54261178/runtime-diagnosis.json).
The comparison command removes only `--enforce-eager`; all model, adapter, image-processing,
prompt and decoding settings stay fixed. Concurrency is a separate later hypothesis. Do not
shorten registered reasoning, discard checkpoints or silently change the output cap to reduce
this estimate. The comparison approval does not authorize a full-validation rental or budget.

The locally verified [comparison packet and operator handoff](../../data/judge/evaluations/obj4-v1/execution-comparison/OPERATOR.md)
uses ten fixed validation pairs plus two base controls per execution mode, saving predictions,
raw responses, token usage and timings after each completed call. Its offline interruption
tests pass. Instance 54325867 completed both modes on the fixed selection. The locally verified
[comparison result](../../data/judge/qualification/vast-54325867/execution-comparison-result.json)
records all 24 calls parsing successfully, matching per-call and aggregate predictions, raw-response
schema checks, unchanged binary verdicts on all 12 matched judgments, and the bundled source hashes.
Both captures passed the frozen raw-image and prepared RGB pixel guards. The default server enabled
compilation and CUDA graphs; its command differed only by removing `--enforce-eager`.

| Execution mode | Completed / parsed calls | Warm adapter calls | Mean warm wall seconds |
|---|---|---|---|
| Eager | 12 / 12 | 9 | 22.071 |
| Default compilation and CUDA graphs | 12 / 12 | 9 | 3.636 |

The observed warm wall speedup was **6.07 times**. Six raw response texts changed, and mean warm
completion lengths were 132.22 versus 110.22 tokens. Wall time normalized by completion-token count
improved by 5.06 times; this includes image processing, prefill and request overhead and is not a
pure decoding-throughput measurement. Default startup took approximately 377 seconds from the
saved launch receipt to the route-registration log. Its saved log records completed shutdown.

Extrapolating the nine warm default calls to 4,902 judgments gives **4.95 hours**, or **$2.21 at the
historical $0.447/hour**, for calls alone. This is not a whole-study upper bound or approved budget.
The selection contains ten adapter pairs on one checkpoint and host, rather than a representative
sample across all candidates. Startup, checkpoint switching, embedding controls, held-out comparisons,
failures, transfers and backups remain outside the projection. The earlier 256-token truncation risk
also remains despite this sample passing. No validation F1, checkpoint selection or held-out evaluation
was performed. Full-validation recovery now checks all saved candidate and control files before
model calls or embedding initialization, reusing only hash-, schema-, alignment- and identity-verified
files. The local regression cases first reproduced repeat calls and late immutable-file rejection,
then passed with the fix; the evaluator suite passed 46 tests and the full backend suite passed
1,447 tests with 87 skips and six provider smoke tests deselected. Recovery is at complete file
boundaries, so an interruption within an unsaved checkpoint still repeats its calls. See the
[evaluation evidence contract](../specs/judge-finetune.md#76-batch-3-evaluation-evidence-and-access-control).
Next budget a bounded validation run using this evidence, allowing time for startup and backups.
The local [first validation batch handoff](../../data/judge/evaluations/obj4-v1/validation-first-batch/OPERATOR.md)
prepares one complete checkpoint and both controls before the remaining candidates. Its
[transport receipt](../../data/judge/evaluations/obj4-v1/validation-first-batch/preparation-receipt.json)
records source, adapter, manifest and image checks. At preparation time, the exact packaged evaluator
passed its offline regression suite and the managed-server handoff awaited a fresh-host run.
No checkpoint-selection result or new rental approval follows from preparing this packet.

Instance 54445936's first complete capture is retained in
[`first-capture-verification.json`](../../data/judge/qualification/vast-54445936/first-capture-verification.json).
The paid judge file and DINOv2 control passed SHA256, ordered-row and identity checks. The CLIP
control failed because Transformers 5.6 returns projected features inside `pooler_output`, while
the evaluator normalized the wrapper. The first-batch contract check reproduced the missing
finite scores before the one-line compatibility fix. Preserve the failed CLIP file and sidecar
as attempt evidence, repair only that control on validation, and retain the judge and DINOv2
files byte-for-byte. The owner reported the remote repair contract passing with 86 finite scores
for each control and the judge and DINOv2 hashes unchanged, recorded in
[`clip-repair-owner-report.json`](../../data/judge/qualification/vast-54445936/clip-repair-owner-report.json).
The [local backup verification](../../data/judge/qualification/vast-54445936/backup-verification.json)
then passed the archive SHA256, 28 safe members, all prediction sidecars and the first-batch
contract. Canonical validation files are retained locally with the failed CLIP attempt preserved.
The owner confirmed instance 54445936 destroyed. No selection or held-out result follows.

The [remaining-validation handoff](../../data/judge/evaluations/obj4-v1/validation-remaining/OPERATOR.md)
prepares the other candidates with compact serving adapters and the three verified first-batch files.
The [transport receipt](../../data/judge/evaluations/obj4-v1/validation-remaining/preparation-receipt.json)
records member hashes, original checkpoint provenance and verification. Capture remains sequential
and saves after each complete checkpoint. The tested restore refuses changed existing files before
writing anything. The private server has a six-hour timeout and one active GPU adapter slot, with
CPU cache capacity for the remaining adapters. At preparation time, live multi-adapter startup and
switching were unmeasured. No checkpoint selection or held-out access followed from local preparation.

Instance 54471883 completed the remaining capture and the remote completion contract. The
[local backup verification](../../data/judge/qualification/vast-54471883/backup-verification.json)
checks the archive and all saved prediction sidecars, complete ordered validation rows, frozen judge
identities, the carried first-batch hashes and transport metadata. The canonical validation folder now
retains the complete capture. An initial verification assertion incorrectly assumed label inversion for
malformed rows; it was corrected to the existing evaluator's `prediction=False` failure representation,
without changing predictions or scoring code. The failed assertion and corrected checks are recorded
in the same receipt. [Capture notes](../../data/judge/qualification/vast-54471883/capture_notes.md)
track the remaining manual screenshot and cleanup records. The owner subsequently retained instance
54471883 for held-out serving; its latest state is in the resume context above. Local checkpoint selection and control threshold fitting subsequently completed using
the existing registered evaluator. The [validation score report](../../data/judge/evaluations/obj4-v1/validation_scores.json)
owns the selected checkpoint metrics, all candidate scores and fitted control thresholds. The
[evaluation lock](../../data/judge/evaluations/obj4-v1/evaluation_lock.json) pins the selected original
checkpoint directories and their hashes. The [scoring verification](../../data/judge/evaluations/obj4-v1/validation-scoring-verification.json)
records a byte-identical rerun and independent checks against confusion counts. Its initial exact-float
comparison failed on rounding and was corrected to a numerical tolerance without changing scores.
These are validation selection results, with few positive pairs, not a held-out improvement finding.
At this validation-selection stage, held-out data had not been opened and evaluation had not run.

For a supplementary research screenshot, open the [validation table](../../data/judge/evaluations/obj4-v1/validation_summary.html)
in a local browser. It shows selected checkpoints, precision, recall, F1, malformed outputs and controls,
and expands to all checkpoint scores. The JSON and CSV remain the numeric evidence. Reproduce the
calculation locally from `backend/`, without a rental or model calls:

```powershell
uv run --frozen python ../data/judge/evaluations/obj4-v1/score_validation.py
Start-Process ../data/judge/evaluations/obj4-v1/validation_summary.html
```

Save a screenshot as `data/judge/evaluations/obj4-v1/validation-selection.png`, keeping the title and
validation-only interpretation visible. The owner reported taking an Excel screenshot, with its saved
location still unconfirmed. The owner-authored [evaluation sign-off](../../data/judge/evaluations/obj4-v1/evaluation_signoff.json)
is now verified against the exact locked bytes and all three original checkpoint directory hashes;
the [sign-off verification](../../data/judge/evaluations/obj4-v1/signoff-verification.json) retains that check.
At sign-off verification, no held-out access had been reserved or performed. The signed lock uses Windows checkpoint paths,
so executing it unchanged on a Linux host would fail the existing path checks. The owner approved
keeping the guarded evaluator local, serving Qwen remotely, and making the separate OpenRouter comparator
calls. Windows control qualification failed, so the retained Linux environment is used for controls. Control qualification and
remote readiness must pass before execution. The [held-out operator handoff](../../data/judge/evaluations/obj4-v1/heldout-1/OPERATOR.md)
records the prepared commands and spending safeguards. No API credential has been used for this preparation.

The [local CPU qualification](../../data/judge/evaluations/obj4-v1/heldout-1/cpu-control-attempt1/cpu-control-verification.json)
checked six validation control scores using verified public model weights. Scores stayed within the
declared numerical tolerance, but DINO's score for a pair exactly at its locked threshold crossed the
boundary on Windows. The original failure evidence and signed thresholds remain unchanged.
The owner reused instance **54471883** with its files retained. Its subsequent GPU availability
blocker is recorded in the resume context above. The [Linux validation-only probe](../../data/judge/evaluations/obj4-v1/heldout-1/serving/verify_linux_controls.py)
checks the existing environment and selected compact adapter files, then replays the same sampled
control comparisons. The [downloaded Linux proof](../../data/judge/qualification/vast-54471883/linux-control-check-54471883.json)
passed all six score and frozen-threshold comparisons exactly, with 14 CPU threads, and verified all six
selected compact adapter files. The controls were not cached because remaining validation reused saved
control results. Their pinned public weights were downloaded and verified before this probe.
The launcher uses those Linux controls through an owner-operated private SSH process. It sends only image
bytes, a request sequence and the control identifier, without held-out labels or pair/character IDs. Control
latency is measured locally around the SSH request, including transfer and computation. The owner terminal passed the live SSH image
replay for all six validation scores and frozen decisions. Server startup subsequently passed and
the first held-out run partially captured two seeds, as recorded in the resume context above. Windows signed-checkpoint checks
and the access ledger remain authoritative. See the operator handoff for the validation-only transport
check before resuming execution. The existing test access reservation must be preserved.

The [backup verification](../../data/judge/qualification/vast-54325867/backup-verification.json)
records the archive SHA256, 82 safe readable members and 28 verified prediction checksum sidecars.
Instance destruction is pending owner confirmation.

## Execution pipeline sequence

Run all commands from `backend/`. Angle-bracket values (`<...>`) are operator inputs, not copy-ready literals.
Before a paid run, record the official Fal price URL, lookup date, authorized USD, pinned `1024x768` size,
raw maximum `0.786432` MP, Fal's `ceil(MP)` billing rule, and the resulting per-call ceiling. Supply the
current highest applicable rate for the two configured image endpoints as `<current-usd-per-megapixel>` and
pass the source plus lookup date as `<official-price-url-and-date>`.

```powershell
# 1. Zero-cost verification on temporary fixture directory
uv run python -m finetune.build_corpus --fixture --limit 1 --out <temporary-fixture-directory>

# 1a. Roster pre-flight (one text call per story; no image call, no database, no writes).
# Runs the real `analyze` node and the real reconciliation, so it returns the verdict the paid run
# would reach. Exits non-zero on any failure. A corpus that fails here must not reach step 2 --
# a roster mismatch found at packaging instead costs that story's entire image spend.
uv run python -m finetune.build_corpus --check-rosters --corpus finetune/corpus_synthetic.json --limit 3

# 1b. Re-adjudicate an invalid_terminal quarantine whose cause was a defect that is now fixed.
# Not resumable or restartable by design; readmission is the only supported path, and it preserves
# the telemetry, the abandoned thread and the stated reason in the bundle metadata.
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --limit 1 --max-usd <cap> --max-calls-per-story 25 --price-per-megapixel <current-usd-per-megapixel> --price-basis "<official-price-url-and-date>" --readmit-quarantined <story_id> --readmit-reason "<why the prior verdict no longer applies>"

# 2. Fresh paid synthetic smoke at the campaign cap (3 stories, 19 calls/story; USD 2.00 at USD 0.035/call).
# Use a NEW --out, never the campaign directory: --max-usd is cumulative per --out, so smoke spend
# written into ../data/judge/corpus would be charged against the campaign's USD 25.
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus-smoke-final --limit 3 --max-usd 2.00 --max-calls-per-story 19 --price-per-megapixel <current-usd-per-megapixel> --price-basis "<official-price-url-and-date>"

# 2a. Current syn-001 one-time cap extension (14 abandoned calls + 25 calls for each smoke story;
# USD 3.12 total campaign authorization at USD 0.035/call). Do not use after this incident closes.
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --limit 3 --max-usd 3.12 --max-calls-per-story 25 --price-per-megapixel 0.035 --price-basis "https://fal.ai/models/fal-ai/qwen-image + https://fal.ai/models/fal-ai/qwen-image-edit-2511 (verified 2026-08-26)" --resume-quarantined syn-001 --extend-story-call-cap syn-001

# 2b. If that isolated execution later stops for resume exhaustion, retain the identical cap and basis.
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --limit 3 --max-usd 3.12 --max-calls-per-story 25 --price-per-megapixel 0.035 --price-basis "https://fal.ai/models/fal-ai/qwen-image + https://fal.ai/models/fal-ai/qwen-image-edit-2511 (verified 2026-08-26)" --resume-quarantined syn-001

# 2c. If the stop is billing-uncertain, acknowledge that exact story while retaining the same cap and basis.
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --limit 3 --max-usd 3.12 --max-calls-per-story 25 --price-per-megapixel 0.035 --price-basis "https://fal.ai/models/fal-ai/qwen-image + https://fal.ai/models/fal-ai/qwen-image-edit-2511 (verified 2026-08-26)" --resume-quarantined syn-001 --acknowledge-uncertain-billing syn-001

# 3. Full synthetic generation (24 train + 6 val stories).
# --max-calls-per-story is MANDATORY here, not optional. Without it the per-story reserve is the
# full IMAGE_BUDGET: 55 x USD 0.035 = USD 1.925, and a story starts only if its whole reserve fits
# what is left. Thirty such reserves are 30 x 1.925 = USD 57.75 and steps 3 and 4 together are
# 45 x 1.925 = USD 86.63, against a USD 30 hard ceiling that --max-usd is silently clamped to. An
# uncapped run therefore cannot complete at any authorization: it halts once charged calls pass
# (30 - 1.925) / 0.035 = 802, having already paid for everything before that.
#
# Steps 3 and 4 share one --out, so they are ONE campaign against one ceiling: 30 synthetic + 15
# donated = 45 stories. The cap is 19 calls/story, measured rather than derived: the smokes at
# a723126 drew syn-002 = 14, syn-003 = 15 (budget-stopped) and syn-001 = 18-26 over five runs, so 15
# would halt the campaign on its first story. The reserve check is per story against what is left,
# so the binding case is every story maxing out: 45 x 19 x 0.035 = USD 29.93, inside the USD 30
# ceiling. 20 does not fit (USD 31.50).
#
# --max-usd is cumulative across every invocation into this --out, not a fresh budget per command.
# Start at the USD 25 working allocation; if late stories do not start because the reserve no
# longer fits, re-run the same command with --max-usd raised toward 30 -- completed stories skip.
uv run python -m finetune.build_corpus --corpus finetune/corpus_synthetic.json --out ../data/judge/corpus --max-usd 25 --max-calls-per-story 19 --price-per-megapixel <same-current-usd-per-megapixel> --price-basis "<same-official-price-url-and-date>"

# 4. Full donated generation (15 candidate stories: 10 primary + 5 backup). Same campaign
# directory, same ceiling, same cap -- the arithmetic above already counts these 15 stories.
uv run python -m finetune.build_corpus --corpus ../data/judge/intake/donated.json --out ../data/judge/corpus --max-usd 25 --max-calls-per-story 19 --price-per-megapixel <same-current-usd-per-megapixel> --price-basis "<same-official-price-url-and-date>"

# 5. Read-only candidate inspection for hard negative selection
uv run python -m finetune.build_dataset --candidate-report --data ../data/judge/corpus

# 6. Upload immutable assets and seed research pair queue
uv run python -m finetune.materialize_pairs --data ../data/judge/corpus --donated-intake ../data/judge/intake/donated.json --selection ../data/judge/intake/dataset_selection.json

# 6a. Annotation dress rehearsal only. `--pilot` seeds the queue from every completed bundle in
# --data with `is_pilot = true`, so the pairs are permanently excluded from the training dataset
# and never reach a freeze. It bypasses dataset selection because selection decides what enters
# training and pilot pairs never do; it therefore refuses --donated-intake and --selection.
# Point --data at a throwaway campaign directory, never at the production corpus: a pair id
# already seeded as production data will hard-fail with `pair conflict` rather than be reflagged.
uv run python -m finetune.materialize_pairs --data ../data/judge/corpus-smoke-a --pilot

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

**Before running step 3, read the smoke's per-story `attempted_calls`.** Nineteen calls per story is
measured on the a723126 smokes (above), but it is a thin measurement: three stories, one of which ranged
18-26. At the production `--scene-attempts 3` a story's structural worst case is the full 55, so a cap of 19
stops an overrunning story at the seam and quarantines it for reconciliation rather than breaching the
campaign ceiling — the intended trade in `research-corpus-operations.md` §6, but one that costs a story rather
than money. A single story that stops at the cap can be resumed with `--resume-quarantined <story_id>
--extend-story-call-cap <story_id>`, spending from the USD 25-30 band. If the smoke shows completed stories
routinely needing more than 19 draws, the corpus must shed stories or `--scene-attempts` must drop; lowering it is not a free tuning knob,
because bundles drawn under different caps are different sampling distributions and may not be mixed without
recording it, so it would have to be applied uniformly and the already-drawn smoke bundles redrawn or excluded.
Do not raise `--max-calls-per-story` instead: 45 stories at 20 calls is 45 x 20 x 0.035 = USD 31.50, past the
hard ceiling.

Steps 3 and 4 exit non-zero when the campaign halts or when any story quarantines, and name on stderr how many
stories ran of how many were requested, which stories quarantined, and the `--max-usd` that would have cleared
the reserve. A roster mismatch quarantines that one story and the run continues, so the expected shape of a
completed step 3 is 30 bundles, or fewer bundles plus a named quarantine list — never a silent partial run.

On a later paid rerun, pre-existing story-local quarantines are counted and skipped unless the matching
`--resume-quarantined`, `--restart-quarantined` or `--readmit-quarantined` option targets them; the CLI still
exits 2 while any remain. A flag for another story does not unlock one, and a targeted recovery still performs
all of its existing validation. `billing_uncertain` remains a hard stop until its matching acknowledgment, and
fixture mode remains a hard stop for every pre-existing quarantine.

`evaluation_signoff.json` is written by the approver, never by evaluation code. It contains exactly the
SHA-256 of `evaluation_lock.json`, a nonblank `approved_by`, and a timezone-bearing `approved_at`.
Prediction JSONL files and their `.sha256` sidecars are immutable run evidence. Reusing the same `--run-id`
after interruption verifies and reuses each completed judge file, records a `resumed` event, and calls only
the missing judges; a missing sidecar, changed file, or checkpoint path/digest drift stops before further
held-out inference. The access ledger contains only run identifiers, hashes, lifecycle status and failure type,
never story text or direct asset paths. A second `heldout` invocation is legal only after a completed Rung-D
report and additionally requires `--deviation <PATH>` with the preregistered report hash, defect, fix commit,
train/validation-only evidence,
and approval timestamp. There is no third-read command and no automatic deployment.

The held-out command validates and writes the canonical `Objective4Report` schema documented in
`docs/specs/judge-finetune.md` §7.7. Preserve `objective4_results.json` with its prediction JSONL files and
sidecars. Re-running the same guarded evidence produces byte-identical sorted JSON. Read
`objective4.requirement_met` as the research conclusion and `deployment_decision.ship_candidate` as the
separate product decision; Rung C is a met research requirement that keeps the incumbent, while only Rung D
marks Objective 4 unmet.
The command verifies `character_slices.json` and `annotation_agreement.jsonl` against
`freeze_report.json`, requires complete held-out coverage, and publishes the report exclusively: an
identical existing report is the only idempotent success, while different bytes stop the run.
Those two artifact hashes are copied into the signed evaluation lock, which is their immutable trust anchor;
agreement pair IDs must also match held-out order exactly. Prediction schema version 2 marks each judge's
first observation as cold-start, excludes it from headline warm latency, and reports it separately.

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

### Fine-tuning evidence for the capstone

This is a capture checklist, not a record of completed training or improvement. Use the existing run and
evaluation directories in steps 10-15 above. Preserve machine-readable evidence first; screenshots and
presentation plots supplement it. No new tracking service is required. The endpoints, checkpoint-selection
rule and held-out access policy remain those in
[the fine-tune spec](../specs/judge-finetune.md#7-evaluation) and
[the preregistration](../product/PREREGISTRATION_OBJ4.md).

#### Agent reminders and capture status

Agents assisting with Objective-4 rental, qualification, training, validation, held-out evaluation or
capstone reporting must use this checklist. At each milestone below:

1. Save the artifacts the agent can obtain directly. Tell the owner which records are saved and which
   require a manual screenshot, written note or independent approval. Remind them while the relevant
   display is available, before starting a long run or closing/deleting the source.
2. Give one concrete capture instruction: what to show, what to hide, a destination filename beside the
   run evidence, and a caption containing the run/seed/step, timestamp and source artifact. For example:
   "Capture the seed-0 completion summary with its final step visible; crop tokens and private content."
3. Keep `capture_notes.md` beside the run evidence once a qualification or study run directory exists.
   For each requested item, record its milestone, source, destination and status: `pending`, `captured`
   or `unavailable`. Mark `captured` only after verifying the saved artifact or receiving the owner's
   confirmation of its location. Record the reason for `unavailable` and retain the underlying logs when
   possible. Until a run directory exists, give the owner the same capture instructions in the conversation.
4. A missing illustrative screenshot alone does not block a run with complete required machine-readable
   evidence. Report the gap; avoid leaving a paid GPU idle waiting for a screenshot. Scientific evidence,
   independent sign-off and spending gates remain required under the existing protocol.
5. Before destroying the instance, verify the downloaded run/evaluation files against retained hashes.
   At handoff or completion, list saved evidence, unavailable items and pending owner actions, including
   their destinations. Describe only stages actually executed and results actually measured.

| Milestone | Owner reminder or manual record |
|---|---|
| Before rental | Save the final offer/cost breakdown, selected template/disk and spend-alarm settings. Record governance approval references only in the restricted study record. |
| Qualification complete | Capture sanitized GPU/version verification, the real-step completion and peak-memory result; retain the raw qualification evidence. |
| Each training seed | Capture progress with seed/step visible and its completion summary. Record any interrupted or failed run as well. |
| Validation locked | Capture the validation checkpoint-selection table and loss/F1 plots generated from saved evidence. Independent evaluation sign-off remains the approver's action. |
| Final evaluation complete | Capture the final comparison table/figures, including uncertainty and all registered comparators. Keep held-out examples closed during development. |
| Before instance deletion | Confirm the local backup is verified and capture the final sanitized spending breakdown. Keep restricted donor evidence separate from presentation material. |

- [ ] **Before rental:** record the approved qualification budget/deadline, active spend alarm, offer and
      host IDs, selected template/image, disk allocation and compute/storage/transfer rates. Preserve the
      run's source snapshot as well as its Git commit; a commit alone cannot reproduce uncommitted changes.
      Exclude credentials, secret files and donated data from a code snapshot or screenshot.
- [ ] **Qualification:** retain the processor/preprocessing checks, actual optimizer-step log, measured
      peak GPU memory, adapter digest and synthetic base/adapter inference evidence required above.
      Record resolved environment versions and image identity in the approved qualification evidence.
- [ ] **Each full training seed:** retain `run_plan.json`, `hardware.json`, `stdout.log`, the output
      checkpoints/adapters, trainer state/log history and any generated loss plots. Capture progress and
      completion screenshots with the seed and step visible. Record start/end times, interruptions and
      failures; do not keep only the best-looking run.
- [ ] **Validation:** retain `validation_candidates.json`, every candidate's prediction evidence and hash
      sidecar, validation scores, selected checkpoint/step per seed and `evaluation_lock.json`. Select on
      `different_character` F1 as specified, never on a screenshot or held-out score. Validation loss can
      be monitored during training; checkpoint F1 is computed by the separate validation evaluation.
- [ ] **Final held-out evaluation:** after independent sign-off, retain `evaluation_signoff.json`,
      `test_access.jsonl`, all prediction JSONL files and their SHA-256 sidecars, and
      `objective4_results.json`. Perform the registered comparison in the single guarded evaluation,
      rather than inspecting test examples or running a test preview during development.
- [ ] **Capstone tables/figures:** derive plots from saved evidence: training/validation loss by step,
      validation F1 by checkpoint, and the final judge-comparison table with precision, recall, F1 and
      character-clustered confidence intervals. Show the base, all three fine-tune seeds, prompted Gemma
      and the registered embedding controls; retain the three-seed mean/sample standard deviation and
      human/non-human slice results. Report missing measurements as unavailable. Loss decreasing alone
      does not establish better held-out judgment. Preserve unchanged, worse and inconclusive results
      alongside any improvement, and distinguish the research result from the deployment decision.
- [ ] **Screenshots and backup:** capture sanitized GPU/environment verification, training progress,
      loss plots, checkpoint-selection results and final tables. Use synthetic examples for illustrative
      before/after verdicts; label them illustrations rather than statistical evidence. Screenshots must
      not expose tokens, signed URLs, donor identifiers or unapproved donor content. Save captions with
      run/seed/step, timestamp and source artifact. Download and verify the complete run/evaluation
      evidence before destroying the rented instance; keep donated evidence in the approved restricted
      location, separate from the presentation material.
- [ ] **Methods and limitations:** preserve the disclosed postregistration base-model amendment,
      AI-assisted labeling limitation, achieved character counts, approval references and any protocol
      deviations. A higher point-estimate F1 with an interval spanning zero is inconclusive evidence of
      improvement, not a confirmed win under the registered base-comparison gate.

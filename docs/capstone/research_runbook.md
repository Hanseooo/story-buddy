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

## Qwen35 host qualification

**Pending, not a passed host qualification.** Installation/runtime and registered preprocessing
checks have passed on the rented host. The original one-step GPU execution logged zero learning
rate and saved zero LoRA B tensors; retain it as training-path evidence only. The later guarded
two-step retry produced a nonzero weight update, verified directly against the saved initial
adapter. Its logs, trainer states, measured peak memory and complete final adapter are locally
verified and backed up. Base/adapter inference remains unqualified.
See the session evidence above for raw results and
capture status. No model-improvement evaluation or registered three-seed run has started.
The owner confirmed this qualification instance destroyed on 2026-10-02 Manila time after
local backups were verified. See the session capture notes for final billing and restore artifacts;
a future host needs fresh runtime checks and the remaining inference qualification.
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
Keep paid work paused until the corrected bundle is restore-verified and a bounded session
is authorized. The next remote probe must check the prepared pixels and grids of the same
bytes sent to both models, then retain actual base/adapter contract responses.
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

# Feature Spec — Consistency Judge Fine-Tune

**Status:** draft · **Phase:** 2.5 · **Owner node:** `backend/pipeline/consistency_check.py` (consumer) + `backend/finetune/` (producer)
**Derived from:** MASTER_SPEC §2, §6 · **Rationale:** ADR-018 (decision), ADR-019 (serving), ADR-004 (judge role), ADR-008 (evaluation)

> Read ADR-018 first. This spec is the *how*; the ADR is the *why* and it is where the binding
> decisions live. Read ADR-016 alongside it — it is superseded, but its reasoning is what makes the
> judge the right target instead of the image model.

---

## 0. The order of operations

**You build the whole product first, with a prompted judge, and you fine-tune nothing until real stories
exist.** The fine-tune is not a prerequisite for anything. It is an upgrade to one replaceable part.

| # | What | When | Judge in use |
|---|---|---|---|
| 1 | Phase 0.5 spike passes | before anything | none |
| 2 | Phase 1 pipeline built, consistency loop working | ~2–3 weeks | **prompted `gemma-3-27b-it`** |
| 3 | Phase 2 safety + classroom | ~3–4 weeks | prompted |
| 4 | Ethics Stage 1 clears → children donate stories | in parallel, starts **now** | — |
| 5 | Run Phase 1 over the donated stories → **images** | 1 day of compute, ~$30 | prompted |
| 6 | Two researchers label those images → **the dataset** | one weekend | — |
| 7 | Train the LoRA on a rented GPU | 2–3 hours, ~$5–15 | — |
| 8 | Evaluate against four baselines | 1–2 days | — |
| 9 | **Objective 4** result: precision/recall/F1 vs. human labels on held-out set (F1 primary). **Deployment gate** (separate, engineering): did the fine-tune beat the base model + does it match prompted Gemma. §7.5's ladder | | |
| 10a | Rung A or B → serve it behind vLLM, flip two env vars | ~2 days | **fine-tuned** |
| 10b | Rung C → Objective 4's F1 result stands regardless; the product keeps the prompted judge | 0 days | prompted |
| 10c | Rung D → the LoRA did nothing. Debug; do not report | | prompted |

**The product is finished before step 7.** Phases 1 and 2 ship on the *prompted* judge. The fine-tune swaps
one replaceable part, and rollback is two environment variables (§8) — which is why it sits at rung 4 of the
ROADMAP's de-scope ladder rather than at the bottom.

**Step 5 cannot start before step 4, and step 6 cannot start before step 5.** Ethics is the long pole; the
fine-tune is four hops downstream of a consent form. Everything after step 5 is a weekend.

The dependency that actually matters: **step 6 cannot start before step 5, step 5 cannot start before
step 4.** Ethics is the long pole. Everything else is a weekend.

---

## 1. Purpose

Fine-tune an open VLM to decide whether two images show **the same character instance**, and to say
*why* before it says *whether*. It replaces the prompted `gemma-3-27b-it` judge that drives targeted
regeneration (ADR-010), and its classification performance against human-established reference labels is
the study's **Objective 4**: precision, recall, and F1 (F1 primary) on the character-disjoint held-out set.
That absolute agreement is the reported result; an **optional secondary comparison** against the zero-shot
base model and the existing prompted incumbent is permitted on the same pairs (ADR-008, revised 2026-07-25) —
see §7.

*(The manuscript states labels as integers — 1 = Different Character, 0 = Same Character; the schema below
encodes the same distinction as the boolean `same_character` field. Same meaning, different serialization.)*

The judge is a **control signal, never an outcome measure.** Read ADR-004's non-circularity note before
writing a single line of the results section.

---

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

The fine-tuned model does not change the contract. It fills the same `vlm_verdict` it always did:

- **Reads:** `characters[].canonical_ref_image`, `scenes[].attempts[].image_ref`
- **Writes:** `scenes[].attempts[].vlm_verdict`, `.failure_reasons`, `.passed`
- **Invariants:**
  - `differences_observed` is declared **before** `same_character`. Field order is load-bearing
    (ADR-004 amendment) — the model must reason before it scores, and structured output emits fields
    in declaration order.
  - `failure_reasons` is drawn from the **closed taxonomy** in §4. Not free text.
  - Multi-character scenes verify **each character separately** against its own reference.

---

## 3. The four dangers

These are the things that quietly ruin a fine-tune, ordered by how likely they are to get you.

### 3.1 Shortcut learning — the one that will actually happen

Hard negatives are free and clean: character **A**'s reference against a scene generated from character
**B**'s reference. Definitely different, zero labour.

Positives are **not** free. `same reference ⇒ same character` looks like a free label and is a **noisy
one, noisy in the exact direction that matters** — because generation *sometimes drifts*, which is the
entire reason the judge exists. Train on auto-labelled positives and the model learns to detect
***"was a reference image used?"*** rather than ***"is this the same character?"***. It will score
brilliantly on your validation set and be useless in the loop.

**Positives must be human-confirmed. There is no way around this.** It is one weekend (§5.4).

Hard negatives must use a tiered matching strategy. Mandatory: species and style. Then maximize similarity over: dominant colour, body configuration, silhouette, clothing/accessories, and facial structure, and select the most similar valid other-character candidate. This keeps negatives genuinely difficult without pre-deciding their specific taxonomy failures.

Style is controlled at story/character-lineage level. Each lineage belongs to exactly one of the three
selectable ADR-042 presets (`cel`, `gouache`, `cut_paper`), and its reference and scenes use that same preset.
The model must therefore compare identity within a style rather than learn that style disagreement implies a
different character. Constructed negatives with different `style_preset_id` values are invalid.

### 3.2 Character leakage across splits

**Split by character, never by pair.** If Bok-Bok the chicken appears in both train and test, κ inflates
and nothing in the metrics tells you. Every image derived from a given canonical reference belongs to
exactly one split. `backend/finetune/manifest.py` enforces this and CI tests it (§10).

### 3.3 Class imbalance

If most generated scenes pass, a model that always answers "same" scores well on accuracy and is worthless.

**Report F1 on the `different_character` class.** It is the minority class, it is the class the control
loop acts on, and a missed failure ships a broken page to a child.

**Balance the training set. Never balance validation or held-out test** — they must reflect the deployment
distribution. Concretely: constructed negatives go into **train only** (§5.4 step 4). Val and test contain
pipeline pairs exclusively.

### 3.4 Structured intermediate rationale supervision

`differences_observed` is retained as a deterministic intermediate supervision signal generated exclusively from the adjudicated failure taxonomy. It precedes the binary verdict in the serialized target so that discrepancy identification is learned before classification. The study does not interpret this field as a faithful representation of internal model reasoning. (A suggested ablation: compare `rationale -> verdict -> taxonomy` against `verdict -> taxonomy`). But if you
generate those rationales with Gemma-27B and train on them, **you have distilled the incumbent's errors
and cannot beat it.** That is arithmetic, not pessimism.

**The fix, and it pays for itself:** annotators pick from a fixed checkbox taxonomy rather than writing
prose. Fast to annotate, human-supervised, and **ADR-010's targeted regeneration already needs exactly
this taxonomy** to correct a prompt. Design it once in Phase 1; annotate it once in Phase 2.5; use it twice.

---

## 4. The failure-reason taxonomy

A closed set. Shared by the judge's training targets and the regeneration controller's prompt corrector.

| Reason | Example | Regeneration correction |
|---|---|---|
| `wrong_colour` | Cream chest patch is now brown | Restate the colour attribute, emphasised |
| `wrong_species` | Fox cub rendered as a dog | Restate species + defining silhouette |
| `wrong_body_feature` | Two eyes instead of three; wings missing | Restate the countable feature |
| `wrong_clothing` | Striped scarf absent or recoloured | Restate the accessory |
| `wrong_style` | Scene does not match its reference's declared preset | Re-inject that story's frozen style fragment (ADR-007/042) |
| `different_face` | Same species, unrelated individual | Strengthen reference conditioning |
| `character_absent` | Character not in the frame at all | Restate presence requirement |

Extend this set **before** annotation begins, never during. A taxonomy that changes mid-annotation
invalidates every label collected under the old one.

---

## 5. Data

**Base model:** `Qwen2.5-VL-7B-Instruct` (Apache-2.0, native multi-image).

### 5.1 There is no dataset to download. You manufacture one.

This was checked, not assumed. Nothing off-the-shelf fits:

| Candidate | Right task? | Right domain? | Verdict |
|---|---|---|---|
| **DreamBench++** | Yes — pairwise identity, 7 human raters | No — 150 **photographic** subjects | **Held-out transfer test** (§5.6) |
| PororoSV / FlintstonesSV | No — frames + captions, no identity ratings | Cartoon, but **9 and 7** characters total | Unusable |
| StorySalon | No — no identity ratings | ~160K animation frames scraped from YouTube + e-books | Unusable |

PororoSV and FlintstonesSV fail §3.2 before licensing is even reached: with nine characters you cannot
split by character, so the model learns *"recognise Pororo,"* not *"compare two images."* StorySalon's
frames come from commercial cartoons — fine to benchmark against, not something to bake into weights that
ship to schoolchildren.

> **State this in the paper.** *No existing benchmark provides human pairwise identity judgments over
> stylized, invented, non-human characters.* That absence is the contribution's negative space, and it is
> the answer to *"why didn't you just use an existing dataset?"* at defense.

### 5.2 What the dataset physically is

One JSONL manifest and a folder of PNGs. One line = one training example:

```json
{"char_id": "quill_007",
 "split": "train",
 "provenance": "synthetic",
 "pair_type": "pipeline",
 "images": ["ref/quill_007.png", "scene/quill_007_s03_a1.png"],
 "differences_observed": "Two eyes rather than three; the scarf is unstriped.",
 "same_character": false,
 "failure_reasons": ["wrong_body_feature", "wrong_clothing"]}
```

> **⚠️ Amended 2026-08-14 — the record above predates three contract fields, and two of them gate.**
> `VlmVerdict` now declares, in order: `differences_observed, same_character, attributes_present,
> style_match, anatomy_intact, subjects_unique, text_free`. §6.1 requires the training target to be
> byte-identical to the production serialization, so the gap is not cosmetic.
> - **`anatomy_intact` and `text_free` are human-annotated** — both gate `passed` in
>   `consistency_check.py` (ADR-028; `lettering-suppression` §2). A judge trained to emit `True`
>   unconditionally for either would break the control loop while scoring well.
> - **`subjects_unique`, `style_match` and `attributes_present` take schema defaults** — non-gating.
>   Promote one to annotated only by amending this spec *before* annotation begins (§4's rule).
>
> This adds two checkboxes to `annotation-surface.md`'s instrument and two columns to the `annotations`
> table. §4's "extend before annotation begins, never during" makes this the last moment it is free.
> Pre-registered in `docs/product/PREREGISTRATION_OBJ4.md` §4.
> **The two COLUMNS shipped 2026-08-14** (`supabase/migrations/0014_annotations.sql`, `not null default
> true`, matching the `VlmVerdict` / `ManifestRecord` defaults). **The two CHECKBOXES have not** — the
> `annotate/` route is blocked on D-K/D-L (`DECISION_BACKLOG.md` Tier 2e). No label has been collected, so
> the "before annotation begins" condition still holds.

- `char_id` — the only field §3.2 splits on. Never enters the training text.
- `provenance` — `synthetic` or `donated`. Guarded: no `test` record may be `synthetic` (§5.4). Never
  enters the training text.
- `pair_type` — `pipeline` (human-labelled) or `constructed` (negative built by pairing across characters).
- `images` — reference first, scene second. Always exactly two. Order is load-bearing.
- The last three fields are what the model learns to emit, **in that order** (§2).

`differences_observed` for a positive is not empty prose — it is the annotator's confirmation, e.g.
`"Three eyes, striped scarf, feathered wings all present."` A blank rationale on positives teaches the
model that rationales only exist for failures.

**Where the rationale prose comes from (fixed 2026-07-13 — no human writes it, no model writes it).**
Annotators only tick checkboxes (§3.4); the `differences_observed` string is rendered
**deterministically by a fixed template** from the ticked taxonomy entries plus the Character
Bible's attribute list — one sentence pattern per taxonomy entry (e.g. `wrong_body_feature` +
bible attribute "three amber eyes" → *"The character does not show the expected three amber
eyes."*), concatenated for multi-reason items; positives render the attribute checklist as an
"all present" sentence. Human-supervised (the checkbox is the supervision), zero prose labour —
which is what keeps step 3's 8-seconds-a-pair estimate honest — and byte-stable, which §6.1's
training-target/production-schema round-trip already requires. If a model wrote this prose instead,
§3.4's distillation ceiling would come back through the side door.

### 5.3 Folder layout

```
backend/finetune/
  corpus_synthetic.json  # 30 strict JSON records: 24 train + 6 val, 10 stories/style; checked in
  build_corpus.py        # corpus_synthetic.json -> paid fal draws -> data/judge/corpus/. Spend-capped.
  manifest.py            # Pydantic record above + the guards (CI-tested) + `local_image_path`
  build_dataset.py       # pipeline output + the `annotations` table -> manifest.jsonl
  to_llamafactory.py     # manifest.jsonl -> sharegpt JSON + dataset_info.json
  train.py               # zero-cost preflight + three pinned LLaMA-Factory invocations
  train_qlora.yaml       # the training config (§6.3)
  evaluation_metrics.py  # pure stdlib metrics and statistics (§7)
  evaluate.py            # prediction evidence, access ledger and four baselines (§7)
data/judge/              # gitignored
  intake/                # controlled donated input + dataset selection
  corpus/                # mutable run bundles, assets, quarantine and build state
  freezes/<freeze-id>/   # immutable manifest, split JSON, verified assets and freeze report
```

The input is a JSON list, not a Python list edited into `build_corpus.py`. Every record declares `story_id`,
`text`, `declared_characters`, `declared_non_human`, `provenance`, `split`, `candidate_role` and
`style_preset_id`. Donated records use the same contract from a controlled gitignored file and add the
approval/withdrawal fields required by `research-corpus-operations.md` §4.1. Before paid generation, the
loader rejects unknown fields, invalid split/provenance combinations, non-selectable styles, duplicate IDs,
or a non-human roster that is not a subset of the declared roster. After generation, declared and extracted
rosters must reconcile before any pair is materialized.

> **⚠️ Superseded (2026-07-28, ADR-026): `labels/` no longer exists.** This spec originally kept raw
> annotator CSVs on disk, one per researcher. Labels now live in the **`annotations` table**, written by the
> `(research)/annotate/` surface — see `docs/specs/annotation-surface.md`. The CSV mechanism was rejected
> because a private-bucket asset cannot be rendered from a local file without a session to mint a signed URL,
> and because silent row misalignment across ~1500 rows is undetectable after the fact and would invalidate
> Objective 4. `build_dataset.py` reads the table. **Polarity note:** the table's `same_character` boolean is
> `true` for *same*, so the manuscript's positive class is `label = not same_character` — converted once, in
> `build_dataset.py`, and nowhere else.

**One naming rule, in one place — `manifest.local_image_path`.** The immutable freeze copies verified bytes
under `assets/{kind}/{storage_path with / → _}`; the manifest's `images` must carry **that** freeze-relative
name, not the Storage path, because LLaMA-Factory resolves `images` against the dataset directory and
**reports nothing useful when a path is wrong — it trains on what it managed to load.** Both sides import
the rule; neither re-implements it. (Built 2026-08-14 by two agents that disagreed on exactly this and
produced a manifest pointing at files that did not exist. The shared function and its test are what closed it.)

The manifest is the source of truth. The LLaMA-Factory JSON is a **build artifact** — regenerate it, never
edit it. That is why `char_id` and `split` live in the manifest and not in the training file: they are
bookkeeping, and if they leaked into the prompt the model could read the answer off them.

### 5.4 How the examples get made

The live corpus allocation, encoding, spend limits, source order, and stop conditions are owned by
[`research-corpus-operations.md`](research-corpus-operations.md). Synthetic stories supply train and
validation, consented donated stories supply held-out test only, and character lineage never crosses a
split. Do not derive operational counts or costs from examples in this judge-training spec.

Constructed negatives use the outcome-blind manual selection protocol in `research-corpus-operations.md`
§4.6. Before annotation, a researcher selects the visually closest valid same-species, same-style target
character for each synthetic training reference using §3.1's five visual dimensions. Dataset construction
then pairs that reference with every natural training scene belonging to the selected target. The controlled
selection file and its hash are frozen with the dataset; an unmapped or ineligible training character is a
hard failure, not an automatic fallback to an easier negative.

> **Reuse the labelling instrument for step 3.** The same interface that shows a human a reference and a scene
> and asks "same character?" produces both the human reference labels and the training labels. One instrument,
> two uses. **That interface is now specified**: `docs/specs/annotation-surface.md` (ADR-026) — the
> `(research)/annotate/` route, with `adjudicate/` covering the third researcher in step 3.

### 5.5 Splits — by character, always

The endpoints in §7 are claims about *differences between judges*, so **the test set must be big enough to
resolve those differences.** That requirement, not the training set, sets the split (ADR-018 amendment a).

| Split | Characters | Provenance | Pairs | Contents |
|---|---|---|---|---|
| Train | ~40–45 | **synthetic** | ~378 pipeline + ~300-400 constructed = **~678-778** | balanced; drift induced deliberately |
| Validation | ~8–10 | **synthetic** | ~72 | pipeline only, natural distribution. **All iteration happens here** |
| Held-out test | **~15–20, maximizing qualifying real characters** | **donated — enforced** | ~192 (additional unique held-out scenes) | pipeline only, natural distribution, 2 annotators + adjudication, IRR reported |
| Transfer test | — | DreamBench++ | as published | **DreamBench++**, never trained on |

The provenance column is not documentation — `manifest.py`'s guard raises on a `test` record marked
`synthetic`, and CI tests it. A synthetic story leaking into the held-out split would void Objective 4
silently, which is the same failure class as §3.2's character leakage and gets the same treatment.

⚠️ **The held-out character count is bounded by what the donation actually yields.** The goal is to maximize naturally qualifying real characters, targeting ~15–20. At ≤2 canonical references per story (ADR-004), 15 donated stories yield roughly 15–20 characters. Objective 4's power is reported against the **achieved** count, and that count
is not knowable before collection closes.

Three consequences worth internalizing:

- **The held-out test set is looked at exactly once.** Consult it while developing and it is no longer held
  out, and the primary endpoint is void. Tune on validation.
- **The primary endpoint (§7.1) is cheap to power** — base-vs-tuned gaps on in-domain data are large. The
  *secondary* Gemma comparison and the non-human slice are not, and that is where the contribution lives.
  The dataset's statistical power is derived from the **character** count rather than the per-character pair count, making character diversity the primary unit of useful variation. Growing the test set with additional unique characters (if more are naturally generated in the donations) is legitimate, and so is stratifying it; moving a character after seeing results is not.
- **Induce drift deliberately** — weaker reference conditioning, higher temperature — to harvest natural
  negatives. **Training split only.** The test set must keep the deployment distribution (§3.3).

**More distinct characters is the cheapest statistical power available** — and since 2026-08-14 the train and
validation halves of that power are a *writing* task rather than a recruitment one: adding characters to
`corpus_synthetic.json` costs authoring time plus the spend governed by the corpus-operations run. **The held-out split's character count
is still unfixable by Phase 2.5** and still tracks the donation (RESEARCH_PROTOCOL §8), which is why the test
split's achieved character count gets reported honestly.

### 5.6 Why DreamBench++ is a *test* set and not a *training* set

DreamBench++ is 150 **photographic** concepts with ~1,350 prompts, rated by seven annotators
([paper](https://arxiv.org/abs/2406.16855), [repo](https://github.com/yuangpeng/dreambench_plus), code
Apache-2.0). Its "style" category is style *transfer*, not children's-book illustration.

Our domain is stylized illustrations of invented, frequently non-human characters — **precisely the regime
where ADR-001 records that nobody has measured anything.** Training a judge on photographs of real corgis
and deploying it on a cartoon dragon aims a domain shift straight at the weakness being fixed.

**Decision: evaluate on it, never train on it, never redistribute it.** Evaluation is the benchmark's stated
and intended use, so this requires no permission and no correspondence with the authors. It also buys the
stronger claim — *"trained only on stylized children's-book illustrations, our judge matches human ratings on
DreamBench++'s photographic split without ever training on it."*

---

## 6. Training — the runbook

Nothing here needs a machine-learning background. It is a config file and a rented GPU.

### 6.1 Convert the manifest

`to_llamafactory.py` emits [the sharegpt multi-image format](https://github.com/hiyouga/LLaMA-Factory/blob/main/data/README.md).
**The number of `<image>` tokens must equal the length of `images`** — that is the one rule the loader enforces
and the one thing that will silently corrupt a run:

```json
[{"conversations": [
    {"from": "human",  "value": "<image><image>Identify the differences that correspond to the allowed failure taxonomy. Then output the required JSON object."},
    {"from": "gpt",    "value": "{\"differences_observed\": \"...\", \"same_character\": false, \"failure_reasons\": [\"wrong_clothing\"]}"}],
  "images": ["assets/ref/quill_007.png", "assets/scene/quill_007_s03_a1.png"]}]
```

The `gpt` turn is the verdict **serialized exactly as the Pydantic schema serializes it**. Import the schema;
do not hand-write the JSON string. The training target and the production parse must be byte-identical or
you have trained the model to emit something `providers.judge()` cannot read.

Register it in `dataset_info.json`:

```json
{"storybuddy_judge_train": {"file_name": "train.json", "formatting": "sharegpt",
                            "columns": {"messages": "conversations", "images": "images"}}}
```

### 6.2 Rent the GPU

Two images at 512px on a 7B model needs ~16–20 GB. A 24 GB **RTX 4090** on RunPod or Vast.ai is
~$0.35–0.45/hour. Three epochs over ~1,000 examples is **1–2 hours**. Budget **$5–15** including the
fumbling. **Set a spend alarm before you start** — an idle pod bills all night.

*Rent, don't buy.* ADR-016 did this arithmetic. The available 8–16 GB card cannot hold it comfortably.

### 6.3 The config

```yaml
### model
model_name_or_path: Qwen/Qwen2.5-VL-7B-Instruct
model_revision: cc594898137f460bfe9f0759e9844b3ce807cfb5   # CC-7. Never "main".
image_max_pixels: 262144                      # 512 x 512
trust_remote_code: true

### method
stage: sft
do_train: true
finetuning_type: lora
lora_rank: 16
lora_alpha: 32
lora_target: all
quantization_bit: 4                           # the Q in QLoRA
quantization_method: bnb

### dataset
dataset: storybuddy_judge_train
eval_dataset: storybuddy_judge_val            # character-disjoint. §3.2
template: qwen2_vl
cutoff_len: 2048

### output
output_dir: saves/judge-lora-seed0
report_to: none
run_name: judge-qlora-seed0
plot_loss: true

### train
per_device_train_batch_size: 1
gradient_accumulation_steps: 8
learning_rate: 1.0e-4
num_train_epochs: 3.0
lr_scheduler_type: cosine
warmup_ratio: 0.1
bf16: true
gradient_checkpointing: true
seed: 0

### eval
eval_strategy: steps
eval_steps: 50
load_best_model_at_end: true                  # early stopping on the disjoint val split
```

### 6.4 Run it

```bash
uv tool install "llamafactory @ git+https://github.com/hiyouga/LlamaFactory.git@7af909522a951e3ad9f022ea6f88b6755257eaa5"
uv run python -m finetune.train --freeze data/judge/freezes/obj4-v1 --qualification data/judge/training_qualification.json --run-root data/judge/runs/obj4-v1 --prepare
```

The command runs in a separate GPU environment, never by adding Torch, Transformers or LLaMA-Factory to
the production backend. `finetune.train` first validates the immutable freeze and required pins, then records
the three exact invocations, including a `dataset_dir` override resolved from that same `--freeze`. The checked-in
YAML contains only the `__SELECTED_FREEZE__` sentinel, so another hardcoded dataset directory fails preflight.
`--execute` is the explicit boundary that starts GPU work. LLaMA-Factory supports
command-line overrides after the YAML path; the runner varies only `seed`, `output_dir`, `run_name` and
`report_to`, leaving one checked-in YAML as the scientific source of truth.

Weights & Biases is optional. The canonical evidence is the local immutable run directory: resolved command,
config and manifest hashes, stdout/stderr log, tool versions, hardware description, checkpoints and adapter
paths. W&B may mirror those artifacts, but it is never the only copy or required for reproduction.

**Checkpoint selection (pre-registered 2026-07-13).** Early stopping stays on eval loss, but the
**reported** checkpoint per seed is selected by `different_character` F1 on the validation split —
token-level loss on an ~80/20 split is dominated by the majority class and by rationale tokens, so
the loss-minimizing checkpoint is not necessarily the best one on the single class the control loop
acts on. A tiny eval script over the ~75 validation pairs per saved checkpoint is enough.

**Run it three times with `seed: 0, 1, 2`.** At ~1,000 examples a single-seed delta is noise, and a reviewer
who has trained a model will know that. Report mean ± std. Cost: three times a rounding error.

### 6.5 What you get

`saves/judge-lora-seed0/` — a **LoRA adapter**, tens of megabytes. Not a model. It is a small patch that
sits on top of the frozen base weights, which is why training is cheap and why the base model stays
swappable. Commit the config and manifest hash; keep the adapter in the immutable local run directory, with
an optional controlled Storage or W&B mirror.

### 6.6 Pin these or the paper cannot claim reproducibility (CC-7)

Base model **revision hash** · LoRA rank + alpha · seed(s) · the exact `manifest.jsonl` (hash it) ·
`image_max_pixels` · LLaMA-Factory version. Evaluation runs at temperature 0.

The Batch-3 pins fixed on 2026-08-25, before any fine-tune or held-out result, are:

- base model `Qwen/Qwen2.5-VL-7B-Instruct` at
  `cc594898137f460bfe9f0759e9844b3ce807cfb5`;
- LLaMA-Factory `v0.9.5` at `7af909522a951e3ad9f022ea6f88b6755257eaa5`;
- seeds `0`, `1`, `2`; bootstrap RNG seed `0`;
- local immutable run evidence as the source of truth, with W&B optional.

The manifest hash, generator IDs/date, prompt version, hardware description and adapter locations do not yet
exist. `finetune.train` and the evaluation lock reject blanks, placeholder text and unhashed artifacts rather
than inventing them.

PyTorch/CUDA and bitsandbytes builds are hardware-specific. Their exact versions are selected only after the
school-or-cloud hardware qualification and declared in `training_qualification.json` with `base_model`,
`base_revision`, `llamafactory_version`, `llamafactory_commit`, and the exact `hardware` inventory emitted by
the target host. Both `--prepare` and `--execute` require that file, reject pin drift, and require the live
inventory to equal its approved record. Preflight also reads the uv tool environment's installed
`direct_url.json` and requires its VCS commit to equal the frozen LLaMA-Factory commit. Changing hardware
requires a new qualification and run directory.
This is an explicit sequencing rule, not permission to use an unpinned package.

The approved record has this exact shape (values under `hardware` must equal
`finetune.train.hardware_inventory()` on the qualified host):

```json
{
  "base_model": "Qwen/Qwen2.5-VL-7B-Instruct",
  "base_revision": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
  "llamafactory_version": "v0.9.5",
  "llamafactory_commit": "7af909522a951e3ad9f022ea6f88b6755257eaa5",
  "hardware": {"os": "...", "python": "...", "gpu": "...", "torch": "...", "cuda": "...", "bitsandbytes": "..."}
}
```

### 6.7 Batch-3 training runner

`finetune.train` has two modes. `--prepare` is zero-cost: it verifies the recorded hashes of `manifest.jsonl`,
`manifest.train.jsonl`, `manifest.val.jsonl`, `train.json`, `val.json`, `dataset_info.json`, and
`dataset_manifest.json`; rejects a test
dataset referenced by the training config; validates the fixed scientific settings; records the current git
commit and the approved hardware/tool inventory; and prints the three resolved command plans while creating
one run directory per seed. It never opens test data. `--execute` repeats the preflight
and invokes the pinned `llamafactory-cli` once per seed. A non-zero child process stops the sequence without
deleting completed evidence.

Every seed uses the same checked-in YAML. Only `seed`, `output_dir`, `run_name` and `report_to` may differ.
The runner records those resolved overrides and refuses to reuse a non-identical output directory. Checkpoint
selection evaluates every saved checkpoint on `manifest.val.jsonl` and chooses the highest
`different_character` F1; ties choose the earlier training step. All three selected checkpoints and their
validation scores are retained and reported. A deployment seed, if needed, is chosen by validation F1 only.

---

## 7. Evaluation

The external requirement is that the fine-tune **demonstrate measurable classification performance.**
ADR-018 amendment (a) is binding here; this section is its operational form. Its central move: **two
questions were being decided by one number.** *Did fine-tuning work?* is answered against the un-fine-tuned
base. *Should this judge replace the one in the product?* is an engineering question, and its comparator is
the prompted incumbent. Separate them and neither is hostage to a coin flip.

> **What reaches the paper (ADR-008, revised 2026-07-25).** **Objective 4** is the fine-tuned judge's
> *agreement with human-established reference labels* on the character-disjoint held-out set — precision,
> recall, and F1, **F1 primary** — with intra-rater test-retest agreement on those labels reported and the held-out set
> **read once**. That absolute number is the reported result. An **optional secondary comparison** against
> the zero-shot base model (§7.1) and the existing prompted Consistency Judge baseline (§7.2, §7.4) is
> permitted on the same held-out pairs and human labels — not required to satisfy Objective 4, and not
> forbidden either. The **deployment gates** below (§7.2, §7.5) answer a separate, engineering question —
> *does this judge replace the one already shipped* — and stay build decisions regardless of how the optional
> comparison reads.

### 7.1 The primary endpoint — the "did the fine-tune work" gate

> ΔF1 on the `different_character` class, held-out test set, **fine-tuned Qwen2.5-VL-7B vs. zero-shot
> `Qwen2.5-VL-7B`.** The gate passes only if the 95% CI on ΔF1 excludes zero. (The deployment build gate;
> as Objective 4's optional secondary comparison it may also be reported alongside the primary F1-vs-human-
> labels result — ADR-008, revised 2026-07-25.)

Same architecture, same weights, same prompt; the adapter is the only difference. It is the cleanest causal
statement available about the fine-tune, it is the ablation every fine-tuning paper reports, and on ~900
in-domain training pairs the expected gap is large.

- **Significance:** McNemar's exact test on the paired per-item decisions — both judges score the same items.
- **Effect size:** ΔF1 with a 95% bootstrap CI, 10,000 resamples, **resampled by `char_id`, not by pair.**
  Fifteen scenes from one character are not fifteen independent observations. A pair-level bootstrap yields
  an interval that is too narrow, and this is the likeliest place a statistics reviewer finds a hole.

> ⚠️ **Beating your own base model is necessary, not impressive.** The panel's reflex will be *"of course
> in-domain fine-tuning beats zero-shot."* It satisfies the requirement; it is not the contribution.
> **Never present it alone.** §7.4's first two items go on the same slide.

### 7.2 The product gate — separate, and non-blocking for Objective 4's reported number

Ship the fine-tuned judge only if **both** hold against prompted `gemma-3-27b-it`:

1. **Non-inferiority:** ΔF1 on `different_character` no worse than δ = 3 points.
2. **No recall regression.** A judge that buys precision with recall ships broken pages. Consistency has a
   best-of fallback (ADR-010); a missed failure has none.

**Failing this does not change what Objective 4 reports.** It means the product keeps the prompted judge it
already shipped Phases 1 and 2 with, and ADR-019's Modal deployment is dropped (de-scope ladder, rung 4).
That is rung C in §7.5. Objective 4 still reports the fine-tuned judge's absolute agreement with human
labels either way; the optional secondary comparison against Gemma (§7.4.1) is reported alongside it
regardless of which way the gate falls.

**Why the Gemma comparison is winnable anyway.** You are not beating Gemma-27B at general vision-language.
You are beating it on Filipino children's invented characters across three controlled StoryBuddy styles,
drawn by one image model — the exact distribution the LoRA trains on, and the exact regime where ADR-004 records a prompting
ceiling and ADR-001 records that nobody has measured anything. Narrow-domain specialization against a large
prompted generalist is the most reliable way a small fine-tune wins.

### 7.3 Baselines — all four, non-negotiable

| Baseline | Role | What its absence would let a reviewer claim |
|---|---|---|
| **Zero-shot `Qwen2.5-VL-7B`** | **the primary comparator** | "Your base model was already good; the LoRA did nothing" |
| **Prompted `gemma-3-27b-it`**, reason-then-score | **the product gate** | "You never beat the system you already had" (ADR-004) |
| CLIP image–image cosine | scientific control | "A 2021 embedding would have done this" |
| **DINOv2 cosine** | scientific control | "A self-supervised embedding beats your VLM at instance identity" |

**CLIP and DINOv2 are controls, not product candidates.** They emit a scalar. ADR-010's regeneration
controller consumes `failure_reasons` — it has to know to *restate the scarf*, and a cosine similarity cannot
tell it that. So **if DINOv2 wins on F1, that is a reported finding about metrics and changes nothing in the
pipeline.** Write that sentence into the paper before the defense, not during it.

### 7.4 Secondary endpoints — ordered in advance, reported regardless of the primary

1. **Fine-tuned vs. prompted `gemma-3-27b-it`.** Same metric, same test set. **The input to the product
   gate** — it decides whether the fine-tuned judge replaces the incumbent in the pipeline (δ = 3
   non-inferiority, §7.5). It also doubles as Objective 4's **optional secondary comparison** against the
   existing prompted baseline — permitted, not required (ADR-008, revised 2026-07-25).
2. The primary metric on the **non-human character slice.** The contribution — and the least-powered slice.
3. **Cohen's κ vs. human**, overall and split by human / non-human.
4. **Latency and $/call.** A structural win: 7B beats 27B, self-hosted beats per-call.
5. **DreamBench++ transfer — descriptive only.** No comparison claim; it is out-of-domain by
   construction. **Binarization is fixed in the pre-registration, before the transfer eval runs:**
   DreamBench++'s human scores are *graded* concept-preservation ratings, not binary same/different
   verdicts, so the threshold mapping them onto the judge's binary output must be declared in
   advance (per the benchmark's own "preserved" convention — verify the exact scale during the A2
   citation check, same PDF). Agreement reported as κ and AUROC. A threshold picked after seeing
   results makes the one transfer number in the paper post-hoc.
6. **Downstream:** serve the fine-tuned judge in the pipeline and ask whether the expert panel's feedback
   (**Objective 3**, `research_instruments.md` §A) is at least as favorable as under the prompted judge.
   This ties the fine-tune to the shipped outputs instead of leaving it a bolt-on.
   (Non-comparative — the pipeline on/off ablation once planned here stays dropped.)
7. **Data Scaling Ablation:** A 50% vs. 100% training-data learning curve comparison evaluated on the validation set. This establishes whether the dataset size has hit diminishing returns.

Also report AUROC from the verdict-token logprob, and precision and recall separately — they are different
failures with different costs. Note that **per-taxonomy performance** (recall/F1 on specific failure reasons) must be treated as an **exploratory diagnostic analysis** rather than a primary conclusion, as the natural drift rate means some taxonomy categories may only have a handful of examples in the held-out test set.

### 7.5 Pre-registration and the claim ladder

**Write and timestamp the analysis plan before any label is collected.** It is the only thing separating a
pre-declared ladder from a moved goalpost, and almost no capstone does it.

**The ladder decides deployment — which judge ships — not what Objective 4 reports** (ADR-008, revised
2026-07-25). Read the "Outcome" column as *the engineering conclusion that decides what ships*. Objective
4's primary result (F1 vs. human labels) is unaffected by this ladder; the ladder only gates whether the
fine-tuned judge replaces the prompted incumbent in the product, and whether the optional Gemma comparison
(§7.4 item 1) reads as a win, a tie, or a loss.

| Rung | Condition | Requirement met? | Outcome (engineering) | Ship? |
|---|---|---|---|---|
| **A** | Beats base **and** beats prompted Gemma | Yes | Specialized 7B judge outperforms the prompted 27B incumbent on our in-domain held-out set, at lower latency and zero marginal cost — a clear swap | Yes |
| **B** | Beats base; within δ = 3 F1 of Gemma; no recall regression | Yes | Specialization recovers 27B-level quality at 7B, self-hostable, zero marginal cost — non-inferiority satisfied, swap | Yes |
| **C** | Beats base; loses to Gemma by > δ | **Yes** | Fine-tuning worked, but specialization at 7B did not close the gap. Keep the incumbent; note it as a limitation, not a finding | No — keep the prompted judge |
| **D** | Does not beat base | No | The LoRA did nothing. A **bug report, not a result** | No — debug |

δ = 3 F1 points is a judgment call, chosen because it sits inside one annotator's disagreement band on ~60
minority-class items. **Adjust it once, before pre-registration. Never after.**

**Rung D is the only failing outcome, and it is a bug.** That is what separating the two gates buys. The
engineering risk now lives in rung C, where it is survivable — the product keeps the judge it already shipped
Phases 1 and 2 with. Moving the gate after seeing held-out numbers is the one thing that ends a capstone badly.

**Test-set access policy (pre-registered 2026-07-13 — resolves the rung-D contradiction).** Rung D
is only *discoverable* by reading the held-out set, and "debug" implies re-evaluating — which would
be a second read of a set that must be read once. The pre-declared resolution: rung D triggers a
debugging investigation conducted **exclusively on train and validation**; **one (1)** second
held-out evaluation is permitted after the defect is identified and fixed; both readings and the
deviation are reported in full. This is the only circumstance under which the held-out set is read
twice. Without this paragraph, "read once" and "rung D → debug" are individually correct and
jointly contradictory, and a panel that notices asks whether you would have re-run until it passed.

**Malformed-output rule (pre-registered 2026-07-13, applies to all four baselines and the
fine-tune alike).** Every judge runs under constrained decoding where the serving stack supports it
(vLLM guided decoding; OpenRouter `require_parameters`). Any residual unparseable verdict is scored
as a **miss on `different_character`** — counted against the judge that produced it. Deciding this
after seeing which baseline emits broken JSON would be a degree of freedom; it is closed here.

### 7.6 Batch-3 evaluation evidence and access control

Predictions use schema version 2 and are immutable JSONL rows keyed by `pair_id`, `char_id`, split and judge ID. Each row records the
binary prediction, verdict-token confidence when supplied, latency, parse status, model and adapter IDs,
prompt version and threshold ID. The first row per judge is explicitly `cold`; all later rows are `warm`.
Malformed calls keep latency unavailable rather than fabricating zero milliseconds. Every judge must cover
the same ordered pair IDs. A duplicate, missing,
reordered or unknown pair aborts the report. Missing confidence makes AUROC unavailable for that judge with a
recorded reason; it never becomes a fabricated probability.

The production `providers.judge()` signature stays unchanged. An additive evaluation-only provider function
returns the parsed verdict plus logprob/latency metadata, keeping all remote calls in `providers.py`. The
offline evaluator consumes that richer result. CI calls neither function against a real model.

Validation is repeatable and uses only `manifest.val.jsonl`. It selects each seed's checkpoint and the
CLIP/DINOv2 thresholds, then writes `evaluation_lock.json` containing every checkpoint/hash, threshold,
prompt/model/tool pin, manifest-projection hash, bootstrap seed and prediction-schema version. The lock must
be signed off before test access and cannot be replaced in place.

Held-out access is file-ledgered and fail-closed. The runner acquires an exclusive lock and reserves a read
before opening `manifest.test.jsonl`. It evaluates all three selected fine-tunes and all four baselines in one
run. The evaluation lock requires prediction schema version 2, normalized SHA-256 values, nonblank registered identifiers,
the frozen hashes for `character_slices.json` and `annotation_agreement.jsonl`, and all three selected
checkpoint directories to still match their frozen paths and directory digests. Lock
creation is exclusive and an existing byte-identical lock is the only idempotent success. Each completed judge
prediction file has an immutable SHA-256 sidecar; a crashed run records `resumed`, verifies the file hash,
alignment and frozen judge/checkpoint identity, and invokes only judges whose evidence is missing. The ledger
records `reserved`, `resumed`, `completed` and `failed` without story text or asset paths. A crashed run may
resume only under the same run ID and identical hashes. A second run is accepted only
when the first completed report is Rung D and a dated deviation record binds the first report, defect, fix
commit and train/validation-only debugging evidence. A third read is always rejected. The ledger is an
auditable protocol control, not DRM; deleting it or copying the freeze is a reportable protocol violation.

### 7.7 Batch-3 statistics

Pure standard-library helpers compute positive-class precision/recall/F1; 10,000-resample
character-clustered F1 and paired ΔF1 percentile intervals; two-sided exact McNemar on discordant item
decisions; tied-rank AUROC; and Cohen's κ. κ is reported for the single rater's ordered rounds 1 and 2
(test-retest) and for each judge against adjudicated human truth, overall and on the frozen human/non-human
slices. Inter-rater agreement remains undefined for this one-rater dataset. All three fine-tune seeds are
reported individually plus mean and sample standard deviation.

Results also record latency, parse failures, label prevalence and prediction-rate drift. A fixed ten-bin
reliability table and Brier score are exploratory calibration diagnostics, not new Objective-4 endpoints.
Empty slices, one-class AUROC inputs and zero-variance κ are reported as unavailable with their reason.

`Objective4Report` in `backend/finetune/evaluate.py` is the one emitted report schema (schema version 1).
For every registered judge, `judges` records `n`, precision, recall, F1 and its clustered 95% interval,
AUROC, Cohen's κ versus adjudicated truth, exploratory calibration, warm-start latency count/mean/sample SD
with the first cold-start observation reported separately,
cost/call availability, parse-failure count/rate, label prevalence, and prediction rate. `slices.human` and
`slices.non_human` repeat that schema without pair, character, story, or asset identifiers.
`intra_rater_agreement` reports overall and slice-level κ and percent agreement for the dataset's single
rater, where rounds 1 and 2 are the test-retest observations. Inter-rater agreement is permanently undefined
for this one-rater dataset. The report also
contains prediction-rate drift versus the validation-selected deployment seed, an `objective4` conclusion,
and a separate `deployment_decision`. Missing evidence and undefined statistics remain explicit unavailable
objects with reasons. Registered transfer, downstream, and validation-only endpoints remain visible with
their collection status rather than disappearing from the report. Before aggregation, the writer verifies
prediction sidecars plus the freeze-report hashes for slice and agreement evidence. It validates the nested
schema and publishes the sorted JSON exclusively/idempotently, so the same immutable inputs regenerate
byte-identical report bytes and a different report can never replace ledgered evidence.

---

## 8. Then what? — serving the thing you trained

Rung A or B (§7.5). This is the entire deployment, and it is why `providers.py` was built the way it was.

Start vLLM with the base model and the adapter attached (ADR-019 — Modal, scale-to-zero):

```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --enable-lora --lora-modules judge=/vol/judge-lora-seed0 --max-lora-rank 16
```

vLLM speaks the OpenAI protocol, so the application change is **two environment variables and no code**:

```
JUDGE_BASE_URL=https://<your-modal-app>.modal.run/v1
JUDGE_API_KEY=<token>
VLM_JUDGE_MODEL=judge
```

`providers.judge()` already omits OpenRouter's `provider.require_parameters` field when `JUDGE_BASE_URL`
is not OpenRouter — vLLM rejects unknown fields, and there is a test asserting exactly this (§10).

**Rollback is the same two variables.** Point them back at OpenRouter and Gemma-27B, redeploy, done. That is
the whole reason the fine-tuned judge sits at rung 4 of the de-scope ladder and not at the bottom: dropping
it costs a config change, not a rewrite.

**What must never happen:** the fine-tuned model on the child-safety path. Image moderation stays on prompted
Gemma with its own rubric (ADR-011). Consistency has a best-of fallback; safety has none.

---

## 9. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-3 Cost control** — data ≈ $29, training ≈ $5–15 one-time; serving is scale-to-zero (ADR-019). Spend alarm on the rented GPU.
- [x] **CC-5 Observability** — judge calls traced through LangSmith unchanged; vLLM is OpenAI-compatible.
- [x] **CC-7 Reproducibility** — §6.6. Eval is deterministic (temperature 0).
- [ ] **CC-1 Moderation ordering** — **explicitly not touched.** ADR-011's image-safety rubric stays on prompted Gemma. **The fine-tuned model never sits on the child-safety path** (ADR-004 amendment b, §8).
- [ ] CC-2, CC-4, CC-6, CC-8, CC-9, CC-10 — N/A. The judge consumes images already stored and moderated.

---

## 10. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Models mocked. Never assert on generated content.

- `providers.judge()` sends **two images** as multimodal content parts, in reference-then-scene order.
- `provider.require_parameters` is sent to OpenRouter and **omitted** for a self-hosted `JUDGE_BASE_URL`
  (vLLM rejects the unknown field — ADR-019, §8).
- The verdict schema declares `differences_observed` **before** `same_character`. A test asserts field order.
- `failure_reasons` outside the §4 taxonomy fail Pydantic validation.
- A `same_character=False` verdict routes to `regenerate`; `True` routes to output moderation (ADR-003 edges).
- **`manifest.py` refuses a manifest where any `char_id` appears in two splits.** *(The §3.2 guard. It belongs
  in CI because it is the one mistake that is invisible in the metrics.)*
- **`to_llamafactory.py` emits exactly as many `<image>` tokens as entries in `images`** (§6.1), and its `gpt`
  turn round-trips through the production verdict schema.
- `pair_type == "constructed"` never appears in the `val` or `test` splits (§3.3).
- Freeze projections reproduce the combined manifest exactly; validation tests fail if code attempts to open
  `manifest.test.jsonl`.
- Known examples cover exact McNemar, tied-rank AUROC, κ, clustered paired ΔF1 and degenerate inputs.
- Training preflight rejects placeholder/mismatched pins and any seed config drift beyond the four allowed
  overrides.
- Held-out fixtures cover an ordinary first read, same-run crash resume, a documented Rung-D second read and
  unconditional rejection of a third read.
- **`test_research_integrity.py` executes the cross-cutting research integrity suite:** character-disjoint splits across train/val/test, test set purity (100% donated, 0 constructed negatives), constructed negatives restricted to train, manifest reconciliation against `dataset_manifest.json`, and strict ShareGPT prompt/output blinding (no leaked identifiers or split tokens).


## 11. Eval / quality checks (Tier B — never CI)

Everything in §7. Real models, real money, offline. Feeds **Objective 4**, and via the downstream swap, the
expert panel's feedback under **Objective 3**.

---

## 12. Linked decisions & open questions

**Depends on:** ADR-018, ADR-019, ADR-004, ADR-008, ADR-010 (taxonomy), ADR-016 (why not identity/style).

**Open — do not guess (CLAUDE.md §1, §7):**

- ⚠️ **Everything here is contingent on the Phase 0.5 kill criterion.** The judge trains on images made by
  `fal-ai/qwen-image-edit-2511`, and every image model drifts in its own characteristic way. If the spike
  escalates to FLUX.1 Kontext, the labelled pairs were produced by a model you no longer run — not worthless,
  but no longer matched to deployment. **This is a sequencing rule, not a risk: do not spend the labelling
  weekend before the spike passes.**
- ⚠️ **Ethics.** The images are generated *from children's stories*, so a child's creative content flows into
  the model weights. Anonymising the name does not touch that. **Stage-1 consent must state that donated
  stories may be used to build and evaluate an AI model** (ADR-008 amendment a, RESEARCH_PROTOCOL §9). One
  sentence, written before collection. Collect first and the options are re-consent every child or delete the
  data. **There is no retroactive fix.**
- **Taxonomy completeness** (§4) — extend before annotation, never during.
- **Modal cold-start budget** for a study session — measure, don't assume (ADR-019).

**Resolved:**

- ~~DreamBench++ licensing beyond evaluation~~ → **evaluate only, never train, never redistribute** (§5.6).
  Evaluation is the benchmark's intended use; no correspondence with the authors is required.
- ~~Are there alternative datasets?~~ → **No.** Surveyed and rejected with reasons (§5.1). The absence is a
  paper claim, not a gap.

---

## 13. Reference reading

Read in this order. Two hours total; do not read the QLoRA paper first.

| # | What | Why |
|---|---|---|
| 1 | [LLaMA-Factory data format](https://github.com/hiyouga/LLaMA-Factory/blob/main/data/README.md) | The exact JSON you must emit. Read §6.1 alongside it. |
| 2 | [LLaMA-Factory examples](https://github.com/hiyouga/LLaMA-Factory/blob/main/examples/README.md) | Working `qwen2_vl` LoRA YAMLs to diff against §6.3. |
| 3 | [Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) | The base model card. Grab the revision hash here (CC-7). |
| 4 | [QLoRA (Dettmers et al., 2023)](https://arxiv.org/abs/2305.14314) | *Why* a 7B model fits in 24 GB. Read after your first successful run. |
| 5 | [DreamBench++ (arXiv:2406.16855)](https://arxiv.org/abs/2406.16855) | The transfer test, and the related-work paragraph. |
| 6 | [vLLM LoRA serving](https://docs.vllm.ai/en/latest/features/lora.html) | §8. `--enable-lora`, `--max-lora-rank`. |

Domain-adjacent, cited in §5.1 as *rejected alternatives* — read only to write that paragraph:
[Intelligent Grimm / StorySalon (CVPR 2024)](https://openaccess.thecvf.com/content/CVPR2024/papers/Liu_Intelligent_Grimm_-_Open-ended_Visual_Storytelling_via_Latent_Diffusion_Models_CVPR_2024_paper.pdf) ·
[ContextualStory (PororoSV / FlintstonesSV statistics)](https://arxiv.org/html/2407.09774v2)

# Objective 4 Corpus Campaign

> Interactive version: https://claude.ai/code/artifact/2b8a93cc-69f1-4d1d-b458-43388c18b9f8
> Last updated 2026-08-30. Commands assume you are in `backend/`.

Everything from here to a trained judge, in the order it has to happen. One thing on this page will change your plan — read "Start here" before running anything.

Updated 30 Aug 2026 | Defense: Oct 2026 | Budget: $25 working / $30 hard | Spent to date: ~$5.35

---

**Start here**

## Three things that change what you do next

> **ALREADY DONE — DON'T REDO THIS**
>
> **The synthetic stories are already written.** All 30 of them live in `backend/finetune/corpus_synthetic.json` — 24 train, 6 val, 10 each in cel / gouache / cut-paper. There is no "fill in the training stories" step. They're written, declared, and they pass the roster preflight 30/30.
>
> The only stories you still need to collect are the **donated** ones, and those are the test set.

> **DO NOT START GENERATION YET**
>
> **Synthetic and donated generation are one campaign, not two.** They write to the same `--out` directory and share one budget ceiling — 30 + 15 = 45 stories.
>
> And `code_commit` is a pinned freeze key. It's stamped into every bundle from `git rev-parse HEAD` at generation time, and `freeze_dataset._pinned_versions` hard-fails if any two bundles disagree.
>
> **So: if you generate the synthetic half now and the donated half after collecting 11 more stories, every commit you land in between breaks the freeze.** You'd have to freeze the whole repo for however many weeks that collection takes.
>
> The fix is just sequencing — collect the donated stories *first*, then run both halves back to back. That's why steps 1–4 below are all paperwork and no scripts. (Step 4 was previously listed as including `dataset_selection.json`; it cannot be — see step 04.)

> **MANDATORY FLAG**
>
> `--max-calls-per-story 15` is **required** on every paid run, not optional. Without it each story reserves the full image budget (55 × $0.035 = $1.93), so 45 stories reserve $86.63 against a $30 hard ceiling. The run cannot complete at any authorization — it halts after burning through everything up to that point.

---

**Status board**

## Where things actually stand

| Item | Status | Detail |
|---|---|---|
| Pipeline | Proven | Full chain verified end to end on live Supabase at $0 |
| Backend tests | Green | 1344 passed, 87 skipped |
| Roster preflight | 30/30 | Second run clean; failures are stochastic and retryable |
| Annotation queue | Empty | 0 pairs, 0 annotations — clean slate |
| Output directory | Fresh | Old mixed-commit corpus archived; ledger starts clean |
| Donated stories | 4 of 15 | The critical path to October |
| Ethics Stage 1 | Verify | Consent clause has no retroactive fix |
| Paid generation | Not started | Blocked on donated collection, by choice |

---

**Blockers**

## What's actually in the way

### 1 · You have 4 donated stories and the loader requires exactly 15

`corpus_io.load_intake` rejects any donated file that isn't exactly 15 records in this frozen allocation, and `freeze_dataset.py:122` and `dataset_selection.py:266` re-assert it independently:

| Style | Primary | Backup | Total |
|---|---|---|---|
| Gouache | 4 | 1 | 5 |
| Cel | 3 | 2 | 5 |
| Cut-paper | 3 | 2 | 5 |
| **Total** | **10** | **5** | **15** |

This isn't only a code gate. Donated stories are your **entire held-out test set** — every headline Objective-4 number is measured on them. The preregistration already concedes 15 stories is thin ("roughly 15–20 distinct characters" against the ~50 the design assumes). Four would not survive a panel.

### 2 · Ethics Stage 1 consent — check this before collecting more

The preregistration flags it plainly: the Stage-1 consent clause must state that donated stories may be used to build and evaluate an AI model, plus the data-lock date, and **"there is no retroactive fix."** If the consent forms you're collecting under don't say that, stories gathered now can't be used later. Confirm the wording before you gather the remaining 11, not after.

### 3 · A preregistration contradiction nobody has resolved

Section 2 contradicts itself and you'll want it settled before the freeze. The split table says **Validation = Synthetic corpus**. Four paragraphs down the prose says the rule is applied "at full strength, with **zero** synthetic characters in validation or test." Both cannot hold — the 6 val stories are synthetic. Resolve it with a dated amendment; the preregistration is append-only, so never edit it in place.

---

**The sequence**

## Phase A — Paperwork (no scripts, no money)

### 01 · Collect 11 more donated stories

***You***

Target 15 total. Confirm the Stage-1 consent wording first (blocker 2). Raw `.txt` is fine at this stage — no metadata needed yet.

> **Gate:** guardian consent and child assent must both be real and recorded. The intake loader refuses a donated record without them, and that refusal is doing its job.

### 02 · Hand-redact each story

***You***

Substitute identifiers rather than deleting them — real names, school, town, teacher. `"Miguel" → "Andres"` keeps the narrative and voice intact. Keep your substitution list **outside** the corpus.

> **Note:** Presidio no longer touches donated text (fixed in `e76961d`). Nothing automated will rewrite your stories. Character names in the redacted story are yours to choose — `declared_characters` is keyed to whatever you write.

### 03 · Build `donated.json`

***You + me***

15 records at `data/judge/intake/donated.json`. Each needs `story_id`, `text`, `declared_characters`, `declared_non_human`, `split:"test"`, `candidate_role`, `style_preset_id`, the four approval booleans, `withdrawal_state:"active"`, and a past `selection_frozen_at`.

> **Gate:** I'll write only what you attest to on the consent and redaction fields. Style and role slots are frozen *before* generation and can't be reshuffled afterwards.

### 04 · Settle the amendments (and read this about `dataset_selection.json`)

***You + me***

Resolve the §2 contradiction (blocker 3) in a dated amendment. That part is paperwork and belongs here.

> **`dataset_selection.json` CANNOT be written in Phase A.** Its `hard_negative_matches` are keyed by
> `lineage_id(story_id, char_id)`, and `char_id` does not exist until the pipeline has generated the
> characters. `validate_hard_negative_matches` then requires **exactly one match for every synthetic
> training character that has a canonical reference** — `set(matches) != set(train_characters)` is a
> hard fail — so the file cannot even be stubbed with an empty list.
>
> It is needed at **step 09** (`materialize_pairs`) and again at step 13 (the freeze), both of which
> run after generation. Write it between step 08 and step 09, off the candidate report.

**Authoring it at step 09**, after `--candidate-report` prints the eligible pairings:

| Field | What goes in it |
|---|---|
| `hard_negatives_frozen_at` | UTC, timezone-aware, and already past. Stamp it when you finish choosing, not before. |
| `hard_negative_matches` | One `{reference_char_id, target_char_id}` per synthetic **train** character with a canonical ref. Both ids are `lineage_id` values (`<story_id>:<char_id>`). |
| `donated_replacements` | Empty list unless a primary donated story failed and a backup took its slot. Each entry needs `primary_story_id`, `backup_story_id`, `reason`, a past `approved_at`, and a non-blank `evidence_ref`. |

`reason` is a closed set — `withdrawal`, `deidentification_failure`, `terminal_pipeline_failure`,
`inadequate_character_yield`. Anything else fails to load.

The validator will reject, before it costs you anything: a self-pair, a duplicate `reference_char_id`,
a reused `backup_story_id`, a target that is not a synthetic training character, a species mismatch, a
style mismatch, a target with no finalized natural scenes, or a future timestamp. The candidate report
exists precisely so you pick from pairings that already satisfy the species/style/scene rules.

> **Gate:** `extra="forbid"` on every model in `dataset_selection.py` — an unrecognized key is a load
> failure, not a warning. There is no partial-credit path here.

---

**The sequence**

## Phase B — Freeze the code, then spend

> **FROM STEP 5 UNTIL STEP 8 COMPLETES: DO NOT COMMIT**
>
> Every bundle stamps the current `HEAD`. One commit mid-campaign and the freeze fails with `pinned run metadata differs for code_commit`, and the only remedy is regenerating everything at one commit. Land what you want, then stop.

### 05 · Land final code, then record the sha

***You***

Merge PR #69 and anything else you want in the corpus. Then `git rev-parse HEAD` and write it down — every bundle must carry this exact value.

### 06 · Free preflight on all 45 stories

***Me***

Text-only. No images, no database, no writes. Catches roster problems that would otherwise cost a story's full image spend.

```bash
uv run python -m finetune.build_corpus --check-rosters \
  --corpus finetune/corpus_synthetic.json
uv run python -m finetune.build_corpus --check-rosters \
  --corpus ../data/judge/intake/donated.json
```

> **Expect:** roughly one story per thirty to fail extraction at random. That's normal and free — see "Known gotchas". Rerun before concluding anything is wrong.

### 07 · Paid smoke — 3 stories

***Me · needs your $ authorization***

Into a throwaway directory, so nothing lands in the real ledger. This is the only unverified thing left: real Fal generation, reference judging and consistency checking outside fixtures.

```bash
uv run python -m finetune.build_corpus \
  --corpus finetune/corpus_synthetic.json \
  --out ../data/judge/corpus-smoke-b \
  --limit 3 --max-usd 2.63 --max-calls-per-story 25 \
  --price-per-megapixel 0.035 \
  --price-basis "<official price URL + date verified>"
```

> **Cost:** $2.63 ceiling. Optional — skipping it means the 45-story campaign is the first real run, which is recoverable but you'd find out at $24 instead of $3.

### 08 · The campaign — 45 stories, two commands, one ceiling

***Me · needs your $ authorization***

Same `--out`, same cap, same price basis on both. They are one campaign against one budget.

```bash
# 30 synthetic (24 train + 6 val)
uv run python -m finetune.build_corpus \
  --corpus finetune/corpus_synthetic.json \
  --out ../data/judge/corpus \
  --max-usd 25 --max-calls-per-story 15 \
  --price-per-megapixel 0.035 \
  --price-basis "<official price URL + date verified>"

# 15 donated (10 primary + 5 backup)
uv run python -m finetune.build_corpus \
  --corpus ../data/judge/intake/donated.json \
  --out ../data/judge/corpus \
  --max-usd 25 --max-calls-per-story 15 \
  --price-per-megapixel 0.035 \
  --price-basis "<official price URL + date verified>"
```

> **Budget:** 45 × 15 × $0.035 = **$23.63** worst case, inside the $25 working allocation and leaving the $25–30 band for a cap extension on a story that needs one. `--max-usd` is silently clamped to the $30 hard ceiling.

---

**The sequence**

## Phase C — Label and freeze

### 09 · Inspect candidates, then seed the queue

***Me***

```bash
uv run python -m finetune.build_dataset --candidate-report \
  --data ../data/judge/corpus

uv run python -m finetune.materialize_pairs \
  --data ../data/judge/corpus \
  --donated-intake ../data/judge/intake/donated.json \
  --selection ../data/judge/intake/dataset_selection.json
```

> **Do not pass `--pilot` here.** Pilot pairs are permanently excluded from training and can never produce a dataset. That flag is for rehearsals only.

### 10 · Round 1 — label the whole queue

***You***

At `/annotate`, blinded. Work through every pair once.

### 11 · Round 2 — label the whole queue again, cold

***You · wait first***

**Same person. You, a second time.** This is test–retest reliability, not a second annotator — there is no annotator 2 in this design, and logging in as a different account produces a shape the resolver rejects.

> **Process discipline, not enforced by code:** leave a real gap. A round 2 run the same evening as round 1 is a weaker measurement than one run a fortnight later, and nothing in the database can tell the difference.

### 12 · Adjudicate the conflicts

***You***

At `/adjudicate`. Round 3 is you looking a third time at the pairs where your own two rounds disagreed. Done when it says "All Conflicts Adjudicated".

### 13 · Reconcile and freeze

***Me***

```bash
uv run python -m finetune.build_dataset --reconcile-only

uv run python -m finetune.build_dataset --freeze \
  --data ../data/judge/corpus \
  --donated-intake ../data/judge/intake/donated.json \
  --selection ../data/judge/intake/dataset_selection.json \
  --out ../data/judge/freezes/obj4-v1
```

> **`--out` is a directory, not a file.** Pass a folder name. It writes the LlamaFactory `train.json`, `dataset_info.json`, per-split manifests and the hash-pinned freeze report.

> **AFTER THE FREEZE**
>
> Steps 14 onward — LlamaFactory install, hardware qualification, three training seeds, validation capture, the threshold lock, and the single guarded held-out run — are already written out in `docs/capstone/research_runbook.md` steps 9–15. They need a qualified GPU host and an independent sign-off file, so they're a separate working session.

---

**Reference**

## Known gotchas

| What you'll see | What it means | What to do |
|---|---|---|
| `character needs at least three visual discriminators` | The extractor invented a vague bit-player ("the other bats") it was told to skip. Random, not deterministic — roughly 1 story in 30. | Nothing is broken. `--restart-quarantined <story_id>`. Costs one text call, zero image spend. |
| `pinned run metadata differs for code_commit` | You committed during the campaign. Bundles disagree on `HEAD`. | No repair exists. Regenerate at one commit. Prevent it by not committing between steps 5 and 8. |
| `declared roster does not reconcile` | A declared character didn't reach the two-slot reference slice, or its humanoid flag disagrees. | Free at preflight, fatal at packaging. Never skip step 6. |
| Run halts, exit code **2** | The budget ceiling stopped the campaign partway. Deliberately loud so a halt can't pass as success. | Read the halt message — it names what never started and what `--max-usd` would have covered. |
| `billing_uncertain` | A provider call may have billed without returning. Outranks everything and stops the run. | `--acknowledge-uncertain-billing <story_id>` once you've checked the Fal dashboard. |
| Annotate says "Round 2" right after round 1 | Correct behaviour. The queue re-serves every pair for your second pass. | Nothing. Ideally wait days first (step 11). |
| `production dataset preparation requires --donated-intake and --selection` | You're materializing or freezing real data without the selection artifacts. | Finish step 4. There's no bypass except `--pilot`, which can't produce a dataset. |

> **NEVER DO THESE**
>
> - Hand-edit or delete `data/judge/corpus/build_state.json` — it's the append-only audit ledger.
> - Edit `corpus_synthetic.json` declarations to make a failing check pass.
> - Rewrite `intake_sha256` to make assets packageable.
> - Edit the preregistration in place. It's append-only; supersede with a dated amendment.
> - Write `true` on a consent or redaction attestation for work that wasn't done.
> - Point a `--pilot` run at the production corpus directory.

---

**Immediate next action:** confirm the Stage-1 consent wording, then collect the remaining 11 donated stories. Nothing downstream can start without them, and starting the synthetic half early costs you the ability to commit code for weeks.

Session spend so far today: ~$0.04, all of it roster preflight. Sunk from earlier runs: ~$5.31, archived and unusable.

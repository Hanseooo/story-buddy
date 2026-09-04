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
> `--max-calls-per-story` is **required** on every paid run, not optional. Without it each story reserves the full image budget (55 × $0.035 = $1.93), so a story late in the run cannot clear the reserve check against what is left of a $30 ceiling. The run halts after burning through everything up to that point.
>
> **The value is 19, not 15.** The reserve check (`build_corpus.py:1060-1064`) compares *this story's* remaining cap against the authorization not yet spent, so the binding case is every story consuming its full cap: 45 × 19 × $0.035 = **$29.93**, just inside the ceiling. 20 does not fit ($31.50).
>
> **15 was never measured and does not work.** Measured on 2026-09-03 at `a723126`:
>
> | story | images | outcome at cap 15 |
> |---|---|---|
> | syn-002 | 14 | completed, 1 image of headroom |
> | syn-003 | 15 | **budget_stopped** |
> | syn-001 | 18 (range 18–26 over five runs) | needs cap 30 |
>
> **19 itself has never executed.** The measured runs used 15, 25 and 30; 19 is derived from the
> reserve arithmetic above, not observed. The derivation is sound and the failure mode is benign — a
> story stops with `budget_stopped` and the extension flag recovers it — but do not read 19 as a
> validated number.
>
> Expect a handful of stories to stop at 19. That is what `--extend-story-call-cap <story_id>` is
> for, and it is allowed **once per story, ever** (`_prepare_cap_extension`, `:640`). Run the
> extension pass *after* the main pass, when actual spend is known and the remaining headroom can
> cover a raised reserve.
>
> Caps are **not** a pinned freeze key (`max_calls_per_story` is absent from `PINNED_METADATA_KEYS`;
> `image_budget` pins the constant 55). Separate invocations may use different caps and still freeze
> as one campaign — verified live on 2026-09-03: a completed story's state entry equals
> `{"bundle": "runs/<id>"}`, which skips the restart block entirely (`:849`), so no cap conflict
> arises.
>
> **Cumulative spend in an output directory is charged against the *current* `--max-usd`**
> (`_recorded_authorization`, `:735`). A second invocation into the same `--out` does not get a
> fresh budget. Both step 08 invocations share `--out`, so `--max-usd 25` is the total across both.

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

### 3 · The corpus could not supply the hard negatives the freeze demanded — **RESOLVED 2026-09-03**

**Resolved by ADR-057 (Accepted), with a preregistration amendment appended the same day. The code
change has landed and the rehearsal now passes.** Kept here because the finding explains why the
achieved constructed-pair count will be far below what the design reads like.

**Found by rehearsing for $0 against the real `corpus-smoke-h` bundles**, before the ~$25 was spent.
It would have been fatal at steps 09 and 13, both of which run after the money. Full write-up:
`docs/product/evidence/phase-c-rehearsal-2026-09-03.md`.

`validate_hard_negative_matches` (`dataset_selection.py:361-362`) hard-failed unless **every**
synthetic train character with a canonical reference had exactly one match, and a match requires the
same species (`:372`, casefold equality) and the same art style (`:379`, raw string, no casefold).

On the two real bundles: **0 legal pairings for 4 characters.** Projected across all 24 synthetic
train stories, **26 of 30 characters have no eligible partner** — only humans repeat within a style,
and cel has one. The corpus was authored with a distinctive creature per story, which is right for
consistency testing and incompatible with a rule that needs species collisions.

`dataset_selection.json` therefore could not be authored as specified, and there was no way to
discover this later that did not cost the campaign.

**How it was resolved.** The completeness rule was never preregistered — `PREREGISTRATION_OBJ4.md:564`
commits only to *frozen before annotation* and *matched on species and style*, and the
every-character requirement entered in `3ababcd` with no spec citation. ADR-057 replaced it with a
membership check: a reference must be a synthetic train character, but a character with no eligible
partner carries no hard negative. **Both match rules are unchanged and relaxing them is now
explicitly out of bounds** — dropping species equality would teach the judge "different species
implies different character", a shortcut that cannot transfer to the donated held-out split.

> **What this costs.** Constructed training pairs drop from roughly 135 to roughly 18. It cannot
> reach the primary endpoint — constructed pairs are train-only, enforced by
> `manifest.py:validate_manifest`. If the training negatives prove too thin, the remedy is induced
> drift, already pre-committed at `PREREGISTRATION_OBJ4.md` §3.3 item 3. **Do not recover coverage by
> relaxing the match.**

### 4 · A preregistration contradiction nobody has resolved

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

Resolve the §2 contradiction (blocker 4) in a dated amendment. That part is paperwork and belongs here.

> **Blocker 3 lands here too.** As specified, `dataset_selection.json` cannot be authored at all:
> 26 of 30 synthetic train characters have no legal hard-negative partner. Settling that is an ADR
> plus a preregistration amendment, and it belongs in this step with the other paperwork — *before*
> step 08 spends the campaign budget on a corpus whose selection artifact cannot be written.

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

***DONE - 2026-09-03, `a723126`, $2.52 spent of a $2.63 authorization.***

Ran in three invocations into `../data/judge/corpus-smoke-g` and `-h`. What it bought:

| invocation | settings | result |
|---|---|---|
| smoke-g | `--limit 3 --max-usd 2.63 --max-calls-per-story 25` | **exit 2, $0.875, zero bundles.** syn-001 consumed all 25 calls and wrote nothing. All 25 provider calls succeeded. |
| smoke-h | `--limit 1 --max-usd 1.05 --max-calls-per-story 30` | **exit 0, $0.630.** syn-001 completed in 18 images, `regen_count` 6. |
| smoke-h | `--limit 3 --max-usd 1.68 --max-calls-per-story 15` | **exit 0, $1.015.** syn-001 skipped cleanly; syn-002 completed in 14; syn-003 `budget_stopped` at 15. |

What it settled, all of it folded into the MANDATORY FLAG block above:

- **cap 15 does not work** - it is why the first invocation returned zero bundles;
- **caps may differ between invocations** into one directory, so the campaign can be split;
- **cumulative spend is charged against the current `--max-usd`**, which is why the third
  invocation needed 1.68 rather than 1.05.

The smoke is spent. Do not re-run it - step 08 is the next paid action.

> **Quality findings are not budget findings.** The pages were scored against the expert
> instrument and two defects reproduce across stories. **Numeric attribute fidelity fails:**
> Quill's three eyes drawn as two, Mopsi's six legs drawn as four - with `"six legs"` stated
> *twice* in the description that fed the generator. **The reference judge does not catch it:**
> on syn-002 it listed `"six legs"` in `attributes_present` for a four-legged sheep and recorded
> `contradictions: []`. Neither is a code bug; neither is fixed by prompting. Related: ADR-028
> (reference failure made visible), ADR-018 (the planned judge fine-tune).
> **Both are unresolved going into the campaign.**
>
> Character consistency across pages *passes* on both stories - the ADR-007 reference-conditioning
> mechanism works. The instrument items at risk are B3/B4 and Question 4, not the recurring-character
> ones.

### 08 · The campaign — 45 stories, two commands, one ceiling

***Me · needs your $ authorization***

Same `--out`, same cap, same price basis on both. They are one campaign against one budget.

```bash
# 30 synthetic (24 train + 6 val)
uv run python -m finetune.build_corpus \
  --corpus finetune/corpus_synthetic.json \
  --out ../data/judge/corpus \
  --max-usd 25 --max-calls-per-story 19 \
  --price-per-megapixel 0.035 \
  --price-basis "<official price URL + date verified>"

# 15 donated (10 primary + 5 backup)
uv run python -m finetune.build_corpus \
  --corpus ../data/judge/intake/donated.json \
  --out ../data/judge/corpus \
  --max-usd 25 --max-calls-per-story 19 \
  --price-per-megapixel 0.035 \
  --price-basis "<official price URL + date verified>"
```

> **Budget:** 45 × 19 × $0.035 = **$29.93** absolute worst case, which is why `--max-usd 25` on
> both invocations is the working allocation and not the ceiling: it is the *shared* cumulative
> total across both, so a run that trends expensive halts at $25 with the $25–30 band still held in
> reserve for the extension pass. Expected actual is far lower — measured consumption is 14–18
> images per story, so ~45 × 16 × $0.035 ≈ **$25**. `--max-usd` is silently clamped to the $30 hard
> ceiling.
>
> If the main pass halts on budget rather than finishing, that is the design working: raise
> `--max-usd` toward 30 and re-invoke into the same `--out`. Completed stories are skipped, and
> cumulative spend carries over.

> **About the $0.035.** It is a deliberate over-reserve, not the price. Fal's published rates are
> **$0.03/MP** for scene edits (`qwen-image-edit-2511`) and **$0.02/MP** for references
> (`qwen-image`), both verified 2026-09-01 and recorded in every bundle's `price_basis`.
> `--price-per-megapixel` takes one scalar and it reserves the budget, so it carries the higher
> number: under-reserving overspends, over-reserving only halts early. The consequence is that
> **every cost this campaign reports is an upper bound, roughly 17% above what Fal actually bills** —
> say so wherever the figure is reported, and read the Fal dashboard for the real total.
> The `$0.02–0.035/image` in ADR-001 and PRD_v2 §15 is a **per-image** figure from a different
> provider comparison. It is not this flag's unit; do not reconcile the two.

---

**The sequence**

## Phase C — Label and freeze

> **Nothing in this phase has ever been executed.** As of 2026-09-03 the generation half is tested
> end to end (2 stories at `a723126`: cap behaviour, split invocations, resume-skip, cumulative
> budget accounting), and `materialize_pairs`, `build_dataset`, `dataset_selection`, `freeze_dataset`
> and `to_llamafactory` have not run against real bundles even once.
>
> That ordering is the risk: the campaign is a single indivisible ~$25 event, and a Phase C failure
> is discovered *after* the money is spent, when the repair may be a code change the freeze itself
> forbids (`code_commit` is pinned — see "Known gotchas").
>
> **Partly rehearsed 2026-09-03. It failed, and the blocker is now fixed.** `--candidate-report` runs
> clean on real bundles but returns zero candidates, and the selection validator hard-failed: see
> blocker 3 above and `docs/product/evidence/phase-c-rehearsal-2026-09-03.md`. ADR-057 resolved it,
> and the rehearsal now reports `PASS -- a valid selection exists` on an empty mapping, which is the
> correct outcome for this corpus.
>
> **Still unrehearsed: everything downstream of `dataset_selection.json`** — `freeze_dataset` and
> `to_llamafactory` — because the blocker sat upstream of them and the rehearsal stopped there.
> Finishing that is still free and still belongs before step 08.
>
> The module unit tests pass (144 across the five Phase C test files). What was missing was the chain
> against real generated data, which is where this surfaced.
>
> **Finish rehearsing before step 08, not after.** `--pilot` cannot contaminate the real dataset:
> pilot pairs are permanently excluded from training. Point it at a throwaway directory, never at
> the production corpus.

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

Spend as of 2026-09-03: **$2.52** on the paid smoke (step 07, authorized $2.63) plus **$0.19** on
the attribute-fidelity count probe. Sunk from earlier runs: ~$5.31, archived and unusable.
Remaining Fal credits: **~$1.87** — the campaign needs roughly $23 more.

# Objective 4 — campaign readiness audit and roadmap

**Date:** 2026-09-12, backlog rewritten 2026-09-14 · **Repo state:** PR #81 merged as `ad9fb0a` (2026-09-15), the segment fix (PR #82) as `059c416` (2026-09-16), the input_gate resume fix (PR #83) as `d6d1a98` (2026-09-16); the moderation-quarantine fix on `fix/corpus-moderation-quarantine` (2026-09-16) moves HEAD again before B6 · **Supersedes:** `OBJECTIVE_4_NEXT_STEPS.md` as the live guide

This replaces the 2026-08-30 runbook, which predates 54 commits and the arrival of the donated corpus.
Every number here was measured against the repo or the bundles on disk. Anything estimated says so.

---

## 0. For agents picking this up

This file is the live Objective 4 backlog. §4 is the ordered sequence: work it top to bottom, and
mark a step done here, with the date, in the same change that finishes it. Do not start a second
backlog or status file for Objective 4 (`AGENTS.md`, "The status surface").

- **Read with it.** `docs/capstone/research_runbook.md` holds the exact commands; §4 cites them by
  step number rather than copying them. `docs/product/PREREGISTRATION_OBJ4.md` binds the method
  (frozen; amendments are appended to §12, never edited in place). `docs/specs/labelling-rulebook.md`
  binds the labels.
- **Who does what.** `[YOU]` is the owner: dashboard clicks, paid runs, labelling, consent, adviser
  signoff. An agent never logs into Supabase, fal or a GPU host, never reads `backend/.env`, and never
  runs a paid command (`build_corpus` without `--check-rosters`, `train --execute`) unasked. `[ME]` is
  agent work.
- **Never:**
  - pass `--pilot` with `--data ../data/judge/corpus`;
  - commit donated stories or anything under `data/`;
  - add a second rater. Round 2 is the same person, cold;
  - hand-edit `build_state.json` or a bundle;
  - commit anything between B1 and the campaign's exit 0. A moved or dirty tree makes the two halves
    unfreezable (P4).
- **Where state lives.** Bundles, intake, freezes and evaluations are local under `data/judge/`
  (git-ignored). Supabase holds uploaded images (`private_assets`), the label queue (`research_pairs`,
  `annotations`, `profiles`) and LangGraph checkpoints. The freeze reads labels from Supabase and
  images from the local bundles (`freeze_dataset.py:256-299`); training and evaluation read neither.
- **A doc that disagrees with the code:** the code wins. Flag the drift here; never reconcile it
  silently.

---

## 1. Verdict

**B6 is done — 42 bundles for $30.100, logged in §7. What remains, in order: Phase C (C1 dataset
selection done, C2 seeds the queue, then the annotation rounds), and D1 (confirm the GPU's VRAM)
before Phase D.** P1–P7,
A6, A7, B1–B6, D2, Finding G and the labelling rulebook (Finding J) are done. Supabase has been on
Pro since 2026-09-14.

The pipeline works, the money path is understood, and the donated corpus arrived on 2026-09-12 —
15 raw stories at `data/judge/intake/raw/`, which retires the blocker that governed the last runbook.

**The dataset-design blocker is closed (2026-09-12).** As the code stood, the campaign would have
spent ~$25 to produce a training set whose `different_character` class was roughly 20 auto-labelled
pairs of obviously-different people, then measured it on real children's stories whose failure mode
is drift *within* one character — trained on the wrong thing. ADR-060 harvests the rejected attempts
the campaign already pays for, a measured 2.32× on scene images. Finding A carries the numbers.

**Single largest risk:** the campaign is one indivisible unrepeatable spend, and the dataset defects
are discovered downstream of it, where the repair is a code change the freeze forbids.

---

## 2. What changed since the last runbook

| Item | Then (2026-08-30) | Now (2026-09-12) |
|---|---|---|
| Donated stories | 4 of 15 — the critical path | **15 of 15 collected**, raw `.txt`, unredacted |
| Stage-1 consent | Unverified, "no retroactive fix" | Owner confirms wording is correct |
| `donated.json` | Not written | Written 2026-09-13; roster pre-flight 15/15 on two passes |
| Commits since freeze guidance | — | 54. Nothing is frozen; the tree is dirty right now |
| Hard negatives | Blocker, resolved by ADR-057 | Resolved, and the cost is now measured: ~20 pairs, not ~300–400 |
| Phase C rehearsal | "Never executed" | Wrong, and it hid a freeze-stopping bug — fixed, see Finding E |

---

## 3. Prerequisites

Ranked by what it costs to be wrong. `[YOU]` needs your decision or your hands; `[ME]` I can do.

### P1 · Harvest rejected attempts — `[YOU]` decided 2026-09-12, `[ME]` implemented · **done**

Settled as **harvest every rejected attempt, no `failure_reason` filter, all three splits**.
ADR-060, with the append-only preregistration amendment of the same date.

**The pool was measured, not projected**, by `docs/product/evidence/scripts/count_attempt_pool.py`
(USD 0, reads committed `memory.json` only). Across all 10 bundles: 65 finalized scenes hold **86**
harvestable rejects — 1.32 per scene, a **2.32× scene-image pool**.

Two numbers in the earlier draft of this section were wrong and the measurement corrects them:

- **"~180 images" was low.** It was read off filename suffixes, which undercount, because the
  pipeline finalizes on the best-ranked attempt rather than the last one — on 52 of 65 real scenes
  the final never passed at all. Annotation labour goes to roughly **2.3×**, not +40%.
- **"almost no hard negatives" overstated the skip case.** The natural negative class is not
  predictable from the judge's flags in either direction: `different_face` sits on 88% of rejects and
  6 of 151 attempts are `passed=True` while carrying failure reasons. The argument for harvesting is
  the train/test task mismatch (ADR-060 Context), not an empty negative class.

`different_face` filtering was rejected on that 88%: it barely bounds anything and selects by the
incumbent judge's own decision boundary, which on the held-out split would tilt the primary endpoint
toward the baseline the fine-tune is measured against.

Implemented in `finetune/manifest.py:scene_images`, imported by both `build_corpus.download_images`
and `build_dataset.pairs_from_memory` so the two cannot drift. Backend suite 1401 passed.

### P2 · Write `data/judge/intake/donated.json` — `[YOU]` attest, `[ME]` build — done 2026-09-13

**Blocks the campaign.** Nothing downstream runs without it, and it is where you make three
decisions that become degrees of freedom if made later:

- which 10 of 15 stories are **primary** (style slots are frozen: 4 gouache / 3 cel / 3 cut_paper
  primary, 1 / 2 / 2 backup — `corpus_io.py:302-310`)
- which style preset each story gets
- which characters are **declared non-human**, which is what assigns the slice
  (`freeze_dataset.py:206-210`)

Do this before generation, so the timestamps precede any result.

**Done.** You attested redaction with independent review, guardian consent and child assent for
all 15, none withdrawn, and approved the allocation. Ids `don-001`..`don-015` follow the raw file
order; `data/judge/intake/build_donated.py` holds the mapping and regenerates the file (git-ignored).
Primaries: gouache g5-s3, g6-s2, g6-s6, g6-s7 · cel g5-s1, g5-s6, g6-s8 · cut_paper g5-s2, g5-s4,
g6-s5. Backups: gouache g6-s4 · cel g5-s7, g6-s3 · cut_paper g5-s5, g6-s1.

Declared names are the extractor's own, verbatim, after four pre-flight runs. Only two non-human
characters survive into the reference slice (the goat, Bingo); the mango tree, imp and star never
rank in the top two. The slice is descriptive-only (P3 item 2), so this costs a count, not an
endpoint. Pre-flight found Finding I on the way.

### P3 · Resolve four preregistration items in one dated amendment — `[YOU]` decided 2026-09-12, `[ME]` drafted · **done**

All four were honest-scoping moves, free then and degrees of freedom the moment data exists. Settled
in the dated block appended to §12 (append-only; nothing edited in place).

1. **The §2 contradiction.** The table (`:104`) says Validation = Synthetic; the prose (`:117`) says
   "zero synthetic characters in validation or test". The table wins — the 2026-08-22 amendment and
   `freeze_dataset.py:116-118` both lock 6 synthetic validation stories. Record that "evaluation
   stimuli" means the held-out test set; validation is a development split.
2. **Demote secondary endpoint #2.** The non-human held-out slice will have 2–4 characters
   (Finding C). A clustered bootstrap over 3 clusters is not an interval. Pre-commit now that it is
   reported as a descriptive count with per-character results, not a CI.
3. **Fix the slice-source text.** `:261` says slices come from the Character Bible `species` field.
   The code reads intake `declared_non_human`. Code wins; the text is stale.
4. **Settle the test-set size.** §2 pre-commits that the 5 backups may enlarge the held-out set
   before labelling; `freeze_dataset.py:122` hard-required exactly 10. Finding B. **Decided: enlarge.**
   Backups serve fail-closed replacement first; every unspent one that is consented and whose run
   finalized then joins the held-out set, floor 10, 4/3/3 kept as a per-style floor. Admission is
   mechanical — `withdrawal_state` plus a completed bundle, never a property of the generated output.

Items 1–3 were documentation catching up to code. Item 4 changed code: `validate_donated_allocation`
in `dataset_selection.py` is now the one floor rule, imported by both the selection guard and
`freeze_dataset._validate_bundles`, so the pair cannot drift apart the way they did here. The
equality checks in both are gone. ~20 held-out characters becomes ~30, at no generation cost —
the campaign already runs all 15 donated stories — and roughly +50% annotation on the test half.

The speculative "report a CI anyway if the non-human slice reaches N characters" escape hatch was
drafted and then cut: the projection is 2–4, so the branch never fires, and a threshold nobody can
justify is worse than no threshold. A later dated amendment covers the case if it ever arrives.

### P4 · Clean the working tree and keep it clean — `[YOU]` · committed 2026-09-13 on `obj4-campaign-readiness`, merge before story 1

`_code_commit` (`build_corpus.py:82-95`) appends `-dirty` when `git status --porcelain` is non-empty,
and its own comment says this makes the bundle "unfreezable on its own". The tree is dirty right
now: as of 2026-09-13, 21 paths — the P1/P3/P6/P7 code and tests, the owner fix, ADR-060, the
amendment, and this doc. They must be committed (and ideally merged) before story 1, not discarded.

Worse than a dirty stamp: if that directory changes *between* the synthetic and donated invocations,
the two halves carry different `code_commit` values and `freeze_dataset._pinned_versions` rejects the
campaign permanently, on data you cannot regenerate.

```
git status --porcelain      # must print nothing before story 1
```

Then commit nothing at all until the campaign exits 0.

### P5 · Upgrade Supabase to Pro — `[YOU]`, ~$25/mo · **done 2026-09-14**

Upgraded 2026-09-14. Its dashboard checks are A6; the downgrade afterwards is Phase E.

Free tier does not hold this campaign. Measured and projected in Finding D: storage lands at
0.95–1.38 GB against a 1 GB limit, egress at 3.2–5.0 GB against 5 GB/month with annotation still to
come, and the free plan pauses projects after ~7 days of low activity — which is exactly the shape of
a multi-week labelling window. P1 adds a measured 2.32x on scene images on top of all three (ADR-060).

### P6 · Fix the annotation queue's row cap — `[ME]` · **done**

`annotate/actions.ts:118-121` selected every one of your annotation rows with no `.range()` and no
`.limit()`. PostgREST caps this at 1000 by default. Your projected rows are ~880 across two rounds
before adjudication, and P1's 2.32x pushes it past 1000 outright.

Past the cap the `labelled` set is silently short, an already-labelled pair is re-served, the insert
hits `23505`, and `:51-56` swallows it with a `console.log` and falls through. You would relabel pairs
and lose the labels, with no error shown.

Fixed: that select is now a paged loop. A test reproducing the truncation was red on the old code
(`expected 1 to be 2` — round 1 re-served) and is green on the new.

`adjudicate/actions.ts:207-210` runs the same unbounded select, and it is **not** the same bug. There
the set is only a pre-filter: an adjudicated pair leaves `status = conflicted`, and if that update
ever failed, the per-pair read at `:254` still sees the round-3 row and skips the pair at `:271`.
Left as is; a regression test now pins that backstop, and breaking `:271` turns it red.

### P7 · Finish the free Phase C rehearsal — `[ME]` — done 2026-09-13

`freeze_dataset` and `to_llamafactory` had run only on the fixture path, which returns early at
`freeze_dataset.py:107-110` and skips the production validation. Finding E. The rehearsal now runs a
production-shaped corpus (24 train + 6 val synthetic, 10 donated, `fixture=False`) through the whole
freeze and export, with and without a constructed negative. It found one bug that would have failed
the real freeze; fixed.

---

## 4. The roadmap

### Phase A — paperwork and fixes · no money

**A1 · Settle the attempt-harvest decision (P1). — done 2026-09-12.** Decided yes. ADR-060, the
append-only amendment of the same date, and `finetune/manifest.py:scene_images` shared by
`download_images` and `pairs_from_memory`.

**A2 · Hand-redact the 15 stories.** Substitute identifiers rather than deleting them —
`"Miguel" → "Andres"` keeps the voice. Keep your substitution list outside the corpus. Nothing
automated will touch donated text.

Three specific hazards found while reading them:

- `g5-s1` spells the protagonist "Marcos" once in paragraph 5 and "Markus" everywhere else.
- `g5-s4` has Erin address her cousin Klare as "Moana" in dialogue.
- `g5-s5` and `g6-s1` are first-person with **no named protagonist at all.** The extractor has to
  invent a name and your `declared_characters` must match it, case-insensitively.

**A3 · Build `donated.json` (P2). — done 2026-09-13.** I write it from what you attest. Declare **at most 2 characters
per story** — `corpus_io.py:93` mints canonical references for `memory.characters[:2]` only, and
`reconcile_declared_roster` hard-fails a declared name that lands outside that slice.

**A4 · Amendments (P3). — done 2026-09-12.** One dated block, four items, appended to §12. Item 4
also changed `dataset_selection.py` and `freeze_dataset.py`; backend suite 1404 passed.

**A5 · Fixes (P6 and P7 done).** Queue pagination is in. The production-shaped rehearsal through
freeze and LlamaFactory export passes. The fal retry (Finding G) and the checkpoint schedule (D2) are in; backend suite 1415 passed. Pre-merge
review (2026-09-14) found the bundle inventory listed only finals, so every harvested attempt failed
`materialize_pairs` with "missing pair asset"; `_assets` now uses `scene_images`, tested through `build`.

**A6 · Supabase dashboard pre-flight — `[YOU]`.** Pro is on (P5).

1. **Max rows → 5000** · **done 2026-09-14.** Integrations → Data API → Settings → Max rows. It is no longer under
   Settings → API, which now shows only the keys. Every reader pages since P6, so this is a second
   line of defence, not the fix.
2. **Storage → Buckets: confirm `private_assets` exists and is private** · **done 2026-09-14.** No
   migration creates it, yet `materialize_pairs.py:28` and `annotate/actions.ts:222` both require it.
   It already holds images from the 2026-08-27 → 09-03 smokes (the local `corpus-smoke-a`..`h`
   folders). Leave them: the campaign's new `--out` hashes to new
   folders (`build_corpus.py:592`), and they cost nothing on Pro. Phase E deletes them.
3. **Record current usage** · **done 2026-09-15.** Organization → Usage, not project Reports (that
   shows the last hour of requests). Baseline: storage 0.56 GB across both org projects
   (`private_assets` 48 objects, 20 MB), egress 0 GB, 2 GB disk provisioned per project, 46 Micro
   compute hours. The org also runs `daytrace`, a second project the $10 compute credit does not cover.
4. **Measure the checkpoint tables** in the SQL editor · **done 2026-09-15:** `checkpoint_blobs`
   10 MB, `checkpoint_writes` 6992 kB, `checkpoints` 2760 kB (~20 MB baseline).

```sql
select relname, pg_size_pretty(pg_total_relation_size(relid))
from pg_catalog.pg_statio_user_tables
where relname in ('checkpoints','checkpoint_blobs','checkpoint_writes');
```

**A7 · Clear the pilot data before any production pair exists — `[YOU]`, dry run first** · **done
2026-09-14:** the dry run printed `annotations=0 pairs=0 objects=0`, so nothing needed clearing. Re-run
the dry run if a pilot is ever seeded again. The 2026-08-30 rehearsal wrote pilot pairs and labels to
Supabase, some from a second account and a third adjudicator profile. The freeze drops pilot pairs, so they
cannot reach the dataset, but they break labelling:

- `/annotate` serves every `pending` or `partially_annotated` pair with no `is_pilot` filter
  (`annotate/actions.ts:170-175`). Leftover pilot pairs mix into round 1, and round 2 cannot open
  until they are labelled.
- `reconcile_pair_status` does not skip pilot pairs (`annotation_truth.py:141-160`). One pilot pair
  with more than two ordinary labels makes `--reconcile-only` (runbook step 7) fail for the whole
  queue.

```bash
cd backend
uv run python -m scripts.clear_research_pilot                                   # dry run: counts only
uv run python -m scripts.clear_research_pilot --confirm DELETE-RESEARCH-PILOT   # labels, then pairs, then research/pilot/*
```

Done when the dry run prints `annotations=0 pairs=0 objects=0`. It touches only `is_pilot` rows and
`research/pilot/` objects (`research-corpus-operations.md` §7). If the rehearsal's labels are cited
anywhere, export `annotations` to CSV before confirming. Label with one account from here on.

### Phase B — freeze the code, then spend

**B1 · Merge PR #81, then stop committing — `[YOU]`.** Merged 2026-09-15 as `ad9fb0a`, then reopened:
B5 found the segment crash below (fix merged as `059c416`), then the input_gate resume trap (merged as
`d6d1a98`, the HEAD B5 passed on), and B6's first attempt found the moderation stop (a fourth merge).
Redo these commands after that merge and record the new hash; it is the one both halves carry.
`syn-001` has no bundle from `d6d1a98`, so no bundle carries the older hash.

```bash
git switch main; git pull
git status --porcelain   # must print nothing
git rev-parse HEAD       # record it; both halves of the campaign must carry it
```

**B2 · Free roster pre-flight on all 45 stories.** · **done 2026-09-15:** synthetic
`{"checked": 30, "failures": []}`, donated `{"checked": 15, "failures": []}`, both exit 0. Not
re-run after the segment or input_gate fixes: `--check-rosters` calls `analyze` directly, and neither
fix touches it.

```bash
cd backend
uv run python -m finetune.build_corpus --check-rosters --corpus finetune/corpus_synthetic.json
uv run python -m finetune.build_corpus --check-rosters --corpus ../data/judge/intake/donated.json
```

Exit 0 required on both. Roughly 1 story in 30 fails extraction at random — rerun before concluding
anything is wrong. This is where a bad `declared_characters` guess surfaces, for a fraction of a cent
instead of a story's full image spend.

**B3 · Re-verify fal pricing and record the URL.** · **done 2026-09-15.** `qwen-image` $0.02/MP
(rounded up to the megapixel), `qwen-image-edit-2511` $0.03/MP. At 1024×768 (0.79 MP) every call
bills as 1 MP, so `--price-per-megapixel 0.035` stays a safe ceiling. `FAL_IMAGE_EDIT_MODEL` is unset
(owner-confirmed), so the default edit model runs; `fal-ai/omnigen-v2` is $0.15/MP and would break
every cap. Use this string on B5 and B6, single-quoted in PowerShell so `$` is not expanded:
`https://fal.ai/models/fal-ai/qwen-image ($0.02/MP) + https://fal.ai/models/fal-ai/qwen-image-edit-2511 ($0.03/MP) (verified 2026-09-15)`

**B4 · Pin the machine.** · **done 2026-09-15.** Run locally — see Finding F for why not Northflank.

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 0
```

Sleep kills the single port-5432 connection held for the whole run, and there is no reconnect path.

**B5 · Fresh 3-story smoke at the real cap.** Use a **new** `--out`; a reused directory carries a
different thread digest and a different ledger. Command: runbook step 2. Before B6, check each
bundle's `attempted_calls` (bundle metadata, `build_corpus.py:517`) is at or under 19.

First attempt, 2026-09-15/16, `--out ../data/judge/corpus-smoke-b5`: exit 1 twice on `syn-001` with
`ValueError: segment: unknown object 'weathervane'`, zero images drawn. The story's weathervane is the
character Bok-Bok, so `analyze` rightly listed no such object, but the segmenter named one, and at
temperature 0 it did so on every run. A bare `ValueError` is neither `RosterMismatch` nor
`CorpusError`, so `build_corpus.py:1169` re-raised it and would have ended B6 on story one. Fixed
2026-09-16: `segment` drops and logs an object name outside the roster, as `analyze` does for unknown
owners (Finding I). Re-run B5 on the new HEAD with a fresh `--out` (`corpus-smoke-b5b`); the old
folder's checkpoint predates the fix. Before B6, also compare fal and OpenRouter balances around the
smoke (2026-09-15: fal $25.94, OpenRouter $7.32) and check average `attempted_calls`: above ~15.8 per
story, 45 stories exceed the 714 calls `--max-usd 25` buys at $0.035.

Second attempt, 2026-09-16, HEAD `059c416`, `--out ../data/judge/corpus-smoke-b5b`: exit 1 at
`input_gate`, zero spend. The text backstop `openai/gpt-oss-safeguard-20b` got a 429 from Groq's
shared pool. `input_gate` returned `moderation_error` as a failed result and the router raised after
it, but LangGraph kept that write, so the same-`--out` resume ran nothing, "completed" with
`characters=[]` and quarantined `syn-001` as `invalid_terminal` (checkpoint history: step 0
`input_gate` errored, step 1 `next=()`). Every story makes this call once, so any 429 that outlasts
the client's 2 retries would have halted B6 and spent that story's single readmission. Fixed
2026-09-16: `input_gate` raises inside the node, as `char_ref_mod` and `output_mod` already did, so a
resume calls the backstop again. Re-run B5 on the new HEAD with `--out corpus-smoke-b5c`; `b5b` holds
the dead thread.

Third attempt · **passed 2026-09-16**, HEAD `d6d1a98`, `--out ../data/judge/corpus-smoke-b5c`: exit 0,
3 stories, 0 quarantined, telemetry 50 attempted / 50 completed, `usd_high` 1.750. `attempted_calls`
18, 16, 16 (average 16.7, above the 15.8 that `--max-usd 25` affords). Balances fal $25.94 → $24.60,
OpenRouter $7.32 → $7.30: **$0.027 per image call measured**. B6 therefore runs `--max-usd 28`: the
reserve check (`build_corpus.py:1062-1064`) would halt a 16.7-call average near story 42 at 25, and 28
allows at most 800 calls, which at the $0.03 edit price is $24.00, inside the fal balance.

**B6 · The campaign — 45 stories, one budget.**

```bash
# 30 synthetic (24 train + 6 val)
uv run python -m finetune.build_corpus \
  --corpus finetune/corpus_synthetic.json \
  --out ../data/judge/corpus \
  --max-usd 25 --max-calls-per-story 19 \
  --price-per-megapixel 0.035 --price-basis "<URL + date verified>"

# 15 donated
uv run python -m finetune.build_corpus \
  --corpus ../data/judge/intake/donated.json \
  --out ../data/judge/corpus \
  --max-usd 25 --max-calls-per-story 19 \
  --price-per-megapixel 0.035 --price-basis "<same string>"
```

Rules that are not optional:

- **`--out` must be byte-identical on every invocation and every resume.** `_campaign_thread_id`
  (`build_corpus.py:592`) hashes the *resolved absolute path*. A different path is a different
  LangGraph thread and a from-scratch re-run.
- `--max-usd 25` is the **cumulative** total across both commands, not per command.
- **Exit code 2 is a failure**, not a warning — the JSON summary on stdout still looks clean. Read
  stderr. Only exit 0 is a finished campaign.
- **Check on it periodically.** Finding G: transient fal blips now retry, but a hard fal failure or a
  600s timeout still quarantines that story and exits 1.
- **A moderation verdict quarantines one story; it no longer stops the run.** First attempt,
  2026-09-16, HEAD `d6d1a98`, `--max-usd 28`: exit 1 on `syn-001` after 17 image calls. The image
  backstop (gemma-3-27b) flagged scene s3 on the draw and on the softened redraw; the NSFW primary
  said safe, and the same scene passed in B5. `build` re-raised the router's
  `output_moderation_failed`. Fixed 2026-09-16: `content_flagged`, `ref_flagged` and
  `output_moderation_failed` quarantine the story `invalid_terminal` and the campaign continues;
  `moderation_error` (a classifier that could not answer) still stops it. The freeze needs all 30
  synthetic stories, so **readmit every moderation quarantine** after the run, and each story can be
  readmitted only once. A resumed thread does not re-raise: LangGraph applies the node's saved write
  and returns "completed", and `_bundle` checks only id, style and roster, so `syn-001` would have
  bundled with s3 empty and s4–s5 never drawn. `run_story` now asks the graph's moderation routers
  about the final state before calling it completed. Re-run the same B6 command: `syn-001`
  quarantines with zero new spend and the campaign continues; readmit it afterwards.
- **A story that hits 19 halts the campaign; resume it alone with a higher cap.** Second attempt,
  2026-09-16, HEAD `1ddf1ce`: `syn-001` quarantined with zero new spend, `syn-002` and `syn-003`
  bundled, and `syn-004` stopped `budget_stopped` at 19 calls with s5 (of 6 scenes) on its second
  draw; nearly every scene took all three draws. `--extend-story-call-cap` refused it
  (`build_corpus.py:805-816` requires an isolated `execution_id`), contrary to
  `research_runbook.md:155`. What worked, zero-loss: `--limit 4 --max-calls-per-story 22
  --resume-quarantined syn-004` without the extension flag; it bundled at 20 calls. That bundle
  records a cap of 22 and no `initial_max_calls_per_story`, so this line is the only record the cap
  was raised from 19. Repeat that shape (`--limit` up to the halted story) for each later halt, then
  rerun the plain B6 command. Two OpenRouter 429s on the text backstop stopped this attempt as
  `moderation_error` with zero spend; a 30-minute wait cleared them.
- **An unknown character no longer ends the run.** Same attempt: `segment` raised
  `ValueError: segment: unknown character 'the other cranes'` on `syn-005` (roster: Pipit) before any
  image, identically at temperature 0. Fixed 2026-09-16: `segment` drops and logs a character name
  outside the roster, as it already did for objects. Redo B1 on the merge, then rerun the plain B6
  command.
- **An upstream error sent as HTTP 200 is retried.** Third attempt, 2026-09-16, HEAD `c1f0557`:
  `syn-005` and `syn-006` bundled, then `syn-007` exited 1 three times at `analyze` with
  `TypeError: 'NoneType' object is not iterable`, zero images. A replay through `structured_text`
  captured the body: status 200, `{"error": {"message": "Provider timed out after 6356ms", "code":
  504}}`, no `choices`. DeepInfra, the only provider `TEXT_PROVIDERS` allows (`providers.py:92-98`),
  timed out on four of five calls; the SDK retries on status only. Fixed 2026-09-16:
  `_fetch_completion` asks again up to three times inside `_bounded`, then raises a `RuntimeError`
  naming the model. Redo B1 on the merge, then rerun the plain B6 command.
- **A fal content flag quarantines the story; the campaign continues.** Fourth attempt,
  2026-09-16, HEAD `ce7f8d5`: `syn-007` passed `analyze`, then `char_bible` drew 4 references and
  the 4th, a "transparent, see-through" sprite that had passed twice, came back HTTP 422 "flagged
  by a content checker". `_run_fal` recorded every exception `failed_uncertain`, so `build`
  quarantined `billing_uncertain` and exited 1. The owner's fal dashboard showed request
  `01a0a6b4-302a-7c00-9274-df4debe36e1f` at cost $0.00; balance $21.74 afterwards. Fixed
  2026-09-16: that 422 is recorded `failed` and the story is quarantined `invalid_terminal` like a
  moderation verdict; any other 422 stays uncertain. Recover `syn-007` with
  `--restart-quarantined syn-007 --acknowledge-uncertain-billing syn-007` (a fresh thread gets its
  own 19-call allowance; the old one saved no references), and readmit it at the end if it is
  flagged again.
- **B6 is complete and logged in §7.** Finished 2026-09-17: **42 of 45 bundles — all 30 synthetic
  and 12 donated — for $30.100**, exit 0, no synthetic story quarantined. don-006, don-013 and
  don-015 stay quarantined on purpose; the donated held-out set is a floor and 12 clears it. What
  broke, what was decided and why, and the measurements worth citing in the defence are all in §7 —
  read it before running a campaign of this shape again.

### Phase C — label and freeze

**C1 · Author `dataset_selection.json`** — **done 2026-09-17**, by
`docs/product/evidence/scripts/author_selection.py`, which applies two rules fixed before any yield
was inspected and refuses to overwrite an existing selection. Written by script rather than by hand
because ADR-057 Decision 3 forbids a selection decision made *after* seeing the achieved count, and
a committed rule is how that stays checkable. `selection_sha256` =
`8ca8f94e9dff9bbba0ad3f425a65385f7c58357a4ade754ebb9f1a867cda9f90`.

- **Hard negatives: 14 matches over 44 synthetic train references**, each reference taking the first
  target in `candidate_report`'s own lexicographic order. The other 30 carry none, which ADR-057
  Decision 1 makes legal. Achieved constructed train pairs: **104**, against 380 natural train pairs
  — reported, not targeted. ADR-057 projected ~18; the ADR-060 harvest is why it is six times that.
  Only humans and one tortoise pair collide within a style, exactly as the ADR predicted.
- **Donated: all three replacements were forced, not chosen.** don-006, don-013 and don-015 are
  *primaries*, and a primary with no bundle fails the freeze unless replaced by a same-style backup.
  cel had exactly two spare backups for its two missing primaries and gouache exactly one, so the
  pairing consumed every backup of those styles and the selected set is identical under any
  ordering. The two cut_paper backups enlarge the held-out set. Final: 12 donated, cel 3 /
  gouache 4 / cut_paper 5, floor cleared on every style.
- Both freeze guards accept it: `select_dataset_bundles` returns 42 bundles (24 train / 6 val /
  12 test) and `validate_hard_negative_matches` passes all 14.

**C1a · Count narrative-change pages** — **done 2026-09-17**, report only, selects and excludes
nothing (§9.7). `docs/product/evidence/scripts/count_narrative_changes.py`, free and read-only.

Of **104 finalized donated scenes, 3 (2.9%)** have a visual direction that *names* an age or costume
change — and one of those, don-014:s6, is a false positive (the "younger cousin" is a second
character, not Lily at another age). The real count is **2, both don-007**, where Iris puts on a
firefighter uniform. A further **4 (3.8%)** imply an age gap without naming it, all in don-011:
three "future" scenes and `s8`, "Ana's daughter". Those four are the Finding J case exactly —
`build_prompt` sends the frozen reference and the visual direction, never the story text, so the
generator draws child-Ana on all of them and the rater labels what the image shows. **Finding J's
"smaller than first written" reading is confirmed on the real corpus**: at most 6 of 104 pages carry
a narrative change of any kind, and only 2 reach the image model.

**C2 · Seed the queue** — **done 2026-09-17**: `{"pairs_inserted": 795, "skipped": 0,
"uploaded": 1590}`, matching the offline preflight exactly. A7's dry run printed
`annotations=0 pairs=0 objects=0` immediately before, so nothing pre-existing mixed in. Queue
verified read-only afterwards: 795 rows, 380 train / 86 val / 329 test, every row
`is_pilot=false` and `is_constructed_negative=false`.

659 MB uploaded across 1,590 objects, of which only **93.6 MB is distinct content** — the reference
PNG is re-stored per pair under `research/corpus/<pair_id>/a.png`, so ~50 references become 795
copies. Harmless against Pro's 100 GB and it keeps each pair self-contained, but it is why the
storage figure is 7x the corpus.

**`research_pairs.char_id` holds the story-local id (`c0`, `c1`), not the lineage id**, so a
`SELECT DISTINCT char_id` over the queue returns 2 and looks alarming. It is inert: the annotation
UI strips `char_id` and never renders it (`annotate/actions.test.ts:341`), `annotation_truth` does
not read it, and §3.2's character-level split discipline runs on the manifest, where `build_records`
qualifies it through `lineage_id`. Recorded so nobody re-derives the scare.

Never pass `--pilot` — pilot pairs are permanently excluded from training.

**C3 · Round 1** at `/annotate`, blinded, every pair once, one account. Read
`docs/specs/labelling-rulebook.md` first; it does not change after this. **Started 2026-09-21.**

The first pair exposed a rulebook gap. The reference draws the eyes as dots, and the page draws them
with whites and pupils on a surprised face. Different Face counts "eye style" and excludes
"expression", and neither rule settles which covers this case. Per the rulebook it got the closest rule
and a line in the rater's private notes (`data/judge/annotation-notes.md`, gitignored), not a new rule.
Expect it to recur. The write-up should report it as a known ambiguity.

**Known generator limitation: duplicated characters.** Some pages draw the referenced character twice.
One page adds a translucent, ghost-like copy. This is a known failure of diffusion edit models,
including Qwen-Image-Edit: the reference subject is repeated or a faded copy is left behind. The
corpus includes rejected draws on purpose (ADR-060), so failed pages are overrepresented, and those
pages are what the judge has to learn to catch. **These pairs stay in the queue.** Removing them now
would be a selection decision made after seeing the data, which ADR-057 Decision 3 forbids. The
rulebook covers the plain case: Step 1 compares the best-matching figure, and a duplicate is not an
identity failure. Broken Anatomy applies only when the copy is fused into the character (merged or
duplicated body parts). The translucent copy is the unclear case: it takes the closest rule and a
line in the rater's notes. **No field records a duplicate**, so the rater's notes tally is the only
count the write-up will have. Keep it.

**Incident, 2026-09-21: two extra raters.** Two groupmates labelled on their own researcher accounts
before this was caught: **42 round-1 rows** (15 from `c4f346f6`, 27 from `d9a03bf8`), written
06:13–06:31 UTC. A read-only check found no pair labelled by more than one account, and the queue
intact at 42 `partially_annotated` and 753 `pending`. The owner first chose to keep one rater. The harm had not
happened yet, but it was close: `submitAnnotation` counts every row on a pair, whoever wrote it
(`annotate/actions.ts:62-98`). A second account's label on the same pair marks it
`complete`/`conflicted` and removes it from the queue, and the freeze then reads two people's labels
as one rater's two rounds.

**Decision, 2026-09-21: two raters, the owner adjudicates.** The owner chose to finish labelling now
rather than stop the groupmates. A read-only check at 07:56 UTC found 342 labels, all round 1, all from
the two groupmate accounts (172 from `c4f346f6`, 170 from `d9a03bf8`), no pair holding both, and none
from the owner. This deviates from the 2026-08-29 amendment ("one rater… there is no second"). It uses
the two-annotator path that amendment kept as a contingency:

- Each groupmate labels every pair once, in round 1. The queue already serves each of them the pairs
  the other has labelled, so a pair ends with one label from each: `complete` or `conflicted`.
- **Whoever finishes first stops when the screen says Round 2.** Round 2 opens for an account once it
  has no round-1 pair left, and a round-2 label would give a pair two labels from one person while the
  other is still working. The same holds if either stops early: the other must not go on to Round 2.
- The owner labels nothing on `/annotate`. Once both are done, the owner's profile gets
  `is_adjudicator = true`, and the owner resolves `conflicted` pairs at `/adjudicate` through the
  distinct-adjudicator path (`adjudicate/actions.ts`, `annotation_truth.is_adjudication`). An
  adjudicator cannot open `/annotate`, which here is what we want.
- The freeze is annotator-agnostic: two ordinary labels per pair, and the adjudication wins a
  conflict. `annotation_agreement.jsonl` then holds the two groupmates' labels, so the number
  `evaluate.py` reports as `intra_rater_agreement` is **inter-rater** agreement. Report it under that
  name. Test–retest reliability is not measured.
- 342 labels were made under the old in-app guide, which left out rulebook Step 3 (see below). The
  rest follow the guide in PR #93 once it deploys. Report the batch boundary.
- Reconcile expectations change: after labelling, complete + conflicted = 795 with `pending` and
  `partially_annotated` both 0. After adjudication, complete + adjudicated = 795.

This needs a dated deviation in `PREREGISTRATION_OBJ4.md` before the freeze.

*Their labels read against the rulebook, 2026-09-21.* A row check flagged 12 of their labels as
breaking a rule: 11 were Different with only Wrong Clothing or Wrong Style (Step 3 says that is always
a mistake), and 1 was Character Absent with Broken Anatomy ticked. Five of the 12 are test pairs and
were deleted unopened. The seven train and val pages, looked at beside their references:

- Five show a real change the rulebook deliberately does not count. One page is drawn in pixel art
  against a flat vector reference. Three cloud pages trade the crayon texture for a glossy, outlined
  render. One teacher's shirt lost its pocket. Face, colours and body features match in all five,
  and the other visible changes are expressions. The groupmates named what they saw correctly; the
  rulebook maps it to Same.
- One page draws the cloud twice in the reference's own style. It was labelled Wrong Style,
  presumably the nearest box, because there is no duplicate reason. Step 1 says compare the better
  match, and that match is Same.
- One page may be a real Different labelled with the wrong reason. The boy's hair reads paler
  (orange-brown to blond) and the face is drawn differently, but only Wrong Clothing was ticked.

So the rule that failed is Step 3. The labels were not careless. The in-app guide listed Wrong
Clothing and Wrong Style as drift reasons, with nothing saying they are not identity on their own,
and it had no Step 1, Step 3 or Step 4. That is fixed in PR #93:
the guide now carries the rulebook's rules, and the screen warns, without blocking, when Different
rests on Clothing or Style alone. No rule changed; the screen now states the frozen rules.

Step 3 also says "References and pages share one style preset". The pixel-art page shows that is not
always true: the generator sometimes drifts out of the preset. That is a generator failure the judge
cannot score, because style is not identity. It needs a line in the write-up's limitations, not a
new rule.

*Superseded for this campaign by the 2026-09-21 decision above: no round 2, and C5 adjudicates
the two groupmates' conflicts.* **C4 · Round 2**, same person, cold. This is test–retest reliability, not a second annotator. There
is no annotator 2 in this design. **Leave a real gap — a fortnight, not an evening.** Nothing in the
database can tell the difference, and the measurement is only as good as the gap.

**C5 · Round 3 adjudication** at `/adjudicate`, on pairs where your own two rounds disagreed.

**C6 · Reconcile and freeze** (runbook steps 7 and 8). The freeze also writes the LlamaFactory
files. Stay on Supabase Pro until Phase E.

#### What makes C3–C6 reliable, read from the code on 2026-09-21

- **Round 2 opens by itself.** `getNextPair` (`annotate/actions.ts:157-199`) serves round 2 once
  round 1 covers all 795 pairs, in the same session, with no confirmation. The only signal is the
  badge changing from `ROUND 1` to `ROUND 2`. **Stop when it changes**, or the gap is gone. A round-2
  label cannot be deleted: there is no update or delete policy (`0018_annotation_rounds.sql`).
- **Round 2 served pairs in exactly round 1's order. Fixed in PR #93 (first opened as #92),
  which must be merged and deployed before C4.** The per-rater shuffle hashed `p.id + user.id`
  (`annotate/actions.ts:206`) without the round. So round 2 would have opened on the same pair round 1
  opened on, the one this section's first paragraph describes. The round now goes through a nonlinear
mix after the hash. Appending it to the hashed string was tried first, and the test showed it did
nothing: the polynomial hash is linear, so a shared suffix shifts every value equally. Labels
  are unaffected. Only the order of the pairs still waiting changes, including round 1's remaining
  ones, which is harmless.
- **Labels are immutable, so a misclick is fixed only by disagreement.** A round-1 mistake stays in
  the table. If round 2 answers differently, the pair goes to adjudication, and that is the only
  correction path. Check before you submit, above all for Different with only Clothing or Style
  ticked. The screen accepts it, and the rulebook says it is always wrong.
- **A conflict is any difference, not only Same versus Different.** `isConsensus` and
  `annotation_truth._signature` compare the verdict, the full set of reasons and both checkboxes. A
  pair labelled Same twice but with Text Visible ticked only once goes to C5. Expect C5 to be larger
  than the Same/Different disagreement rate suggests.
- **The reliability number is narrower than the labels.** `annotation_agreement.jsonl` records only
  `same_character` for each round (`freeze_dataset.py:201-217`). `evaluate.py:1391-1440` reports
  Cohen's kappa and percent agreement on **test-split pairs only** (329), split human/non-human.
  Reason-level agreement is not computed anywhere. It is recoverable from E2's CSV export if the
  write-up wants it. Adjudication writes a new round-3 row and never changes rounds 1 and 2, so it
  cannot inflate the statistic.
- **Do not look at round-1-versus-round-2 agreement until round 2 is finished.** Seeing it would
  make round 2 less cold.

Progress checks, all `uv run python -m finetune.build_dataset --reconcile-only` (runbook step 7;
it rewrites only the derived `research_pairs.status` cache):

| After | Expected `statuses` |
| --- | --- |
| C3 | `partially_annotated: 795` |
| C4 | `complete + conflicted = 795` |
| C5 | `complete + adjudicated = 795`, `conflicted: 0` |

The freeze refuses to run until every pair has two ordinary labels and every conflict has an
adjudication (`resolve_annotations` raises `ManifestError`).

**Export.** C6's freeze (runbook step 8, `--out ../data/judge/freezes/obj4-v1`) is the dataset
export. `train.json`, `val.json` and `dataset_info.json` are LlamaFactory's input. The
`manifest.{train,val,test}.jsonl`, `annotation_agreement.jsonl` and `character_slices.json` files are
what `evaluate.py` reads. The held-out split is `manifest.test.jsonl`. It must stay unopened, and
the runbook's "`test.json`" names a file the freeze does not write. The folder is immutable, and a change means
a new `obj4-v2`. Per-round reasons and timestamps are not in the freeze, so export them separately
(E2).

### Phase D — train and evaluate

**D1 · Pick the GPU.** Your current laptop cannot do this: RTX 3050 Ti, 4 GB VRAM. Qwen2.5-VL-7B at
4-bit is ~5 GB of weights before activations or the vision tower.

The 4060 Ti is viable if it is the **16 GB** variant. At 8 GB it is marginal for a 7B VLM QLoRA —
image tokens make activations expensive, and you would be fighting OOM with gradient checkpointing
and a reduced image resolution, which changes the thing being measured. Confirm which card it is
before planning around it. Reducing resolution is not an option: `image_max_pixels` is a §10 pin.
Unless the card is the 16 GB one, rent a 24 GB GPU (RTX 4090 on RunPod or Vast.ai,
`judge-finetune.md` §6.2) for the three seeds. That money is **outside** the $25/$30 generation ceiling.
Budget disk for ~15 checkpoints per seed after D2.

**D2 · Checkpoint schedule — done 2026-09-14.** `train_qlora.yaml` pinned `eval_steps: 50` and never
set `save_steps`. 24 training stories give ~60–150 optimizer steps over 3 epochs (the range is the
achieved harvest), so a seed left one to three `checkpoint-*` directories, and §9.5's selection by
validation F1 had almost nothing to choose from. Now evaluated and saved every 10 steps, pinned in
the YAML and `train.FIXED_CONFIG_PINS`; a sparse schedule fails preflight (test red before the pin,
green after). Dated amendment §12, 2026-09-14. Epochs, learning rate, batch × accumulation and rank
are unchanged.

**D3 · Three seeds, threshold lock on validation, then the single guarded held-out run.** Detailed
steps 9–15 are in `docs/capstone/research_runbook.md`.

### Phase E — back up, clean up, downgrade Supabase

Safe once C6's freeze folder is backed up, and it can run alongside Phase D: the freeze copies every
image from the local bundles into its own `assets/` (`freeze_dataset.py:291-299`), and `train.py` and
`evaluate.py` never call Supabase. Back up before deleting. If the ethics approval sets how long
donated data is kept, it overrides this phase.

**E1 · Back up `data/judge/` — `[YOU]`.** Corpus, intake, freezes, evaluations and the selected
checkpoints, to a private second drive. It contains the donated stories: never git, never a shared
link.

**E2 · Export the label tables — `[YOU]`.** Table Editor → `annotations`, `research_pairs`,
`profiles` → Export → CSV. The freeze keeps resolved labels and each round's same/different answer
(`annotation_agreement.jsonl`); every per-round failure reason and timestamp exists only in these
tables.

**E3 · Delete the campaign's Storage objects — `[YOU]`, dashboard.** In `private_assets`: `research/`
(`materialize_pairs.py:109-110`) and every folder named after a story ID — `syn-*`, `don-*`, `fix-*`,
with or without a `--campaign-<hash>` suffix, smoke folders included. Leave every UUID-named folder
and anything unrecognised: app storybooks live under the job UUID (`worker/run_job.py:191`,
`generate_scene.py:33`, `char_bible.py:259`). Storage files cannot be removed by SQL
(`storage.protect_delete`).

**E4 · Delete the campaign's checkpoint rows — `[YOU]`, SQL editor.** They hold story text, donated
stories included. App threads are job UUIDs, so the filter excludes them. Run the preview first; only
story IDs should appear.

```sql
select thread_id, count(*) from checkpoints where thread_id !~ '^[0-9a-f-]{36}$' group by 1;
delete from checkpoint_writes where thread_id !~ '^[0-9a-f-]{36}$';
delete from checkpoint_blobs  where thread_id !~ '^[0-9a-f-]{36}$';
delete from checkpoints       where thread_id !~ '^[0-9a-f-]{36}$';
```

Then, as a statement on its own, `vacuum full checkpoints, checkpoint_blobs, checkpoint_writes;` —
a delete alone does not shrink the reported database size.

**E5 · Check usage, then downgrade — `[YOU]`.** Usage must sit inside the Free quotas: 1 GB storage,
and the database limit on the current pricing page. Then Billing → change plan → Free. **Keep the label
tables:** re-running C6 reads them. A Free project pauses after ~7 days idle; restore it from the
dashboard before any re-freeze.

---

## 5. Findings

### A · The pipeline generates the missing training data and discards it

**Measured on the real bundles at `data/judge/corpus-smoke-h`:**

| Story | Scenes | Attempts | Rejected | Rejected with a durable Storage path |
|---|---|---|---|---|
| syn-001 | 5 | 12 | **9** | 9 |
| syn-002 | 5 | 11 | **6** | 6 |

7.5 rejected images per story. Each is an image of the *correct* character that drifted, and each
carries the judge's own structured reasons. A real sample:

```json
{"image_ref": "syn-001--campaign-.../s0-1.png", "passed": false,
 "failure_reasons": ["wrong_body_feature", "different_face"]}
```

`Attempt.image_ref` is a durable Storage path (`contracts/story_memory.py:185`). But
`download_images` (`build_corpus.py:313-322`) pulls only `canonical_ref_image` and `final_image_ref`,
and `pairs_from_memory` (`build_dataset.py:101-115`) walks only `scene.final_image_ref`. Rejected
attempts never enter the bundle and never become pairs.

**Why this is the finding that matters.** There is no natural cross-character negative anywhere in
the code — `pairs_from_memory` only pairs a reference with a scene that character is *in*. So the
entire `different_character` training class comes from ~20 auto-labelled constructed pairs
(Marisol/Nonoy, Ate Rina/Lala — trivially different people) plus whatever drift survived a retry loop
whose purpose is to eliminate drift.

The held-out test set is real children's stories where the failure mode is drift *within* one
character. Training on "obviously a different person" and testing on "same girl, wrong hair" is a
transfer gap by construction.

**Measured 2026-09-12, superseding the estimate this section first carried.**
`docs/product/evidence/scripts/count_attempt_pool.py` counts the real pool across all 10 bundles:
65 finalized scenes hold **86** discarded attempts, 1.32 per scene, a **2.32x scene-image pool** at
no extra generation cost. The earlier "~180" was read off filename suffixes and undercounts, because
the pipeline finalizes on the best-ranked attempt, not the last one.

**Caveats, all real:**

1. They cannot be auto-labelled. The judge rejected them and the judge is the thing being replaced
   (ADR-034, plus the measured finding that no off-the-shelf VLM grounds attributes). Training on its
   verdicts is circular. These go through human annotation like every other pair.
2. That roughly doubles your labelling workload. This is the main cost.
3. ~~Train split only~~ — **this was wrong, and ADR-060 D3/D4 corrects it.** §3.3 item 3 confines
   *deliberately induced* drift to train; harvested rejects were drawn at unmodified production
   settings, so it does not reach them. They are pipeline pairs and enter all three splits. The judge
   is deployed on candidates (`consistency_check.py:296`), so sampling only finals was itself the
   departure from the deployment distribution.
4. Needs an ADR and a dated amendment before annotation begins. **Done:** ADR-060 and the
   2026-09-12 amendment.
5. Cleanest if `download_images` changes **before** the campaign. A later harvest is possible —
   `memory.json` preserves the paths, and `code_commit` only requires bundles to agree with each
   other, so committing after all generation is safe — but it depends on those PNGs still being in
   Storage and costs a second egress pass.

This is arguably the pre-committed remedy at `PREREGISTRATION_OBJ4.md:149` arriving by a better
route. That clause exists to harvest natural negatives; this is natural drift from the deployment
distribution rather than artificially weakened conditioning. Note that induced drift as written —
weaker conditioning, higher temperature — **is not implemented**: `build_corpus.py` has no such flag
(`:1269-1297`) and nothing in `backend/finetune/` references it.

### B · The code blocks a test-set power gain the preregistration already granted — **resolved 2026-09-12**

`PREREGISTRATION_OBJ4.md` §2 pre-commits: *"Backup stories (5) may be used to enlarge the held-out set
before labelling begins."* `methodology.md:567` repeats it as the stated mitigation for low
Objective-4 power. `judge-finetune.md:296-315` sizes the test set assuming **15** donated stories.

`freeze_dataset.py:122` hard-requires donated bundles to equal exactly
`{gouache: 4, cel: 3, cut_paper: 3}` — 10 stories. `select_dataset_bundles`
(`dataset_selection.py:183`) admits primaries plus approved replacements only.

At ≤2 canonical references per story that is ≤20 test characters instead of ≤30. Power is
bootstrapped **by character** (`PREREGISTRATION_OBJ4.md:255-257`), so this is a ~50% swing in the
resampling unit of your primary endpoint.

**Resolved** by P3 item 4 and the 2026-09-12 amendment: both equality checks became floors, and
unspent backups enter the held-out set under a mechanical consented-and-finalized rule. The cost is
annotation, not generation — B6 runs all 15 donated stories either way.

### C · The non-human slice is not measurable

Counted across the 15 raw donated stories: **21 human, 1 non-human** named character (Bingo, `g6-s5`)
out of 22. Widening to unnamed agentive non-humans gives 6 candidates — the goat, the talking mango
tree, the imp, the star, Bingo, the red shoes — and every one sits behind a human protagonist
competing for one of only 2 reference slots. Only 10 of 15 stories reach the test set.

**Realistic count: 2–4 non-human test characters.** A clustered bootstrap over 3 clusters does not
produce an interpretable interval. Demote the endpoint now, before you see the data (P3 item 2).

**The related structural fact, stated plainly because a reviewer will compute it:**

| | Synthetic train | Synthetic val | Donated test |
|---|---|---|---|
| Stories | 24 | 6 | 15 raw / 10 primary |
| Mean words | **153.3** | 153 | **312.7** |
| Non-human share of characters | **83% (25/30)** | 22% (2/9) | **~5% (1/22)** |
| Projected scenes/story | 5 (measured) | 5 | 9–10 (`MAX_SCENES = 10`) |

Train and validation were written to two different specs — validation resembles the test set,
training does not. Put this in your limitations section with the numbers. A reviewer who derives it
independently reads it as something you missed; a reviewer who reads it in your own limitations
reads it as a constraint you understood.

**Do not fix this by rewriting the corpus.** It is frozen by the 2026-08-22 amendment, editing it
changes `intake_sha256`, and doing it after seeing smoke outcomes is outcome-directed selection that
ADR-057 already rejected on these grounds.

### D · Supabase free tier does not hold this campaign

Measured from the bundles on disk: reference PNG mean **785 KB**, scene WebP mean **74 KB**, all
assets 1024×768, ~1.93 MB per story locally.

The important asymmetry: **Storage holds PNG for both kinds**; the WebP conversion happens locally in
`download_images`. And every image is re-read out of Storage many times — fal fetching references per
scene attempt, `consistency_check` pulling scene plus reference per attempt, `output_mod` handing the
URL to two classifiers. That is roughly **73 full-image reads per story**, about 4× the naive count.

| | Projected | Free | Pro |
|---|---|---|---|
| Storage | 0.95–1.38 GB | **1 GB** | 100 GB |
| Egress | 3.2–5.0 GB | **5 GB/mo** | 250 GB/mo |
| Inactivity pause | — | **~7 days** | none |

The 7-day pause is aimed directly at your labelling window. P1 multiplies scene images by a measured 2.32x on top.

### E · Phase C is less rehearsed than the runbook says

The runbook says `freeze_dataset` and `to_llamafactory` have never run. They have — on the **fixture**
path. `data/judge/fixture/dataset.jsonl/` holds a complete `train.json`, `val.json`, `test.json`,
`dataset_info.json` and `freeze_report.json`.

But `_validate_bundles` returns early when every bundle is `fixture: "true"`
(`freeze_dataset.py:107-110`), skipping the **production** branch at `:112-124` — the one enforcing
8 train + 2 val per style and the donated allocation. The tested path skips exactly the validation
that will run on your real campaign.

**Resolved 2026-09-13.** `tests/test_finetune_dataset.py` now builds production-shaped bundles and
covers the production branch (accepts 8+2 per style with 4/3/3 or an enlarged donated set, rejects a
short synthetic style and a donated style below the floor), then freezes that corpus end to end.

That rehearsal found a real bug. `build_dataset` appended ADR-057 constructed negatives after every
test record. `_write_evaluation_artifacts` requires the combined manifest to equal the train, val and
test manifests concatenated, so any freeze with at least one constructed negative — every real one —
raised `split manifest projections differ from combined manifest order`. That is the last step of
Phase C, after the whole generation spend and labelling window. `build_dataset` now stable-sorts
records by split before writing. No dataset had been frozen, so the manifest order change costs
nothing. The regression test goes red with the sort removed.

### F · Run the campaign locally, not on Northflank

The campaign never touches RQ, Redis, or the Northflank worker. `build_corpus.py:1381-1398` runs the
same LangGraph the worker compiles, in-process, holding one direct port-5432 connection for the whole
run. ADR-036's 1800-second RQ deadline therefore does not apply.

Northflank is disqualified on one point: its runtime filesystem is ephemeral and erased on restart,
which destroys `build_state.json` — the append-only ledger the design says must never be lost.
Provisioning and verifying a persistent volume on a job type where volume support could not be
confirmed is new untested infrastructure introduced immediately before a one-shot spend. There is
also no Northflank config in this repo to audit; every setting is dashboard-only.

Local failure modes are real but recoverable: checkpoints are in Postgres, assets are in Storage,
completed bundles are skipped on resume, and `generate_scene.py:37` does not re-pay for an asset
already uploaded.

### G · One transient provider error stops the entire campaign — **resolved 2026-09-13**

The original finding overstated the gap. `fal_client` 1.0.0 already retries each queue request on
its own — submit, status poll and result fetch, 10 attempts on 408/409/429, transport errors and
nginx 502/503/504 — so a 429 on the queue never reached `_run_fal`. Two gaps were real:

- **No ceiling on `subscribe`.** A stuck job polled forever. The campaign bypasses RQ, so nothing
  killed it and the run hung with no diagnostic.
- **No retry on the image download.** The image is paid for by then, yet one dropped connection
  fired `failed_uncertain`, quarantined the story `billing_uncertain` and exited the campaign.

Fixed in `providers.py`: `subscribe` gets `client_timeout=600` (fal cancels the request and raises),
and the download retries transport errors, 408, 429 and 5xx up to 3 times with backoff. There is
deliberately **no resubmission** after fal accepts a job: it would pay twice and put a draw past the
budget ledger. Tests: `test_run_fal_retries_a_transient_download_failure_without_resubmitting`,
`test_run_fal_does_not_retry_a_download_the_server_refused`; backend suite 1412 passed.

What remains: a hard fal failure (a job that errors server-side, or hits the 600s ceiling) still
quarantines that story `billing_uncertain` and exits 1. That is the correct record — billing is
genuinely unknown — and the restart is `--resume-quarantined <id> --acknowledge-uncertain-billing <id>`
after checking the fal dashboard. Check on the run periodically; it no longer needs watching.

### H · Honest answer on "an improvement is a must"

The improvement is likely to arrive, but not from the corpus you wrote.

Zero-shot VLM judges have a large documented "same character" bias — they agree with the reference by
default and rarely fire `different`, producing near-zero recall on the minority class and therefore a
low F1. A fine-tune on in-domain examples relocates that decision prior and teaches the output shape.
That mechanism is domain-general: it transfers from hedgehogs to Filipino schoolgirls because it is a
prior shift, not a visual-feature shift. `judge-finetune.md:558` already says the quiet part —
*"beating your own base model is necessary, not impressive."*

One accidental piece of good news: the four surviving hard negatives are all human-vs-human,
same-style. ADR-057 deleted 96% of the constructed pairs, but the ones that survived are the ones
whose distribution matches a 95%-human test set.

The ways it could still fail, ranked:

1. **Ceiling effect.** The test set is ~95% human, and human face identity is where a 7B VLM's
   zero-shot discrimination is *strongest*. You are training on the slice with the most headroom and
   reporting on the slice with the least.
2. **Checkpoint selection is noise.** A small validation split over 9 characters, with maybe 8–12
   positives. D2 now gives selection ~15 candidates per seed instead of one to three, but picking
   among them on so few positives is still noisy. Expect a wide seed-to-seed std.
3. **Narrative-shape shift — smaller than first written (Finding J).** Donated stories span time
   jumps, costume changes and ghosts — `g6-s4` shows Ana as a child and as an adult. But the pipeline
   draws every page from one frozen reference and never sends story text to the image model, so most
   such pages still show the child. Only a page whose visual direction names the change is at risk,
   and the rulebook labels it on what the images show.
4. **Format compliance is not a free win.** Constrained decoding applies to the base model too, so
   you do not get cheap ΔF1 from the baseline emitting broken JSON. That is good preregistration.

Finding A is the one lever that addresses 1 and 3 directly, because it supplies training examples of
the same character drifting — which is what the test set is made of.

### I · Three real stories died in `analyze` on every run — **resolved 2026-09-13**

The roster pre-flight on the 15 donated stories failed don-002, don-004 and don-010 with
`analyze: unknown owner` — "Angela's parents", "Erin and Klare", "Nico's grandfather". The spec made
an owner outside the character roster a hard error (`story-analyzer.md` §4.2). Extraction runs at
`temperature=0` and the single re-ask is blind, so the failure repeated on all three runs. Children
write group and relative owners routinely; the live app had the same defect.

Fixed at the rule, not per story: an owner that resolves to no persisted character leaves the object
unowned with a logged warning — the path an owner capped out of the roster already took
(`pipeline/analyze.py`). A group owner can never map to one `owner_char_id`, so only a relation the
object never had is lost; its appearance axes are kept. Test red on the old `raise`, green after;
backend suite 1410 passed. Both specs updated.

The same pre-flight showed declared names must be the extractor's names verbatim ("the goat", not
"Goat"), and that don-005 and don-015 extract unstably across runs. Declarations were set to the
names that repeated; don-005 declares only the stable narrator.

### J · No written rule for Same versus Different — **resolved 2026-09-14**

The annotation screen says "Classify character consistency according to the pre-registered study
rubric". No rubric existed. §4 of the preregistration froze the fields, not what they mean on a
hard page. With one rater, round 2's agreement measures consistency with rules that were only in
your head, and the test set carries exactly the pages where that matters.

**Time jumps need no pipeline change.** Checked against the code:

- A `Character` has one `canonical_ref_image` and fixed axes (species, colours, body features,
  clothing). Only objects carry a per-scene state (`Scene.object_states`); characters do not.
- `build_prompt` sends the character's axes and the scene's visual direction, never the story text.
  The generator is pulled toward the reference on every page.
- The judge's prompt (`to_llamafactory.QUESTION`) and the annotation screen show no story either.
  Neither the rater nor the judge can tell a change the story explains from generator drift, so an
  age or costume state in the pipeline would create pairs with no image-only right answer. It would
  also change the data contract after preregistration, and a picture book wants Ana recognisable.
- The synthetic corpus has no time jumps (the "years" matches are background), and adding stories
  modelled on the donated ones would design training data around the test set. Not done.

**Resolved:** `docs/specs/labelling-rulebook.md`, frozen by the 2026-09-14 amendment. Image-only;
Different needs a named reason (the screen enforces it); clothing, style and lighting alone are Same;
age, costume, back views and transformations follow the ordinary identity rules. One correction to
advice given in conversation: "Same, with `wrong_clothing` ticked" cannot be recorded, because
`TaxonomyControls.tsx` disables the reasons unless Different is chosen.

**Free check after generation (C1a):** count donated scenes whose visual direction names an age or
costume change. Report the count in the write-up. It selects and excludes nothing (§9.7).

---

## 6. What I could not verify

- ~~Whether the Supabase project is Free or Pro today~~ Pro since 2026-09-14, and `private_assets`
  exists and is private (owner, 2026-09-14). No pilot rows or objects remain (A7, 2026-09-14).
- Supabase dashboard paths in A6, E2 and E5 follow Supabase's docs as of 2026-03; the UI moves.
- LangGraph checkpoint table sizes. Estimated at 2–3 MB/story, 90–135 MB for 45. Query in A6.
- Scene PNG size *as stored in Supabase* — no scene PNG exists on disk, so storage and egress figures
  are banded 0.76–1.32 MB per stored PNG.
- Whether the available 4060 Ti is the 8 GB or 16 GB variant.
- Current fal.ai and OpenRouter balances and rate-limit tiers.
- All Northflank settings — no config exists in this repo.

---

## 7. Campaign log — Phase B6, 2026-09-15 → 2026-09-17

Written as B6 ran, so the defence has the record rather than a reconstruction — including the
wrong turns, which a write-up afterwards would have quietly dropped. §5 holds findings about the
*design*; this section holds what the *run* did. Numbers were read off `build_state.json` and the
42 bundles on 2026-09-17.

### 7.1 Outcome — B6 is complete

**42 of 45 bundles: all 30 synthetic and 12 donated. Spend $30.100.** Exit 0 on the final synthetic
run, no synthetic story quarantined. The allocation is exactly what the freeze demands:

| Provenance | Split | cel | gouache | cut_paper |
| --- | --- | --- | --- | --- |
| synthetic | train | 8 | 8 | 8 |
| synthetic | val | 2 | 2 | 2 |
| donated | test | 3 | 4 | 5 |

Three donated stories stay quarantined **on purpose** — don-006 and don-015 (`invalid_terminal`),
don-013 (`budget_stopped`) — because the donated held-out set is a floor and 12 bundles clear it.

The asymmetry drove every spending decision in the endgame. `freeze_dataset.py:112-124` treats the
synthetic allocation as an **equality** (8 train + 2 val per style, all 30), so one missing synthetic
story blocks the freeze outright. Donated is a **floor** (`validate_donated_allocation`: gouache >= 4,
cel >= 3, cut_paper >= 3). There are no spare synthetic stories — `corpus_synthetic.json` holds
exactly 30. That is why the last four stories were worth four budget raises and three donated
stories were worth none.

**Authorization moved four times**: $28 -> $29.50 -> $30.00 -> $30.38 -> $30.75, finishing at
$30.100 actual. Two of those raises were needed only because the estimate behind the previous one
was too low (7.2 item 8). The `hard_usd` ceiling in `build_corpus.py` was raised twice by commit,
from $30.00 to $30.50 to $30.75.

### 7.1a How the last four stories actually went

All four were `invalid_terminal` and all four needed more than one override:

| Story | Rounds | Outcome |
| --- | --- | --- |
| syn-027 | 2 | passed on the second readmission, 13 calls |
| syn-019 | 2 | passed on the second readmission under PR #88, 13 calls, no fal refusal |
| syn-001 | 2 | first readmission applied but budget-halted before spending; ran next pass, 23 calls |
| syn-017 | 4 | refused on rounds 1, 2 and 3 (7, 8 and 10 calls), passed on round 4, 12 calls |

syn-017 is the instructive one. Its scene s0 was refused three separate times, every time as
`backstop (primary said safe) after retry` — the same scene, the same verdict. That looked
deterministic, and the scene-level override in 7.3 was built on the strength of it. **On the fourth
round s0 passed moderation unaided and the override never fired.** The refusal is stochastic with a
high rate, not deterministic. Recorded because the wrong conclusion was acted on: see 7.4.

### 7.2 What went wrong, in the order it bit

1. **The per-story call cap was set from the wrong population.** `--max-calls-per-story 19` was
   sized on synthetic stories. Donated stories are longer, so they keep more images —
   mean 16.7 kept for donated against 13.0 for synthetic, and don-012 kept 26 — and five donated
   stories halted mid-run having spent every call while still making progress. Raising the cap to 22
   was not enough; 30 rescued don-005, don-010 and don-012 and built don-014, and don-009 needed 40.
   *The cap is a spend guard, not a length guard, and it has to be sized on the longest population
   you intend to run.*
2. **I mis-diagnosed that halt before measuring it.** I told the operator the consistency checker's
   redraws were pushing donated stories past the cap. Measured, the redraw rate is 3.8% for donated
   against 17.2% for synthetic — the opposite of the claim. Story *length* was the cause. The wrong
   explanation was retracted before it cost anything, but it nearly bought a redraw-tuning change
   that would have fixed nothing.
3. **fal's own content checker rejects prompts ours clear.** syn-018, syn-019 and don-015 were each
   refused by fal with HTTP 422 `content_policy_violation`, billed $0.00. syn-019's refusal was a
   *sock puppet dragon reference sheet*; don-015 is *The Red Shoes*, where the source text has feet
   "bleeding and swollen" at a funeral. fal judges the finished image, so the same prompt passes on a
   later draw — but before PR #87 a 422 crashed the campaign, and after it the story is quarantined
   and the campaign survives. PR #88 goes one step further and simply asks again.
4. **Our conservative backstop over-refuses, and it is the one doing the refusing.** All four
   `output_moderation_failed` quarantines carry the same shape: `backstop (primary said safe) after
   retry`. The primary classifier cleared every one of them. The primary also *errored* 15+ times
   campaign-wide, and `output_mod._check_image` degrades to backstop-only on a primary error, so a
   flaky primary silently hands the decision to the stricter model. The operator reviewed the stored
   images in Supabase on 2026-09-17 and found no safety issue in any of them — syn-027's only defect
   was an anatomy artefact (extra limbs on a running figure), which is image quality, not safety.
5. **`--readmit-quarantined` was once per story, and two stories needed it twice.** syn-019 spent its
   readmission, was refused by fal again on 2 of 4 draws, then crashed at `input_gate` with
   `moderation_error`. syn-027 spent its readmission on 17 fresh calls and the backstop refused it
   again. Both were left with no CLI path at all. PR #89 adds
   `--acknowledge-prior-readmission STORY_ID`, which must name the same story as
   `--readmit-quarantined` so the widening stays per-story rather than one flag freeing the campaign.
6. **A readmission does not skip moderation. It redraws.** Which is the whole reason it works, because
   the refusal turned out to be stochastic: every story that looked permanently refused eventually
   passed on a later round of draws, syn-017 on its fourth. The cost is that each readmission is a
   bet at full price — syn-017 spent 37 calls across four rounds on a story that cost 12 to build —
   and a story can absorb an unbounded number of them. Budget for the number of rounds, not for one.
7. **One provider outage, one timeout.** syn-012 died in a DeepInfra outage. don-009's `analyze` node
   raised `TimeoutError: mistralai/mistral-small-3.2-24b-instruct did not answer within 120s` at
   `pipeline/analyze.py:307` and exited 1 with zero image spend; the checkpoint restarts at `analyze`,
   so rerunning was free.
8. **Two guards met and left a story unreachable at any price.** syn-017 could not restart, and
   neither guard was wrong on its own. `_validate_restart_cap` (`build_corpus.py:671`) is an
   **equality**: once a story is isolated for restart its recorded call allowance cannot be changed
   in either direction, and it runs at line 919, *before* the readmit branch at 923, so a readmission
   cannot rewrite it either. Meanwhile the per-story budget reserve refuses to *start* a story it
   cannot finish at that allowance. So the locked 30-call allowance reserved $1.05 while $0.82
   remained, and every route out was closed: `--restart-quarantined` refuses a story that already has
   an `execution_id`, and `--extend-story-call-cap` requires `--resume-quarantined`, which does not
   accept `invalid_terminal`. Only raising the ceiling by commit unblocked it.
9. **The hard ceiling silently clamped a raise, and that was the guard working.** `hard_usd`
   (`build_corpus.py:108`) is a constant with **no CLI flag**, and `authorized_usd = min(max_usd,
   hard_usd)`. A `--max-usd 30.38` was clamped to $30.00 and the run halted rather than spending. It
   is the one limit `--max-usd` cannot escalate, which is exactly why it caught an operator — an
   agent — walking the budget up one flag at a time. It stays hardcoded on purpose; raising it is a
   reviewed commit.
10. **Budget estimates were wrong twice, in the same direction.** The $29.50 and $30.00 ceilings were
    both sized on an estimate of ~13 calls per story, taken from syn-027 and syn-019. syn-001 took
    23. Each bad estimate cost a round trip and a decision the owner had to make again with no new
    information. The third figure was computed instead of estimated — the per-story call cap binds
    before the budget does, so `spent + cap * price` is a *provable* worst case — and it held.
11. **A budget halt is free, and that is worth knowing.** Three separate runs refused to start:
    twice on `budget_reserve`, once on the cap equality. All three spent $0.00, and the readmission
    they were carrying was not consumed, because the reserve check runs before the readmit branch
    writes. A refusal to start is not a failed attempt.

### 7.3 Decisions taken, and why

- **Relax the `code_commit` pin — implemented 2026-09-17, commit `f8b3ecc`.** The decision was taken
  mid-campaign; the code change came after B6 finished, because editing the tree during a run stamps
  every bundle `-dirty`. `freeze_dataset.PINNED_METADATA_KEYS` no longer contains `code_commit`;
  differing values are collected into `code_commits`, the same idiom `style_preset_id` already used.
  The 42 bundles span five commits — `f2048a4` x33, `56d7f4c` x3, `1ddf1ce` x3, `c1f0557` x2,
  `3b42361` x1 — and **none is `-dirty`**. Of the merges only PR #85 (segment roster fix) can touch
  image content; #86, #87, #88 and #91 are error handling and a spend constant, which change which
  stories *survive*, not what they draw. Keeping the equality would have meant discarding 42 paid
  bundles to rerun them under one HEAD, at a cost the budget does not have, to buy a property the
  campaign never had.
- **And replace it with the property it was standing in for.** The same change now refuses any
  bundle whose `code_commit` ends `-dirty`. The old equality could not see that: bundles built from
  one dirty tree all agree with each other and pass. Relaxing the weaker guard without adding this
  would have left nothing checking that a bundle traces to a commit anyone can check out.
- **Add a scene-level moderation override** (commit `8836537`).
  `--acknowledge-scene-moderation STORY_ID:SCENE_ID`, with a required `--scene-moderation-reason`,
  accepts one named scene on exactly one verdict: the backstop refusing after retry what the primary
  classifier called safe. A primary flag or a primary error is a different event and still fails the
  job, so naming a scene cannot switch the gate off for it. The accepted scene carries
  `passed_operator_override`, never `passed` — the classifier did refuse, and the bundle has to say
  so rather than launder it into a clean verdict. Built because story-level readmission only
  *redraws*, so a scene the backstop refuses reliably was unreachable at any price. **It has never
  fired**: syn-017 passed unaided on the run it was built for (7.1a). It closes a real gap and the
  gap is real regardless, but it is untested in production and should be described that way.
- **Raise the hard ceiling twice, by commit** (`aff5516` to $30.50, `3b42361` to $30.75), rather than
  making `hard_usd` a CLI flag. A flag would have removed the only limit that the escalating
  `--max-usd` raises could not pass, which is the guard that caught them.
- **Spend the remaining budget on synthetic, not donated.** Forced by the equality-vs-floor
  asymmetry in 7.1. don-006, don-013 and don-015 stay quarantined.
- **Readmit on a human verdict, not on an appeal to the classifier.** Each `readmit_reason` records
  who looked, what they saw, and that the primary cleared it — the record has to stand on its own,
  because a quarantined story writes no bundle and `run_metadata` is the only place its justification
  lives. That is also why `_prior_readmissions` carries the first justification forward into the
  second. syn-001's reason is deliberately weaker than the others: the reviewer could not check every
  image and said so, and it is recorded as *an absence of a finding, not a positive all-clear*, with
  the readmission resting on the campaign-wide backstop pattern instead.
- **One recommendation reversed before it was acted on.** I recommended dropping five synthetic
  stories and freezing at 29. Reading `freeze_dataset.py` showed the synthetic allocation is an
  equality, so a 29-story freeze raises `ManifestError("style allocation drift in production
  bundles")` and is not a freeze at all. Retracted before any money moved.
- **Drop the syn-018/syn-019 readmissions in favour of donated work** (taken mid-campaign, when the
  budget looked tighter). Correct at the time; superseded once the donated floor was met.

### 7.4 What to do differently next campaign

- Size `--max-calls-per-story` on the longest story in the population, then add headroom. A halt at
  the cap costs everything already spent on that story plus a rerun.
- **Compute spend ceilings, never estimate them.** Where a cap binds before the budget does,
  `spent + cap * price` is provable. Two of the four authorization raises existed only because an
  average was used where an arithmetic bound was available, and each cost the owner a decision they
  had already made.
- **Do not generalise a failure from one story to another.** syn-027 passed on its second readmission,
  so the backstop refusal was called stochastic; syn-017 then failed three times on the same scene,
  so it was called deterministic and code was written on that basis; it then passed on the fourth.
  Both readings were drawn from three or fewer observations of a stochastic process. Say "refused
  3 of 4 times" and let the number stand.
- Measure before explaining. Three of the wrong turns in 7.2 were confident causal claims made from
  plausibility rather than from the state file.
- Do not pin the code commit across a campaign long enough to need a bug fix. Record the commits and
  require the tree to be clean, which is the property that actually matters.
- Treat a third-party content checker as a distinct failure surface from your own moderation, with
  its own classifier and its own retry, because it will refuse things yours clears.
- An override that can only be used once strands exactly the cases that need review most. Both the
  story-level readmission and the scene-level gate needed a repeatable route in the end.
- Land the operational fixes a campaign needs **before** it starts, not during. Every mid-campaign
  merge added a commit to the provenance spread and forced the `code_commit` decision in 7.3.

### 7.5 For the technical defence

These are measurements the write-up can use as-is:

- Donated vs synthetic redraw rate: **3.8% vs 17.2%**. Kept images per story: **16.7 vs 13.0**.
  Donated stories are longer and more consistent; the synthetic set does more of the work of teaching
  the consistency judge what a failed draw looks like.
- **The conservative backstop refused four stories unilaterally — syn-001, syn-017, syn-022 and
  syn-027 — and human review upheld the primary classifier in all four.** Every one carries the same
  log shape, `backstop (primary said safe) after retry`. The primary also *errored* 15+ times
  campaign-wide, and `output_mod._check_image` degrades to backstop-only on a primary error, so a
  flaky primary silently hands the decision to the stricter model.
- The refusal is **stochastic, not content-stable**. syn-017's scene s0 was refused on three
  independent rounds of draws and passed on the fourth, with no change to the prompt or the story.
  A moderation gate whose verdict on the same scene varies across draws cannot be characterised by a
  single pass — it is a distribution, and the campaign sampled it four times.
- fal's content checker independently refused three stories our two-layer moderation cleared
  (syn-018, syn-019, don-015 — *The Red Shoes*, whose source text has feet "bleeding and swollen" at
  a funeral), with **$0.00 billed** on each refusal. Third-party moderation is not a redundant copy
  of yours; it is a differently-calibrated third opinion.
- Provenance is documented, not pinned: 42 bundles across five commits, **no `-dirty` stamps**, one
  content-affecting change (PR #85) among the merges. The freeze now enforces the clean-tree property
  directly (7.3).
- Cost of the campaign: **$30.100** by the conservative ledger, which charges $0.035 per image call
  against a real fal price of $0.0157-$0.0236, so actual spend is materially lower.

# Feature Spec — lettering suppression

**Status:** draft · **Phase:** 2 · **Owner nodes:** `backend/pipeline/char_bible.py`,
`consistency_check.py`, `regenerate.py`, `prompt_optimizer.py`
**Derived from:** MASTER_SPEC §2 · **Rationale:** ADR-004 (reason-then-score field order),
ADR-010 (one corrected retry, no resampling), ADR-023 §8 (additive fields), ADR-028
(`FailureReason` frozen at 7), ADR-025 (the check failing ≠ the artifact failing)

> **Deviation from "one spec = one module", declared not smuggled.** Four nodes change because
> this addresses one *artifact class* — text the image model draws on its own — which is produced
> on both image paths, must be detected by both judges, and is corrected in a third place.
> Precedent: `scene-setting-and-subject-binding.md`, `moderation-stack.md`.

---

## 1. Purpose

Qwen-Image renders text by design (`providers.py:277`). Nothing in this pipeline can see it.

Observed 2026-08-13, in a seed-matched two-arm probe run through the production reference and scene
paths: a wooden burrow door came back lettered **"IOREGIAO"** (new gouache fragment, seed 21),
**"CAP"** (new, seed 7) and **"AFAI-cl"** (old, seed 7), and clean at seed 99 in both arms. It
appears in **both style arms**, so it is not caused by the gouache fragment change; it is
seed-dependent, so it is partly luck; and `edit_image` demonstrably already sends
`providers.NEGATIVE_PROMPT`, whose list contains *text, letters, words, writing, signage, labels,
captions* — and the door lettered anyway.

Three prior attempts to fix this by prompt wording have failed:

| # | Attempt | Outcome |
|---|---|---|
| 1 | every style fragment ended `no speech bubbles, no captions, no lettering` (2026-08-11) | a gouache page lettered again, then a cel run drew chat bubbles |
| 2 | `char_bible.REFERENCE_PROMPT` said "A single character reference…" | the word **"Reference;"** was lettered across the top of a draw |
| 3 | `NEGATIVE_PROMPT` widened to 12 terms | the burrow door drew "CAP" |

The governing finding, already recorded in three places in the codebase: **a negative prompt
subtracts a tendency; it cannot outvote a word sitting in the positive prompt, and naming a thing
summons it.** Attempts 1 and 2 named it. Attempt 3 is the honest use of the channel and still
leaks, because the model draws letters absent any instruction at all.

So this spec does not add another prohibition. It adds the missing **detection channel**, gates on
it, and corrects with a clause that asserts blankness without ever naming what it is suppressing.

**In scope:** any visible text — letters, numbers, writing — anywhere in a reference draw or a
scene page. Not only gibberish: a crisply spelled shop sign is equally a defect in a book whose
reader is six and whose text lives in the app, not in the picture.

---

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

Two additive booleans, both defaulted `True`, both **declared last** in their model so ADR-004's
wire order is untouched. Additive with defaults → **no `schema_version` bump**
(`story-memory-contract.md` §8; precedent `VlmVerdict.anatomy_intact`, `.subjects_unique`).

```python
class RefVerdict(BaseModel):
    ...
    attributes_present: list[str] = Field(default_factory=list)
    text_free: bool = True          # NEW — declared LAST

class VlmVerdict(BaseModel):
    ...
    subjects_unique: bool = True
    text_free: bool = True          # NEW — declared LAST
```

and the node-local judge boundary schema, which mirrors `VlmVerdict` and then appends:

```python
class SceneVerdict(BaseModel):      # consistency_check.py
    ...
    subjects_unique: bool = True
    text_free: bool = True          # NEW — after subjects_unique, BEFORE failure_reasons
    failure_reasons: list[FailureReason] = Field(default_factory=list)   # stays LAST
```

- **`char_bible`** — writes `characters[].ref_verdict.text_free`.
- **`consistency_check`** — writes `scenes[].attempts[].vlm_verdict.text_free`.
- **`regenerate`** — reads it; writes nothing new.
- **`prompt_optimizer`** — pure; reads nothing, writes nothing.

**Invariants**

1. `FailureReason` stays frozen at **7** (ADR-028). This is a boolean exactly as `anatomy_intact`
   is, and for the same reason: it is a rendering property, not a described attribute, so there is
   nothing per-character to fill into a clause.
2. `text_free=True` is the safe default — an old checkpoint and an unchecked attempt both read as
   "no lettering seen", never as a failure.
3. Reference acceptance becomes `not verdict.contradictions and verdict.text_free`. A judge
   *failure* (exception) is still accept-unchecked, unchanged — ADR-025's asymmetry stands.
4. Scene `passed` becomes `same_character and anatomy_intact and text_free`. `style_match` and
   `subjects_unique` still do not gate.
5. `correct_prompt` never drops content (its invariant 3) — the new clause is appended, like every
   other.

---

## 3. Position in the system map

**No new nodes, no new edges.** ADR-003 is untouched: every change is inside an existing node body,
an existing judge prompt, or a pure helper. The `consistency_check` pass/fail branch keeps its
shape; only the boolean expression behind it widens. `char_bible`'s `MAX_DRAWS = 3` loop is
node-internal (ADR-028 Decision 3) and gains no iteration bound.

---

## 4. Behavior & edge cases

### 4.1 Detection — one question per judge prompt

Both judge prompts gain one question, asked **in schema-declaration order**, because
`providers._assert_field_order` rejects a provider that answers out of order (ADR-004).

Wording, identical in both:

> whether the picture is free of any text — any letters, numbers or writing anywhere in it,
> including on signs, doors, books and clothing.

Naming surfaces here is safe and is the point: this prompt goes to the **VLM judge**, never to the
image model. The rule that naming summons applies to the generator's prompt; the judge has to be
told what to look at, and the door, the book and the shirt collar are exactly where it landed.

- `char_bible.JUDGE_PROMPT` — appended after "list which of the described attributes are actually
  present in the image", matching `RefVerdict`'s new tail position.
- `consistency_check.JUDGE_PROMPT` — appended after the uniqueness question and **before** "Finally
  list the failure reasons", matching `SceneVerdict`.

Both version markers bump, so the hit-rate series stays comparable within a version — an unversioned
reword has already cost this project one discarded series:

| Constant | Old | New |
|---|---|---|
| `char_bible.JUDGE_PROMPT_VERSION` | 3 | **4** |
| `consistency_check.JUDGE_PROMPT_VERSION` | 2 | **3** |

`char_bible`'s is persisted as `Character.ref_verdict_prompt_version`; `consistency_check`'s reaches
the log line only (its own §8 open question, unchanged by this spec).

### 4.2 The reference gate

The reference is the higher-value catch: `char_bible` mints one canonical image per character and
**every page inherits it**, so a lettered reference letters the whole book. It already has a
re-roll loop with a budget, so gating costs nothing new architecturally.

- acceptance: `if not verdict.contradictions and verdict.text_free:` → accept and upload
- `best_draw`'s key gains one position, **behind contradictions, ahead of attributes_present**:
  `(-len(contradictions), text_free, len(attributes_present), -i)`
- the existing per-draw `log.info` gains `text_free=%s`
- no seed is passed today (`char_bible.py:261`, deliberate), so the re-roll already resamples

Ordering rationale: a draw that contradicts the child's own description is worse than one with a
sign in it — the first is the wrong character, the second is the right character in a marked room.
Above `attributes_present` because that key is documented as noisy (ADR-034).

### 4.3 The scene gate and ranking

- fold: `text_free=all(v.text_free for v in verdicts)` — worst-wins, like every other boolean
- `passed = verdict is not None and verdict.same_character and verdict.anatomy_intact and verdict.text_free`
- `_rank` gains one position:
  `(1, same_character, anatomy_intact, text_free, subjects_unique, style_match)`, and the unchecked
  tuple widens to `(0, 0, 0, 0, 0, 0)`
- the existing per-scene `log.info` gains `text_free=%s`

Ordering rationale: **after** `anatomy_intact`, because a merged limb is a worse picture than a
lettered door; **ahead of** `subjects_unique` and `style_match`, because those two deliberately do
not gate and this one does.

**Why gate here at all**, when `scene-setting-and-subject-binding.md` §4.4 declined to gate
`subjects_unique` on latency grounds (issue #26): the two are not comparable. That decision was
blocked on an unmeasured duplicate rate. Here the rate is not zero and not unknown — at least 3 of
the 6 burrow-door draws in the probe came back lettered — and the artifact is unambiguous rather
than a judgement call about
whether "the stars" in a night sky counts as a second character. Latency cost is bounded by the
same one-retry cap ADR-010 already imposes; a scene still draws at most twice.

### 4.4 The correction

```python
# prompt_optimizer.py, beside IDENTITY_CLAUSE and ANATOMY_CLAUSE
TEXT_CLAUSE = "every surface in the picture is blank and unmarked"
```

Appended by `correct_prompt` when a new `text_free: bool = True` keyword argument is `False`,
mirroring `anatomy_intact` exactly — a fixed string with no `.format`, driven by a **boolean, never
an 8th enum value** (ADR-028).

`regenerate` passes it the same way it passes the other two, and its CC-5 log line gains
`text_clause=%s` so a correction that fired is distinguishable from one that silently appended
nothing (invariant 5: every reachable path appends at least one clause).

On every retry, `regenerate` starts from the immutable original `Scene.prompt` and appends only
the correction clauses derived from the latest checked attempt, including `TEXT_CLAUSE` when
`text_free=False`. It never uses `last.prompt` or accumulates correction history from earlier
attempts.

**The wording is the whole trick.** It asserts blankness and never says *text, letters, words,
writing, signage, captions* or *lettering*. Those words are what put lettering on the canvas the
last three times, and this clause fires precisely on images that already have some — the worst
possible moment to name it. `regenerate` passes no seed, so the retry also resamples for free; the
clause is what makes it a **correction** rather than the pure re-roll ADR-010 rejects.

### 4.5 Edge cases

| Case | Behavior |
|---|---|
| Scene has no character with a canonical reference | `judge_attempt` returns `[]` → unchecked → `text_free` defaults `True` and the page ships. **Unchanged existing hole**, see §4.6.1 |
| Judge/Storage raises | unchecked; page ships; `anatomy_intact` behaves identically today |
| Reference judge raises mid-loop | accept-unchecked and return, exactly as today — ADR-025's deliberate asymmetry, untouched |
| All 3 reference draws letter | `best_draw` picks the least-bad and persists a FAILING verdict, as it already does for contradictions. A lettered reference can still ship |
| Scene fails only on `text_free` | corrected retries with `TEXT_CLAUSE`; if the last attempt also letters, `finalize` on `len(attempts) >= MAX_SCENE_ATTEMPTS` (3 with ADR-037; was 2) and best-of picks among the lettered images |
| Old checkpoint resumed | both fields default `True`; a pre-change attempt reads as clean and is never re-judged |
| Text that is part of the child's story ("a sign that said HOME") | judged as a defect and redrawn. Accepted: the excerpt is read aloud in the app, and pseudo-lettering has never once come back spelling what was asked |

### 4.6 Risks carried, stated not solved

1. **Coverage matches `anatomy_intact`, no wider.** `judge_attempt` returns `[]` when a scene has
   no referenced character, so those pages go unchecked for lettering exactly as they go unchecked
   for merged limbs. Widening that is a different change (a subject-less judge call is a new paid
   call per page) and is not smuggled in here.
2. **False positives on texture.** Wood grain, ben-day halftone dots and brush marks can read as
   writing to a VLM. Cost is bounded — one retry per scene, `MAX_DRAWS = 3` per reference, and
   `regenerate` already raises on `IMAGE_BUDGET` (ADR-025 D4). **The fallback, if the rate is bad:
   demote `text_free` to rank-only, the shape `subjects_unique` already sits in.** That is a
   two-line reversal, not a redesign.
3. **The judge is not measured on this axis.** Nobody knows its recall for small lettering in a
   corner of a 1024² page. The first real number arrives from the telemetry this spec adds — the
   same bootstrap `subjects_unique` is on.
4. **Neither `NEGATIVE_PROMPT` nor any style fragment changes.** Deliberate. The prompt lever has
   lost three times, and leaving it fixed is what makes this change's effect attributable.
   **Overtaken by events, 2026-08-13:** `NEGATIVE_PROMPT` held, the `gouache` fragment did not —
   see §9. The `cel` and `comic` arms are still clean reads; `gouache`'s is confounded.
5. **Latency.** A gate that fires buys a redraw (~40s, issue #26 open). §4.3 argues the trade is
   worth it; if #26 forces a retreat, risk 2's fallback is the lever.

### 4.7 Blast radius

| File | Change |
|---|---|
| `backend/contracts/story_memory.py` | +2 additive fields; the ADR-010 rank comment widens |
| `docs/specs/story-memory-contract.md` | mirrors both, same rank comment |
| `backend/pipeline/char_bible.py` | judge question, `JUDGE_PROMPT_VERSION` 3→4, acceptance condition, `best_draw` key, log |
| `backend/pipeline/consistency_check.py` | judge question, `JUDGE_PROMPT_VERSION` 2→3, `SceneVerdict` field, fold, `passed`, `_rank`, log |
| `backend/pipeline/prompt_optimizer.py` | `TEXT_CLAUSE`, `correct_prompt` keyword arg |
| `backend/pipeline/regenerate.py` | pass the flag, log it |
| `docs/specs/character-bible.md`, `consistency-checker.md`, `prompt-optimizer.md`, `regeneration-controller.md` | behavior changed → updated in the same change |

**Not touched, deliberately:** `providers.py` (`NEGATIVE_PROMPT` unchanged — §4.6.4),
`app/config.py` (no fragment changes), `generate_scene.py` (the first draw is unchanged; this only
adds a reason to redraw), `graph.py` (no edges), `output_mod.py`. `IMAGE_BUDGET` and
`RECURSION_LIMIT` are unchanged and cannot trip: this spec adds **zero** judge calls — both booleans
ride calls that already happen — and adds image calls only within budgets that already provision
two attempts per scene and three draws per reference.

---

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-3 Cost control** — zero new judge calls. New image draws are bounded by the existing
      `MAX_DRAWS = 3` and ADR-010's one retry; `IMAGE_BUDGET` untouched and still enforced ahead of
      spend in `regenerate`.
- [x] **CC-5 Observability** — `text_free` reaches both existing log lines; `regenerate` logs
      whether the clause fired; both judge prompt versions bump.
- [x] **CC-6 Accessibility** — the motivating one. A picture book for a pre-reader must not carry
      words the child cannot read and the app never speaks; the story's text lives in the reader UI.
- [x] **CC-9 Failure states = success states** — every failure path still ships an image. A lettered
      reference, a lettered second attempt, a judge outage: all finalize.
- [x] **CC-10 Checkpointing / resumability** — both fields additive with `True` defaults, so a
      pre-change checkpoint deserializes and reads as clean.
- [ ] CC-1, CC-2, CC-4, CC-7, CC-8 — untouched. (CC-7: `char_bible`'s re-roll stays seedless and
      `regenerate` stays seedless, both as they are today.)

---

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Models mocked. No assertion on generated content. **Every test seen red first** (AGENTS.md §4 —
this has branches and a loop).

**Contract**
1. `RefVerdict()` and `VlmVerdict()` default `text_free=True`.
2. `text_free` is the LAST declared field on both, and on `SceneVerdict` it sits after
   `subjects_unique` and before `failure_reasons`.
3. A checkpoint blob lacking both fields deserializes with the documented defaults.

**`char_bible`**
4. A first draw with `text_free=False` and no contradictions is **rejected**, and a second draw is
   made.
5. A draw with no contradictions and `text_free=True` is accepted on the spot (unchanged path,
   asserted so the gate cannot swallow it).
6. `best_draw` prefers the text-free draw when contradiction counts tie.
7. `best_draw` still prefers fewer contradictions over text-free — the key order is load-bearing.
8. `JUDGE_PROMPT_VERSION == 4`, and the judge prompt asks the text question after the attributes
   question.

**`consistency_check`**
9. `text_free=False` on any per-character verdict folds to `False`.
10. `text_free=False` alone flips `passed` to `False`.
11. `_rank` sorts a lettered attempt below a clean one and above one that fails anatomy.
12. `_rank` prefers a text-free attempt over a duplicate-subject one when the higher keys tie.
13. Unchecked ranks below every checked attempt with the widened 6-tuple.
14. `JUDGE_PROMPT_VERSION` is current (**4** since pose-viewpoint-composition §5.2; this spec took
    it to 3), and the question order matches `SceneVerdict`'s declaration order.

**`prompt_optimizer`**
15. `correct_prompt(..., text_free=False)` appends `TEXT_CLAUSE`; `text_free=True` does not.
16. The clause appends alongside `ANATOMY_CLAUSE` without duplicating or reordering it.
17. **`TEXT_CLAUSE` contains none of `providers.NEGATIVE_PROMPT`'s terms** — the invariant that
    already exists for style fragments in `test_config.py`, applied to the one other string this
    project sends the image model about text.

**`regenerate`**
18. A verdict with `text_free=False` reaches `correct_prompt` as that keyword.
19. The log line reports whether the clause fired.

---

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

There is no eval harness (single-rater, non-blind — `PHASE_05_RESULTS.md`). What this adds is the
**first machine-readable lettering signal in the pipeline**: after N books,
`characters[].ref_verdict.text_free` and `scenes[].attempts[].vlm_verdict.text_free` yield a rate,
per judge-prompt version, which is what §4.6.2's demote-or-keep decision needs and what nobody has
today.

The probe that motivated this spec (6 burrow-door draws, 2 fragment arms, 3 seeds, at least 3
lettered — the fourth cell was not re-read) is the only
prior data point and is **not** a measurement of this change — it predates it and used no judge.

---

## 8. Linked decisions & open questions

**Depends on:** ADR-003 (no new edges — satisfied), ADR-004 (field order — both fields declared
last, both prompts ask in declaration order), ADR-010 (one corrected retry; the clause is what keeps
this from being resampling), ADR-023 §8 (additive fields), ADR-025 (unchecked ≠ failed; budget
breaker before spend), ADR-028 (`FailureReason` frozen at 7 — untouched; `MAX_DRAWS` unchanged),
ADR-034 (`contradictions` is the reference gate — `text_free` is ANDed with it, not folded into it).

**Not an ADR.** Both contract fields are additive with defaults, which §8 of the contract spec
permits without an ADR or a `schema_version` bump.

**Open questions — flagged, not guessed:**

1. **What is the judge's false-positive rate on texture?** Unknown until this runs. §4.6.2 names the
   fallback in advance so the decision is cheap when the number arrives.
2. **Should scenes with no referenced character be judged at all?** They are unchecked for anatomy
   and uniqueness today; this spec inherits that hole rather than widening scope. Deserves its own
   issue, alongside `scene-setting-and-subject-binding.md` §8.2.
3. **Is `TEXT_CLAUSE` the right wording?** It is unmeasured — like every prompt string in this
   project. It is at least the first one that does not name what it is trying to remove.
4. **Should `char_bible` also rank on `text_free` when the judge is unavailable?** No — a `None`
   verdict short-circuits the loop entirely, so the question does not arise; noted so nobody
   "fixes" it later.

---

## 9. Definition of Done

Per AGENTS.md — completion is not claimed without proof.

**Must pass, with output shown:**

```bash
cd backend && uv run ruff check . && uv run pytest
```

**Must be true:**

- [x] All 19 assertions in §6 exist and pass.
- [x] Every test was seen failing first.
- [x] The four specs in §4.7 plus `story-memory-contract.md` are updated in the same change.
- [x] `git diff -- backend/pipeline/graph.py` is empty (no new edge).
- [ ] ~~`providers.NEGATIVE_PROMPT` and `app/config.py`'s `STYLE_PRESETS` are byte-identical to
      before (§4.6.4 — attributability).~~ **BROKEN, deliberately, 2026-08-13.**
      `NEGATIVE_PROMPT` is byte-identical. `STYLE_PRESETS` is **not**: the `gouache` fragment
      changed `thick confident ink outlines` → `no outlines, shapes formed by brushed colour` in
      the same branch. That is unrelated work (the model was treating the outline clause as
      optional and `char_bible` flips that coin once for a whole book), but it lands here, so
      **§4.6.4's attributability argument no longer holds**: a lettering-rate change measured on
      the first job after this branch cannot be attributed to the detection channel alone,
      because the gouache arm's prompt also moved. Read the first `text_free` numbers per style
      preset, and treat `gouache`'s as confounded.
- [x] `grep -rn` sweep for tests asserting the old `_rank` arity, the old `passed` expression, the
      old `best_draw` key, or either judge prompt's exact text.

**Must be reported, not silently omitted:**

- **Observed `text_free` rate on a real job:** No production or staging job has run against this code yet (CI deterministic tests only). Until a real job runs, this change's effect on shipped books is **unmeasured**, exactly like the probe that motivated it.
- **False-positives seen:** None recorded yet (awaiting first live job execution).

**Explicitly NOT in scope, and not to be added mid-implementation:**

- any change to `NEGATIVE_PROMPT` or to a style fragment
- an 8th `FailureReason` (frozen, ADR-028)
- judging scenes that have no referenced character (§8.2)
- an eval harness
- OCR or any non-VLM text detector — a second dependency for a signal the existing judge call
  already carries for free

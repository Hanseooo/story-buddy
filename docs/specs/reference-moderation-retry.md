# Feature Spec — reference-moderation-retry

**Status:** draft · **Phase:** 2 · **Owner nodes:** `backend/pipeline/char_ref_mod.py`,
`backend/pipeline/char_bible.py`, `backend/pipeline/graph.py`, `backend/app/config.py`
**Derived from:** MASTER_SPEC §2 (system map) · **Rationale:** ADR-011c, ADR-024, ADR-025, ADR-029

> Declared deviation from "one spec = one module". The change is a single loop threaded through
> four files — the node that detects, the router that decides, the node that redraws, and the two
> budget constants that have to move with it. Splitting it four ways would put the cap in one
> document and the thing it caps in another. `moderation-stack.md` keeps ownership of the gate's
> *rubric*; this spec owns only what happens after it fires. Precedent:
> `lettering-suppression.md`, `scene-setting-and-subject-binding.md`.

## 1. Purpose

A flagged character reference ends the book. It should cost one redraw.

### What happened

Prod job `4feff195-cc53-46e5-ba17-8b68476222c0` (2026-08-13 05:54 UTC, `gouache`) died at
`char_ref_mod`. The two classifiers disagreed on c0:

| Classifier | Verdict | Reasoning (logged, truncated at 300 chars) |
|---|---|---|
| `mistral-small-3.2-24b-instruct` (primary) | safe | "a young boy with short hair, smiling, and wearing a white and red shirt" |
| `gemma-3-27b-it` (backstop) | **flagged** | "a child with what appears to be a smear of red on their shirt, potentially resembling blood" |

The image is a white shirt with a red half-vest whose edge reads as torn. The backstop's veto is
unilateral by design (`char_ref_mod.py:28-32`), so `char_ref_mod` wrote
`ref_moderation_status="flagged"`, `moderation_router` raised `RuntimeError("ref_flagged")`
(`graph.py:31`), and `run_job.py:198` recorded `failure_reason="machine"`. c1 had already passed.
Nine scenes were segmented and never drawn.

### It is not the prompt, and not the style fragment

The merge that shipped hours earlier (`a269787`) rewrote the `gouache` fragment from
`thick confident ink outlines` to `no outlines, shapes formed by brushed colour`, which made it the
obvious suspect: unbounded brushed shapes are a plausible way a garment starts reading as a smear.

The trace (Langfuse `019ff9c0-699d-70f0-8b40-704b9b48eaf2`) shows the prod prompt took the
`THIN_DESCRIPTION_FILLER` path — subject `"Miguel, boy, a friendly children's picture-book
character"`, i.e. c0's description carried `species="boy"` and nothing else drawable. A probe
reproduced that prompt exactly, across three fragment arms × two seeds, and screened every draw
through both production classifiers:

| Arm | Fragment | s21 | s7 |
|---|---|---|---|
| `current` | as merged | passed | passed |
| `nobrush` | minus `shapes formed by brushed colour` | passed | passed |
| `old` | pre-merge, `thick confident ink outlines` | passed | primary 429, not classified |

No arm drew anything red at all — the classifiers describe "white short-sleeve shirt, blue shorts",
"white t-shirt with blue horizontal stripes", "pajamas", "a one-piece outfit". The same prompt that
produced the flagged vest produced clean clothing on both seeds. `char_bible` draws references
**unseeded** (`char_bible.py:261`, deliberate), so the red vest was a draw-to-draw variation, not a
property of the prompt. The `gouache` rewrite is exonerated and stays.

### The actual defect

Every other way a reference can be wrong buys three draws. A flag buys none.

| Failure | Detected by | Budget |
|---|---|---|
| Contradicts the child's description | `RefVerdict.contradictions` | `MAX_DRAWS = 3` |
| Carries lettering | `RefVerdict.text_free` | `MAX_DRAWS = 3` |
| Fails moderation | `classify_image_*` | **0 — terminal** |

`moderation-stack.md` §4b step 4 already reached the diagnosis and stopped one step short of the
consequence: *"Character-reference content should never be genuinely harmful; a flag here is almost
certainly the image model misbehaving, not a borderline creative case."* A misbehaving image model
is exactly what a redraw is for. This spec adds the redraw and amends that step.

**Scope.** The reference gate only. `input_gate` is untouched. `output_mod` already owns a
one-retry loop and is untouched. The rubric in `classify_image_backstop` does not move, and neither
classifier loses its veto — what changes is the price of a flag, not the threshold for one.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `characters[].canonical_ref_image`, `characters[].ref_moderation_status`,
  `cost.ref_mod_retry_count`, `cost.ref_retry_count`
- **Writes:** `characters[].canonical_ref_image` (cleared, then rewritten),
  `characters[].ref_moderation_status`, `cost.ref_mod_retry_count`, `cost.image_count`

One additive field, declared LAST in `Cost`, following the documented extension point
(ADR-023 §8) — default-safe, no `schema_version` bump:

```python
class Cost(BaseModel):                 # CC-3
    image_count: int = 0
    regen_count: int = 0
    usd_estimate: float = 0.0
    ref_retry_count: int = 0            # ADR-029 — the 3-tap budget, per book
    ref_mod_retry_count: int = 0        # NEW — moderation redraw cycles, per book
```

**Per book, not per character.** `char_ref_mod` screens every character in one node run, so one
cycle re-mints every character that flagged. The counter measures loop iterations. A book where
both c0 and c1 flag spends one cycle, not two.

### Invariants

1. `ref_mod_retry_count` never exceeds `MAX_MOD_REDRAWS`.
2. A character reaching `reveal` has `ref_moderation_status == "passed"` — unchanged from
   `moderation-stack.md` §2b. The retry does not weaken this; it adds an attempt before the failure.
3. Neither classifier's veto changes. A flag is still a flag.
4. `ref_moderation_status` is `None` only between a mint and its screening.
5. The flagged image is never deleted and never becomes `canonical_ref_image` again.

## 3. Position in the system map

No new nodes. One new edge, from an existing conditional router to an existing node.

```
char_bible ──► char_ref_mod ──► moderation_router
                                      │
                                      ├─ all passed ───────────► reveal
                                      ├─ flagged, budget left ─► char_bible   ◄── NEW
                                      └─ flagged, budget spent ► raise RuntimeError("ref_flagged")
                                                                 → job failed, reason "machine"
```

The middle branch is the whole change. It closes a loop —
`char_bible → char_ref_mod → char_bible` — that can run at most twice.

`moderation_router` is wired without a `path_map` (`graph.py:108`, `graph.py:112`), unlike
`route_reveal` which has an explicit one (`graph.py:118`). A new return label should therefore need
no mapping change — **verify this at the top of the plan**, because a wrong assumption here is a
graph-build error rather than a routing bug.

The loop shape is not new. `route_reveal` already returns `"try_again"` → `char_bible` under a cap
(`graph.py:72`), and ADR-029's retry cycles are already counted in `SUPER_STEP_PRELUDE`.

## 4. Behavior & edge cases

### 4.1 `char_ref_mod` — detect and clear

Two changes to the flag branch (`char_ref_mod.py:55-61`), and one guard at the top of the loop.

On a flag, the node keeps writing `ref_moderation_status="flagged"` **and additionally clears
`canonical_ref_image` to `None`.** Clearing is the entire mechanism: `char_bible.py:377`'s existing
filter is `[c for c in state.characters[:2] if c.canonical_ref_image is None]`, so a cleared
character — and only a cleared character — is picked up for re-minting. `ref_verdict` needs no
clearing; the re-mint overwrites it.

The node holds **no** cap logic and bumps **no** counter. It reports; the router decides; the node
that spends the redraw does the accounting. This mirrors how `_mint_targeted` owns the
`ref_retry_count` bump today.

New guard, before the signed-URL call:

```python
if char.ref_moderation_status == "passed":
    updated.append(char)          # already screened, ref unchanged — do not re-bill the classifiers
    continue
```

Without it the second pass re-screens characters that already passed, paying for two classifier
calls per character to re-derive an answer nothing has invalidated.

The log line gains the counter so a redraw is distinguishable from a terminal flag in prod:

```
char_ref_mod: char_id=%s flagged by backstop (primary=%s) — cleared, ref_mod_retry_count=%d
```

It reports **cycles already spent** and claims nothing about what happens next. The node does not
know: whether this flag buys a redraw or ends the book is the router's decision, one super-step
later, and a log line that guesses would be wrong on exactly the run someone is reading it for.

### 4.2 `moderation_router` — hold the cap

The router stays pure (ADR-024) and gains one branch. The cap lives here for the same reason
`route_reveal`'s does, and its docstring already states the principle: *"The cap is enforced HERE,
not only in the UI."*

```python
if any(c.ref_moderation_status == "flagged" for c in state.characters):
    if state.cost.ref_mod_retry_count < MAX_MOD_REDRAWS:
        return "char_bible"
    raise RuntimeError("ref_flagged")
```

Placed exactly where the current `raise` sits (`graph.py:30-31`), after the `input.moderation`
block and before the `state.scenes` check. The `input_gate` edge shares this router but has no
characters yet, so the new branch is unreachable from there — the same reasoning that already lets
one function serve both edges.

`MAX_MOD_REDRAWS = 1`, defined in `char_ref_mod.py` and imported by `graph.py`, mirroring
`MAX_RETRY_TAPS` living in `reveal.py` and being imported at `graph.py:15`.

### 4.3 `char_bible` — re-mint and account

Two changes to the main path (`char_bible.py:396-411`), both small:

1. **Reset the status.** The `model_copy(update={...})` at `:397` sets `canonical_ref_image`,
   `ref_verdict` and `ref_verdict_prompt_version` but leaves `ref_moderation_status` alone — only
   `_mint_targeted` resets it (`:351`). Without the reset the re-minted character still reads
   `"flagged"`, and the router either raises on a fresh image or spins. Add
   `"ref_moderation_status": None` to the same update.
2. **Bump the counter once per cycle**, not once per character:

```python
was_flagged = any(c.ref_moderation_status == "flagged" for c in selected)
mrc = state.cost.ref_mod_retry_count + (1 if was_flagged else 0)
cost = state.cost.model_copy(update={"image_count": state.cost.image_count + draws_made,
                                     "ref_mod_retry_count": mrc})
```

**`mrc` must be computed BEFORE the minting loop, not after it**, because §4.4's suffix is derived
from it. `char_bible` currently builds `cost` after the loop (`:411`); the counter has to move
above `:387` so `mint_reference` can be handed the right `n`.

The redraw is a full `mint_reference` call — the same 3-draw, judge-gated loop the original got.
Nothing new is drawn or judged differently, so a replacement reference cannot be worse-checked than
the one it replaces. Worst case is +3 images per flagged character, +6 if both flag.

### 4.4 Suffixes — one sequence, not two

`mint_reference` hardcodes `_upload(image, story_id, char_id, 1)` (`:303`, `:312`). It gains an `n`
parameter defaulting to `1`, and both minting paths join the single monotonic per-book sequence
that `_mint_targeted`'s comment already establishes (*"a uniqueness suffix, not a per-character
draw count"*):

```
mint_reference   n = ref_retry_count + ref_mod_retry_count + 1   (ref_mod_retry_count POST-bump)
_mint_targeted   n = ref_retry_count + ref_mod_retry_count + 2   (both counters PRE-bump, as today)
```

The post-bump reading is load-bearing and easy to get wrong: `char_bible` builds `cost` *after* the
minting loop today, so a pre-bump `ref_mod_retry_count` would still be `0` during a redraw and
`n` would come out as `1` — silently overwriting the flagged image this section exists to preserve.
§4.3 moves the counter above the loop for exactly this reason. `_mint_targeted` keeps its existing
pre-bump convention, which its own comment already documents (*"+2 = +1(initial) +1(this tap)"*).

Walked through, with a moderation flag and then two child taps:

| Event | `rc` | `mrc` | Path | Fate |
|---|---|---|---|---|
| initial mint | 0 | 0 | `ref-c0-1.png` | flagged, **kept** |
| moderation redraw | 0 | 1 | `ref-c0-2.png` | passed → canonical |
| child taps a chip | 0 | 1 | `ref-c0-3.png` | canonical |
| child taps again | 1 | 1 | `ref-c0-4.png` | canonical |

The flagged PNG stays in the bucket, unreferenced and undeleted. That is deliberate:
`providers.py:625` marks the backstop's image rubric **⚠️ UNMEASURED** and names
`tests/fixtures/moderation_cases.py` as the guard that does not exist yet. Overwriting in place
destroys the artifact at the moment it becomes evidence. Every future false positive now
accumulates one labelled case at zero additional API cost.

### 4.5 Constants

| Constant | Was | Becomes | Why |
|---|---|---|---|
| `MAX_MOD_REDRAWS` | — | `1` | New, in `char_ref_mod.py` |
| `IMAGE_BUDGET` prelude | `9` | `15` | Today's 9 is 6 (2 refs × 3 draws) + 3 (ADR-029 taps). One moderation cycle can add another 6. |
| `SUPER_STEP_PRELUDE` | `15` | `17` | One extra `char_bible` + `char_ref_mod` pair. |

Both `config.py` comments spell out their arithmetic and must be updated with it, not just the
number — `config.py:142-144` already warns that the two preludes are different units that were
"only ever coincidentally equal at 9".

**`char_bible` has no `IMAGE_BUDGET` breaker.** Only `generate_scene.py:72` and `regenerate.py:40`
carry one. The prelude is bounded by `MAX_MOD_REDRAWS` and `MAX_RETRY_TAPS`, not by cost. This spec
does **not** add a third breaker: the bound is structural and small, and a breaker inside
`char_bible` would be a new ADR-025 D4 surface for a loop that can run at most twice.

### 4.6 Edge cases

| Case | Behaviour |
|---|---|
| Species-only character, no reference drawn | `char_ref_mod.py:12-14` already marks it `"passed"`. Never cleared, never loops. |
| Both c0 and c1 flag | One cycle re-mints both. `ref_mod_retry_count` goes to 1, not 2. |
| c0 flags, c1 passed | Only c0 is cleared and re-minted; §4.1's guard stops c1 being re-screened. |
| The redraw flags too | `RuntimeError("ref_flagged")` → `failure_reason="machine"`, exactly as today. Two independent draws flagging is no longer a coin flip. |
| Primary flags instead of the backstop | Identical path. `char_ref_mod.py:42-46` short-circuits the backstop; the retry is downstream of both. |
| Flag lands on a **tapped** redraw | Falls back to the untargeted 3-draw mint and **loses the child's tapped attribute** — `reference_retry` was consumed by `_mint_targeted` and cleared. Accepted degradation; see §8. |
| Old checkpoint resumed | `ref_mod_retry_count` defaults to `0`, so a resumed book gets a fresh budget. Harmless — the flag is re-derived from the same image. |
| Classifier raises rather than flags | Unchanged: primary error → backstop-only, backstop error → `moderation_error`. The retry is on the *flag* path only. |
| Budget already spent, new flag | Router raises immediately; no clearing is wasted because the job is over. |

### 4.7 Risks

- **A genuinely unsafe reference now gets a second draw.** Mitigated by the redraw being screened
  identically and the cap being 1. The gate is never re-asked about the same pixels — that would be
  rolling dice against our own guard — so the only way through is a *different* image that passes
  on its own merits.
- **The moderation rubric is still unmeasured.** This spec does not fix that; it makes the corpus
  collectable (§4.4) and reduces the blast radius of the false positives it can't yet predict.
- **A persistent false positive costs more than before.** A description that reliably leads
  somewhere red now burns up to 6 extra images before failing. Judged worth it: the same book would
  very likely have died at `output_mod` anyway, later and more expensively.
- **`n = 1` is currently load-bearing somewhere unknown.** `mint_reference` has always uploaded to
  suffix 1; if anything outside `char_bible` reconstructs that path by convention rather than
  reading `canonical_ref_image`, this breaks it. Grep before implementing (§9).

### 4.8 Blast radius

| File | Change |
|---|---|
| `contracts/story_memory.py` | `Cost.ref_mod_retry_count`, declared last |
| `pipeline/char_ref_mod.py` | `MAX_MOD_REDRAWS`; clear on flag; skip already-passed; log the counter |
| `pipeline/graph.py` | One branch in `moderation_router`; one import |
| `pipeline/char_bible.py` | Reset status on mint; bump the counter; `n` parameter on `mint_reference`; suffix arithmetic in `_mint_targeted` |
| `app/config.py` | `IMAGE_BUDGET`, `SUPER_STEP_PRELUDE`, and both comments |
| `docs/specs/moderation-stack.md` | Amend §4b step 4 |

**Not touched:** `classify_image_primary`, `classify_image_backstop`, either rubric, the
backstop's veto, `input_gate`, `output_mod`, `NEGATIVE_PROMPT`, any style fragment, `MAX_DRAWS`,
`MAX_RETRY_TAPS`, `run_job.py`'s failure mapping, the `jobs` table, and any frontend copy.

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-1 Moderation ordering** — unchanged. Text → char-ref → output. The retry inserts a
      redraw *before* the char-ref gate clears, never a path around it.
- [x] **CC-3 Cost control** — one new counter, a hard cap of 1 cycle, and both budget constants
      resized to the new worst case rather than left to trip on it.
- [x] **CC-4 Security** — signed URLs unchanged; the retained flagged image is a Storage object
      under the same RLS as every other reference.
- [x] **CC-5 Observability** — the flag log line carries `ref_mod_retry_count`, so a redraw and a
      terminal flag are distinguishable in prod without a trace.
- [x] **CC-9 Failure states = success states** — a coin-flip flag stops being a dead job. The
      terminal failure keeps its existing `failure_reason="machine"` and its existing copy.
- [x] **CC-10 Checkpointing** — the counter is state, so a resumed book cannot silently reset its
      budget mid-cycle; an old checkpoint resumes with a fresh one (§4.6).

CC-2, CC-6, CC-7, CC-8 untouched.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Models mocked throughout, red first. No assertions on generated content.

**`char_ref_mod`**
1. A backstop flag clears `canonical_ref_image` and leaves `ref_moderation_status == "flagged"`.
2. A primary flag does the same, without calling the backstop.
3. A character already `"passed"` with an unchanged ref is returned untouched and calls neither
   classifier.
4. A character with `canonical_ref_image is None` and no prior status is still marked `"passed"`
   (species-only path, unchanged).
5. The node bumps no counter.

**`moderation_router`**
6. Flagged character, `ref_mod_retry_count < MAX_MOD_REDRAWS` → returns `"char_bible"`.
7. Flagged character, `ref_mod_retry_count == MAX_MOD_REDRAWS` → raises `RuntimeError("ref_flagged")`.
8. All characters `"passed"`, scenes present → returns `"reveal"` (unchanged).
9. No characters, input moderation passed → returns `"analyze"` (unchanged, guards the shared edge).
10. Input moderation failed **and** a character flagged → raises `content_flagged`, not
    `ref_flagged` (ordering, CC-1).

**`char_bible`**
11. A re-mint sets `ref_moderation_status` to `None`.
12. `ref_mod_retry_count` bumps by exactly 1 when two characters arrive flagged.
13. `ref_mod_retry_count` does not bump on a first, unflagged mint.
14. The re-mint uploads to suffix `2` while `ref-c0-1.png` is neither overwritten nor deleted.
15. `_mint_targeted` after a moderation redraw picks a suffix that collides with nothing.

**Graph**
16. flag → redraw → pass reaches `reveal`, with `image_count` reflecting both mints.
17. flag → flag raises `RuntimeError("ref_flagged")` and the graph does not loop a third time.

**Constants**
18. `IMAGE_BUDGET` and `SUPER_STEP_PRELUDE` each equal their documented decomposition, so the
    comment and the number cannot drift apart.

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

No eval harness. What this spec contributes is the input to one: `providers.py:625` names
`tests/fixtures/moderation_cases.py` as the missing guard on an **⚠️ UNMEASURED** rubric, and §4.4
makes every flagged reference a preserved, labelled artifact. Job `4feff195`'s `ref-c0-1.png` is
the first case — a confirmed false positive, with both classifiers' reasoning in the logs and a
6-draw probe showing the same prompt drawing clean.

Building that fixture stays Post-Phase-2 and out of scope here.

## 8. Linked decisions & open questions

**Depends on:** ADR-011c (two-layer moderation), ADR-024 (pure routers, one label each),
ADR-025 (D4 budget breaker; no partial book), ADR-029 (`ref_retry_count`, the tap budget and the
suffix sequence), ADR-023 §8 (additive contract fields).

**Amends:** `moderation-stack.md` §4b step 4 — "→ router fails → job `failed`" becomes
"→ router redraws once, then fails".

**Open questions:**

1. **The tapped-attribute loss (§4.6).** A moderation flag on a child's tapped redraw falls back to
   an untargeted mint and silently drops what the child asked for. Preserving it means either not
   clearing `reference_retry` in `_mint_targeted` or reconstructing it. Rare enough to defer, ugly
   enough to name.
2. **Should a terminal `ref_flagged` say something truer than "machine"?** Considered and declined
   for now — a dedicated `failure_reason` costs an enum value, a `jobs` migration and frontend copy,
   for a path this spec is trying to make rare.
3. **Does anything reconstruct `ref-<id>-1.png` by convention?** §4.7 flags it; §9 makes grepping
   for it a gate on starting.
4. **Is `MAX_MOD_REDRAWS = 1` the right number?** Chosen because a second flag is evidence, not
   noise. Revisit only against a book that failed twice on draws a human judged safe.

## 9. Definition of Done

```
cd backend && uv run ruff check . && uv run pytest
```

**Must be true:**

- [ ] Every test in §6 exists, and each failed before its implementation existed.
- [ ] `git grep -n "ref-.*-1\|_upload(" backend/` run before implementing, confirming nothing
      reconstructs the suffix-1 path by convention (§4.7, open question 3).
- [ ] The `path_map` assumption in §3 verified against a built graph, not assumed.
- [ ] `IMAGE_BUDGET` and `SUPER_STEP_PRELUDE` updated **with their comments**, arithmetic shown.
- [ ] `moderation-stack.md` §4b step 4 amended.
- [ ] Full suite green, and the count reported.

**Must be reported, not silently accepted:**

- Any test in §6 that turns out to be unwritable as specified.
- Any classifier call count that changes for a book where nothing flags.
- Any need to touch a file outside §4.8's list.

**Explicitly NOT in scope:** the backstop rubric or either classifier's veto; a consensus rule
between primary and backstop; `tests/fixtures/moderation_cases.py`; `output_mod`'s retry loop;
`input_gate`; a new `failure_reason`; deleting flagged artifacts; any style fragment or
`NEGATIVE_PROMPT` change.

# Feature Spec — regeneration-controller

**Status:** draft · **Phase:** 1 · **Owner node:** `backend/pipeline/regenerate.py`
**Derived from:** MASTER_SPEC §2 (system map, node-I/O table), §3 (frozen contract), §5 (CC registry), §6 (test seam)
**Rationale:** ADR-003 (conditional edges only at real branch points), ADR-004 (VLM-as-judge, each
character judged separately), ADR-010 (one targeted retry, best-of fallback, never a broken page),
ADR-024 (partial return, sequential per-scene loop, pure routers, `recursion_limit`),
ADR-025 (resilience posture, D4 cost breaker), ADR-028 (`anatomy_intact`, `FailureReason` frozen at 7,
the lexicographic best-of signal)

> Builds ADR-010: the one corrected retry, the `regenerate` node, `route_after_check`, and the
> best-of rule that picks between two failing attempts. Takes the three gaps `consistency-checker`
> §8 handed over. No `contracts/` change — every field it writes already exists.

## 1. Purpose

When the consistency judge fails a scene image, redraw it **once** with a prompt corrected from the
judge's failure reasons, then keep whichever attempt is better. This is the last node of the Phase-1
pipeline loop, and the only place ADR-010 exists in code.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `scenes[]` (`scene_id`, `attempts[]`, `final_image_ref`, `characters_present`, `prompt`);
  `characters[]` (`char_id`, `name`, `description`, `canonical_ref_image`); `style.prompt_fragment`;
  `cost.image_count`; `story_id`.
- **Writes:** `scenes[].attempts` (appends exactly one `Attempt`); `cost.image_count`,
  `cost.regen_count`.
- **Invariants:**
  1. **`regenerate` appends exactly one `Attempt`, or raises. It never returns `{}`.** A `{}` return
     leaves state unchanged, so `consistency_check` re-judges the same attempt, reaches the same
     verdict, and `route_after_check` sends control straight back — an infinite loop bounded only by
     `recursion_limit`. The two guards in §4 are unreachable by construction and therefore raise.
  2. **`regenerate` never writes `final_image_ref`.** `consistency_check` remains its only writer
     (`consistency-checker` invariant 2, unchanged).
  3. **`regenerate` never writes `scenes[].prompt`.** That field holds the original `build_prompt`
     output; per-attempt provenance is `Attempt.prompt`, which is what the contract comment on that
     field says it exists for (CC-5 tracing).
  4. At most **one** regeneration per scene (ADR-010). The budget is `len(scene.attempts)`, derived —
     there is no budget field, for the same reason ADR-024 rejected a loop cursor.
  5. `regenerate` can never send an **uncorrected** prompt: every path that reaches it appends at
     least one clause (§4, *"The correction is total"*). A prompt identical to the previous attempt's
     would be resampling, which ADR-010 rejects.
  6. `cost.regen_count` is incremented on every invocation; `cost.image_count` only when the image
     was actually paid for. The asymmetry is deliberate — see §4.
  7. `scenes[].regeneration_count` is **deliberately not written**. It equals `len(attempts) - 1`,
     and a stored copy of a derived fact is a second source of truth that a resume can desynchronise.

## 3. Position in the system map

This spec builds the branch `consistency-checker` §3 named and deliberately left out.

```
                                        ┌──────────────────────────┐
char_bible ────────────┐                │                          ▼
                       ├─► route_next_scene ─ scene remains ─► generate_scene
                       │        └─ none remain ─► compose            │
                       │                                             ▼
                       └──────────── else ──── route_after_check ◄─ consistency_check
                                                    │                    ▲
                                                    └─ "regenerate" ─► regenerate
```

`graph.py` changes in three places: `add_node("regenerate", regenerate)`; the
`add_conditional_edges("consistency_check", route_next_scene)` registration is re-pointed to
`route_after_check`; and a plain `add_edge("regenerate", "consistency_check")`. `route_next_scene`
keeps its `char_bible` registration and is called *by* `route_after_check`, not replaced by it.

This is ADR-024 Decision 3's reference wiring, unchanged. ADR-003 is unamended — consistency
pass/fail is one of the two branch points it sanctions, and this is that branch.

### `consistency_check` stops finalizing unconditionally

```python
finalize = passed or verdict is None or len(scene.attempts) >= 2
```

The **`verdict is None` term is load-bearing**: an *unchecked* attempt finalizes, it does not retry.
Without it a judge or Storage outage turns every scene into two paid draws with no signal to correct
on — and a redraw chosen by an outage is exactly the uncorrected resample ADR-010 rejects. ADR-025's
posture applies unchanged: the *check* failed, not the artifact. Only a real verdict that says *fail*
buys a retry.

`route_after_check` is pure and holds no policy (ADR-024 Decision 4) — it reads what the node wrote:

```python
def route_after_check(state: StoryMemory) -> str:
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is not None and scene.attempts:
        return "regenerate"
    return route_next_scene(state)
```

The `scene.attempts` guard is load-bearing, not padding: it is what stops `consistency_check`'s
"scene has no attempts → return `{}`" guard from becoming a `check ⇄ regenerate` ping-pong. A scene
with no attempts belongs to `generate_scene`, and `route_next_scene` says so.

**The ADR-024 loop invariant survives.** Every entry into `generate_scene`…`consistency_check` still
finalizes exactly one scene; it now takes at most two node visits instead of one, bounded by
`len(attempts) >= 2`. The loop still terminates because each pass reduces the count of
`final_image_ref is None` scenes by one.

## 4. Behavior & edge cases

### The Storage path must carry the attempt index — a prerequisite, not a choice

`generate_and_store` writes `f"{story_id}/{scene_id}.png"`, and opens with a CC-10 "download it; if
it exists, reuse and don't pay" check. Against a second attempt that check is wrong twice over: it
finds attempt 1, returns `paid=False`, and `regenerate` appends an `Attempt` pointing at attempt 1's
bytes — so attempt 2 is never drawn and best-of ranks one image against itself. Remove the skip and
the upload clobbers attempt 1 instead, leaving best-of nothing to fall back to. **Best-of is
unbuildable until the path is per-attempt.**

```python
def generate_and_store(prompt, story_id, scene_id, attempt_n, ref_paths) -> tuple[str, bool]:
    path = f"{story_id}/{scene_id}-{attempt_n}.png"
```

`attempt_n = len(scene.attempts) + 1` at both call sites. Attempt 1 moves from `{scene_id}.png` to
`{scene_id}-1.png` — uniform beats a special case, and no persisted book depends on the old name.
**CC-10 still composes:** a re-executed super-step recomputes the same `len(attempts)`, hits the same
path, and the skip stays correct. The idempotency property just becomes per-attempt instead of
per-scene. `docs/specs/image-generator.md` is corrected in the same change (§8).

### The correction is total

`passed = same_character and anatomy_intact`, so a scene reaches `regenerate` only when one of those
two is false. Each has a hole where `correct_prompt` would otherwise append **nothing**, making the
retry a pure resample:

| Failure | Hole | Fix |
|---|---|---|
| `anatomy_intact is False` | ADR-028 froze anatomy **out** of `FailureReason`, so no clause exists | `anatomy_intact` param → fixed anatomy clause |
| `same_character is False`, `failure_reasons == []` | The judge named the failure but no reason for it | `same_character` param → generic identity clause, **only when `failure_reasons` is empty** |

```python
def correct_prompt(
    prompt, failure_reasons, characters, style_fragment,
    same_character: bool = True,      # NEW
    anatomy_intact: bool = True,      # NEW
) -> str:
    ...
    clauses = [FAILURE_CLAUSES[r].format(**values) for r in FailureReason if r in present]
    if not same_character and not failure_reasons:
        clauses.append(IDENTITY_CLAUSE)
    if not anatomy_intact:
        clauses.append(ANATOMY_CLAUSE)
    return "\n".join([prompt, *clauses]) if clauses else prompt
```

The two clauses are fixed strings — no `.format`, since neither has a per-character value to fill
(the judge named no reason, or the failure is a rendering property rather than an attribute):

```python
IDENTITY_CLAUSE = "the characters must match the reference images exactly"
ANATOMY_CLAUSE  = "anatomy must be correct: no merged, missing or duplicated body parts"
```

The anatomy wording deliberately mirrors `consistency_check.JUDGE_PROMPT`'s phrasing, so the
correction restates the thing the judge was asked about.

Both are driven by a **boolean**, never an 8th enum value: `FailureReason` stays frozen at 7, so the
closed set Objective 4's F1 is computed over is untouched (ADR-028). The identity clause is guarded
on empty `failure_reasons` so it never duplicates `different_face`. Together the two params make
invariant 5 total. Defaults keep the existing signature call-compatible; `docs/specs/prompt-optimizer.md`
is updated in the same change.

**One asymmetry, recorded so it isn't rediscovered as a bug.** `correct_prompt`'s `wrong_style` clause
re-appends the same `style.prompt_fragment` the prompt already carries, which `consistency-checker`
noted makes a style-only retry near-resample. It never fires alone: `style_match` does not gate, so a
style-only failure never reaches this node. The clause only ever appears alongside a real identity or
anatomy failure.

### The node

Its own file per AGENTS.md ("one module = one concern, one file per pipeline node"), importing
`generate_scene.generate_and_store` rather than restating the effect boundary — the fal upload cache,
the Storage round-trip and the CC-10 skip exist once.

```python
def regenerate(state: StoryMemory) -> dict:
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)   # same rule, no cursor
    if scene is None or not scene.attempts:
        raise RuntimeError(...)                       # invariant 1 — unreachable, never `{}`
    last = scene.attempts[-1]
    if last.prompt is None and scene.prompt is None:
        raise RuntimeError(...)                       # nothing to correct; see below

    if state.cost.image_count >= IMAGE_BUDGET:        # ADR-025 D4, before any spend
        raise RuntimeError(...)

    ref_paths = [...]                                 # identical to generate_scene's loop, below
    v = last.vlm_verdict
    prompt = correct_prompt(
        last.prompt or scene.prompt,
        last.failure_reasons,
        state.characters,
        state.style.prompt_fragment,
        same_character=v.same_character if v else True,
        anatomy_intact=v.anatomy_intact if v else True,
    )
    path, paid = generate_and_store(
        prompt, state.story_id, scene.scene_id, len(scene.attempts) + 1, ref_paths
    )
    return {
        "scenes": [scene.model_copy(update={
            "attempts": [*scene.attempts, Attempt(image_ref=path, prompt=prompt, passed=False)],
        })],
        "cost": state.cost.model_copy(update={
            "image_count": state.cost.image_count + (1 if paid else 0),
            "regen_count": state.cost.regen_count + 1,
        }),
    }
```

`ref_paths` is built by the identical loop `generate_scene` uses — each `char_id` in
`characters_present` that resolves to a `Character` carrying a `canonical_ref_image`, unresolvable ids
skipped and logged. The retry is conditioned on the same references as the original, or it would be
measuring a different thing.

**No prompt to correct → raise.** Unreachable today (`generate_scene` always sets both `Attempt.prompt`
and `Scene.prompt`), and the alternative — drawing from correction clauses with no base prompt — is a
guaranteed-garbage paid image. An ADR-025 hard failure is the honest outcome.

### Best-of, in `consistency_check`

```python
def _rank(a: Attempt) -> tuple[int, int, int, int]:
    """ADR-028's lexicographic signal, with unchecked sorting below every checked attempt."""
    v = a.vlm_verdict
    return (0, 0, 0, 0) if v is None else (1, v.same_character, v.anatomy_intact, v.style_match)

# `updated` replaces the last element, it does not append — len(updated) == len(scene.attempts).
updated   = [*scene.attempts[:-1], attempt.model_copy(update={...the existing fold's writes...})]
finalize  = passed or verdict is None or len(scene.attempts) >= 2
final_ref = max(reversed(updated), key=_rank).image_ref if finalize else None
```

Three things about that expression:

- **Ranking runs over `updated`, not `scene.attempts`** — the attempt judged this pass must carry its
  own verdict into the comparison.
- **`reversed` is required.** Python's `max` returns the *first* maximal element, so plain
  `max(updated, key=_rank)` would keep attempt 1 on a tie. The chosen rule is **tie → attempt 2**: on
  a genuine tie the corrected prompt is the better prior, and ADR-010 calls attempt 2 refinement
  rather than resampling. `reversed` is what implements that.
- **No special case for a passing attempt.** A pass scores `(1, 1, 1, …)` and beats anything that
  gated, so `max` is correct uniformly.

**Unchecked sorts last** (`(0,0,0,0)`), so a checked failure beats an unjudged image. Promoting an
unjudged image over a judged one would let a judge outage silently decide the page, contradicting
`consistency-checker` invariant 4 (*unchecked is never a pass*). Both unchecked → attempt 2, which
falls out of the same rule with no extra branch.

### `regen_count` is not gated on `paid` — and that is not a bug

It sits one line below `image_count`, which *is* gated, so the asymmetry looks like an oversight. It
isn't. On an ADR-025 resume the checkpoint predates this node's return, so both counters start from
their pre-`regenerate` values: `image_count + 0` correctly records that the Storage skip meant no
re-pay, and `regen_count + 1` correctly records the regeneration whose increment the lost checkpoint
never persisted. Gating `regen_count` on `paid` would count it as zero.

### `recursion_limit` — taken here, not left unowned

`run_job.py:34` calls `invoke()` with only `thread_id`. LangGraph's default is **25 super-steps**, and
today's graph costs 5 non-loop nodes plus 2 per scene: a **13-scene book already dies with
`GraphRecursionError`**, before any of this. ADR-024 calls setting it explicitly "required, not
optional"; `consistency-checker` §8 marked it **unowned**. This change takes the loop from 2 deep to 4
— the exact ×4 ADR-024's formula assumes — so leaving it would be shipping a bug this spec doubled.

```python
# app/config.py, beside IMAGE_BUDGET
RECURSION_LIMIT = MAX_SCENES * 4 + 9    # ADR-024: max_scenes × 4 + fixed_prelude
```

Passed as `config={"configurable": {"thread_id": job_id}, "recursion_limit": RECURSION_LIMIT}`. The
`+ 9` is the same prelude term `IMAGE_BUDGET` uses, honouring ADR-025 D4's requirement that the
domain-level and graph-level backstops share **one number**. It is generous today (the prelude is 5)
because ADR-029's Phase-2 `reveal` node will add to it; that is deliberate headroom, not a
miscalculation.

### Edge cases

| Case | Behavior |
|---|---|
| **Attempt 1 passes** | `consistency_check` finalizes; `route_after_check` never returns `"regenerate"`. No second image, no cost. |
| **Attempt 1 unchecked** (`vlm_verdict is None`) | Finalized, **not** retried. A judge outage must not double the image bill for zero signal (§3). |
| **Attempt 1 fails, attempt 2 passes** | Attempt 2 wins best-of on its own score. `final_image_ref` = attempt 2. |
| **Both attempts fail** | Best-of by `_rank`; a real image ships (ADR-010). `Attempt.passed` is `False` on both — the book records that it shipped a failing page. |
| **Attempt 2 unchecked** | `len(updated) >= 2` finalizes; attempt 1 (checked) outranks it. |
| **Both unchecked** | Cannot occur — attempt 1 unchecked finalizes immediately, so there is no attempt 2. Listed because `_rank` handles it anyway (→ attempt 2). |
| **`IMAGE_BUDGET` tripped inside `regenerate`** | Raises, job `failed` (ADR-025 D4). Same posture as `generate_scene`; a retry is not exempt from the breaker. |
| **A `char_id` absent from `state.characters`** | Skipped and logged — identical to `generate_scene` and `consistency_check`. This node may not extend the roster. |
| **No canonical references for the scene** | `ref_paths == []` → `text_to_image`, same branch `generate_scene` takes. The corrected prompt still applies. |
| **Scene has no attempts, or no unfinalized scene** | Raises (invariant 1). Unreachable given `route_after_check`'s guard. |
| **Resume mid-retry** | Storage skip → `paid=False`, `image_count` unchanged, `regen_count + 1`. See above. |

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-5 Observability** — one line per regeneration: `scene_id`, `attempt_n`, the
      `failure_reasons` that drove the correction, `same_character`/`anatomy_intact`, whether the
      identity or anatomy clause fired, `paid`, `prompt_len`. `consistency_check`'s existing line
      gains `attempt=2/2 best_of=1` — without the winner, a book with an off-character page gives no
      way to tell whether the retry ran and lost or never ran at all.
- [x] **CC-10 Checkpointing / resumability** — the per-attempt Storage path preserves
      `image-generator`'s exists-skip at attempt granularity; a re-executed super-step recomputes the
      same path and re-pays nothing. `regen_count`'s ungated increment is correct under resume (§4).
- [ ] **CC-3 Cost control** — *partial, image half closed.* `IMAGE_BUDGET = MAX_SCENES * 2 + 9` already sized
      for two draws per scene, so the breaker needs no change and `regenerate` enforces it before any
      spend. `cost.regen_count` gains its first writer. **Judge calls remain uncounted and this spec
      widens the gap** — a retried scene costs up to 4 judge calls, not 2. Still a `contracts/`
      change, still unowned (§8).
- [ ] **CC-7 Reproducibility (seed)** — **not satisfied, and ADR-010 explicitly asks for it.** ADR-010
      ends *"Control seeds for reproducibility,"* and this is the spec implementing ADR-010. It is
      also where seeds matter most: same seed + corrected prompt isolates the prompt's effect, while a
      free-running seed makes every retry partly a resample however good the correction. `eval.seed`
      exists and stays unwritten — Probe 2 (fal seed determinism) never ran and per
      `PHASE_05_RESULTS.md` does not gate Phase 1. Recorded as **ADR-010 partially satisfied**, not
      silently dropped.
- [ ] **CC-4 Security** — *partial, inherited unchanged.* Durable Storage paths are read and
      persisted, never signed URLs; the fal reference upload is `generate_scene`'s existing boundary.
      No new external exposure.
- [ ] **CC-9 Failure states** — a page can now ship **checked, failed, and finalized** by best-of,
      and nothing surfaces that to a teacher. `consistency-checker` left CC-9 unticked because nothing
      surfaces *"unverified"*; this adds *"verified and failed."* Both are `teacher-dashboard`'s
      (Phase 2). No status field is invented here. The child-facing behaviour is correct and
      deliberate: ADR-010 ships a slightly-off page rather than a placeholder.
- CC-1 (output-image moderation — `moderation-stack`, Phase 2), CC-2 (PII — `input_gate`, upstream),
  CC-6, CC-8: N/A.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

**Node (`regenerate`, `generate_and_store` patched — the node seam), `backend/tests/test_regenerate_node.py`:**
- Appends exactly one `Attempt`; the pre-existing attempt is returned byte-identical.
- `attempt_n` passed to the helper is `len(scene.attempts) + 1`.
- `cost.image_count + 1` when `paid`, unchanged when not; `cost.regen_count + 1` in **both** cases.
- `scenes[].prompt` is unchanged (invariant 3) and `final_image_ref` stays `None` (invariant 2).
- `scenes[].regeneration_count` is unchanged (invariant 7).
- `ref_paths` matches `generate_scene`'s for the same state; an unresolvable `char_id` is skipped
  without raising.
- Raises on: no unfinalized scene, a scene with no attempts, `image_count >= IMAGE_BUDGET`, and no
  prompt on either the attempt or the scene. **Never returns `{}`** (invariant 1).
- The prompt handed to the helper is not equal to `last.prompt` (invariant 5) for every reachable
  verdict: reasons-only, anatomy-only, and `same_character is False` with empty reasons.

**Helper (`correct_prompt`, pure — no mocks), extending `test_prompt_optimizer.py`:**
- `anatomy_intact=False` appends the anatomy clause; `True` appends nothing.
- `same_character=False` with empty `failure_reasons` appends the identity clause.
- `same_character=False` **with** `failure_reasons` appends the reason clauses and **not** the
  identity clause (no duplication with `different_face`).
- Defaults reproduce the current output byte-for-byte — the existing assertions stay green unedited.
- Invariant 3 holds throughout: `prompt` is never dropped.

**Best-of and finalization (`consistency_check`, helper patched), extending `test_consistency_check_node.py`:**
- A checked failure with one attempt → `final_image_ref is None` (defers to `regenerate`).
- An **unchecked** attempt with one attempt → `final_image_ref` **is** set (does not retry).
- A pass with one attempt → finalized.
- Two attempts, both failing → `final_image_ref` is the higher `_rank`; asserted separately for a
  `same_character` win, an `anatomy_intact` win, and a `style_match` win.
- Two attempts, **tied** ranks → attempt 2 wins (the `reversed` behaviour, pinned explicitly).
- Attempt 2 unchecked, attempt 1 checked-failing → attempt 1 wins.
- Attempt 1's `vlm_verdict` is never rewritten on the second pass (invariant 3 of `consistency-checker`).

**Routers (`route_after_check`, pure — no mocks), extending the graph tests:**
- Unfinalized scene **with** attempts → `"regenerate"`.
- Unfinalized scene **without** attempts → `"generate_scene"` (the ping-pong guard).
- All finalized → `"compose"`. Empty `scenes[]` → `"compose"`.

**Graph (loop termination):**
- A two-scene run where scene 1 fails once then passes reaches `compose` with both scenes finalized,
  three attempts total, and `cost.regen_count == 1`.
- A two-scene run where every judge call fails the gate reaches `compose` with four attempts and both
  scenes finalized — the ADR-010 best-of termination test.

**Regression (existing files):**
- `test_generate_scene_node.py`: the `generate_and_store` signature and every `job-1/s0.png`
  assertion become `job-1/s0-1.png`. The two `scene-1.png` collision regressions are preserved, not
  deleted — the per-attempt path must not reintroduce a per-scene collision.
- `run_job.py`: `invoke()` is called with `recursion_limit == RECURSION_LIMIT`.

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

No new instrument. Two rules this spec imposes on the existing ones:

1. **`judge-finetune` / `annotation-surface` join on `pair_id` per attempt, not per scene.** A retried
   scene now contributes **two** judged attempts. Collapsing them to one row would silently drop half
   the corpus, and the two attempts are the most informative pairs it contains — same scene, same
   references, one corrected prompt between them.
2. **`consistency-checker` §7's unchecked-exclusion rule is unchanged and still binding:** an attempt
   with `vlm_verdict is None` has no prediction and is dropped from the agreement denominator.

**The one number worth watching once the corpus exists:** the fraction of retried scenes whose
attempt 2 outranks attempt 1. If it is near chance, ADR-010's "refinement not resampling" premise is
unsupported at this prompt-correction strength, and the honest response is an ADR revisit — not a
higher retry cap, which ADR-010 already rejected.

## 8. Linked decisions & open questions

**Depends on:** ADR-003 (consistency pass/fail is a sanctioned branch point — this is that branch) ·
ADR-004 (each character judged separately; the verdict this node corrects from) · ADR-010 (one
targeted retry, best-of, never a broken page — this spec *is* ADR-010) · ADR-024 (partial return, pure
routers, loop position from `final_image_ref is None`, the loop invariant, `recursion_limit`'s
formula) · ADR-025 (D4 breaker before any spend; a hard failure raises rather than shipping a partial
book; at-least-once re-pay) · ADR-028 (`anatomy_intact`, `FailureReason` frozen at 7, the
lexicographic best-of signal).

**Takes ownership of** (handed over by `consistency-checker` §8): `route_after_check`, the `regenerate`
node, ADR-010's one corrected retry, `correct_prompt` wiring, ADR-028's lexicographic best-of ranking,
the anatomy correction gap, and `recursion_limit`.

**Hands off — named here, owned elsewhere:**
- **A judge-call counter on `Cost` (CC-3)** → **unowned.** A `contracts/` change covering this node,
  `consistency_check` and `char_bible` together. Widened here, flagged rather than absorbed.
- **Surfacing a shipped-but-failing page to a teacher (CC-9)** → **`teacher-dashboard`** (Phase 2).
- **Seed control (CC-7, ADR-010's own clause)** → blocked on **Probe 2**, which does not gate Phase 1.
- **Output-image moderation (CC-1)** → **`moderation-stack`** (Phase 2). Note it must gate **both**
  attempts, not only the finalized one, if the intermediate is ever surfaced.

**Open:**
- **`recursion_limit`'s prelude term is 9 while today's prelude is 5.** Deliberate headroom for
  ADR-029's Phase-2 `reveal` node, and it keeps ADR-025 D4's "one number" promise. If a real book ever
  trips `GraphRecursionError`, the diagnosis is a scene that never finalizes — a logic bug — not a
  limit that is too low.
- **Two base64 images per judge call remains untested against OpenRouter's body limit**
  (`consistency-checker` §8). Unchanged here, but a retried scene doubles the number of such calls.
- **Whether a corrected retry actually beats its predecessor is unmeasured** (§7). ADR-010's premise
  is argued, not evidenced.

## 9. Definition of done

Per AGENTS.md *Definition of Done*. This module is done when **all** of the following hold:

1. `backend/pipeline/regenerate.py` implements §4: the guards that raise, the ADR-025 D4 breaker, the
   `correct_prompt` call with both new booleans, the `generate_and_store` call at
   `len(attempts) + 1`, and the partial return appending one `Attempt` plus both `cost` bumps.
2. `backend/pipeline/prompt_optimizer.py` gains `same_character` and `anatomy_intact` params,
   `IDENTITY_CLAUSE` and `ANATOMY_CLAUSE`. `FailureReason` is **not** touched.
3. `backend/pipeline/generate_scene.py`: `generate_and_store` takes `attempt_n` and writes
   `{story_id}/{scene_id}-{n}.png`; the node passes `len(scene.attempts) + 1`.
4. `backend/pipeline/consistency_check.py`: `_rank`, the `finalize` rule, and
   `max(reversed(updated), key=_rank)`. Its CC-5 line gains the best-of winner.
5. `backend/pipeline/graph.py`: `route_after_check`, the `regenerate` node, the re-pointed
   `consistency_check` registration, and `add_edge("regenerate", "consistency_check")`.
6. `backend/app/config.py` defines `RECURSION_LIMIT`; `backend/worker/run_job.py` passes it to
   `invoke()`.
7. Every §6 assertion exists and passes, in `backend/tests/test_regenerate_node.py` and the named
   existing files.
8. Backend verify is green and its output is **shown, not claimed**:
   `uv run ruff check . && uv run pytest` from `backend/`.
9. **Status line above flips to `built`** with the commit range (MASTER_SPEC §7).
10. **The finding-change grep is run** and every hit fixed in the same change. Known surface:
    - `docs/specs/consistency-checker.md` — §2 invariants 1 and 2, §3 (`route_after_check` "deliberately
      not built" is now built), §4 edge table (*"The attempt fails the gate"*, *"Two attempts already
      exist"*), the ⚠️ anatomy gap, §5 CC-3, §6 (`final_image_ref == attempts[-1].image_ref`), §8
      hand-offs and open items, §9 *Not done* clause.
    - `docs/specs/image-generator.md` — the `generate_and_store` signature and the Storage path scheme.
    - `docs/specs/prompt-optimizer.md` — `correct_prompt`'s signature, the two new clauses, and its
      "no caller yet" note.
    - `docs/product/DECISION_BACKLOG.md` — tick `regeneration-controller`. **Every row in the Phase-1
      feature-spec list is then built**, but `compose` is still a pass-through stub and has **no row
      at all** — it was never added to that list. *"Recommended next session"* must say so rather
      than declaring Phase 1 finished.
    - `docs/WORKFLOW.md` §"Right now".
    - `AGENTS.md` *Validation Notes* **and** *Project Context* — the "Built today" graph line, the
      `compose`-is-the-only-stub claim, and the `regeneration-controller` hand-off list.

**Not done** if: `backend/contracts/` is modified; `FailureReason` gains a value; `regenerate` returns
`{}` on any path; `regenerate` writes `final_image_ref`, `scenes[].prompt`, or
`scenes[].regeneration_count`; a scene can be regenerated twice; the Storage path is not per-attempt;
`correct_prompt` can return its input unchanged on a path `regenerate` reaches; best-of promotes an
unchecked attempt over a checked one; an unchecked attempt triggers a retry; `recursion_limit` is left
unset; or the hand-offs above (the judge counter, the CC-9 teacher signal, seeds) are silently
absorbed.

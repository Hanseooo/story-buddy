# Scene Setting & Subject Binding — Part 3: `consistency_check` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ask the scene judge whether each character is drawn exactly once, record the answer as `subjects_unique`, rank on it — and deliberately **do not gate** on it.

**Architecture:** One file changes. `consistency_check.JUDGE_PROMPT` gains a uniqueness question, asked **after** anatomy and **before** the failure reasons so the wire order still matches the schema (`providers._assert_field_order` rejects a provider that answers out of order). `SceneVerdict` gains the matching field in the same position, the worst-wins fold gains one `all(...)`, `_rank` widens from four terms to five, and the per-scene log line gains the value plus a new `JUDGE_PROMPT_VERSION` module constant. `passed` is **byte-identical to before**.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, ruff, uv. No new dependencies.

**Source spec:** `docs/specs/scene-setting-and-subject-binding.md` (§4.4, §6 tests 18–21, §9 Definition of Done).

**Depends on Part 1:** `VlmVerdict.subjects_unique` must exist. Parts 2 and 3 are independent of each other, but the final sweep in Task 4 assumes both have landed.

## Global Constraints

- Backend commands run from `backend/`: `uv run ruff check .` and `uv run pytest`.
- **`passed` is unchanged.** Its definition stays `verdict is not None and verdict.same_character and verdict.anatomy_intact`, byte-identical. `subjects_unique` does **not** gate. Gating is a follow-up decision blocked on (a) a measured duplicate rate from this telemetry and (b) issue #26 — **not** to be added mid-implementation.
- **Zero new judge calls, zero new image calls.** `subjects_unique` rides the existing per-character judge call. `IMAGE_BUDGET` is untouched.
- **ADR-004 field order is enforced on the wire.** The question's position in the prompt must match the field's position in `SceneVerdict`: after `anatomy_intact`, before `failure_reasons`.
- **`FailureReason` is frozen at 7** (ADR-028) and gains nothing.
- **No new graph node and no new edge.** `backend/pipeline/graph.py` stays untouched; the `consistency_check` pass/fail branch keeps its current condition.
- The judge question must scope to the **character**, not the noun — `"the stars"` in `"she looked up at the stars"` names no character and must stay drawable.
- Deterministic tests only; every `providers.py` call is mocked.
- Every test must be seen **failing first**.

---

## File Structure

| File | Responsibility after this part |
|---|---|
| `backend/pipeline/consistency_check.py` | +`JUDGE_PROMPT_VERSION`, uniqueness question in `JUDGE_PROMPT`, +`SceneVerdict.subjects_unique`, fold, widened `_rank`, log line. |
| `backend/tests/test_consistency_check_node.py` | +6 new tests; `_verdict`/`_attempt` helpers gain a `unique` kwarg; the field-order test updated. |
| `docs/specs/consistency-checker.md` | Behavior changed → updated in the same change. |

---

## Task 1: The judge question, the schema field, and the prompt version

**Files:**
- Modify: `backend/pipeline/consistency_check.py:21-59` (`JUDGE_PROMPT`, `SceneVerdict`)
- Test: `backend/tests/test_consistency_check_node.py:126-139` and new tests

**Interfaces:**
- Consumes: `VlmVerdict.subjects_unique` (Part 1 Task 1).
- Produces: `SceneVerdict.subjects_unique: bool = True`, declared between `anatomy_intact` and `failure_reasons`; module constant `JUDGE_PROMPT_VERSION: int = 2`.

**Why a version constant:** `consistency_check.JUDGE_PROMPT` is unversioned, unlike `char_bible`'s, and that omission has already cost this project one discarded measurement series (the 2026-08-11 rewording changed what a `False` means, and nothing recorded the prompt). Adding a question can shift the answers to the questions already there. This is a **module constant plus the existing log line** — deliberately not a persisted `Attempt` field, which would be a third contract change for a problem logs already make traceable. The underlying gap deserves its own issue.

- [ ] **Step 1: Write the failing tests**

Update the existing field-order test at `backend/tests/test_consistency_check_node.py:132-139`:

```python
    assert names == [
        "differences_observed",
        "same_character",
        "attributes_present",
        "style_match",
        "anatomy_intact",
        "subjects_unique",
        "failure_reasons",
    ]
```

Then append to the same file:

```python
# --- §4.4 D3(b): uniqueness, measured not gated ---

def test_scene_verdict_declares_subjects_unique_between_anatomy_and_the_reasons():
    """ADR-004: the wire order must match the schema, and `providers._assert_field_order` rejects
    a provider that answers out of order. The prompt asks in exactly this order."""
    names = list(SceneVerdict.model_fields)
    assert names.index("anatomy_intact") < names.index("subjects_unique") < names.index("failure_reasons")


def test_the_judge_prompt_asks_the_uniqueness_question_after_anatomy_and_before_the_reasons():
    from pipeline.consistency_check import JUDGE_PROMPT

    assert JUDGE_PROMPT.index("anatomy is intact") < JUDGE_PROMPT.index("drawn exactly once")
    assert JUDGE_PROMPT.index("drawn exactly once") < JUDGE_PROMPT.index("failure reasons")


def test_the_uniqueness_question_scopes_to_the_character_not_the_noun():
    """§4.4: `REFERENCE_CLAUSE` already draws this distinction — "the stars" in "she looked up at
    the stars" names no character and stays drawable. A question phrased "is there more than one
    star" fails a legitimate night sky."""
    from pipeline.consistency_check import JUDGE_PROMPT

    question = JUDGE_PROMPT.format(name="the star")
    assert "the star is drawn exactly once" in question
    assert "not other things of the same kind" in question


def test_scene_verdict_subjects_unique_defaults_to_true():
    """A provider that omits the field must not read as a duplicate — same default as the
    contract field, for the same CC-10 reason."""
    verdict = SceneVerdict(differences_observed="d", same_character=True)
    assert verdict.subjects_unique is True


def test_the_judge_prompt_carries_a_version_constant():
    """§8.2: the prompt is unversioned, and that omission already cost one discarded measurement
    series. A module constant plus the existing log line — not a third contract change."""
    from pipeline.consistency_check import JUDGE_PROMPT_VERSION

    assert JUDGE_PROMPT_VERSION == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_consistency_check_node.py -k "subjects_unique or uniqueness or version_constant or declares_differences_first" -v`
Expected: FAIL — `ImportError: cannot import name 'JUDGE_PROMPT_VERSION'`, `'SceneVerdict' object has no attribute 'subjects_unique'`, and `ValueError: substring not found` on `"drawn exactly once"`.

- [ ] **Step 3: Write the minimal implementation**

In `backend/pipeline/consistency_check.py`, add the version constant above `JUDGE_PROMPT`:

```python
# ponytail: a module constant plus the existing log line, NOT a persisted `Attempt` field —
# that would be a third contract change for a problem logs already make traceable. Bump it on
# every wording change; the ADR-028-style hit rate is only comparable within one version, and the
# 2026-08-11 rewording already cost this project a whole discarded series. Upgrade path: if a
# measurement series ever has to be reconstructed from checkpoints rather than logs, promote this
# to an `Attempt` field the way `Character.ref_verdict_prompt_version` was promoted.
# 1 = pre-2026-08-13; 2 = adds the uniqueness question (scene-setting-and-subject-binding §4.4).
JUDGE_PROMPT_VERSION = 2
```

Replace the last two sentences of `JUDGE_PROMPT` (keep everything above `"and whether the character's anatomy is intact"` exactly as it is):

```python
JUDGE_PROMPT = """\
The FIRST image is the canonical character reference for {name}. The SECOND image is one page of \
the same picture book, in which {name} should appear drawn to match that reference.

First describe every difference you observe between {name} on the page and the reference. Then \
say whether it is the same character; list which of the reference's attributes are actually \
present on the page; whether the page is drawn in the same art style as the reference — the same \
linework, shading and colouring technique — ignoring background, composition, pose, crop and \
expression; whether the character's anatomy is intact, meaning no merged, missing or \
duplicated body parts; and whether {name} is drawn exactly once — count only {name} itself, not \
other things of the same kind that the scene simply contains. Finally list the failure reasons \
that apply, choosing only from the fixed set."""
```

Add the field to `SceneVerdict`, between `anatomy_intact` and `failure_reasons`:

```python
    anatomy_intact: bool = True
    subjects_unique: bool = True                 # §4.4 — asked after anatomy, before the reasons
    failure_reasons: list[FailureReason] = Field(default_factory=list)   # LAST — the closed 7
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_consistency_check_node.py -v`
Expected: PASS, whole file green.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check .
git add backend/pipeline/consistency_check.py backend/tests/test_consistency_check_node.py
git commit -m "feat(consistency-check): ask the judge whether each character is drawn once"
```

---

## Task 2: The fold — worst-wins, and `passed` unchanged

**Files:**
- Modify: `backend/pipeline/consistency_check.py:148-161`
- Test: `backend/tests/test_consistency_check_node.py`

**Interfaces:**
- Consumes: `SceneVerdict.subjects_unique` (Task 1), `VlmVerdict.subjects_unique` (Part 1).
- Produces: `VlmVerdict.subjects_unique` on every written verdict, folded `all(...)` like the other booleans.

- [ ] **Step 1: Write the failing tests**

Update the `_verdict` helper at `backend/tests/test_consistency_check_node.py:31-47` to take the new kwarg:

```python
def _verdict(
    same: bool = True,
    *,
    anatomy: bool = True,
    style: bool = True,
    unique: bool = True,
    attributes: list[str] | None = None,
    reasons: list[FailureReason] | None = None,
    differences: str = "none",
) -> SceneVerdict:
    return SceneVerdict(
        differences_observed=differences,
        same_character=same,
        attributes_present=attributes or [],
        style_match=style,
        anatomy_intact=anatomy,
        subjects_unique=unique,
        failure_reasons=reasons or [],
    )
```

Then append:

```python
def test_one_duplicated_subject_folds_the_whole_verdict_to_not_unique():
    """§6 test 18: worst-wins, like every other folded boolean."""
    state = _state(
        [_scene_with_attempt(characters_present=["c0", "c1"])],
        [_char("c0", "the dog", "job-1/ref-c0.png"), _char("c1", "the cat", "job-1/ref-c1.png")],
    )

    result = _run(state, [_verdict(True, unique=True), _verdict(True, unique=False)])

    assert result["scenes"][0].attempts[-1].vlm_verdict.subjects_unique is False


def test_all_unique_verdicts_fold_to_unique():
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])

    result = _run(state, [_verdict(True, unique=True)])

    assert result["scenes"][0].attempts[-1].vlm_verdict.subjects_unique is True


def test_a_duplicated_subject_alone_does_not_flip_passed():
    """§6 test 19 / §4.4: `passed` is unchanged — `same_character and anatomy_intact`. Gating
    means more regenerations, and issue #26 is open and already critical: prod job f4d0fd74 burned
    500s of a 900s timeout on a 7-scene book. Cost is not the constraint; latency is."""
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])

    result = _run(state, [_verdict(True, anatomy=True, unique=False)])

    attempt = result["scenes"][0].attempts[-1]
    assert attempt.vlm_verdict.subjects_unique is False
    assert attempt.passed is True
    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"    # and it finalized


def test_a_duplicated_subject_alone_does_not_buy_a_regeneration():
    """The consequence of not gating, pinned separately: `route_after_check` must still send this
    scene onward, not back to `regenerate`."""
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])

    result = _run(state, [_verdict(True, unique=False)])
    merged = _state([result["scenes"][0]], [_char("c0", "the dog")])

    assert route_after_check(merged) != "regenerate"


def test_an_unchecked_attempt_writes_no_verdict_and_therefore_no_uniqueness_signal():
    """A judge or Storage outage means *unchecked*, not *unique* — the verdict stays None."""
    state = _state([_scene_with_attempt(characters_present=[])])

    result = _run(state, [])

    assert result["scenes"][0].attempts[-1].vlm_verdict is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_consistency_check_node.py -k "unique or duplicated" -v`
Expected: FAIL — `assert True is False` on the fold test, because `VlmVerdict.subjects_unique` keeps its default when the node never sets it.

- [ ] **Step 3: Write the minimal implementation**

In `consistency_check`, add one line to the `VlmVerdict(...)` construction, after `anatomy_intact`:

```python
            anatomy_intact=all(v.anatomy_intact for v in verdicts),
            subjects_unique=all(v.subjects_unique for v in verdicts),
```

**Do not touch the `passed` line.** It must stay byte-identical:

```python
    passed = verdict is not None and verdict.same_character and verdict.anatomy_intact
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_consistency_check_node.py -v`
Expected: PASS, whole file green.

- [ ] **Step 5: Prove `passed` did not change**

Run: `cd backend && git diff -U0 pipeline/consistency_check.py | grep -E "^[-+].*passed = "`
Expected: **no output** — the `passed` assignment appears in neither the added nor the removed lines.

- [ ] **Step 6: Commit**

```bash
cd backend && uv run ruff check .
git add backend/pipeline/consistency_check.py backend/tests/test_consistency_check_node.py
git commit -m "feat(consistency-check): fold subjects_unique worst-wins without gating on it"
```

---

## Task 3: `_rank` widens to five terms

**Files:**
- Modify: `backend/pipeline/consistency_check.py:95-103`
- Test: `backend/tests/test_consistency_check_node.py`

**Interfaces:**
- Consumes: `VlmVerdict.subjects_unique`.
- Produces: `_rank(a: Attempt) -> tuple[int, int, int, int, int]` — `(1, same_character, anatomy_intact, subjects_unique, style_match)`, unchecked `(0, 0, 0, 0, 0)`.

**Why ranking buys something for free:** when a retry fires for some *other* reason, best-of now prefers the non-duplicated attempt at no extra draw. Precedent for record-and-rank-without-gating is `style_match`, in this same file.

**`subjects_unique` ranks ABOVE `style_match`** — the pre-existing style tie-break tests still hold, because both attempts there default to `subjects_unique=True` and tie on the new term.

- [ ] **Step 1: Write the failing tests**

Update the `_attempt` helper at `backend/tests/test_consistency_check_node.py:380-391`:

```python
def _attempt(
    image_ref: str,
    *,
    same: bool | None = None,
    anatomy: bool = True,
    style: bool = True,
    unique: bool = True,
) -> Attempt:
    """An already-judged attempt. same=None means UNCHECKED (vlm_verdict is None)."""
    if same is None:
        return Attempt(image_ref=image_ref, prompt="p", passed=False)
    return Attempt(
        image_ref=image_ref,
        prompt="p",
        vlm_verdict=VlmVerdict(
            differences_observed="d",
            same_character=same,
            style_match=style,
            anatomy_intact=anatomy,
            subjects_unique=unique,
        ),
        passed=same and anatomy,
    )
```

Add `_rank` to the `pipeline.consistency_check` import, then append:

```python
def test_rank_prefers_the_unique_attempt_when_the_higher_keys_tie():
    """§6 test 20 / §4.4: the free improvement. When a retry fires for some OTHER reason, best-of
    now prefers the non-duplicated attempt at no extra draw."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, unique=False, style=True),
        _attempt("job-1/s0-2.png", same=False, anatomy=True, unique=True, style=True),
    )

    result = _run(
        _state([scene], [_char("c0", "the dog")]),
        [_verdict(False, anatomy=True, unique=True, style=True)],
    )

    assert result["scenes"][0].final_image_ref == "job-1/s0-2.png"


def test_rank_puts_uniqueness_above_style_match():
    """The declared order is (same_character, anatomy_intact, subjects_unique, style_match), so a
    unique-but-off-style attempt beats a duplicated-but-on-style one."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, unique=True, style=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=True, unique=False, style=True),
    )

    result = _run(
        _state([scene], [_char("c0", "the dog")]),
        [_verdict(False, anatomy=True, unique=False, style=True)],
    )

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_rank_puts_uniqueness_below_anatomy():
    """Anatomy GATES and uniqueness does not, so anatomy must outrank it."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, unique=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=False, unique=True),
    )

    result = _run(
        _state([scene], [_char("c0", "the dog")]),
        [_verdict(False, anatomy=False, unique=True)],
    )

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_the_unchecked_rank_tuple_widened_to_five_zeros():
    """§6 test 21: unchecked must still sort below EVERY checked attempt, and a four-tuple
    compared against a five-tuple would raise or mis-order."""
    assert _rank(Attempt(image_ref="job-1/s0-1.png", prompt="p", passed=False)) == (0, 0, 0, 0, 0)


def test_the_checked_rank_tuple_is_five_terms_in_the_declared_order():
    ranked = _rank(_attempt("job-1/s0-1.png", same=True, anatomy=False, unique=True, style=False))
    assert ranked == (1, True, False, True, False)


def test_the_worst_possible_checked_attempt_still_outranks_an_unchecked_one():
    """§6 test 21, the behavioural half. Promoting an unjudged image over a judged one would let
    a judge outage silently decide the page (invariant 4)."""
    worst = _attempt("job-1/s0-1.png", same=False, anatomy=False, unique=False, style=False)
    unchecked = _attempt("job-1/s0-2.png", same=None)

    assert _rank(worst) > _rank(unchecked)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_consistency_check_node.py -k "rank or unique_attempt" -v`
Expected: FAIL — `assert (0, 0, 0, 0) == (0, 0, 0, 0, 0)`, and the tie-break tests pick the wrong attempt because `subjects_unique` is not in the tuple.

- [ ] **Step 3: Write the minimal implementation**

Replace `_rank`:

```python
def _rank(a: Attempt) -> tuple[int, int, int, int, int]:
    """ADR-028's lexicographic best-of signal, with unchecked sorting below every checked attempt.

    A pass scores (1, 1, 1, …) and beats anything that gated, so `max` needs no special case for
    it. Unchecked scores all zeros: promoting an unjudged image over a judged one would let a
    judge outage silently decide the page, contradicting invariant 4 (unchecked is never a pass).

    `subjects_unique` sits between anatomy and style (§4.4): it does not GATE, but when a retry
    fires for some other reason best-of now prefers the non-duplicated attempt at no extra draw.
    Same record-and-rank-without-gating shape `style_match` already has below it.
    """
    v = a.vlm_verdict
    return (
        (0, 0, 0, 0, 0) if v is None
        else (1, v.same_character, v.anatomy_intact, v.subjects_unique, v.style_match)
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_consistency_check_node.py -v`
Expected: PASS, whole file green — including the pre-existing `test_best_of_prefers_the_attempt_that_wins_on_style_when_the_first_two_terms_tie`, which ties on the new term and still resolves on style.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check .
git add backend/pipeline/consistency_check.py backend/tests/test_consistency_check_node.py
git commit -m "feat(consistency-check): rank on subjects_unique between anatomy and style"
```

---

## Task 4: CC-5 — the log line, the spec, and the whole-feature sweep

**Files:**
- Modify: `backend/pipeline/consistency_check.py:189-196` (the per-scene log line)
- Modify: `docs/specs/consistency-checker.md`
- Test: `backend/tests/test_consistency_check_node.py`

**Interfaces:**
- Consumes: `JUDGE_PROMPT_VERSION`, the folded verdict.
- Produces: the CC-5 observability surface. `scenes[].attempts[].vlm_verdict.subjects_unique` is the **first machine-readable duplicate-rate signal in the pipeline** — once N books have run it yields a rate, which is what a gating decision needs and what nobody has today.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_consistency_check_node.py`:

```python
def test_the_per_scene_log_line_carries_uniqueness_and_the_prompt_version(caplog):
    """CC-5: a duplicated page in the finished book traces to a scene, an attempt, the verdict
    that let it through, AND the prompt version that produced the verdict."""
    import logging

    from pipeline.consistency_check import JUDGE_PROMPT_VERSION

    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])
    with caplog.at_level(logging.INFO):
        _run(state, [_verdict(True, unique=False)])

    assert "subjects_unique=False" in caplog.text
    assert f"judge_prompt_version={JUDGE_PROMPT_VERSION}" in caplog.text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && uv run pytest tests/test_consistency_check_node.py -k per_scene_log_line -v`
Expected: FAIL — `assert 'subjects_unique=False' in caplog.text`.

- [ ] **Step 3: Write the minimal implementation**

Extend the existing log call in `consistency_check` — add the two fields to the format string and the two values in matching positions:

```python
    log.info(
        "consistency_check: scene_id=%s attempt=%d/%d subjects=%d %s same_character=%s "
        "anatomy_intact=%s style_match=%s subjects_unique=%s failure_reasons=%s passed=%s "
        "best_of=%s judge_prompt_version=%d",
        scene.scene_id, len(updated), 2, len(subjects), "checked" if verdict else "unchecked",
        verdict and verdict.same_character, verdict and verdict.anatomy_intact,
        verdict and verdict.style_match, verdict and verdict.subjects_unique,
        [r.value for r in reasons], passed,
        None if best is None else best + 1, JUDGE_PROMPT_VERSION,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/test_consistency_check_node.py -v`
Expected: PASS, whole file green.

- [ ] **Step 5: Update `docs/specs/consistency-checker.md`**

Add to the behavior section:

```markdown
### Uniqueness — measured, not gated (`scene-setting-and-subject-binding.md` §4.4)

`JUDGE_PROMPT` asks, after the anatomy question and before the failure reasons, whether the named
character is drawn **exactly once**. The wording scopes to the **character**, not the noun — "the
stars" in "she looked up at the stars" names no character and stays drawable — and its position in
the prompt matches `subjects_unique`'s position in `SceneVerdict`, because
`providers._assert_field_order` rejects a provider that answers out of order.

- Folded worst-wins: `subjects_unique = all(v.subjects_unique for v in verdicts)`.
- Ranked: `_rank` is `(1, same_character, anatomy_intact, subjects_unique, style_match)`; the
  unchecked tuple is `(0, 0, 0, 0, 0)`.
- **Not gated.** `passed` remains `same_character and anatomy_intact`. Gating means more
  regenerations and issue #26 is open and already critical — cost is not the constraint, latency
  is. Precedent for record-and-rank-without-gating is `style_match`, in this same file. Gating is a
  follow-up decision, blocked on a measured duplicate rate and on #26 being closed.
- CC-5: the per-scene log line carries `subjects_unique` and `judge_prompt_version`.

`JUDGE_PROMPT_VERSION` is a module constant, bumped on every wording change. It is deliberately
**not** a persisted `Attempt` field — that would be a third contract change for a problem logs
already make traceable. The underlying gap (this prompt is unversioned in a way `char_bible`'s is
not) deserves its own issue.
```

Add §6 tests 18–21 to the spec's deterministic-test list.

- [ ] **Step 6: Whole-feature verification sweep (spec §9 Definition of Done)**

Run each, and paste the output into the completion report:

```bash
cd backend && uv run ruff check . && uv run pytest
cd ../frontend && pnpm lint && pnpm test          # expected untouched; run to prove it
```

```bash
cd .. && git diff backend/pipeline/graph.py                      # must be EMPTY (no new edge)
git diff backend/pipeline/regenerate.py backend/pipeline/output_mod.py   # must be EMPTY
grep -rn "Image 1 is" backend/ docs/                             # no unfolded-roll assertions left
grep -rn "build_prompt(" backend/ docs/                          # every call/signature is 5-arg
grep -rn "segment_scenes(" backend/                              # every call is 4-arg
```

- [ ] **Step 7: Confirm the 22 assertions and the invariants**

Tick each only after seeing it pass:

- [ ] §6 tests 1–7 and 22 (Part 1), 8–17 (Part 2), 18–21 (Part 3) all exist and pass.
- [ ] Test 4 has **one assertion per constructor site, eight in total** — a single combined test does not satisfy it.
- [ ] Every test was seen **failing first**.
- [ ] All five specs in §4.6 updated in the same change: `story-analyzer.md`, `scene-segmentation.md`, `prompt-optimizer.md`, `image-generator.md`, `consistency-checker.md`. `prompt-optimizer.md`'s invariant 2 explicitly names the location.
- [ ] `passed`'s definition in `consistency_check.py` is byte-identical to before.
- [ ] `referenced_characters` returns its survivors in the same relative order as before, and `build_prompt`'s roll index still matches `generate_scene`'s `ref_paths` index (invariant 4).
- [ ] `CURRENT_SCHEMA_VERSION` is still `1`.

- [ ] **Step 8: Commit**

```bash
git add backend/pipeline/consistency_check.py backend/tests/test_consistency_check_node.py docs/specs/consistency-checker.md
git commit -m "feat(consistency-check): log subjects_unique and the judge prompt version"
```

---

## Task 5: The one real job run (not automatable — do this last, with the human)

The Definition of Done requires evidence no test can produce. This task ships nothing; it produces the report.

- [ ] **Step 1: Run one real job end to end** on a multi-location story, and read the Langfuse trace.

- [ ] **Step 2: Confirm from the trace**
  - a `Setting:` line is present on every page of the multi-location story
  - the roll is folded — `"Image 1 is <name> - <attributes>."`

- [ ] **Step 3: Report, do not silently omit** (spec §9):
  - Whether the §4.3 duplicate-`char_id` hypothesis was **confirmed** against a real trace, or remains a mechanism fixed on principle. **Do not report it as the cause of any observed book without the trace.** It is a hypothesis with a mechanism, not a confirmed diagnosis.
  - The `subjects_unique` values from that run — the first duplicate-rate data point.
  - That D1 and D2 improvements are **eyeballed on one job, not measured** (§7). Seven prompt changes ship together with no eval harness; if output regresses it cannot be attributed. The only real mitigation is that the roll fold is reversible inside one function.

- [ ] **Step 4: File the two follow-up issues named by the spec**
  - `consistency_check.JUDGE_PROMPT` has no persisted version field (§8.2).
  - `analyze` does not check for duplicate character names (§8.3) — §4.3 fixes the consequence in `segment`; whether `analyze` should disambiguate at its own boundary is unsettled.

---

## Explicitly NOT in scope, and not to be added mid-implementation

- Gating on `subjects_unique` (§8.1).
- An eval harness.
- Any `FailureReason` change (frozen at 7, ADR-028).
- Chaining a previous scene's image as an extra reference — rejected: it breaks the `referenced_characters` ordering contract shared by three modules and compounds drift page over page.
- Reducing the number of references sent per scene — rejected: incoherent without also changing `characters_present`, which would make `character_absent` fire for characters deliberately withheld.
- A location judge (§4.5.2) — rejected for cost, not merit. It is a new paid VLM call per book, which is an ADR.

## Risks this change carries, stated not solved (spec §4.5)

1. **Unmeasurable.** Seven prompt changes ship together with no eval harness.
2. **Location descriptions are unjudged**, and a wrong one repeats onto **every** page in that location — a worse blast radius than a wrong character description. This is the one new failure mode this spec creates, accepted deliberately.
3. **Setting-vs-excerpt conflict is reduced, not eliminated.**
4. **Attribute bleeding is reduced, not fixed** — Qwen-Image-Edit composites; nothing here changes the model.
5. **D3 is measured, not fixed.** Duplicated pages still reach the child. The deliverable is a number and a free ranking preference, not a guarantee.
6. **A location name is not redacted.** `providers.py:310-327` deliberately excludes `LOCATION` from the allowlist. This spec **repeats** that exposure across more pages; it does not create it. Not a new CC-2 surface, but a wider one.
7. **`JUDGE_PROMPT` was unversioned.** Adding a question can shift the answers to the questions already there. Mitigated cheaply by the module constant, not fully.

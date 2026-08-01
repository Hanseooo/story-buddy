# Regeneration Controller — Part 1: Prerequisites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/specs/regeneration-controller.md`
**Part 2:** `docs/specs/plans/2026-08-02-regeneration-controller-part-2-retry-loop.md` — do not start it until this plan is complete and `uv run ruff check . && uv run pytest` is green.

**Goal:** Land the three changes ADR-010's retry loop cannot be built on top of — an explicit `recursion_limit`, a per-attempt Storage path, and a `correct_prompt` that can never return its input unchanged — without changing any routing behaviour.

**Architecture:** Three independent edits to existing files. Task 1 fixes a live `GraphRecursionError` bug on `main` (a 13-scene book already dies today). Task 2 moves `generate_and_store`'s Storage path from `{scene_id}.png` to `{scene_id}-{n}.png`, which is what makes a second attempt a *different object* instead of the CC-10 exists-skip handing attempt 1's own bytes back. Task 3 gives `correct_prompt` two boolean parameters so an anatomy-only or reason-less identity failure produces a real correction clause rather than a pure resample. After all three, the pipeline behaves exactly as it does today — nothing routes anywhere new until Part 2.

**Tech Stack:** Python 3.12, uv, pytest, ruff, Pydantic v2, LangGraph 1.2.8, Supabase Storage.

## Global Constraints

Copied verbatim from `AGENTS.md` and the spec. Every task's requirements implicitly include this section.

- **`backend/contracts/` must not be modified.** Not one field. The spec's *Not done* clause names this first.
- **`FailureReason` must not gain a value.** It is frozen at 7 permanently (ADR-028). Corrections that fall outside the 7 are driven by **booleans**, never an 8th enum member.
- **All commands run from `backend/`.** Verify with `uv run ruff check . && uv run pytest`. Never `pip`, never `poetry`, never a bare `python`.
- **Deterministic tests mock every `providers.py` call.** Never assert on generated content.
- **`ruff format` is not adopted.** Only `ruff check`. Do not reformat files you touch.
- **Surgical changes only.** Every changed line traces to a task step. Do not improve adjacent code, comments, or formatting.
- **One module = one concern, one file per pipeline node.**
- Model IDs live in `backend/app/config.py`; provider SDKs/endpoints/keys live in `backend/providers.py` and nowhere else.
- Existing constants, exact values: `MAX_SCENES = 15`, `IMAGE_BUDGET = MAX_SCENES * 2 + 9` (= 39), `BUCKET = "storybook-images"`.
- New constant, exact value: `RECURSION_LIMIT = MAX_SCENES * 4 + 9` (= 69).
- New Storage path scheme, exact form: `f"{story_id}/{scene_id}-{attempt_n}.png"`.
- New clause strings, exact text:
  - `IDENTITY_CLAUSE = "the characters must match the reference images exactly"`
  - `ANATOMY_CLAUSE  = "anatomy must be correct: no merged, missing or duplicated body parts"`

## File Structure

| File | Task | Responsibility after this plan |
|---|---|---|
| `backend/app/config.py` | 1 | Adds `RECURSION_LIMIT` beside `IMAGE_BUDGET`, so ADR-025 D4's domain breaker and LangGraph's graph-level backstop derive from the one `MAX_SCENES`. |
| `backend/worker/run_job.py` | 1 | Passes `recursion_limit` into `invoke()`'s config alongside `thread_id`. |
| `backend/tests/test_config.py` | 1 | Pins the `RECURSION_LIMIT` formula. |
| `backend/tests/test_run_job.py` | 1 | Pins that the worker actually passes it. |
| `backend/pipeline/generate_scene.py` | 2 | `generate_and_store` gains `attempt_n` and writes a per-attempt path; the node passes `len(scene.attempts) + 1`. |
| `backend/tests/test_generate_scene_node.py` | 2 | Path assertions become `-1.png`; the two collision regressions are preserved, not deleted. |
| `backend/tests/test_graph_stub.py` | 2 | The `generate_and_store` stub gains `attempt_n`; `final_image_ref` assertion becomes `stub/s0-1.png`. |
| `backend/pipeline/prompt_optimizer.py` | 3 | `correct_prompt` gains `same_character` / `anatomy_intact` params and the two fixed clauses. `FailureReason` untouched. |
| `backend/tests/test_prompt_optimizer.py` | 3 | New cases for both booleans; every existing assertion stays green **unedited**. |
| `docs/specs/image-generator.md` | 2 | Signature + path scheme corrected in the same change. |
| `docs/specs/prompt-optimizer.md` | 3 | Signature + the two clauses + the "no caller yet" note corrected in the same change. |

---

### Task 1: Explicit `recursion_limit`

This is a **live bug on `main`, independent of the retry loop.** `run_job.py:35` calls `invoke()` with only `thread_id`, so LangGraph's default of 25 super-steps applies. Today's graph costs 5 non-loop nodes plus 2 per scene, so a 13-scene book raises `GraphRecursionError` before any of this work. Part 2 takes the loop from 2 deep to 4, which is why the spec takes ownership here rather than leaving it unowned.

**Files:**
- Modify: `backend/app/config.py:66-67` (append below `IMAGE_BUDGET`)
- Modify: `backend/worker/run_job.py:3` (import) and `backend/worker/run_job.py:34-36` (the `invoke` call)
- Test: `backend/tests/test_config.py` (append), `backend/tests/test_run_job.py` (append)

**Interfaces:**
- Consumes: `MAX_SCENES` from `app.config` (already exists, value `15`).
- Produces: `app.config.RECURSION_LIMIT: int` — value `69`. Part 2 does not read it; only `run_job.py` and the two tests do.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_config.py`:

```python
def test_recursion_limit_derives_from_max_scenes_at_four_visits_per_scene():
    """ADR-024's formula: max_scenes × 4 + fixed_prelude. The ×4 is generate_scene,
    consistency_check, regenerate, consistency_check — the deepest a single scene can go."""
    assert RECURSION_LIMIT == MAX_SCENES * 4 + 9


def test_recursion_limit_shares_its_prelude_term_with_image_budget():
    """ADR-025 D4: the domain-level and graph-level backstops share ONE number.
    The prelude is 9 in both, deliberately generous today (it is really 5) to leave
    headroom for ADR-029's Phase-2 `reveal` node."""
    assert RECURSION_LIMIT - MAX_SCENES * 4 == IMAGE_BUDGET - MAX_SCENES * 2
```

and change that file's import line (`backend/tests/test_config.py:1`) to:

```python
from app.config import IMAGE_BUDGET, MAX_SCENES, RECURSION_LIMIT, STYLE_PRESETS, settings
```

Append to `backend/tests/test_run_job.py`:

```python
def test_run_storybook_job_passes_the_recursion_limit_to_invoke():
    """Spec §6 regression: without this, LangGraph's default of 25 super-steps applies and a
    13-scene book dies with GraphRecursionError before it ever reaches compose."""
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    config = fake_graph.invoke.call_args.kwargs["config"]
    assert config["recursion_limit"] == RECURSION_LIMIT
    assert config["configurable"]["thread_id"] == "job-1"
```

and change that file's config import (`backend/tests/test_run_job.py:3`) to:

```python
from app.config import RECURSION_LIMIT, STYLE_PRESETS
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_config.py tests/test_run_job.py -v`
Expected: FAIL — collection errors, `ImportError: cannot import name 'RECURSION_LIMIT' from 'app.config'`.

- [ ] **Step 3: Add the constant**

Append to `backend/app/config.py`, directly below the `IMAGE_BUDGET` line:

```python
# Spec `docs/specs/regeneration-controller.md` §4: LangGraph's graph-level backstop.
# ADR-024's formula — max_scenes × 4 + fixed_prelude. The ×4 is the deepest a single scene
# can go: generate_scene → consistency_check → regenerate → consistency_check. The prelude
# term is 9, the same one IMAGE_BUDGET uses (ADR-025 D4: the two backstops share one number).
# It is generous — today's prelude is 5 — as deliberate headroom for ADR-029's `reveal` node.
RECURSION_LIMIT = MAX_SCENES * 4 + 9
```

- [ ] **Step 4: Pass it from the worker**

In `backend/worker/run_job.py`, change the config import (line 3) from:

```python
from app.config import STYLE_PRESETS, settings
```

to:

```python
from app.config import RECURSION_LIMIT, STYLE_PRESETS, settings
```

and change the `invoke` call (lines 34-36) from:

```python
            result = app_graph.invoke(
                initial_state, config={"configurable": {"thread_id": job_id}}
            )
```

to:

```python
            result = app_graph.invoke(
                initial_state,
                config={
                    "configurable": {"thread_id": job_id},
                    "recursion_limit": RECURSION_LIMIT,
                },
            )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_config.py tests/test_run_job.py -v`
Expected: PASS — 3 new tests plus the 9 that were already there.

- [ ] **Step 6: Run the full backend verify**

Run: `uv run ruff check . && uv run pytest`
Expected: all green. No existing test asserted on `invoke`'s config, so nothing else moves.

- [ ] **Step 7: Commit**

```bash
git add backend/app/config.py backend/worker/run_job.py backend/tests/test_config.py backend/tests/test_run_job.py
git commit -m "fix(worker): set recursion_limit explicitly — a 13-scene book died on the default 25"
```

---

### Task 2: Per-attempt Storage path

**This is the prerequisite that would otherwise silently break best-of, not a design preference.** `generate_and_store` opens with a CC-10 "download it; if it exists, reuse and don't pay" skip. Against a second attempt at the same path that check is wrong twice over: it finds attempt 1, returns `paid=False`, and the caller appends an `Attempt` pointing at **attempt 1's own bytes** — so attempt 2 is never drawn, and Part 2's best-of ranks an image against itself and always reports a tie. Removing the skip instead makes the upload clobber attempt 1, leaving best-of nothing to fall back to.

CC-10 still composes after this change: a re-executed super-step recomputes the same `len(attempts)`, hits the same path, and the skip stays correct. The idempotency property just becomes per-attempt instead of per-scene.

Attempt 1 moves from `{scene_id}.png` to `{scene_id}-1.png`. Uniform beats a special case, and no persisted book depends on the old name.

**Files:**
- Modify: `backend/pipeline/generate_scene.py:27-35` (signature + path) and `backend/pipeline/generate_scene.py:84` (the call site)
- Modify: `backend/tests/test_generate_scene_node.py` (path assertions)
- Modify: `backend/tests/test_graph_stub.py:53-56` (the stub lambda) and `:100` (the `final_image_ref` assertion)
- Modify: `docs/specs/image-generator.md`

**Interfaces:**
- Consumes: nothing new.
- Produces: `generate_and_store(prompt: str, story_id: str, scene_id: str, attempt_n: int, ref_paths: list[str]) -> tuple[str, bool]`. `attempt_n` is 1-based and sits **fourth**, before `ref_paths`. Part 2's `regenerate` imports this exact function and calls it with `len(scene.attempts) + 1`.

- [ ] **Step 1: Write the failing tests**

Replace the four `generate_and_store` tests in `backend/tests/test_generate_scene_node.py` (lines 84-139) with these five — note the new one at the end, which is the whole point of the change:

```python
def test_generate_and_store_uploads_image_bytes_and_returns_paid_true():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.text_to_image", return_value=b"fake-png-bytes"), \
         patch("pipeline.generate_scene._fal_ref_url"):
        path, paid = generate_and_store("a friendly dog", "job-123", "s0", 1, [])

    assert path == "job-123/s0-1.png"
    assert paid is True
    fake_supabase.storage.from_.assert_called_with("storybook-images")
    fake_supabase.storage.from_.return_value.upload.assert_called_once()


def test_generate_and_store_reuses_existing_storage_asset():
    """CC-10: a re-executed super-step is free. Now per-ATTEMPT, not per-scene."""
    fake_supabase = _make_supabase(has_existing=True)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.edit_image") as mock_edit, \
         patch("pipeline.generate_scene.text_to_image") as mock_text:
        path, paid = generate_and_store("a dog", "job-1", "s0", 1, [])

    assert path == "job-1/s0-1.png"
    assert paid is False
    mock_edit.assert_not_called()
    mock_text.assert_not_called()


def test_generate_and_store_calls_edit_image_when_refs_given():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene._fal_ref_url", side_effect=lambda p: f"https://fal/{p}"), \
         patch("pipeline.generate_scene.edit_image", return_value=b"img-bytes") as mock_edit, \
         patch("pipeline.generate_scene.text_to_image") as mock_text:
        path, paid = generate_and_store("a dog", "job-1", "s0", 1, ["ref-c0.png"])

    assert path == "job-1/s0-1.png"
    assert paid is True
    mock_edit.assert_called_once_with("a dog", ["https://fal/ref-c0.png"])
    mock_text.assert_not_called()


def test_generate_and_store_calls_text_to_image_when_no_refs():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.text_to_image", return_value=b"img-bytes") as mock_text, \
         patch("pipeline.generate_scene.edit_image") as mock_edit:
        path, paid = generate_and_store("a dog", "job-1", "s0", 1, [])

    assert path == "job-1/s0-1.png"
    assert paid is True
    mock_text.assert_called_once_with("a dog")
    mock_edit.assert_not_called()


def test_generate_and_store_gives_two_attempts_of_one_scene_distinct_paths():
    """The prerequisite for ADR-010 best-of (spec §4). At a shared per-scene path the CC-10
    exists-skip would find attempt 1, return paid=False, and hand back attempt 1's OWN bytes —
    so attempt 2 is never drawn and best-of ranks an image against itself."""
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.text_to_image", return_value=b"img-bytes"):
        path1, _ = generate_and_store("a dog", "job-1", "s0", 1, [])
        path2, _ = generate_and_store("a corrected dog", "job-1", "s0", 2, [])

    assert path1 == "job-1/s0-1.png"
    assert path2 == "job-1/s0-2.png"
    assert path1 != path2
```

Then update the four node-seam assertions further down the same file. Change line 158 from `assert scene.attempts[-1].image_ref == "job-123/s0.png"` — and every other `("job-123/s0.png", True)` / `("job-123/s1.png", True)` / `("job-123/scene-abc.png", True)` return value — to the `-1` form, and update the three `mock_store.assert_called_once_with(...)` calls to include the new argument. Concretely, the three that assert on arguments become:

```python
    mock_store.assert_called_once_with("p", "job-123", "scene-abc", 1, [])
```
```python
    mock_store.assert_called_once_with("p", "job-123", "s0", 1, ["job-123/ref-c0.png"])
```

The `assert_called_once_with("p", "job-123", "s0", 1, ["job-123/ref-c0.png"])` form applies to all three of
`test_generate_scene_collects_refs_only_for_present_characters_with_canonical_images`,
`test_generate_scene_skips_absent_char_id_when_collecting_refs`, and
`test_generate_scene_includes_ref_even_when_verdict_failed`.

Add one node-seam test pinning the new argument:

```python
def test_generate_scene_passes_attempt_n_of_one_for_a_scene_with_no_attempts():
    """Spec §6: attempt_n is len(scene.attempts) + 1 at BOTH call sites. generate_scene only
    ever sees a scene with no attempts, so it is always 1 here — regenerate is where it is 2."""
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)) as mock_store:
        generate_scene(state)

    assert mock_store.call_args.args[3] == 1
```

**Do not delete** `test_generate_scene_uses_scene_id_in_storage_path` or
`test_generate_scene_two_successive_invocations_produce_distinct_paths`. Those are the two
`scene-1.png` collision regressions; the per-attempt path must not reintroduce a per-scene
collision. Only their path strings change.

In `backend/tests/test_graph_stub.py`, change the stub (lines 53-56):

```python
    monkeypatch.setattr(
        "pipeline.generate_scene.generate_and_store",
        lambda prompt, story_id, scene_id, attempt_n, ref_paths: (f"stub/{scene_id}-{attempt_n}.png", True),
    )
```

and line 100:

```python
    assert result["scenes"][0].final_image_ref == "stub/s0-1.png"
```

and line 175:

```python
    assert [s.final_image_ref for s in result["scenes"]] == ["stub/s0-1.png", "stub/s1-1.png"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_generate_scene_node.py tests/test_graph_stub.py -v`
Expected: FAIL with `TypeError: generate_and_store() takes 4 positional arguments but 5 were given`, plus assertion failures on the `-1.png` paths.

- [ ] **Step 3: Change the signature and the path**

In `backend/pipeline/generate_scene.py`, change lines 27-35 from:

```python
def generate_and_store(
    prompt: str, story_id: str, scene_id: str, ref_paths: list[str]
) -> tuple[str, bool]:
    """The node's ONE effect boundary (MASTER_SPEC §6). Returns (storage_path, paid).

    CC-10: if the path already exists in Storage, reuse it — a re-executed
    super-step is free. The Attempt is still appended by the caller.
    """
    path = f"{story_id}/{scene_id}.png"
```

to:

```python
def generate_and_store(
    prompt: str, story_id: str, scene_id: str, attempt_n: int, ref_paths: list[str]
) -> tuple[str, bool]:
    """The node's ONE effect boundary (MASTER_SPEC §6). Returns (storage_path, paid).

    CC-10: if the path already exists in Storage, reuse it — a re-executed
    super-step is free. The Attempt is still appended by the caller.

    The path carries `attempt_n` (1-based) because ADR-010's best-of needs two DISTINCT
    objects: at a shared per-scene path the exists-skip above would hand attempt 2 back
    attempt 1's own bytes, and best-of would rank an image against itself. The skip stays
    correct — a re-executed super-step recomputes the same len(attempts) and the same path —
    it is just per-attempt idempotency now instead of per-scene.
    """
    path = f"{story_id}/{scene_id}-{attempt_n}.png"
```

and the call site (line 84) from:

```python
    path, paid = generate_and_store(prompt, state.story_id, scene.scene_id, ref_paths)
```

to:

```python
    path, paid = generate_and_store(
        prompt, state.story_id, scene.scene_id, len(scene.attempts) + 1, ref_paths
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_generate_scene_node.py tests/test_graph_stub.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend verify**

Run: `uv run ruff check . && uv run pytest`
Expected: all green.

- [ ] **Step 6: Correct `docs/specs/image-generator.md` in the same change**

Grep the spec for what moved and fix every hit — the spec's own DoD item 10 requires it:

```bash
grep -n 'generate_and_store\|{scene_id}.png\|s0\.png\|scene_id}\.png' docs/specs/image-generator.md
```

For each hit: update the `generate_and_store` signature to include `attempt_n: int` in fourth position, change the path scheme from `{story_id}/{scene_id}.png` to `{story_id}/{scene_id}-{attempt_n}.png`, and add one sentence recording *why* — CC-10's exists-skip is now per-attempt, and a shared per-scene path would make ADR-010's best-of rank an image against itself. Do not restate the whole rationale; point at `docs/specs/regeneration-controller.md` §4.

- [ ] **Step 7: Commit**

```bash
git add backend/pipeline/generate_scene.py backend/tests/test_generate_scene_node.py backend/tests/test_graph_stub.py docs/specs/image-generator.md
git commit -m "feat(image-generator): per-attempt Storage path — the prerequisite for ADR-010 best-of"
```

---

### Task 3: `correct_prompt` can never resample

`passed = same_character and anatomy_intact`, so a scene reaches the retry only when one of those two is false. Each has a hole where `correct_prompt` appends **nothing** today, making the retry a pure resample — which ADR-010 explicitly rejects:

| Failure | Hole | Fix |
|---|---|---|
| `anatomy_intact is False` | ADR-028 froze anatomy **out** of `FailureReason`, so no clause exists | `anatomy_intact` param → fixed anatomy clause |
| `same_character is False`, `failure_reasons == []` | The judge named the failure but no reason for it | `same_character` param → generic identity clause, **only when `failure_reasons` is empty** |

Both are driven by a **boolean, never an 8th enum value** — `FailureReason` stays frozen at 7, so the closed set Objective 4's F1 is computed over is untouched. The identity clause is guarded on empty `failure_reasons` so it never duplicates `different_face`. The anatomy wording deliberately mirrors `consistency_check.JUDGE_PROMPT`'s phrasing, so the correction restates the thing the judge was asked about.

**Files:**
- Modify: `backend/pipeline/prompt_optimizer.py:66-95`
- Test: `backend/tests/test_prompt_optimizer.py` (append only — existing assertions stay unedited)
- Modify: `docs/specs/prompt-optimizer.md`

**Interfaces:**
- Consumes: `FailureReason`, `Character` from `contracts.story_memory` (already imported at `prompt_optimizer.py:11`).
- Produces:
  ```python
  IDENTITY_CLAUSE: str
  ANATOMY_CLAUSE: str

  def correct_prompt(
      prompt: str,
      failure_reasons: list[FailureReason],
      characters: list[Character],
      style_fragment: str | None,
      same_character: bool = True,
      anatomy_intact: bool = True,
  ) -> str
  ```
  Both new params are keyword-defaulted so the existing 4-positional-arg signature stays call-compatible. Part 2's `regenerate` passes both by keyword.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_prompt_optimizer.py`:

```python
# --- regeneration-controller §4: the two booleans that make the correction total ---

def test_correct_prompt_anatomy_intact_false_appends_the_anatomy_clause():
    """ADR-028 froze anatomy OUT of FailureReason, so an anatomy-only failure yields no
    reason clause. Without this the retry is a pure resample — what ADR-010 rejects."""
    result = correct_prompt("draw a dog", [], [], "cel", anatomy_intact=False)

    assert result.startswith("draw a dog")
    assert ANATOMY_CLAUSE in result


def test_correct_prompt_anatomy_intact_true_appends_nothing():
    assert correct_prompt("draw a dog", [], [], "cel", anatomy_intact=True) == "draw a dog"


def test_correct_prompt_same_character_false_with_no_reasons_appends_the_identity_clause():
    """The judge named the failure but no reason for it — a generic identity clause is the
    only correction available, and it beats resampling."""
    result = correct_prompt("draw a dog", [], [], "cel", same_character=False)

    assert result.startswith("draw a dog")
    assert IDENTITY_CLAUSE in result


def test_correct_prompt_same_character_false_with_reasons_omits_the_identity_clause():
    """Guarded on EMPTY failure_reasons so it never duplicates different_face."""
    result = correct_prompt(
        "draw a dog", [FailureReason.different_face], [], "cel", same_character=False
    )

    assert IDENTITY_CLAUSE not in result
    assert "match the reference character's face exactly" in result


def test_correct_prompt_both_booleans_false_appends_identity_then_anatomy():
    result = correct_prompt("draw a dog", [], [], "cel", same_character=False, anatomy_intact=False)

    assert result.index(IDENTITY_CLAUSE) < result.index(ANATOMY_CLAUSE)


def test_correct_prompt_reason_clauses_precede_the_two_boolean_clauses():
    """Enum-order reason clauses first, then identity, then anatomy — so a reader of the
    prompt sees the specific corrections before the generic ones."""
    result = correct_prompt(
        "draw a dog",
        [FailureReason.different_face],
        [],
        "cel",
        same_character=False,
        anatomy_intact=False,
    )

    assert result.index("match the reference character's face exactly") < result.index(ANATOMY_CLAUSE)


def test_correct_prompt_defaults_reproduce_the_previous_behaviour_exactly():
    """The existing call signature stays byte-compatible: four positional args, no clauses
    added by the new params. Every pre-existing assertion in this file depends on it."""
    assert correct_prompt("draw a dog", [], [], "cel") == "draw a dog"
    assert correct_prompt("draw a dog", [FailureReason.different_face], [], "cel") == (
        "draw a dog\nmatch the reference character's face exactly"
    )


def test_correct_prompt_never_drops_the_base_prompt_under_either_boolean():
    """Invariant 3: correct_prompt only ever APPENDS."""
    for kwargs in ({"same_character": False}, {"anatomy_intact": False}):
        result = correct_prompt("the base prompt survives", [], [], "cel", **kwargs)
        assert "the base prompt survives" in result
```

and change the import line (`backend/tests/test_prompt_optimizer.py:2`) to:

```python
from pipeline.prompt_optimizer import ANATOMY_CLAUSE, IDENTITY_CLAUSE, build_prompt, correct_prompt
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_prompt_optimizer.py -v`
Expected: FAIL — `ImportError: cannot import name 'ANATOMY_CLAUSE' from 'pipeline.prompt_optimizer'`.

- [ ] **Step 3: Add the clauses and the two params**

In `backend/pipeline/prompt_optimizer.py`, insert directly below the `FAILURE_CLAUSES` dict (after line 66):

```python
# The two corrections that have no FailureReason to hang on (spec `regeneration-controller` §4).
# Fixed strings, no .format — neither has a per-character value to fill: the judge named no
# reason, or the failure is a rendering property rather than an attribute. Driven by a BOOLEAN,
# never an 8th enum value — FailureReason stays frozen at 7 (ADR-028), so the closed set
# Objective 4's F1 is computed over is untouched.
IDENTITY_CLAUSE = "the characters must match the reference images exactly"
# Mirrors consistency_check.JUDGE_PROMPT's phrasing, so the correction restates the thing the
# judge was actually asked about.
ANATOMY_CLAUSE = "anatomy must be correct: no merged, missing or duplicated body parts"
```

Then change the `correct_prompt` signature (lines 69-74) from:

```python
def correct_prompt(
    prompt: str,
    failure_reasons: list[FailureReason],
    characters: list[Character],
    style_fragment: str | None,
) -> str:
```

to:

```python
def correct_prompt(
    prompt: str,
    failure_reasons: list[FailureReason],
    characters: list[Character],
    style_fragment: str | None,
    same_character: bool = True,
    anatomy_intact: bool = True,
) -> str:
```

Append to its docstring, after the existing "Attribution ceiling" paragraph:

```
    `same_character` / `anatomy_intact` close the two holes where the reason clauses alone
    append NOTHING, which would make the retry a pure resample (ADR-010 rejects resampling).
    Defaulted so the four-positional-arg signature stays call-compatible.
```

and change the clause-building lines (93-95) from:

```python
    present = set(failure_reasons)
    clauses = [FAILURE_CLAUSES[reason].format(**values) for reason in FailureReason if reason in present]
    return "\n".join([prompt, *clauses]) if clauses else prompt
```

to:

```python
    present = set(failure_reasons)
    clauses = [FAILURE_CLAUSES[reason].format(**values) for reason in FailureReason if reason in present]
    # Guarded on EMPTY failure_reasons so it never duplicates different_face's clause.
    if not same_character and not failure_reasons:
        clauses.append(IDENTITY_CLAUSE)
    if not anatomy_intact:
        clauses.append(ANATOMY_CLAUSE)
    return "\n".join([prompt, *clauses]) if clauses else prompt
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_prompt_optimizer.py -v`
Expected: PASS — 8 new tests, and all 22 pre-existing ones still green **without having been edited**.

- [ ] **Step 5: Run the full backend verify**

Run: `uv run ruff check . && uv run pytest`
Expected: all green.

- [ ] **Step 6: Correct `docs/specs/prompt-optimizer.md` in the same change**

```bash
grep -n 'correct_prompt\|no caller yet\|FAILURE_CLAUSES' docs/specs/prompt-optimizer.md
```

Fix three things: the `correct_prompt` signature gains the two defaulted booleans; document `IDENTITY_CLAUSE` and `ANATOMY_CLAUSE` with the one-line reason each exists (anatomy is outside the frozen 7; identity fires only when the judge gave no reason); and update the "no caller yet" note to say `regenerate` is the caller as of Part 2. State explicitly that `FailureReason` was **not** touched.

- [ ] **Step 7: Commit**

```bash
git add backend/pipeline/prompt_optimizer.py backend/tests/test_prompt_optimizer.py docs/specs/prompt-optimizer.md
git commit -m "feat(prompt-optimizer): identity and anatomy clauses close the resample holes (ADR-010)"
```

---

## Done criteria for Part 1

All of these hold before Part 2 starts:

1. `backend/app/config.py` defines `RECURSION_LIMIT = MAX_SCENES * 4 + 9`; `backend/worker/run_job.py` passes it to `invoke()`.
2. `generate_and_store` takes `attempt_n: int` fourth and writes `{story_id}/{scene_id}-{n}.png`; `generate_scene` passes `len(scene.attempts) + 1`.
3. `correct_prompt` has `same_character` and `anatomy_intact` params plus `IDENTITY_CLAUSE` and `ANATOMY_CLAUSE`.
4. `backend/contracts/` is untouched. `FailureReason` still has exactly 7 values.
5. Both `scene-1.png` collision regression tests still exist and still pass.
6. `uv run ruff check . && uv run pytest` from `backend/` is green and **its output is shown, not claimed**.
7. `docs/specs/image-generator.md` and `docs/specs/prompt-optimizer.md` are corrected.

**Deliberately NOT done in Part 1** — all of it is Part 2: the `regenerate` node, `route_after_check`, the graph re-wiring, `_rank` / best-of / the `finalize` rule in `consistency_check`, and the wider doc sweep (`consistency-checker.md`, `DECISION_BACKLOG.md`, `WORKFLOW.md`, `AGENTS.md`) including flipping the spec's status line to `built`.

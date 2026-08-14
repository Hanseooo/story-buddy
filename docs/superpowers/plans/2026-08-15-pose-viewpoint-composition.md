# Pose, Viewpoint, and Scene Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the image generation pipeline tolerant of different viewpoints and poses, and preserve the requested composition on retries, without adding new calls or changing the pipeline shape.

**Architecture:** Increment the judge prompt version and explicitly instruct the judge on viewpoint tolerance. Reorder the fallback ranking to prioritize scene constraints (composition) over identity. Append a fixed composition preservation clause when generating corrected prompts for retries.

**Tech Stack:** Python, LangGraph, pytest

## Global Constraints

- S3 makes story fidelity the selection priority while retaining the existing identity gate, one corrected retry, and best-of fallback. It adds no pose catalogue, view detector, reference image, model call, or budget term.
- S3 may claim that the prompt, retry, and ranking policy changed as specified; it may not claim that pose/viewpoint quality or direction-detection accuracy improved.

---

### Task 1: Update Consistency Check Judge Prompt and Ranking

**Files:**
- Modify: `backend/pipeline/consistency_check.py`
- Modify: `backend/tests/test_consistency_check_node.py`

**Interfaces:**
- Consumes: Existing `Attempt` and verdict data.
- Produces: `_rank(a: Attempt)` with reordered priorities.

- [ ] **Step 1: Write the failing tests**

```python
# In backend/tests/test_consistency_check_node.py
# Update JUDGE_PROMPT_VERSION check
def test_judge_prompt_version():
    from pipeline.consistency_check import JUDGE_PROMPT_VERSION
    assert JUDGE_PROMPT_VERSION == 4

# Update ranking tests to verify composition > identity priority and other edge cases
def test_rank_prioritizes_composition():
    from pipeline.consistency_check import _rank
    from contracts.story_memory import Attempt, VlmVerdict
    
    def make_attempt(same_character=True, contradictions=None, checked=True):
        vlm = VlmVerdict(
            same_character=same_character, anatomy_intact=True, text_free=True, 
            subjects_unique=True, style_match=True, differences_observed=""
        ) if checked else None
        return Attempt(
            image_ref="dummy.png", passed=False, vlm_verdict=vlm,
            scene_contradictions=contradictions, failure_reasons=[]
        )
    
    a_comp_clean = make_attempt(same_character=False, contradictions=[])
    a_comp_fail = make_attempt(same_character=True, contradictions=["Pose"])
    a_two_contra = make_attempt(same_character=True, contradictions=["1", "2"])
    a_comp_fail_id_fail = make_attempt(same_character=False, contradictions=["Pose"])
    a_unchecked = make_attempt(checked=False, contradictions=None)
    a_comp_unavail = make_attempt(same_character=True, contradictions=None)
    
    # Composition clean > composition failed
    assert _rank(a_comp_clean) > _rank(a_comp_fail)
    
    # Fewer scene contradictions wins
    assert _rank(a_comp_fail) > _rank(a_two_contra)
    
    # Identity breaks tie for equal contradictions
    assert _rank(a_comp_fail) > _rank(a_comp_fail_id_fail)
    
    # Fully unchecked is lowest
    assert _rank(a_comp_fail_id_fail) > _rank(a_unchecked)
    
    # Clean > Unavailable > Bad
    assert _rank(a_comp_clean) > _rank(a_comp_unavail)
    assert _rank(a_comp_unavail) > _rank(a_comp_fail)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_consistency_check_node.py -k "test_rank_prioritizes_composition or test_judge_prompt_version" -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Modify `backend/pipeline/consistency_check.py`:
1. Change `JUDGE_PROMPT_VERSION = 4`.
2. Update `JUDGE_PROMPT` to add the required wording before "First describe every difference...":
   "The FIRST image is the canonical character reference for {name}. The SECOND image is one page of the same picture book, in which {name} should appear drawn to match that reference. Rear, profile, foreshortened, and partially occluded views can depict the same character; pose, crop, expression, and viewing angle are not identity differences by themselves. Compare using visible evidence only: a feature naturally hidden by the requested viewpoint is not a missing body part, visible contradiction, or reason to emit wrong_body_feature, different_face, or character_absent. A visible substitution, visible attribute contradiction, or genuinely malformed, merged, missing, or duplicated anatomy still fails normally.\n\nFirst describe..."
3. Update `_rank` return tuple to:
   ```python
   return (
       checked,
       contradictions == [],
       -len(contradictions or []),
       True if verdict is None else verdict.same_character,
       True if verdict is None else verdict.anatomy_intact,
       True if verdict is None else verdict.text_free,
       not (GATING_REASONS & set(a.failure_reasons)),
       True if verdict is None else verdict.subjects_unique,
       True if verdict is None else verdict.style_match,
   )
   ```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_consistency_check_node.py -v`
Expected: PASS (Fix any other broken tests in the file due to reordered assertions).

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/consistency_check.py backend/tests/test_consistency_check_node.py
git commit -m "feat: consistency_check viewpoint tolerance and composition-first best-of"
```

---

### Task 2: Append Composition Preservation Clause on Retries

**Files:**
- Modify: `backend/pipeline/prompt_optimizer.py`
- Modify: `backend/tests/test_prompt_optimizer.py`
- Modify: `backend/tests/test_regenerate_node.py`

**Interfaces:**
- Consumes: Failed `Attempt.failure_reasons` and `Attempt.scene_contradictions`.
- Produces: String prompt appended with `COMPOSITION_CLAUSE`.

- [ ] **Step 1: Write the failing test**

```python
# In backend/tests/test_prompt_optimizer.py
def test_correct_prompt_appends_composition_clause():
    from pipeline.prompt_optimizer import correct_prompt, COMPOSITION_CLAUSE
    from contracts.story_memory import FailureReason
    
    # When no corrections, it shouldn't append
    base = "Draw Ana."
    assert correct_prompt(base, [], [], "") == base
    
    # When corrected, it should append the composition clause last
    corrected = correct_prompt(base, [], [], "", same_character=False)
    assert corrected.endswith(COMPOSITION_CLAUSE)
    assert COMPOSITION_CLAUSE in corrected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_prompt_optimizer.py -v`
Expected: FAIL 

- [ ] **Step 3: Write minimal implementation**

Modify `backend/pipeline/prompt_optimizer.py`:
1. Add constant:
   `COMPOSITION_CLAUSE = "Preserve the Visual direction exactly: do not change the requested action, movement direction, pose, crop, expression, or viewing angle."`
2. At the end of `correct_prompt`, before returning, append the clause if any other clauses exist:
   ```python
       if clauses:
           clauses.append(COMPOSITION_CLAUSE)
       return "\n".join([prompt, *clauses]) if clauses else prompt
   ```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_prompt_optimizer.py backend/tests/test_regenerate_node.py -v`
Expected: PASS (Update any broken tests that check the exact length or content of regenerated prompts).

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/prompt_optimizer.py backend/tests/test_prompt_optimizer.py backend/tests/test_regenerate_node.py
git commit -m "feat: correct_prompt appends composition preservation clause"
```

---

### Task 3: Update Documentation Assertions

**Files:**
- Modify: `docs/specs/prompt-optimizer.md`
- Modify: `docs/specs/consistency-checker.md`
- Modify: `docs/specs/regeneration-controller.md`
- Modify: `docs/specs/visual-continuity.md`
- Modify: `docs/specs/story-memory-contract.md`
- Modify: `docs/specs/lettering-suppression.md`
- Modify: `docs/specs/scene-setting-and-subject-binding.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Grep for outdated assertions**

Run: `grep -r "JUDGE_PROMPT_VERSION" docs/ AGENTS.md`
Run: `grep -r "identity-first" docs/ AGENTS.md`
Run: `grep -r "best-of" docs/ AGENTS.md`

- [ ] **Step 2: Update all relevant documentation files**

Update the mentioned files to reflect:
1. `JUDGE_PROMPT_VERSION` is now 4.
2. The identity prompt explicitly instructs viewpoint tolerance.
3. Ranking (best-of) prioritizes fewer scene contradictions (composition) over identity.
4. `correct_prompt` always appends a composition preservation clause to retries.

- [ ] **Step 3: Commit**

```bash
git add docs/ AGENTS.md
git commit -m "docs: update spec assertions for composition-first best-of and v4 prompt"
```

---

### Task 4: Verification and Cleanup

**Files:**
- Delete: `docs/superpowers/plans/2026-08-15-pose-viewpoint-composition.md`

- [ ] **Step 1: Run verification commands**

From `backend/`:
Run: `uv run ruff check .`
Run: `uv run pytest`

From `frontend/`:
Run: `pnpm lint`
Run: `pnpm test`
Expected: All pass.

- [ ] **Step 2: Delete this plan**

Run: `rm docs/superpowers/plans/2026-08-15-pose-viewpoint-composition.md`
Run: `git add docs/superpowers/plans/2026-08-15-pose-viewpoint-composition.md`
Run: `git commit -m "chore: delete completed pose-viewpoint-composition plan"`

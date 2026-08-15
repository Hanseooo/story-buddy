# Spend-and-Retry Economics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a concretely failed scene one additional corrected attempt while reducing the graph's structurally possible worst-case paid-image spend from 60 to 55.

**Architecture:** We are updating boundary limits (words and scenes), incrementing the consistency-check retry allowance from 2 to 3, recalculating the `IMAGE_BUDGET` and `RECURSION_LIMIT` formulas to include the new retry and output moderation's redraw, and tracking output moderation's actual image spend. No contract schema changes are made.

**Tech Stack:** React (Next.js), Python (FastAPI/LangGraph), pytest, Vitest

## Global Constraints

- Trade book length for one more corrected scene attempt while making the paid-image breaker truthful.
- The product accepts at most 300 words and 10 scenes; each scene may use three consistency attempts and one output-moderation redraw; every structurally permitted draw is funded inside a 55-image ceiling.
- `MAX_STORY_WORDS = 300`, `MAX_SCENES = 10`, `IMAGE_BUDGET = 55`, and `RECURSION_LIMIT = 87` are one coupled policy.
- `IMAGE_BUDGET` funds every structurally permitted paid draw.
- Output moderation retains exactly one softened redraw. Its paid draw is counted, breaker-bound, and never bypasses moderation.

---

### Task 1: Update Frontend Ceilings

**Files:**
- Modify: `frontend/app/s/[profileId]/write/page.tsx`

**Interfaces:**
- Consumes: User input text
- Produces: Disables submission above 300 words, keeps existing `Too long!` state.

- [ ] **Step 1: Write the minimal implementation**

Modify `frontend/app/s/[profileId]/write/page.tsx` to change `MAX_STORY_WORDS`:

```tsx
// Find this line:
const MAX_STORY_WORDS = 800;

// Change it to:
const MAX_STORY_WORDS = 300;
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd frontend && pnpm test`
Expected: PASS (fix any tests asserting on the 800 word limit if they fail).

- [ ] **Step 3: Commit**

```bash
cd frontend && git add app/s/\[profileId\]/write/page.tsx
git commit -m "feat: reduce frontend max story words to 300"
```

---

### Task 2: Update Backend Configuration Constants

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/tests/test_config.py`

**Interfaces:**
- Produces: New constants for `MAX_STORY_WORDS`, `MAX_SCENES`, `IMAGE_BUDGET`, `RECURSION_LIMIT`.

- [ ] **Step 1: Write the failing tests**

Update assertions in `backend/tests/test_config.py`.

```python
# test_config.py
def test_image_budget_derives_from_max_scenes():
    assert IMAGE_BUDGET == MAX_SCENES * 4 + 15

def test_recursion_limit_derives_from_max_scenes_and_the_super_step_prelude():
    assert RECURSION_LIMIT == MAX_SCENES * 7 + 17  # SUPER_STEP_PRELUDE is 17

def test_max_story_words_is_three_hundred():
    assert MAX_STORY_WORDS == 300

def test_max_scenes_is_ten():
    assert MAX_SCENES == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_config.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Modify `backend/app/config.py`:

```python
# backend/app/config.py
MAX_SCENES = 10
MIN_SCENE_WORDS = 12
MIN_SCENES = 3
MIN_STORY_WORDS = 5
MAX_STORY_WORDS = 300

IMAGE_BUDGET = MAX_SCENES * 4 + 15

SUPER_STEP_PRELUDE = 17
RECURSION_LIMIT = MAX_SCENES * 7 + SUPER_STEP_PRELUDE
```
Update any comments in the file referencing `15 scenes x 2`, `x5 is the deepest`, `800-word` to match the new formulas in the spec.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_config.py -v`
Expected: PASS. If tests in `test_finetune_corpus.py` or `test_length.py` fail due to asserting old boundaries, update them to match `MAX_STORY_WORDS` and `MAX_SCENES`.

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/config.py tests/test_config.py
git commit -m "feat: update backend policy limits and formulas"
```

---

### Task 3: Update Scene Segmentation Limits

**Files:**
- Modify: `backend/pipeline/segment.py`

**Interfaces:**
- Produces: Dynamic `SEGMENTATION_PROMPT` containing the new `MAX_SCENES` limit.

- [ ] **Step 1: Write minimal implementation**

Modify `backend/pipeline/segment.py`:

```python
# Change the specific string inside SEGMENTATION_PROMPT from:
# - At most 15 scenes.
# To:
# - At most {max_scenes} scenes.

# And update the format call in `segment_scenes()` from:
    result = structured_text(
        SEGMENTATION_PROMPT.format(
            numbered=numbered, roster=roster, locations=places, objects=things, plot=plot
        ),
        SceneSegmentation,
    )

# To:
    result = structured_text(
        SEGMENTATION_PROMPT.format(
            numbered=numbered, roster=roster, locations=places, objects=things, plot=plot, max_scenes=MAX_SCENES
        ),
        SceneSegmentation,
    )
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_segment_node.py -v`
Expected: PASS (Update any mock assertions that check the prompt literal for "15").

- [ ] **Step 3: Commit**

```bash
cd backend && git add pipeline/segment.py
git commit -m "feat: interpolate MAX_SCENES in segmentation prompt"
```

---

### Task 4: Update Consistency Finalization Logic

**Files:**
- Modify: `backend/pipeline/consistency_check.py`
- Modify: `backend/tests/test_consistency_check_node.py`

**Interfaces:**
- Consumes: `len(scene.attempts)`
- Produces: Allows up to 3 consistency-checked attempts.

- [ ] **Step 1: Write the failing tests**

Update or add tests in `backend/tests/test_consistency_check_node.py` to assert the 3rd attempt finalizes:

```python
def test_concrete_failure_on_attempt_1_remains_unfinalized_and_routes_to_regenerate(state):
    # Set up scene with 1 attempt
    state.scenes[0].attempts = [Attempt(image_ref="1.png", passed=False, scene_contradictions=["Missing hat"])]
    result = consistency_check(state)
    assert result["scenes"][0].final_image_ref is None

def test_concrete_failure_on_attempt_2_remains_unfinalized_and_routes_to_regenerate(state):
    # Set up scene with 2 attempts
    state.scenes[0].attempts = [
        Attempt(image_ref="1.png", passed=False, scene_contradictions=["Missing hat"]),
        Attempt(image_ref="2.png", passed=False, scene_contradictions=["Missing hat"])
    ]
    result = consistency_check(state)
    assert result["scenes"][0].final_image_ref is None

def test_attempt_3_finalizes_whether_it_passes_or_concretely_fails(state):
    # Set up scene with 3 attempts
    state.scenes[0].attempts = [
        Attempt(image_ref="1.png", passed=False, scene_contradictions=["Missing hat"]),
        Attempt(image_ref="2.png", passed=False, scene_contradictions=["Missing hat"]),
        Attempt(image_ref="3.png", passed=False, scene_contradictions=["Missing hat"])
    ]
    result = consistency_check(state)
    assert result["scenes"][0].final_image_ref is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_consistency_check_node.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Modify `backend/pipeline/consistency_check.py`. 

Change the exact finalization threshold logic:
```python
# Before:
    finalize = passed or not concrete_failure or len(scene.attempts) >= 2
# After:
    finalize = passed or not concrete_failure or len(scene.attempts) >= 3
```

Change the specific log line string format:
```python
# Before:
    log.info(
        "consistency_check: scene_id=%s attempt=%d/2 roster_ids=%s visible_cast=%s "

# After:
    log.info(
        "consistency_check: scene_id=%s attempt=%d/3 roster_ids=%s visible_cast=%s "
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_consistency_check_node.py -v`
Expected: PASS. Also ensure `test_graph_stub.py` passes.

- [ ] **Step 5: Commit**

```bash
cd backend && git add pipeline/consistency_check.py tests/test_consistency_check_node.py
git commit -m "feat: increase consistency check retry limit to 3"
```

---

### Task 5: Add Image Cost to Output Moderation

**Files:**
- Modify: `backend/pipeline/output_mod.py`
- Modify: `backend/tests/test_output_mod_node.py`

**Interfaces:**
- Consumes: `state.cost.image_count`, `IMAGE_BUDGET`, `generate_and_store`
- Produces: Accurate tracking of paid images, raises on budget exceeded, returns updated `Cost`.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_output_mod_node.py`:

```python
from app.config import IMAGE_BUDGET

def test_output_mod_raises_when_image_budget_reached(state_with_flagged_scene):
    state_with_flagged_scene.cost.image_count = IMAGE_BUDGET
    with pytest.raises(RuntimeError, match="image budget exceeded"):
        output_mod(state_with_flagged_scene)

def test_output_mod_increments_image_count_when_paid(state_with_flagged_scene, mocker):
    mocker.patch("pipeline.output_mod.generate_and_store", return_value=("retry.png", True))
    initial_count = state_with_flagged_scene.cost.image_count
    result = output_mod(state_with_flagged_scene)
    assert result["cost"].image_count == initial_count + 1

def test_output_mod_does_not_increment_image_count_when_reused(state_with_flagged_scene, mocker):
    mocker.patch("pipeline.output_mod.generate_and_store", return_value=("retry.png", False))
    initial_count = state_with_flagged_scene.cost.image_count
    result = output_mod(state_with_flagged_scene)
    assert result["cost"].image_count == initial_count
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_output_mod_node.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Modify `backend/pipeline/output_mod.py`:

```python
from app.config import IMAGE_BUDGET

def output_mod(state: StoryMemory) -> dict:
    updated_scenes = []
    current_image_count = state.cost.image_count

    for scene in state.scenes:
        if scene.moderation_status == "passed":
            updated_scenes.append(scene)
            continue

        if scene.final_image_ref is None:
            updated_scenes.append(scene)
            continue

        signed_url = get_signed_url(scene.final_image_ref)

        try:
            flagged_by = _check_image(signed_url)
        except Exception as exc:
            log.error("output_mod: scene_id=%s classifier error (%s)", scene.scene_id, exc)
            raise RuntimeError("moderation_error") from exc

        if flagged_by is None:
            log.info("output_mod: scene_id=%s passed", scene.scene_id)
            updated_scenes.append(scene.model_copy(update={"moderation_status": "passed"}))
            continue

        if current_image_count >= IMAGE_BUDGET:
            raise RuntimeError(
                f"image budget exceeded: {current_image_count} >= {IMAGE_BUDGET} (ADR-025)"
            )

        log.info(
            "output_mod: scene_id=%s flagged by %s — softening and retrying",
            scene.scene_id, flagged_by,
        )
        softened = _soften_prompt(scene.prompt or "")
        ref_paths = [
            c.canonical_ref_image
            for c in referenced_characters(scene.characters_present, state.characters)
        ]

        retry_n = len(scene.attempts) + 1
        retry_path, paid = generate_and_store(softened, state.story_id, scene.scene_id, retry_n, ref_paths)
        if paid:
            current_image_count += 1
            
        retry_url = get_signed_url(retry_path)

        try:
            retry_flagged_by = _check_image(retry_url)
        except Exception as exc:
            log.error("output_mod: scene_id=%s retry classifier error (%s)", scene.scene_id, exc)
            raise RuntimeError("moderation_error") from exc

        if retry_flagged_by is None:
            log.info("output_mod: scene_id=%s retry passed", scene.scene_id)
            updated_scenes.append(scene.model_copy(update={
                "final_image_ref": retry_path,
                "moderation_status": "passed",
                "attempts": [*scene.attempts, Attempt(image_ref=retry_path, prompt=softened, passed=True)],
            }))
        else:
            log.error(
                "output_mod: scene_id=%s still flagged by %s after retry — "
                "route_after_output_mod will fail job",
                scene.scene_id, retry_flagged_by,
            )
            updated_scenes.append(scene.model_copy(update={
                "final_image_ref": None,
                "moderation_status": "failed",
                "attempts": [*scene.attempts, Attempt(image_ref=retry_path, prompt=softened, passed=False)],
            }))

    return {
        "scenes": updated_scenes,
        "cost": state.cost.model_copy(update={"image_count": current_image_count}),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_output_mod_node.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add pipeline/output_mod.py tests/test_output_mod_node.py
git commit -m "feat: track paid image cost in output moderation"
```

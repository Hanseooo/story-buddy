# image-generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `generate_scene` from a text-to-image stub to a reference-conditioned node that uses `edit_image` when canonical character references are present, fixes the `scene-1.png` Storage-path collision, adds an ADR-025 cost breaker, and is idempotent on resume.

**Architecture:** Three changes land together in `generate_scene.py`: (1) a module-level `_fal_ref_url` helper with `@lru_cache` to convert Storage paths into fal upload URLs, (2) a widened `generate_and_store` that selects `edit_image` vs `text_to_image` and returns `(path, paid)`, (3) a rewritten node body that adds the breaker, collects refs, and conditionally bumps `cost`. `MAX_SCENES = 15` and `IMAGE_BUDGET = 39` move to `app/config.py` so `segment.py` and `generate_scene.py` share one number. No graph change, no contracts change.

**Tech Stack:** Python 3.12, `functools.lru_cache`, `fal_client` via `providers.py`, `supabase-py` for Storage — same as every other backend pipeline module.

## Global Constraints

- No `backend/contracts/` change. `Scene.prompt`, `Attempt`, `Cost`, and `FailureReason` already exist and are frozen.
- `graph.py` is **not** touched — no new edge, no new router.
- `final_image_ref` set by this node is **provisional**. The comment in code must name it as `consistency_check`'s to take (spec §3).
- `Attempt.passed` is always `False` on a fresh attempt — only `consistency_check` may write `True`.
- `cost.image_count` bumped **only when `paid=True`** (i.e., fal was called). A Storage-reuse does not bump it.
- `cost` is always returned via `state.cost.model_copy(update={...})` — never rebuilt from zero (char_bible §4 precedent).
- A failing `ref_verdict` (`matches_description=False`) does **not** filter out the reference (ADR-028).
- A `char_id` in `characters_present` that is absent from `state.characters` is skipped silently — same posture as `build_prompt` and `segment`.
- The ADR-025 D4 breaker fires **before** any fal call: `cost.image_count >= IMAGE_BUDGET → raise`.
- Backend verify must be green and shown: `uv run ruff check . && uv run pytest` from `backend/`.

---

## File Structure

- **Modify** `backend/app/config.py` — add `MAX_SCENES = 15` and `IMAGE_BUDGET = MAX_SCENES * 2 + 9` as module-level constants after `STYLE_PRESETS`.
- **Modify** `backend/pipeline/segment.py` — import `MAX_SCENES` from `app.config`, replace the three bare `15` literals on lines 118–120.
- **Rewrite** `backend/pipeline/generate_scene.py` — new imports, `_fal_ref_url`, widened `generate_and_store`, rewritten `generate_scene`.
- **Rewrite** `backend/tests/test_generate_scene_node.py` — complete replacement: new helper tests + all updated node tests.
- **Modify** `docs/specs/image-generator.md` — flip `Status: draft` → `built` with commit range.
- **Modify** `docs/product/DECISION_BACKLOG.md`, `docs/WORKFLOW.md`, `AGENTS.md` — finding-change grep targets (spec §9 item 6).

---

### Task 1: `MAX_SCENES` and `IMAGE_BUDGET` constants

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/pipeline/segment.py`

**Interfaces:**
- Produces: `app.config.MAX_SCENES: int = 15`, `app.config.IMAGE_BUDGET: int = 39` — consumed by Task 2 (`generate_scene`) and by `segment` (Task 1 only; no test change needed per spec §6 note).

No new tests — segment's existing `≤15` assertions already cover the extracted constant (spec §6: "no new test is added for a constant move"). Run the existing suite to confirm no regression.

- [ ] **Step 1: Add the constants to `app/config.py`**

Open `backend/app/config.py`. After the closing brace of `STYLE_PRESETS`, append:

```python
# Spec `docs/specs/image-generator.md` §4: ADR-025 D4 domain-level breaker.
# ADR-024's `recursion_limit` is set to this same number in `graph.py` so both
# share one source of truth. Writing 39 here would create a second copy of 15.
MAX_SCENES = 15
IMAGE_BUDGET = MAX_SCENES * 2 + 9   # 15 scenes × 2 + 9-image prelude (ADR-029)
```

- [ ] **Step 2: Update `segment.py` to import and use `MAX_SCENES`**

Open `backend/pipeline/segment.py`. Add `MAX_SCENES` to the imports from `app.config` (it currently doesn't import from `app.config`; add the import):

At the top of the file (after the existing `from contracts.story_memory import ...` line), add:
```python
from app.config import MAX_SCENES
```

Then replace the three bare `15` literals on lines 117–120:

```python
# OLD (lines 117-120):
    # Merge to ≤15 — smallest combined unit count, ties → earliest
    if len(deoverlapped) > 15:
        log.info("segment/repair: merging %d scenes → 15", len(deoverlapped))
    while len(deoverlapped) > 15:

# NEW:
    # Merge to ≤MAX_SCENES — smallest combined unit count, ties → earliest
    if len(deoverlapped) > MAX_SCENES:
        log.info("segment/repair: merging %d scenes → %d", len(deoverlapped), MAX_SCENES)
    while len(deoverlapped) > MAX_SCENES:
```

- [ ] **Step 3: Run the backend suite to confirm no regression**

Run (from `backend/`): `uv run ruff check . && uv run pytest`
Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py backend/pipeline/segment.py
git commit -m "refactor(config): extract MAX_SCENES and IMAGE_BUDGET constants from segment bare literals"
```

---

### Task 2: Rewrite `generate_scene.py` + tests (TDD)

**Files:**
- Rewrite: `backend/pipeline/generate_scene.py`
- Rewrite: `backend/tests/test_generate_scene_node.py`

**Interfaces:**
- Consumes: `app.config.IMAGE_BUDGET` (Task 1); `pipeline.prompt_optimizer.build_prompt` (already wired); `providers.edit_image`, `providers.text_to_image`, `providers.upload_reference` (existing); `app.db.get_supabase_client` (existing); `contracts.story_memory.Attempt`, `StoryMemory`, `Cost` (frozen).
- Produces: `generate_scene(state: StoryMemory) -> dict` — unchanged signature; new keys `"scenes"` (as before) and `"cost"` (new). Also produces the private `_fal_ref_url(ref_path: str) -> str` and `generate_and_store(prompt: str, story_id: str, scene_id: str, ref_paths: list[str]) -> tuple[str, bool]` — both are the node's mock seam in tests.

- [ ] **Step 1: Write the failing tests**

Replace the entire contents of `backend/tests/test_generate_scene_node.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

from app.config import IMAGE_BUDGET
from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Cost,
    Input,
    RefVerdict,
    Scene,
    Style,
    StoryMemory,
)
from pipeline.generate_scene import _fal_ref_url, generate_and_store, generate_scene


def _make_supabase(*, has_existing: bool = False) -> MagicMock:
    """Storage mock. has_existing=True → download returns bytes (asset found).
    has_existing=False → download raises (asset not found, proceed to generate)."""
    fake = MagicMock()
    if has_existing:
        fake.storage.from_.return_value.download.return_value = b"existing-bytes"
    else:
        fake.storage.from_.return_value.download.side_effect = Exception("not found")
    return fake


def _state(
    scenes: list[Scene],
    characters: list[Character] | None = None,
    style: Style | None = None,
    cost: Cost | None = None,
) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-123",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        characters=characters or [],
        style=style or Style(),
        scenes=scenes,
        cost=cost or Cost(),
    )


# --- _fal_ref_url (lru_cache — clear before and after to avoid test cross-contamination) ---

def test_fal_ref_url_downloads_from_storage_and_uploads_to_fal():
    _fal_ref_url.cache_clear()
    fake_supabase = MagicMock()
    fake_supabase.storage.from_.return_value.download.return_value = b"ref-bytes"

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.upload_reference", return_value="https://fal/ref.png") as mock_upload:
        url = _fal_ref_url("job-1/ref-c0.png")

    assert url == "https://fal/ref.png"
    mock_upload.assert_called_once_with(b"ref-bytes")
    _fal_ref_url.cache_clear()


def test_fal_ref_url_memoizes_so_a_second_call_skips_download_and_upload():
    """Spec §6: two calls for the same path perform one download and one upload_reference."""
    _fal_ref_url.cache_clear()
    fake_supabase = MagicMock()
    fake_supabase.storage.from_.return_value.download.return_value = b"ref-bytes"

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.upload_reference", return_value="https://fal/ref.png") as mock_upload:
        url1 = _fal_ref_url("job-1/ref-c0.png")
        url2 = _fal_ref_url("job-1/ref-c0.png")

    assert url1 == url2 == "https://fal/ref.png"
    assert fake_supabase.storage.from_.return_value.download.call_count == 1
    mock_upload.assert_called_once()
    _fal_ref_url.cache_clear()


# --- generate_and_store (providers + Supabase mocked) ---

def test_generate_and_store_uploads_image_bytes_and_returns_paid_true():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.text_to_image", return_value=b"fake-png-bytes"), \
         patch("pipeline.generate_scene._fal_ref_url"):
        path, paid = generate_and_store("a friendly dog", "job-123", "s0", [])

    assert path == "job-123/s0.png"
    assert paid is True
    fake_supabase.storage.from_.assert_called_with("storybook-images")
    fake_supabase.storage.from_.return_value.upload.assert_called_once()


def test_generate_and_store_reuses_existing_storage_asset():
    """CC-10: a re-executed super-step is free."""
    fake_supabase = _make_supabase(has_existing=True)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.edit_image") as mock_edit, \
         patch("pipeline.generate_scene.text_to_image") as mock_text:
        path, paid = generate_and_store("a dog", "job-1", "s0", [])

    assert path == "job-1/s0.png"
    assert paid is False
    mock_edit.assert_not_called()
    mock_text.assert_not_called()


def test_generate_and_store_calls_edit_image_when_refs_given():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene._fal_ref_url", side_effect=lambda p: f"https://fal/{p}"), \
         patch("pipeline.generate_scene.edit_image", return_value=b"img-bytes") as mock_edit, \
         patch("pipeline.generate_scene.text_to_image") as mock_text:
        path, paid = generate_and_store("a dog", "job-1", "s0", ["ref-c0.png"])

    assert path == "job-1/s0.png"
    assert paid is True
    mock_edit.assert_called_once_with("a dog", ["https://fal/ref-c0.png"])
    mock_text.assert_not_called()


def test_generate_and_store_calls_text_to_image_when_no_refs():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.text_to_image", return_value=b"img-bytes") as mock_text, \
         patch("pipeline.generate_scene.edit_image") as mock_edit:
        path, paid = generate_and_store("a dog", "job-1", "s0", [])

    assert path == "job-1/s0.png"
    assert paid is True
    mock_text.assert_called_once_with("a dog")
    mock_edit.assert_not_called()


# --- generate_scene (generate_and_store patched — the node seam) ---

def test_generate_scene_returns_scenes_and_cost_keys():
    """ADR-024: partial-return shape. Cost is always included when a scene is processed."""
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="a friendly dog"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)):
        result = generate_scene(state)

    assert set(result) == {"scenes", "cost"}
    scene, = result["scenes"]
    assert scene.scene_id == "s0"
    assert scene.final_image_ref == "job-123/s0.png"
    assert scene.prompt == "a friendly dog"


def test_generate_scene_records_the_attempt_with_passed_false():
    """CC-5: per-attempt provenance (ADR-010). Attempt.passed=False — only consistency_check writes True."""
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="a friendly dog"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)):
        result = generate_scene(state)

    attempt, = result["scenes"][0].attempts
    assert attempt.image_ref == "job-123/s0.png"
    assert attempt.prompt == "a friendly dog"
    assert attempt.passed is False


def test_generate_scene_picks_the_first_scene_without_an_image():
    """ADR-024: loop position is derived from `final_image_ref is None` — there is no cursor."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="already.png"),
        Scene(scene_id="s1", text_excerpt="1"),
    ])

    with patch("pipeline.generate_scene.build_prompt", return_value="next"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s1.png", True)):
        result = generate_scene(state)

    scene, = result["scenes"]
    assert scene.scene_id == "s1"


def test_generate_scene_is_a_no_op_when_every_scene_has_an_image():
    state = _state([Scene(scene_id="s0", text_excerpt="0", final_image_ref="already.png")])

    with patch("pipeline.generate_scene.generate_and_store") as mock_store:
        result = generate_scene(state)

    assert result == {}
    mock_store.assert_not_called()


def test_generate_scene_calls_build_prompt_with_the_scenes_roster_and_style():
    """Spec §6: generate_scene calls build_prompt with (scene.text_excerpt,
    scene.characters_present, state.characters, state.style.prompt_fragment)."""
    dog = Character(char_id="c0", name="the dog", description=CharacterDescription(species="dog"))
    state = _state(
        [Scene(scene_id="s0", text_excerpt="The dog ran.", characters_present=["c0"])],
        characters=[dog],
        style=Style(prompt_fragment="flat gouache storybook"),
    )

    with patch("pipeline.generate_scene.build_prompt", return_value="built") as build, \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)):
        generate_scene(state)

    build.assert_called_once_with("The dog ran.", ["c0"], [dog], "flat gouache storybook")


def test_generate_scene_uses_scene_id_in_storage_path():
    """Regression: old code hardcoded 'scene-1.png', clobbering every scene in a multi-scene book."""
    state = _state([Scene(scene_id="scene-abc", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/scene-abc.png", True)) as mock_store:
        result = generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "scene-abc", [])
    assert result["scenes"][0].final_image_ref == "job-123/scene-abc.png"


def test_generate_scene_two_successive_invocations_produce_distinct_paths():
    """Regression: old hardcoded scene-1.png made every scene clobber the same Storage object."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0"),
        Scene(scene_id="s1", text_excerpt="1"),
    ])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)):
        result1 = generate_scene(state)

    # Simulate LangGraph applying the partial return before the second invocation
    updated = state.model_copy(update={"scenes": [
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-123/s0.png"),
        Scene(scene_id="s1", text_excerpt="1"),
    ]})

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s1.png", True)):
        result2 = generate_scene(updated)

    path1 = result1["scenes"][0].final_image_ref
    path2 = result2["scenes"][0].final_image_ref
    assert path1 != path2


def test_generate_scene_bumps_cost_image_count_when_paid():
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)):
        result = generate_scene(state)

    assert result["cost"].image_count == 1


def test_generate_scene_does_not_bump_cost_when_asset_reused():
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", False)):
        result = generate_scene(state)

    assert result["cost"].image_count == 0


def test_generate_scene_raises_before_calling_helper_when_image_budget_reached():
    """ADR-025 D4: breaker is evaluated before any fal spend."""
    state = _state(
        [Scene(scene_id="s0", text_excerpt="x")],
        cost=Cost(image_count=IMAGE_BUDGET),
    )

    with patch("pipeline.generate_scene.generate_and_store") as mock_store, \
         pytest.raises(RuntimeError):
        generate_scene(state)

    mock_store.assert_not_called()


def test_generate_scene_collects_refs_only_for_present_characters_with_canonical_images():
    dog = Character(char_id="c0", name="dog", description=CharacterDescription(),
                    canonical_ref_image="job-123/ref-c0.png")
    cat = Character(char_id="c1", name="cat", description=CharacterDescription(),
                    canonical_ref_image=None)
    state = _state(
        [Scene(scene_id="s0", text_excerpt="x", characters_present=["c0", "c1"])],
        characters=[dog, cat],
    )

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)) as mock_store:
        generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "s0", ["job-123/ref-c0.png"])


def test_generate_scene_skips_absent_char_id_when_collecting_refs():
    dog = Character(char_id="c0", name="dog", description=CharacterDescription(),
                    canonical_ref_image="job-123/ref-c0.png")
    state = _state(
        [Scene(scene_id="s0", text_excerpt="x", characters_present=["c0", "ghost-id"])],
        characters=[dog],
    )

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)) as mock_store:
        generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "s0", ["job-123/ref-c0.png"])


def test_generate_scene_includes_ref_even_when_verdict_failed():
    """ADR-028: a failing ref_verdict still ships its reference.
    Filtering it would silently degrade the scene to text-to-image."""
    dog = Character(
        char_id="c0", name="dog", description=CharacterDescription(),
        canonical_ref_image="job-123/ref-c0.png",
        ref_verdict=RefVerdict(differences_observed="wrong color", matches_description=False),
    )
    state = _state(
        [Scene(scene_id="s0", text_excerpt="x", characters_present=["c0"])],
        characters=[dog],
    )

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)) as mock_store:
        generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "s0", ["job-123/ref-c0.png"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`): `uv run pytest tests/test_generate_scene_node.py -v`
Expected: collection errors or FAIL — `_fal_ref_url` not importable, and `generate_and_store` returns a `str` not a `tuple[str, bool]`.

- [ ] **Step 3: Write the implementation**

Replace the entire contents of `backend/pipeline/generate_scene.py`:

```python
import logging
from functools import lru_cache

from app.config import IMAGE_BUDGET
from app.db import get_supabase_client
from contracts.story_memory import Attempt, StoryMemory
from pipeline.prompt_optimizer import build_prompt
from providers import edit_image, text_to_image, upload_reference

log = logging.getLogger(__name__)

BUCKET = "storybook-images"


@lru_cache(maxsize=8)
def _fal_ref_url(ref_path: str) -> str:
    """Download a canonical reference from Storage and upload it to fal.

    Keyed on `ref_path` which already contains story_id + char_id, so collisions
    across jobs are impossible. Cache is process-local; a worker restart re-uploads
    at the cost of latency, no correctness loss (spec §8).
    """
    image_bytes = get_supabase_client().storage.from_(BUCKET).download(ref_path)
    return upload_reference(image_bytes)


def generate_and_store(
    prompt: str, story_id: str, scene_id: str, ref_paths: list[str]
) -> tuple[str, bool]:
    """The node's ONE effect boundary (MASTER_SPEC §6). Returns (storage_path, paid).

    CC-10: if the path already exists in Storage, reuse it — a re-executed
    super-step is free. The Attempt is still appended by the caller.
    """
    path = f"{story_id}/{scene_id}.png"
    supabase = get_supabase_client()

    try:
        supabase.storage.from_(BUCKET).download(path)
        log.info("generate_scene: reusing existing %s (paid=False)", path)
        return path, False
    except Exception:
        pass

    fal_urls = [_fal_ref_url(r) for r in ref_paths]
    if fal_urls:
        image_bytes = edit_image(prompt, fal_urls)
    else:
        # ponytail: text-to-image path — no canonical references for this scene.
        # ADR-007's identity+style mechanism fires only when ref images are present.
        image_bytes = text_to_image(prompt)

    supabase.storage.from_(BUCKET).upload(
        path, image_bytes, {"content-type": "image/png", "upsert": "true"}
    )
    return path, True


def generate_scene(state: StoryMemory) -> dict:
    # ADR-024: loop position is the first scene with no final_image_ref — no cursor field.
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is None:
        return {}

    # ADR-025 D4: breaker before any spend. IMAGE_BUDGET = MAX_SCENES * 2 + 9.
    if state.cost.image_count >= IMAGE_BUDGET:
        raise RuntimeError(
            f"image budget exceeded: {state.cost.image_count} >= {IMAGE_BUDGET} (ADR-025)"
        )

    prompt = build_prompt(
        scene.text_excerpt, scene.characters_present, state.characters, state.style.prompt_fragment
    )

    by_id = {c.char_id: c for c in state.characters}
    ref_paths = [
        c.canonical_ref_image
        for char_id in scene.characters_present
        if (c := by_id.get(char_id)) and c.canonical_ref_image
    ]

    path, paid = generate_and_store(prompt, state.story_id, scene.scene_id, ref_paths)

    log.info(
        "generate_scene: scene_id=%s refs=%d paid=%s prompt_len=%d",
        scene.scene_id, len(ref_paths), paid, len(prompt),
    )

    return {
        "scenes": [
            scene.model_copy(
                update={
                    "prompt": prompt,
                    # CC-5: per-attempt prompt provenance (ADR-010).
                    "attempts": [*scene.attempts, Attempt(image_ref=path, prompt=prompt, passed=False)],
                    # ponytail: provisional — consistency_check takes final_image_ref ownership (spec §3).
                    "final_image_ref": path,
                }
            )
        ],
        # Invariant 6: copy-and-bump, never rebuild from zero (char_bible §4 precedent).
        "cost": state.cost.model_copy(
            update={"image_count": state.cost.image_count + (1 if paid else 0)}
        ),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_generate_scene_node.py -v`
Expected: all tests pass.

- [ ] **Step 5: Run the full backend suite**

Run: `uv run ruff check . && uv run pytest`
Expected: all tests pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/generate_scene.py backend/tests/test_generate_scene_node.py
git commit -m "feat(pipeline): upgrade generate_scene to reference-conditioned node per image-generator spec"
```

---

### Task 3: Spec status flip, finding-change grep, final verify

**Files:**
- Modify: `docs/specs/image-generator.md`
- Modify: `docs/product/DECISION_BACKLOG.md`
- Modify: `docs/WORKFLOW.md`
- Modify: `AGENTS.md`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Get the commit range for Tasks 1–2**

Run: `git log --oneline -5`

Note the two commit hashes from Tasks 1–2 (first and last of the range) — used in Step 2.

- [ ] **Step 2: Update `docs/specs/image-generator.md`**

Edit line 3 from:
```
**Status:** draft · **Phase:** 1 · **Owner node:** `backend/pipeline/generate_scene.py`
```
to (substitute the real short hashes from Step 1):
```
**Status:** built · <first-hash>–<last-hash> · **Phase:** 1 · **Owner node:** `backend/pipeline/generate_scene.py`
```

- [ ] **Step 3: Update `docs/product/DECISION_BACKLOG.md`**

Edit the `image-generator` line from:
```
- [ ] `image-generator`   *(code: `pipeline/generate_scene.py` — partial, still text-to-image)*
```
to:
```
- [x] `image-generator`   *(spec **built 2026-07-31** — `docs/specs/image-generator.md`;
      `generate_scene` is now reference-conditioned: `edit_image` when canonical refs are present,
      `text_to_image` otherwise. Fixes the `scene-1.png` Storage-path collision (deterministic
      per-scene paths). ADR-025 D4 cost breaker live. CC-10 Storage-exists skip (idempotent resume).
      `MAX_SCENES` and `IMAGE_BUDGET` extracted to `app/config.py`. `contracts/` untouched.
      `final_image_ref` is provisional — `consistency-checker` takes ownership.)*
```

Edit the "Recommended next session" block to replace `image-generator` with `consistency-checker`:
```
> ✅ **`image-generator` is built (2026-07-31).** See `docs/specs/image-generator.md`.

**Build `consistency-checker`** — write `docs/specs/consistency-checker.md` from `docs/specs/TEMPLATE.md` before any code (AGENTS.md).

**No open decision blocks Phase 1, and the backlog has no open rows.** Tiers 1, 2, 2b, 2c, and 3 are all
resolved. D-I closed 2026-07-31 → ADR-029; it builds in Phase 2 behind the char-ref moderation gate.

After `consistency-checker`, in roadmap order: `regeneration-controller`.
```

- [ ] **Step 4: Update `docs/WORKFLOW.md` §"Right now"**

Edit the current "Next action: `image-generator`" block to:
```
`image-generator` is **built** (2026-07-31): `backend/pipeline/generate_scene.py` is now
reference-conditioned (`edit_image` when canonical refs present, `text_to_image` otherwise).
Fixes the `scene-1.png` path collision. ADR-025 D4 breaker live. `final_image_ref` is provisional.

**Next action: `consistency-checker`** — write `docs/specs/consistency-checker.md` from
`docs/specs/TEMPLATE.md` before writing any code (AGENTS.md).
```

- [ ] **Step 5: Update `AGENTS.md`**

**Validation Notes:** After the `prompt-optimizer` paragraph (ending "Remaining Phase-1 specs: `image-generator`, `consistency-check`, `regeneration-controller`."), append:

```
  **`image-generator` is built (2026-07-31):** `generate_scene` is reference-conditioned —
  `edit_image` when `canonical_ref_image` is present for a character, `text_to_image` otherwise.
  Fixes `scene-1.png` Storage-path collision (now `{story_id}/{scene_id}.png`). ADR-025 D4 breaker
  live at `IMAGE_BUDGET = 39`. CC-10 Storage-exists skip (idempotent resume). `final_image_ref` is
  provisional — `consistency_check` takes ownership. `MAX_SCENES` and `IMAGE_BUDGET` in
  `app/config.py`. Remaining Phase-1 specs: `consistency-check`, `regeneration-controller`.
```

Remove the old "Remaining Phase-1 specs: `image-generator`, `consistency-check`, `regeneration-controller`." sentence from the prompt-optimizer paragraph (it's superseded by the new paragraph's sentence above).

**Project Context "Built today" line:** The line currently says `generate_scene has real behavior`. Update that clause to:

```
`generate_scene` is reference-conditioned (edit_image when canonical refs present, text_to_image otherwise), with Storage-based idempotent resume and an ADR-025 D4 cost breaker;
```

The full "Built today" sentence to update (find it by searching for `generate_scene has real behavior`):

OLD:
```
`generate_scene` has real behavior. Fill the stubs in per ADR-024's partial-return conventions; don't
invent a different graph shape.
```

NEW:
```
`generate_scene` is reference-conditioned (edit_image when canonical refs present, text_to_image otherwise), with Storage-based idempotent resume and an ADR-025 D4 cost breaker. Fill the stubs in per ADR-024's partial-return conventions; don't invent a different graph shape.
```

- [ ] **Step 6: Run the finding-change grep**

Run: `git grep -n "image-generator\|scene-1\.png\|text-to-image stub\|text_to_image stub" -- docs AGENTS.md`

Confirm every remaining hit is either:
(a) a durable spec cross-reference that names the spec, not its status (e.g. `docs/MASTER_SPEC.md`'s Phase-1 spec list — these are correct as-is), or
(b) already updated in Steps 2–5.

If any hit still asserts `image-generator` as undone/next-action outside the four files above, fix it.

- [ ] **Step 7: Run the final backend verify**

Run (from `backend/`): `uv run ruff check . && uv run pytest`
Expected: both green. **Paste the actual output when reporting completion** — do not claim done without showing it (AGENTS.md §4 Verification).

- [ ] **Step 8: Commit**

```bash
git add docs/specs/image-generator.md docs/product/DECISION_BACKLOG.md docs/WORKFLOW.md AGENTS.md
git commit -m "docs: flip image-generator to built, update status surface"
```

---

## Self-Review Notes

**Spec coverage:**
- §4 `_fal_ref_url` helper → Task 2 Step 3 (lru_cache, download, upload_reference).
- §4 happy path breaker-first → Task 2 Step 3 (`cost.image_count >= IMAGE_BUDGET → raise`).
- §4 happy path edit_image/text_to_image branch → Task 2 Step 3 (`if fal_urls`).
- §4 Storage-exists skip (CC-10) → Task 2 Step 3 (`try download → return path, False`).
- §4 `passed=False` on fresh attempt → Task 2 Step 3 (`Attempt(..., passed=False)`).
- §4 cost bumped iff `paid` → Task 2 Step 3 (`model_copy(update={... + (1 if paid else 0)})`).
- §4 `{story_id}/{scene_id}.png` deterministic path → Task 2 Step 3 (fixes `scene-1.png` collision).
- §4 edge case: no refs → `text_to_image` → Task 2 tests `test_generate_and_store_calls_text_to_image_when_no_refs` + `test_generate_scene_collects_refs_only_for_present_characters_with_canonical_images`.
- §4 edge case: absent `char_id` → skipped → `test_generate_scene_skips_absent_char_id_when_collecting_refs`.
- §4 edge case: failing `ref_verdict` still contributes → `test_generate_scene_includes_ref_even_when_verdict_failed`.
- §4 edge case: asset already exists → reuse → `test_generate_and_store_reuses_existing_storage_asset`.
- §4 edge case: budget reached → raise before helper → `test_generate_scene_raises_before_calling_helper_when_image_budget_reached`.
- §6 `_fal_ref_url` memoizes → `test_fal_ref_url_memoizes_so_a_second_call_skips_download_and_upload`.
- §6 two invocations → two distinct paths → `test_generate_scene_two_successive_invocations_produce_distinct_paths`.
- §6 `Attempt.passed is False` → `test_generate_scene_records_the_attempt_with_passed_false`.
- §6 cost bumped iff paid → `test_generate_scene_bumps_cost_image_count_when_paid` + `test_generate_scene_does_not_bump_cost_when_asset_reused`.
- §6 breaker fires before helper → `test_generate_scene_raises_before_calling_helper_when_image_budget_reached`.
- §6 unchanged from today: partial-return shape, first-unfinalized-scene, `{}` when all done, `build_prompt` call signature → carried forward in updated tests.
- §9 DoD items 1–3 → Tasks 1–2. §9 DoD item 4 (verify green) → Task 3 Step 7. §9 DoD item 5 (status flip) → Task 3 Step 2. §9 DoD item 6 (finding-change grep) → Task 3 Steps 3–6.
- §8 hand-offs: `final_image_ref` ownership + router wiring not touched; `correct_prompt` not wired; `jobs.failure_reason` migration not absorbed.

**Placeholder scan:** No TBD/TODO in code or test steps. The `<first-hash>–<last-hash>` placeholder in Task 3 Step 2 is deliberate — those hashes don't exist until Tasks 1–2 are committed; Task 3 Step 1 tells exactly how to get them.

**Type consistency:** `generate_and_store` returns `tuple[str, bool]` throughout — Task 2 Step 1 tests unpack `path, paid = ...`, Task 2 Step 3 implementation returns `(path, False)` / `(path, True)`, `generate_scene` unpacks `path, paid = generate_and_store(...)`. `_fal_ref_url` is typed `(str) -> str` throughout.

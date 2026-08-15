# Setting Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze one permanent textual canon per location and use it in the scene-constraint judge to enforce visual consistency across pages without adding new provider calls.

**Architecture:** Updates `analyze` to extract a required, permanent description for each location and updates the `consistency_check` judge prompt to check concrete violations of this permanent setting against the image, ignoring temporary conditions. Bumps `SCENE_CONSTRAINT_PROMPT_VERSION` to 3.

**Tech Stack:** Python 3.12, Pydantic, pytest

## Global Constraints

- No new provider calls, image generations, or budget terms.
- `Location.description` persists as `Optional[str]` for backward compatibility.
- Only open-weight models; no visual quality claim without a named defect.

---

### Task 1: Update `analyze` prompt and `ExtractedLocation` schema

**Files:**
- Modify: `backend/pipeline/analyze.py:33-35`, `77-94`
- Modify: `backend/tests/test_analyze_node.py`

**Interfaces:**
- Consumes: User story text
- Produces: `ExtractedLocation` with a strict non-blank `description: str`

- [ ] **Step 1: Write the failing tests for `analyze`**

```python
# Add to backend/tests/test_analyze_node.py
from pydantic import ValidationError
import pytest
from pipeline.analyze import ExtractedLocation, EXTRACTION_PROMPT, extract_entities
from contracts.story_memory import Location

def test_extracted_location_rejects_blank_description():
    with pytest.raises(ValidationError):
        ExtractedLocation(name="Park", description="   ")
    with pytest.raises(ValidationError):
        ExtractedLocation(name="Park")
    with pytest.raises(ValidationError):
        ExtractedLocation(name="Park", description=None)

    valid_loc = ExtractedLocation(name="Park", description="A large green park")
    assert valid_loc.description == "A large green park"

def test_extraction_prompt_contains_new_instructions():
    assert "permanently there" in EXTRACTION_PROMPT
    assert "Copy every stated permanent fact" in EXTRACTION_PROMPT
    assert "neutral, child-safe" in EXTRACTION_PROMPT
    assert "not the weather" in EXTRACTION_PROMPT

def test_valid_description_reaches_location_unchanged(mocker):
    # Mock structured_text to return an ExtractedLocation with a description
    mock_response = mocker.Mock()
    mock_response.characters = []
    mock_response.locations = [ExtractedLocation(name="Park", description="A large green park")]
    mock_response.objects = []
    mock_response.timeline = []
    mocker.patch("pipeline.analyze.structured_text", return_value=mock_response)
    
    result = extract_entities("some text")
    assert result.locations[0].description == "A large green park"

def test_persisted_location_contract_accepts_none():
    loc = Location(loc_id="loc0", name="Park", description=None)
    assert loc.description is None

def test_locations_remain_uncapped(mocker):
    # Mock to return 10 locations
    mock_response = mocker.Mock()
    mock_response.characters = []
    mock_response.locations = [ExtractedLocation(name=f"Park {i}", description=f"Desc {i}") for i in range(10)]
    mock_response.objects = []
    mock_response.timeline = []
    mocker.patch("pipeline.analyze.structured_text", return_value=mock_response)
    
    result = extract_entities("some text")
    assert len(result.locations) == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_analyze_node.py -k "test_extracted_location_rejects_blank_description or test_extraction_prompt_contains_new_instructions or test_valid_description_reaches_location_unchanged or test_persisted_location_contract_accepts_none or test_locations_remain_uncapped"`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Modify `backend/pipeline/analyze.py`:
Change `ExtractedLocation`:
```python
from pydantic import BaseModel, field_validator # ensure field_validator is imported

class ExtractedLocation(BaseModel):
    name: str
    description: str

    @field_validator("description", mode="after")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description cannot be blank")
        return v
```

Modify `EXTRACTION_PROMPT` in `backend/pipeline/analyze.py`:
Replace the `Locations and objects:` line with:
```python
Locations and objects: whatever the story mentions. Describe each location by what is permanently there — not the weather, the time of day, or what happens there. Copy every stated permanent fact without alteration. Fill missing detail once with neutral, child-safe features that make the place visually recognizable. For each object, provide a stable physical description and set owner_name to the character's name if owned by a character, or null if unowned.
```

Remove conflicting test from `backend/tests/test_analyze_node.py`:
Delete the `test_extracted_location_description_stays_optional` test entirely, as it conflicts with our new required description constraint.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_analyze_node.py -k "test_extracted_location_rejects_blank_description or test_extraction_prompt_contains_new_instructions or test_valid_description_reaches_location_unchanged or test_persisted_location_contract_accepts_none or test_locations_remain_uncapped"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/analyze.py backend/tests/test_analyze_node.py
git commit -m "feat(analyze): enforce strict location description extraction"
```

### Task 2: Update `consistency_check` prompt

**Files:**
- Modify: `backend/pipeline/consistency_check.py:93-112`
- Modify: `backend/tests/test_consistency_check_node.py`

**Interfaces:**
- Consumes: Scene constraints and image attempt
- Produces: `SceneConstraintVerdict` based on v3 prompt.

- [ ] **Step 1: Write the failing tests**

```python
# Add to backend/tests/test_consistency_check_node.py
from pipeline.consistency_check import SCENE_CONSTRAINT_PROMPT_VERSION, SCENE_CONSTRAINT_PROMPT

def test_scene_constraint_prompt_version_and_content():
    assert SCENE_CONSTRAINT_PROMPT_VERSION == 3
    assert "Setting:" in SCENE_CONSTRAINT_PROMPT
    assert "permanent description" in SCENE_CONSTRAINT_PROMPT
    assert "concrete violations of stated permanent features" in SCENE_CONSTRAINT_PROMPT
    assert "do not report weather, lighting, time" in SCENE_CONSTRAINT_PROMPT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_consistency_check_node.py -k "test_scene_constraint_prompt_version"`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Modify `backend/pipeline/consistency_check.py`:
Change `SCENE_CONSTRAINT_PROMPT_VERSION` from 2 to 3:
```python
SCENE_CONSTRAINT_PROMPT_VERSION = 3
```

Update `SCENE_CONSTRAINT_PROMPT` to:
```python
SCENE_CONSTRAINT_PROMPT = """\
The image is one page of a children's picture book. Check it only against the exact scene \
constraints below.

{constraints}

The constraints state only what the story fixed. The page will necessarily show detail they do \
not mention — scenery, lighting, texture, ornament, how a thing is drawn — and that is NOT a \
contradiction. A contradiction is a stated requirement the page violates, never a detail the \
constraints are simply silent about.

When a Setting: line exists, check its name and permanent description against the page. Report \
only concrete violations of stated permanent features as contradictions. Do not report weather, \
lighting, time, damage, or other temporary differences when the later excerpt supports them.

First describe every observed difference from those constraints. Then list each contradiction \
separately. Every contradiction must name the subject and the violated requirement. Check that \
every expected visible character appears exactly once, no unrequested character appears, every \
text-only character matches its frozen profile, each visible object matches its frozen appearance \
and current holder, and the action, movement direction and viewpoint match Visual direction. \
Leave contradictions empty only when every check is clean."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_consistency_check_node.py -k "test_scene_constraint_prompt_version"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/consistency_check.py backend/tests/test_consistency_check_node.py
git commit -m "feat(consistency): bump constraint prompt to v3 for setting checks"
```

### Task 3: Update documentation specs

**Files:**
- Modify: `docs/specs/story-analyzer.md`
- Modify: `docs/specs/consistency-checker.md`

**Interfaces:**
- Consumes: Setting consistency spec updates.

- [ ] **Step 1: Write updates for `story-analyzer.md`**

In `docs/specs/story-analyzer.md`, replace the `ExtractedLocation` block (around line 80) with:
```python
class ExtractedLocation(BaseModel):
    name: str
    description: str # Enforced strictly at the transient boundary, no longer nullable
```
And add to the `Edge cases` section or `The extraction schema` section:
"Locations require a strict permanent description. The prompt instructs the model to preserve stated permanent facts and fill missing detail neutrally, excluding temporary conditions."

- [ ] **Step 2: Write updates for `consistency-checker.md`**

In `docs/specs/consistency-checker.md`, add under `The pass rule` or `Happy path`:
"The scene-constraint judge checks the `Setting:` line (if present) against the page, reporting only concrete violations of stated permanent features as contradictions. Temporary differences supported by the excerpt (weather, lighting) are ignored. This is enforced by `SCENE_CONSTRAINT_PROMPT_VERSION = 3`."

- [ ] **Step 3: Commit**

```bash
git add docs/specs/story-analyzer.md docs/specs/consistency-checker.md
git commit -m "docs: update analyzer and consistency specs for setting constraints"
```

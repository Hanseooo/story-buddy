# Reference Pipeline Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent narrative-role prose from changing a character's physical kind and remove the full-image Supabase download from fal reference delivery.

**Architecture:** Keep the existing graph, Story Memory contract, PII pseudonymization, model IDs, retry caps, and provider seams. Tighten the existing analyzer/reference prompt boundary, then reuse the existing short-lived signed-URL helper instead of downloading and re-uploading canonical references.

**Tech Stack:** Python 3.12, Pydantic, pytest, Supabase Storage, fal-client.

## Global Constraints

- Do not change `backend/contracts/`, graph topology, model IDs, PII pseudonymization, or image retry limits.
- Do not add a dependency, configuration value, provider endpoint, or new abstraction.
- All model/provider calls remain in `backend/providers.py`; `generate_scene` may reuse the existing `get_signed_url(path: str) -> str` seam.
- Preserve moderation ordering and private Storage; only a short-lived signed URL may leave the worker.
- Behavior changes update the relevant existing specs in the same task.
- Follow red-green TDD and keep the diff surgical.

---

### Task 1: Keep narrative role notes out of canonical reference identity

**Files:**
- Modify: `backend/pipeline/analyze.py`
- Modify: `backend/pipeline/char_bible.py`
- Modify: `backend/tests/test_analyze_node.py`
- Modify: `backend/tests/test_char_bible_node.py`
- Modify: `docs/specs/story-analyzer.md`
- Modify: `docs/specs/character-bible.md`

**Interfaces:**
- Consumes: `ExtractedDescription`, `reference_prompt(description, name, style_fragment)`, and the existing targeted-redraw fallback in `_mint_targeted`.
- Produces: concrete analyzer instructions and an initial reference prompt containing physical axes but not `CharacterDescription.notes`.

- [ ] **Step 1: Add failing regression tests.** Assert that `EXTRACTION_PROMPT` explicitly requires concrete visible values and forbids placeholder values such as `neutral`, `none`, `unknown`, and `unspecified`. Assert that a description with `species="human"` and notes containing `"builds and names the robot"` produces a reference prompt containing `human` but not the narrative note or the word `robot`.
- [ ] **Step 2: Run the two focused tests and confirm they fail for the intended missing behavior.** Run `uv run pytest tests/test_analyze_node.py tests/test_char_bible_node.py -k "concrete or narrative_role"` from `backend/`.
- [ ] **Step 3: Implement the minimum prompt changes.** Reword the analyzer instruction so missing visual axes receive concrete, directly drawable, non-stereotyped details and never placeholder words. Make normal `reference_prompt` rendering exclude `notes`. Do not add semantic validation that can turn a model wording mistake into a terminal job failure.
- [ ] **Step 4: Pin targeted-redraw behavior.** Add or adjust a test proving a tapped attribute still reaches `_mint_targeted` through its existing explicit `Be sure to include:` fallback even though normal reference prompts omit notes.
- [ ] **Step 5: Update `story-analyzer.md` and `character-bible.md` to describe the concrete-value rule, the draw-prompt exclusion of narrative notes, and the targeted-redraw exception.**
- [ ] **Step 6: Run focused verification.** Run `uv run pytest tests/test_analyze_node.py tests/test_char_bible_node.py` and `uv run ruff check pipeline/analyze.py pipeline/char_bible.py tests/test_analyze_node.py tests/test_char_bible_node.py`.
- [ ] **Step 7: Commit only Task 1 files.** Commit message: `fix: keep narrative roles out of character identity`.

### Task 2: Give fal short-lived signed reference URLs directly

**Files:**
- Modify: `backend/pipeline/generate_scene.py`
- Modify: `backend/tests/test_generate_scene_node.py`
- Modify: `docs/specs/image-generator.md`

**Interfaces:**
- Consumes: existing `providers.get_signed_url(path: str) -> str` and `providers.edit_image(prompt, image_urls, seed=None)`.
- Produces: `_fal_ref_url(ref_path: str) -> str` returning a fresh signed private-Storage URL without downloading bytes or uploading them to fal storage.

- [ ] **Step 1: Add failing regression tests.** Assert `_fal_ref_url` delegates to `get_signed_url` and returns its value. Assert two calls for the same path invoke `get_signed_url` twice so an expiring URL is never held in a process-local cache. Existing generation tests must still prove reference order and `edit_image` use.
- [ ] **Step 2: Run the focused tests and confirm they fail because `_fal_ref_url` still downloads and caches.** Run `uv run pytest tests/test_generate_scene_node.py -k "signed or fal_ref_url"`.
- [ ] **Step 3: Implement the minimum change.** Remove `_fal_ref_url`'s `lru_cache`, Supabase download, and `upload_reference` use; import and return `get_signed_url(ref_path)`. Keep the 300-second TTL owned by the existing provider helper and do not persist the URL.
- [ ] **Step 4: Update `image-generator.md`.** Replace the download/upload description with direct short-lived signed-URL delivery and record why caching expiring URLs is forbidden.
- [ ] **Step 5: Run focused verification.** Run `uv run pytest tests/test_generate_scene_node.py` and `uv run ruff check pipeline/generate_scene.py tests/test_generate_scene_node.py`.
- [ ] **Step 6: Commit only Task 2 files.** Commit message: `fix: send signed reference URLs directly to fal`.

### Task 3: Combined blast-radius verification

**Files:**
- Review only: all files changed by Tasks 1 and 2 plus callers found by `rg`.

- [ ] **Step 1: Grep every caller and stale assertion.** Run `rg -n "reference_prompt|_fal_ref_url|upload_reference|neutral, child-safe|description.notes|get_signed_url" backend docs/specs` and reconcile every relevant hit without unrelated cleanup.
- [ ] **Step 2: Run backend pre-merge verification.** From `backend/`, run `uv run ruff check .` and `uv run pytest`.
- [ ] **Step 3: Review residual risks.** Confirm fal's live retrieval of a signed URL remains external-provider verification, not a deterministic CI assertion; note the existing opt-in smoke-test boundary rather than adding paid CI work.


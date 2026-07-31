# Feature Spec — image-generator

**Status:** built · acebc6f–6291502 · **Phase:** 1 · **Owner node:** `backend/pipeline/generate_scene.py`
**Derived from:** MASTER_SPEC §2 (system map, node-I/O table), §3 (frozen contract), §5 (CC registry)
**Rationale:** ADR-001 (fal image models), ADR-004 (≤2 references), ADR-007 (style rides the
reference), ADR-010 (no placeholder page), ADR-024 (per-scene loop, partial return), ADR-025
(resilience, idempotency, cost breaker), ADR-028 (the reference is checked, not assumed)

> Turns `generate_scene` from a text-to-image stub into the reference-conditioned node the rest of
> the pipeline already assumes. No `contracts/` change — every field it writes already exists.

## 1. Purpose

Render one scene image per super-step, conditioned on the canonical character references
`char_bible` minted. This is the node where ADR-007's mechanism — identity *and* style carried by
the reference — actually fires; today it does not, because the node still calls `text_to_image`.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `story_id`; `scenes[]` (`scene_id`, `text_excerpt`, `characters_present`,
  `final_image_ref`); `characters[]` (`char_id`, `canonical_ref_image`, `description`);
  `style.prompt_fragment`; `cost.image_count`.
- **Writes:** `scenes[].prompt`, `scenes[].attempts[]` (appended), `scenes[].final_image_ref`
  (provisional — see §3), `cost.image_count`.
- **Invariants:**
  1. The Storage path is `{story_id}/{scene_id}.png` — deterministic and unique per scene.
  2. Exactly one scene is finalized per invocation, **or the node raises** (ADR-025 Decision 2).
     Never a placeholder, never a partial book.
  3. `providers.edit_image` is used whenever at least one present character has a
     `canonical_ref_image`; `providers.text_to_image` **only** when there are none.
  4. `cost.image_count` is bumped **only when fal was actually paid**. A Storage-skip bumps nothing.
  5. A newly appended `Attempt` carries `passed=False`. Only `consistency_check` may write `True`.
  6. `cost` has no reducer — copy and bump, never rebuild from zero (same rule as `char_bible`).

### The `scene-1.png` collision (fixed by invariant 1)

`generate_scene.py:14` currently hardcodes `path = f"{job_id}/scene-1.png"`. Every scene of a
15-scene book writes the same Storage object with `upsert: true`. A book has exactly one image
today, and each scene's `final_image_ref` points at whichever scene ran last. This is a defect, not
a simplification, and this spec is where it is fixed.

## 3. Position in the system map

Unchanged and linear. `graph.py` is **not** touched by this spec.

```
char_bible ──► generate_scene ──► consistency_check ──► compose
                     ▲
         build_prompt (prompt-optimizer, already wired)
```

**No conditional edge.** ADR-024 specifies `route_next_scene` at the loop head and
`route_after_check` after the consistency gate; neither exists, and both are handed to
`consistency-checker` (§8) so the two halves of one loop land in one change.

**Provisional `final_image_ref`.** Under ADR-024 the finalizing write belongs to
`consistency_check` / `regenerate`. Until those nodes are real, dropping the write here means no
scene ever finalizes, `compose` reads nothing, and the job regresses against what works today. The
node therefore keeps setting it, marked in code as provisional and named in §8 as
`consistency-checker`'s to take.

## 4. Behavior & edge cases

### Effect boundary

One module-level helper per node (MASTER_SPEC §6 "The node test seam"). The fal reference upload
lives **inside** it, not beside it — same shape as `char_bible.mint_reference`.

```python
IMAGE_BUDGET = MAX_SCENES * 2 + 9    # ADR-025 D4; prelude 9 per ADR-029

@lru_cache(maxsize=8)                # keyed on the path, which already contains story_id + char_id
def _fal_ref_url(ref_path: str) -> str: ...        # Storage download → providers.upload_reference

def generate_and_store(
    prompt: str, story_id: str, scene_id: str, ref_paths: list[str]
) -> tuple[str, bool]:               # (storage_path, paid)
```

`MAX_SCENES = 15` moves out of `segment.py`'s bare literals (`segment.py:118-120`) into
`app/config.py` as a module-level constant, alongside the `STYLE_PRESETS` precedent, and both
modules import it. ADR-025 Decision 4 is explicit that the domain-level breaker and ADR-024's
`recursion_limit` share **one** number; writing `39` here would create the second copy of `15` and
exactly the drift AGENTS.md's *Definition of Done* grep exists to prevent.

### Happy path

1. Select the first `Scene` whose `final_image_ref is None` (ADR-024 — no cursor). None → `{}`.
2. **Breaker first.** `state.cost.image_count >= IMAGE_BUDGET` → raise. Pure arithmetic, evaluated
   before any spend, so a runaway cannot buy one more image on its way out.
3. `build_prompt(scene.text_excerpt, scene.characters_present, state.characters,
   state.style.prompt_fragment)` — unchanged from `prompt-optimizer`.
4. Collect `canonical_ref_image` for each `char_id` in `characters_present` that resolves to a
   `Character` carrying one.
5. Helper: if `{story_id}/{scene_id}.png` already exists in Storage → return it with `paid=False`.
   Otherwise `edit_image(prompt, [fal urls])` — or `text_to_image(prompt)` when `ref_paths` is
   empty — then upload, `paid=True`.
6. Partial-return the scene with `prompt`, the appended `Attempt(image_ref=path, prompt=prompt,
   passed=False)`, the provisional `final_image_ref`, and `cost` bumped **iff `paid`**.

### Edge cases

| Case | Behavior |
|---|---|
| **`characters_present` empty, or no present character has a reference** | `text_to_image` with the same prompt, logged. `segment` can legitimately produce unreferenced scenes, and the style fragment is still in the prompt (ADR-007's belt-and-suspenders half). |
| **`char_id` present but absent from `state.characters`** | Skipped, logged. Same posture as `build_prompt` and `segment` — this node may not extend the roster. |
| **Reference exists but `ref_verdict.matches_description is False`** | **Used anyway.** ADR-028 deliberately ships the best-of reference and persists the failing verdict. Filtering it here would silently drop the scene to text-to-image and discard the art style with it (ADR-001's "no error, no warning" failure mode). |
| **Storage asset already exists (resume)** | Reused; no fal call, no `image_count` bump. The `Attempt` is still appended — a re-executed super-step must still produce its state write. |
| **fal hard failure after ADR-025 retries** | Propagates out of the node → `run_job.py`'s top-level `except` → job `failed`. No placeholder (ADR-010, ADR-025 D2). |
| **`cost.image_count` at or over `IMAGE_BUDGET`** | Raise before step 3. The helper is never called. |
| **More than 2 references for one scene** | Cannot occur — ADR-004 caps `char_bible` at 2 per book. No defensive truncation. |

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-3 Cost control** — bumps `cost.image_count` per paid draw and trips the ADR-025
      Decision 4 breaker at `MAX_SCENES × 2 + 9 = 39`. `character-bible` §8 handed the scene half of
      this field here and noted the breaker "cannot trip until this node writes its share"; it
      becomes live with this spec.
- [x] **CC-5 Observability** — one line per scene: `scene_id`, reference count, `paid|reused`,
      prompt length. A wrong character downstream traces to a specific scene and a specific
      reference set.
- [x] **CC-10 Checkpointing / resumability** — the Storage-exists skip (ADR-025 Decision 3's named
      optional upgrade) makes a re-executed super-step free. Side effect: it narrows
      `character-bible` §4's widened mid-node re-pay window.
- [ ] **CC-4 Security** — *partial.* Durable Storage paths are persisted, never signed URLs. But the
      fal reference upload sends a child's generated character to a third party. Same posture as
      `char_bible` sending base64 to OpenRouter; noted, not closed.
- [ ] **CC-1 Moderation ordering** — **open.** This node produces the images a child actually sees
      and there is no output-image gate. Owned by `moderation-stack` (Phase 2). Not ticked.
- [ ] **CC-7 Reproducibility (seed)** — **not satisfied.** No seed is passed. Probe 2 never ran and
      `qwen-image-edit-2511`'s seed behaviour is unverified (`PHASE_05_RESULTS.md` Probe 2), so a
      seed seam here would build for a claim that cannot be made. Recorded as a gap, not omitted.
- [ ] **CC-9 Failure states** — the raise reaches `run_job.py`, but ADR-025 Decision 5's
      `jobs.failure_reason` column does not exist, so a breaker trip lands in the generic handler as
      a dev-only `error` string. Flagged in §8, not absorbed.
- CC-2 (PII — `input_gate`'s job, upstream), CC-6, CC-8: N/A.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

**Helper (`generate_and_store`, providers + Supabase client mocked):**
- An existing Storage asset is reused: `paid is False`, and neither `edit_image` nor `text_to_image`
  is called.
- `ref_paths` non-empty → `edit_image` called with the resolved fal URLs.
- `ref_paths` empty → `text_to_image` called, `edit_image` not.
- `_fal_ref_url` memoizes: two calls for the same path perform one download and one
  `upload_reference`.

**Node (`generate_scene`, helper patched — the node seam):**
- The path is `{story_id}/{scene_id}.png`, and two successive invocations over evolving state
  produce **two distinct paths**. *(Regression test for the `scene-1.png` collision, §2.)*
- The appended `Attempt` has `passed is False`.
- `cost.image_count` is +1 when `paid`, and unchanged when the asset was reused.
- `cost.image_count >= IMAGE_BUDGET` → raises, and the helper is never called.
- `ref_paths` contains only `characters_present` entries that resolve to a `Character` with a
  `canonical_ref_image`.
- A `char_id` absent from `state.characters` is skipped without raising.
- A `Character` whose `ref_verdict.matches_description is False` still contributes its reference.
- Unchanged from today: partial-return shape, first-unfinalized-scene selection, `{}` when every
  scene is finalized, and `build_prompt`'s call signature.

`segment`'s existing ≤15 assertions cover the `MAX_SCENES` extraction; no new test is added for a
constant move.

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

N/A as a separate instrument. This node's output *is* the artifact the study measures — its quality
is read by `consistency-checker`'s eval leg (Objective 4's judge labels) and by Objective 3's expert
validation of the finished books. Adding a third instrument here would duplicate both.

## 8. Linked decisions & open questions

**Depends on:** ADR-001 (`fal_image_edit_model`, and `providers.REFERENCE_FIELD`'s silent-drop
warning) · ADR-004 (≤2 canonical references) · ADR-007 (style and identity ride the reference) ·
ADR-010 (never a placeholder page) · ADR-024 (partial return, `final_image_ref is None` loop
position) · ADR-025 (Decision 2 raise-or-finalize, Decision 3 Storage-exists skip, Decision 4 count
breaker) · ADR-028 (a failing `ref_verdict` still ships its reference).

**Hands off — named here, owned elsewhere:**
- **`final_image_ref` ownership and the loop wiring** (`route_next_scene`, `route_after_check`, the
  loop-back edge) → **`consistency-checker`**. Both routers are halves of one loop; splitting them
  across specs would leave `graph.py` in a shape ADR-024 does not describe.
- **`correct_prompt` wiring and the ADR-010 retry draw** → **`regeneration-controller`**.
- **Output-image moderation (CC-1)** → **`moderation-stack`** (Phase 2).
- **`jobs.failure_reason` migration + `run_job.py`'s taxonomy map** (ADR-025 Decision 5) →
  **unowned.** `run_job.py:38` writes only `{status: failed, error: str(exc)}`. It is a migration
  `0003` plus a second-module change; flagged rather than absorbed.
- **Seed / CC-7** → blocked on Probe 2 (`PHASE_05_RESULTS.md`), which does not gate Phase 1.

**Open:**
- ⚠️ **fal reference-URL lifetime is unverified.** If a `upload_reference` URL expires inside a
  15-scene run, later scenes silently lose their reference — fal drops an unfetchable input the same
  way ADR-001's pre-flight found it drops an unknown key: a confident, well-formed image of the
  wrong character. Verify on the first real multi-scene run; the fix is re-uploading per scene
  (drop the cache), which costs latency, not correctness.
- The `lru_cache` is process-local and lost on worker restart — a re-upload, no correctness loss.
- **Character dedup** — still unowned, inherited ceiling from `character-bible` §8. Not taken here.

## 9. Definition of done

Per AGENTS.md *Definition of Done*. This module is done when **all** of the following hold:

1. `backend/app/config.py` gains `MAX_SCENES = 15`; `backend/pipeline/segment.py` imports it in
   place of its bare literals.
2. `backend/pipeline/generate_scene.py` implements §4: `_fal_ref_url`, the widened
   `generate_and_store` returning `(path, paid)`, the deterministic per-scene path, the breaker, the
   `edit_image`/`text_to_image` branch, `passed=False`, and the conditional `cost` bump. The
   `# ponytail: text-to-image, no character reference yet` comment is removed — this spec is the
   change it was waiting for.
3. Every §6 assertion exists and passes in `backend/tests/test_generate_scene_node.py`.
4. Backend verify is green and its output is **shown, not claimed**:
   `uv run ruff check . && uv run pytest` from `backend/`.
5. **Status line above flips to `built`** with the commit range (MASTER_SPEC §7).
6. **The finding-change grep is run** and every hit fixed in the same change. Known surface:
   - `docs/product/DECISION_BACKLOG.md` — tick `image-generator`, move *"Recommended next session"*
     to `consistency-checker`.
   - `docs/WORKFLOW.md` §"Right now".
   - `AGENTS.md` *Validation Notes* (add `image-generator` built) **and** *Project Context* — the
     "Built today" graph line still describes `generate_scene` as text-to-image.

**Not done** if: `backend/contracts/` is modified; `graph.py` gains an edge or a router; the
`scene-1.png` path collision survives; `passed=True` is written on a fresh attempt; `cost.image_count`
is bumped on a reused asset; a failing `ref_verdict` is used to filter out a reference; or the
`consistency-checker` hand-off (`final_image_ref` ownership, the loop wiring) is silently absorbed
into this change.

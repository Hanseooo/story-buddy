# Feature Spec — style-presets

**Status:** built · 2026-07-31 (amended by ADR-042 2026-08-17, cut_paper promoted 2026-08-17) · **Phase:** 1 · **Owner:** `backend/app/config.py`, `backend/app/main.py`,
`backend/worker/run_job.py` — **config + wiring, not a graph node**
**Derived from:** MASTER_SPEC §2 (system map), §3 (frozen contract)
**Rationale:** ADR-022, ADR-042, PRD §8 flow step 4

> Three selectable hand-authored prompt fragments (`gouache` default, `cel`, `cut_paper`), plus one
> compatibility-only fragment (`comic`) for existing books, and the plumbing that gets one of them into
> `StoryMemory.style` before `char_bible` runs. No new node, no new model call, no contract change —
> `Style` already exists in `backend/contracts/story_memory.py`, frozen since `story-memory-contract`.

> **ADR-042 policy:** new jobs select Gouache, Cel, or Paper Cutout and default to an explicitly stored `gouache`; new Comic
> submissions are rejected at the API boundary (422) while existing Comic jobs and legacy null→Cel worker
> resolution remain executable. `cut_paper` ("Paper Cutout") is promoted as the third selectable preset.

## 1. Purpose

Let the author pick one of three selectable art styles (`gouache` default, `cel`, `cut_paper`) before the canonical
character reference is generated, while preserving execution compatibility for existing `comic` books. ADR-022 and ADR-042 decide *how* style works — a prompt fragment
riding the canonical reference, no style-anchor image, chosen once and frozen for the storybook. What
was still unowned in code: the fragments themselves, and a path for the choice to reach
`StoryMemory.style` given that `kid-flow-ui` (the real picker) is Phase 2.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** none.
- **Writes:** `style.style_preset_id`, `style.prompt_fragment` — written once, at `StoryMemory`
  construction in `run_job.py`, before the graph starts. No node in the graph writes `style`.
- **Invariants:**
  1. `STYLE_PRESETS` has the four keys: `cel`, `comic`, `gouache`, `cut_paper`.
  2. `SELECTABLE_STYLE_PRESET_IDS` has exactly the three selectable keys: `cel`, `gouache`, `cut_paper`.
  3. `STYLE_PRESETS["cel"] == settings.default_style_fragment` (single source of truth — no duplicated
     text to drift).
  4. Once written, `style` is never modified by any node (ADR-022: frozen for the life of the
     storybook). This spec doesn't add an enforcement mechanism beyond "no node writes it" — the same
     guarantee `char_bible`'s spec already relies on.

## 3. Position in the system map

Upstream of the graph entirely. `POST /storybooks` validates the choice against `SELECTABLE_STYLE_PRESET_IDS` →
`jobs.style_preset_id` (defaulting to `"gouache"`) → `run_job.py` resolves it into `StoryMemory.style` at
construction (defaulting legacy null rows to `"cel"`) → `char_bible` reads `state.style.prompt_fragment`
(already implemented, with a fallback to `settings.default_style_fragment` that becomes dead code on the normal
path once this ships, and stays as defense-in-depth). No conditional edge, no new node — consistent with
MASTER_SPEC §2's "style presets are config, not a node."

## 4. Behavior & edge cases

**Happy path:**
1. Client `POST /storybooks` with `{"text": ..., "style_preset_id": "cel"}` (or `"cut_paper"`, or omitted for `"gouache"` default).
2. `CreateStorybookRequest` validates `style_preset_id` is `None` or in `SELECTABLE_STYLE_PRESET_IDS` (`{"cel", "gouache", "cut_paper"}`).
3. API stores `payload.style_preset_id or "gouache"` on the `jobs` row alongside `input_text`.
4. Worker reads the row, resolves `chosen_id = row.style_preset_id or "cel"` (preserving legacy null rows as `cel`), looks up
   `STYLE_PRESETS[chosen_id]`, and constructs `StoryMemory(..., style=Style(style_preset_id=chosen_id, prompt_fragment=fragment))`.
5. `char_bible` consumes `state.style.prompt_fragment` unchanged from today.

**Edge cases:**
- `style_preset_id` omitted or `null` on new API request → stored as `"gouache"` (ADR-042 default).
- Legacy worker row with `null` `style_preset_id` → resolves to `"cel"` (ADR-042 legacy compatibility).
- `style_preset_id` is `"comic"` on new API request → rejected with **422 at the API boundary** (ADR-042 hard retirement).
- `style_preset_id` is `"cut_paper"` on new API request → **200 accepted** (ADR-042 promotion).
- `style_preset_id` present but not in `SELECTABLE_STYLE_PRESET_IDS` → **422 at the API boundary** (CLAUDE.md §7).
- Empty string `""` → 422, same as any other unknown id.

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] CC-3 Cost control — zero marginal cost; presets are strings, no extra model call (ADR-022).
- [x] CC-5 Observability — `style.style_preset_id` is already part of the traced `StoryMemory`; no
      new tracing needed.
- [x] CC-8 Kid vs parent design — the actual picker UI (three sample cards for Gouache, Cel, and Paper Cutout, not a dropdown per PRD
      §8) in `frontend/app/s/[profileId]/write/page.tsx`, defaulting to Gouache.
- All other CC items: N/A — no moderation, PII, security, accessibility, reproducibility, or
  checkpointing surface changes.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Models mocked / not invoked — this is config and plumbing:

1. `STYLE_PRESETS` has exactly the keys `{"cel", "comic", "gouache", "cut_paper"}`.
2. `SELECTABLE_STYLE_PRESET_IDS` has exactly the keys `{"cel", "gouache", "cut_paper"}`.
3. `STYLE_PRESETS["cel"] == settings.default_style_fragment`.
4. `POST /storybooks` with a valid selectable `style_preset_id` → 200, and the `jobs` row stores it.
5. `POST /storybooks` with `"comic"` or unknown `style_preset_id` → 422, no `jobs` row created. `"cut_paper"` → 200.
6. `POST /storybooks` with `style_preset_id` omitted or `None` → 200, row's `style_preset_id` is `"gouache"`.
7. `run_job.py`: given a `jobs` row with `style_preset_id="gouache"`, the constructed `StoryMemory.style`
   has `style_preset_id="gouache"` and `prompt_fragment == STYLE_PRESETS["gouache"]`.
8. `run_job.py`: given a `jobs` row with `style_preset_id="comic"`, the constructed `StoryMemory.style`
   has `style_preset_id="comic"` and `prompt_fragment == STYLE_PRESETS["comic"]`.
9. `run_job.py`: given a legacy `jobs` row with `style_preset_id=None`, `StoryMemory.style.style_preset_id ==
   "cel"`.

## 7. Eval / quality checks

N/A. The aesthetic acceptance condition ADR-022 / ADR-042 attaches to presets ("must not read as
generic AI art... must hold character identity") is measured offline on frozen story corpora, not by this
spec — this spec only ships the fragments and the wiring, it doesn't re-run that evaluation.

## 8. Linked decisions & open questions

- **ADR-022** — prompt fragment riding canonical reference; within-preset judging.
- **ADR-042** — amends ADR-022 selectable catalog (`gouache` default, `cel`, `cut_paper`), retires `comic` from new creation,
  and specifies the provisional `cut_paper` offline candidate gate and promotion.
- **ADR-007** — style rides the canonical character reference; unchanged.
- **Schema note:** `jobs.style_preset_id` nullable column in `0002_jobs_style_preset_id.sql`, updated constraint in `0015_add_cut_paper_style_preset.sql`.
- **No open questions.** The reveal/confirm step (D-I, closed 2026-07-31 → **ADR-029**) is out of scope
  here — it governs when the child *sees* the reference, not which style fragment gets chosen. ADR-029's
  targeted redraw restates a `CharacterDescription` attribute, never the style fragment, so the frozen
  `style.prompt_fragment` survives a reveal retry unchanged.

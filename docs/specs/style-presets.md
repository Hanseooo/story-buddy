# Feature Spec — style-presets

**Status:** draft · **Phase:** 1 · **Owner:** `backend/app/config.py`, `backend/app/main.py`,
`backend/worker/run_job.py` — **config + wiring, not a graph node**
**Derived from:** MASTER_SPEC §2 (system map), §3 (frozen contract)
**Rationale:** ADR-022 (amends ADR-007), PRD §8 flow step 4

> Three hand-authored prompt fragments and the plumbing that gets one of them into `StoryMemory.style`
> before `char_bible` runs. No new node, no new model call, no contract change — `Style` already exists
> in `backend/contracts/story_memory.py`, frozen since `story-memory-contract`.

## 1. Purpose

Let the author pick one of three art styles (`cel` / `comic` / `gouache`) before the canonical
character reference is generated. ADR-022 already decided *how* style works — a prompt fragment
riding the canonical reference, no style-anchor image, chosen once and frozen for the storybook. What
was still unowned in code: the three fragments themselves, and a path for the choice to reach
`StoryMemory.style` given that `kid-flow-ui` (the real picker) is Phase 2.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** none.
- **Writes:** `style.style_preset_id`, `style.prompt_fragment` — written once, at `StoryMemory`
  construction in `run_job.py`, before the graph starts. No node in the graph writes `style`.
- **Invariants:**
  1. `settings.style_presets` has exactly the three ADR-022 keys: `cel`, `comic`, `gouache`.
  2. `style_presets["cel"] == settings.default_style_fragment` (single source of truth — no duplicated
     text to drift).
  3. Once written, `style` is never modified by any node (ADR-022: frozen for the life of the
     storybook). This spec doesn't add an enforcement mechanism beyond "no node writes it" — the same
     guarantee `char_bible`'s spec already relies on.

## 3. Position in the system map

Upstream of the graph entirely. `POST /storybooks` validates the choice → `jobs.style_preset_id` →
`run_job.py` resolves it into `StoryMemory.style` at construction → `char_bible` reads
`state.style.prompt_fragment` (already implemented, with a fallback to `settings.default_style_fragment`
that becomes dead code on the normal path once this ships, and stays as defense-in-depth). No
conditional edge, no new node — consistent with MASTER_SPEC §2's "style presets are config, not a
node."

## 4. Behavior & edge cases

**Happy path:**
1. Client `POST /storybooks` with `{"text": ..., "style_preset_id": "comic"}`.
2. `CreateStorybookRequest` validates `style_preset_id` is `None` or a key of `settings.style_presets`.
3. API stores it on the `jobs` row (nullable `style_preset_id` column) alongside `input_text`.
4. Worker reads the row, resolves `chosen_id = row.style_preset_id or "cel"`, looks up
   `settings.style_presets[chosen_id]`, and constructs
   `StoryMemory(..., style=Style(style_preset_id=chosen_id, prompt_fragment=fragment))`.
5. `char_bible` consumes `state.style.prompt_fragment` unchanged from today.

**Edge cases:**
- `style_preset_id` omitted or `null` → defaults to `"cel"` (ADR-022's "flagship default kids see
  first"). Same behavior as today's unset-`style` path, just now explicit instead of falling through
  `char_bible`'s fallback.
- `style_preset_id` present but not one of the three keys → the request **422s at the API boundary**
  (CLAUDE.md §7: validate at the trust boundary). It never reaches the worker or the pipeline.
- Empty string `""` is not a valid key → 422, same as any other unknown id.

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] CC-3 Cost control — zero marginal cost; presets are strings, no extra model call (ADR-022).
- [x] CC-5 Observability — `style.style_preset_id` is already part of the traced `StoryMemory`; no
      new tracing needed.
- [ ] CC-8 Kid vs parent design — the actual picker UI (three sample cards, not a dropdown per PRD
      §8) is `kid-flow-ui`, Phase 2. This spec only makes the API accept and validate the choice; it
      ships no UI.
- All other CC items: N/A — no moderation, PII, security, accessibility, reproducibility, or
  checkpointing surface changes.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Models mocked / not invoked — this is config and plumbing:

1. `settings.style_presets` has exactly the keys `{"cel", "comic", "gouache"}`.
2. `settings.style_presets["cel"] == settings.default_style_fragment`.
3. `POST /storybooks` with a valid `style_preset_id` → 200, and the `jobs` row stores it.
4. `POST /storybooks` with an invalid `style_preset_id` → 422, no `jobs` row created.
5. `POST /storybooks` with `style_preset_id` omitted → 200, row's `style_preset_id` is `null`.
6. `run_job.py`: given a `jobs` row with `style_preset_id="gouache"`, the constructed `StoryMemory.style`
   has `style_preset_id="gouache"` and `prompt_fragment == settings.style_presets["gouache"]`.
7. `run_job.py`: given a `jobs` row with `style_preset_id=None`, `StoryMemory.style.style_preset_id ==
   "cel"`.

## 7. Eval / quality checks

N/A. The aesthetic acceptance condition ADR-022 attaches to the three presets ("must not read as
generic AI art... must hold character identity") is measured by Probe 1's secondary arm, not by this
spec — this spec only ships the fragments and the wiring, it doesn't re-run that evaluation.

## 8. Linked decisions & open questions

- **ADR-022** — the three presets, their content direction, and the "config not a node" mechanism are
  frozen there; this spec implements it, it doesn't reopen it.
- **ADR-007** — style rides the canonical character reference; unchanged.
- **Schema note:** `jobs.style_preset_id` is a new nullable column. No migration files exist in-repo
  (schema is managed Supabase-side); this is called out here since it's an additive, non-breaking
  column, not a decision that needs its own ADR.
- **No open questions.** D-I (Tier 2c, the reveal/confirm step) is explicitly out of scope here — it
  governs when the child *sees* the reference, not which style fragment gets chosen.

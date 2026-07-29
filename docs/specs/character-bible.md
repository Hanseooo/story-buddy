# Feature Spec — character-bible

**Status:** draft · **Phase:** 1 · **Owner node:** `backend/pipeline/char_bible.py`
**Derived from:** MASTER_SPEC §2 (system map), §3 (frozen contract), §5 (CC registry), §6 (test seam)
**Rationale:** ADR-002, ADR-004, ADR-007 (as amended by ADR-028), ADR-010, ADR-022, ADR-023 (D-F, D-G),
ADR-024, ADR-025, ADR-028, PRD §8

> The node every other image in the book depends on. It draws the canonical character reference,
> **checks it against the description it came from** (ADR-028), and persists both. This spec adds
> **no** contract fields and bumps **no** `schema_version` — every type it needs already exists.

## 1. Purpose

Draw one canonical reference image per principal character, judge it against that character's
`CharacterDescription`, re-roll up to a cap of 3 draws, and persist the accepted image path plus its
verdict.

Every scene image is a reference-conditioned edit of these images (`providers.edit_image`), so
**identity and style both ride on what this node produces** (ADR-007, ADR-022). ADR-028 falsified
ADR-007's assumption that a reference is correct *because* it was generated from the description —
`fal-ai/qwen-image` produced an off-spec reference on the character's defining feature in 3 draws out
of 4. This node is the gate that makes that failure visible.

⚠️ **This gate makes the failure loud. It does not fix the rate** (ADR-028). At the measured draw
quality, 3 draws still ship an off-spec reference roughly 42% of the time — now with the verdict
persisted instead of silently. The fix for the *rate* is swapping `fal_image_model` (ADR-001's named
seam), not anything in this file.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `characters[]` (`name`, `description`, `canonical_ref_image`), `style.prompt_fragment`,
  `story_id`, `cost`
- **Writes:** `characters[]` (the **full** list), `cost.image_count`
- **Does not write:** `ref_moderation_status` (owned by the Phase-2 char-ref moderation node — see
  §8), `scenes[]`, `style`

**Invariants** (each guarded by a test in §6):

1. **At most 2 characters get a reference** — `characters[0]` and `characters[1]`, in the prominence
   order `analyze` minted. ADR-004: *"max 2 canonical refs, v1."* A third character keeps
   `canonical_ref_image = None`.
2. **The returned `characters` list is complete.** `characters` carries **no reducer** — only
   `scenes[]` is `Annotated` with `upsert_scenes` (ADR-024, `story_memory.py:173`). A partial-return
   of `{"characters": [...]}` therefore **replaces** the list, so returning only the two modified
   entries would silently delete the third character.
3. **At most 3 draws per character** (ADR-028).
4. `cost.image_count` rises by **exactly** the number of draws actually made. `cost` has no reducer
   either, so it is copied from `state.cost` and bumped — never rebuilt from zero, which would erase
   any field a future node has written.
5. `canonical_ref_image` is a durable Storage **path**, never a signed URL and never the base64 data
   URI the judge was shown.
6. A character that already has a `canonical_ref_image` is **skipped** — zero draws, zero cost.

## 3. Position in the system map

```
input_gate ──► analyze ──► segment ──► char_bible ──► generate_scene ──► ...
```

Linear. **No conditional edge.** ADR-003's two branch points are moderation pass/fail and consistency
pass/fail, and this node is neither.

**The acceptance loop adds no edge and no super-step.** ADR-028 Decision 3 settles this explicitly: a
node that re-rolls its own output and returns once is node-internal. ADR-003 constrains the *graph*;
ADR-024 §4 constrains *routers*. Neither speaks to node internals, so **ADR-003 and ADR-024 are
unamended** by this spec.

**Test seam (MASTER_SPEC §6):** one module-level helper,
`mint_reference(description, name, style_fragment, story_id, char_id) -> tuple[str, RefVerdict | None, int]`,
is the effect boundary. The third element is the **number of draws made** — the node cannot compute it
(the loop is inside the helper) and needs it for invariant 4, so the helper reports it rather than the
node inferring it. It wraps all three of this node's effects — `text_to_image`, `judge`, and the
Storage upload — exactly as `generate_scene.generate_and_store` already bundles generate + store
behind one seam. Node and graph tests patch `pipeline.char_bible.mint_reference`; the helper's own
tests patch `pipeline.char_bible.text_to_image` / `.judge` and the Storage client.

`reference_prompt` and `best_draw` are **pure** functions, so they are not second effect boundaries
(§6 rule 1 governs the *effect* seam) and need no mocks at all.

## 4. Behavior & edge cases

### Module shape

```
char_bible(state) -> dict                                      # pure: select, map, partial-return
  └─ mint_reference(...) -> (path, RefVerdict | None, draws)   # the one effect boundary
        ├─ reference_prompt(description, name, style_fragment) -> str   # pure
        └─ best_draw(verdicts) -> int                                   # pure
```

### Happy path

1. Take `characters[:2]` (invariant 1), **then** drop any that already have a `canonical_ref_image`
   (invariant 6). The order matters: filtering first and *then* taking two would slide the window onto
   `c2` when `c0` is already referenced, producing three canonical references and breaking ADR-004's
   cap.
2. `style_fragment = state.style.prompt_fragment or settings.default_style_fragment`.
3. For each selected character, `mint_reference(...)` → `(path, verdict, draws)`; accumulate `draws`.
4. Build the **full** `characters` list: modified entries via `model_copy(update=...)`, everything
   else unchanged (invariant 2).
5. Partial-return `{"characters": [...], "cost": ...}` (ADR-024 — never mutate `state`).

### The acceptance loop (ADR-028 Decision 3)

```python
candidates = []
for _ in range(MAX_DRAWS):              # 3
    image = text_to_image(prompt)       # hard failure → raises (ADR-025)
    draws += 1
    try:
        verdict = judge([_data_uri(image)], RefVerdict)
    except Exception:                   # the artifact exists; the CHECK failed — see below
        return _upload(image), None, draws
    if verdict.matches_description:
        return _upload(image), verdict, draws
    candidates.append((image, verdict))

image, verdict = candidates[best_draw([v for _, v in candidates])]
return _upload(image), verdict, draws   # a FAILING verdict, persisted — loud, never a placeholder
```

**Cap of 3, not ADR-010's 1**, because the blast radius differs: a bad scene is one page, a bad
reference is every page (ADR-028).

**Best-of ranks on `len(attributes_present)`**, ties → earliest draw. This is `char_bible`'s own rule
over `RefVerdict` and is **unrelated** to `regeneration-controller`'s lexicographic scene rule over
`VlmVerdict` — different schema, different question. Do not unify them.

### Two `providers.py` calls, two failure policies — deliberate

This is the first node in the codebase where two provider calls get **different** ADR-025 treatment.
Stated loudly so nobody "fixes" the inconsistency later:

| Call | Failure | Why |
|---|---|---|
| `text_to_image` | **Raises** → job `failed`, `provider_error` | No artifact. There is nothing to ship, so ADR-025 Decision 1 applies as written. |
| `judge` | **Degrades** → accept the draw, `ref_verdict = None` | The artifact exists and is paid for. The *check* failed. An unchecked reference is precisely what ADR-007 shipped before ADR-028 amended it — it is not a placeholder and not a broken page, so ADR-010's "always something shippable" governs and ADR-025's "never a partial book" rationale does not bite. |

`ref_verdict = None` stays honest and is distinguishable from a *failed* verdict
(`matches_description = False`). The cost is real and recorded: for that book, ADR-028's stated
Phase-1 measurement — the reference generator's true hit rate — silently reverts to unmeasured.

### No seed, by necessity

`providers.text_to_image` accepts a seed, but a **fixed seed makes all three draws identical** and the
re-roll a no-op. Draws are therefore independent and unseeded. CC-7 is unsatisfied here as a direct
consequence of the mechanism, not an oversight — see §5.

### Prompts (D-F: transient, so they live beside their node)

Two module-level constants. Neither introduces a contract type; `RefVerdict` already lives in
`backend/contracts/` because `StoryMemory` embeds it (D-F, ADR-023 amendment).

`reference_prompt` renders the `CharacterDescription` axes (`species`, `colours`, `body_features`,
`clothing`, `notes`) plus the style fragment, and asks for a single full-body character reference on a
plain neutral background. Per ADR-022 the fragment **names a medium and its physical artifacts** — it
never says "beautiful", "8k", or "highly detailed".

The judge prompt shows the drawn image and the description it should depict, and asks for
`differences_observed` before `matches_description`. ADR-004's reason-then-score ordering applies to
**every** judge call; `RefVerdict` already declares the fields in that order and
`providers._assert_field_order` enforces it on the wire.

### `settings.default_style_fragment`

One new config field, holding ADR-022's `cel` preset — *"the flagship default kids see first"*. This is
ADR-007 as originally written (one fixed style). **ADR-022's three-preset `style_presets` dict, the
`style_preset_id` resolution, the picker UI, and the binding "must not read as generic AI art"
acceptance condition remain wholly owned by the `style-presets` spec.** This node only needs *a*
fragment to exist.

### Edge cases

| Case | Behavior |
|---|---|
| **Zero characters** | Return `{}`. No refs, no cost change. Scenes generate unreferenced — `analyze`'s precedent; a book with drifting art beats no book (ADR-010). |
| **One character** | One reference. The cap is a ceiling, not a quota. |
| **Three characters** | `c0` and `c1` get references; `c2` keeps `None` and its scenes generate unreferenced. Documented ceiling per ADR-004, not a bug. |
| **Duplicate character** ("my sister" / "Ate") | Both reference slots burned by one real character; the genuine second character gets nothing. **Sharper than `story-analyzer` §4 documented it** — under a 3-character roster a duplicate cost one of three slots, under a 2-reference cap it costs both. Not guarded here: dedup is unowned (§8). |
| **Species-only description** | **Draw anyway, never refuse.** A thin description is exactly when an anchor matters most — consistency across scenes comes from *having* a reference, not from the reference matching the child's mental image (ADR-010). Ceiling: with one attribute `matches_description` is near-vacuously true, so the loop de facto collapses to 1 draw for that character. ADR-028 targets *off-spec on a stated feature*; a thin description states none. This closes `story-analyzer` §8's richness handoff. |
| **Fully empty description** | The contract permits it (`CharacterDescription` is all-Optional) even though `analyze`'s LLM boundary requires `species` — a resumed pre-`story-analyzer` checkpoint could carry one. The prompt floors to `Character.name`. |
| **`style.prompt_fragment` is `None`** | Falls back to `settings.default_style_fragment`. Nothing writes `style` today; the fallback is the normal path in Phase 1, not an error path. |
| **All 3 draws fail** | Best-of by `len(attributes_present)`, ties → earliest. The **failing verdict is persisted** — never a failed job, never a placeholder, the same policy ADR-010 sets for scenes (ADR-028). |
| **All `attributes_present` empty** | `best_draw` returns `0`. Deterministic, never arbitrary. |
| **Judge hard failure** | Accept the current draw, `ref_verdict = None`, stop re-rolling. See the two-policies table above. |
| **`text_to_image` hard failure** | Raises → job `failed` with an ADR-025 `failure_reason`. No character gets a reference; never a partial roster. No node-level retry — the OpenAI SDK / fal helper bounded retry is the entire policy (ADR-025 Decision 1). |
| **Image-model self-refusal** | Surfaces as a provider error → same as above. Knowingly blunt: ADR-025 classes content-refusal as *not* a resilience concern and hands soften-and-retry to `self-refusal-fallback` (Phase 2). |
| **Resume mid-node** | All-or-nothing. LangGraph checkpoints *after* the node, so a crash inside it re-pays **up to 6 draws** on resume. ADR-025 accepted at-least-once re-pay sized as *"a rare crash, cents of cost"* — for this node that window is materially wider. Flagged, not absorbed; the fix ADR-025 sanctions (deterministic path + skip-if-exists) is owned by `image-generator` (§8). |
| **Re-entry after success** | Invariant 6: any character with a `canonical_ref_image` is skipped. Zero draws, zero cost. |
| **Prompt injection via the description** | The description derives from child text and enters an image prompt. `input_gate` moderates the text **first** — CC-1's ordering is the mitigation and it is a graph edge, not something this node re-implements. Strict `json_schema` constrains the *shape* of the judge's reply, not content. Defence-in-depth, same posture as `analyze`. |
| **Base64 payload size** | A 1024² PNG is ~1.4 MB raw, ~1.9 MB base64-encoded, and `providers._run_fal` hardcodes `output_format: "png"`. **Recorded as a build-time risk, not assumed fine.** Verify the judge accepts it on the first real call; if OpenRouter rejects the body, the fallback is a Storage upload plus a new signed-URL helper in `app/db.py` (§8). |

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-3 Cost control** — writes `cost.image_count` (invariant 4) and supplies the number ADR-025
  Decision 4 left unstated: the breaker bound `max_scenes × 2 + prelude` has **`prelude = 6`**
  (2 references × 3 draws). The 2-reference cap *is* the pre-scene ceiling.
  ⚠️ **One inaccuracy in ADR-025 to record, not amend.** ADR-025 states the domain-level breaker and
  `recursion_limit` *"share one number"*. They no longer track together: ADR-028's loop is
  node-internal, so it consumes **zero** super-steps (`recursion_limit`'s `fixed_prelude` is
  unaffected) while adding up to 6 to `image_count`. The two preludes are different units. Neither
  bound is wrong; the claim that they are the same number is.
- [x] **CC-5 Observability** — the helper logs, per character: draws made, each verdict's
  `matches_description` and `attributes_present`, and which draw won. A wrong character downstream
  traces back to a specific reference and a specific draw.
- [x] **CC-9 Failure states** — a missing reference is **not** a failure and must never fail the job.
  Only a `text_to_image` hard failure does, through the ADR-025 `failure_reason` enum.
- [x] **CC-10 Checkpointing** — idempotent re-entry (invariant 6), one partial-return, no partial
  writes. The widened mid-node re-pay window is stated in §4 rather than hidden behind this tick.
- [ ] **CC-1 Moderation ordering** — **not satisfied.** No image from this node reaches a child
  *today*, but the surface where one would — PRD §8 flow step 7's reveal — has no graph
  representation at all (§8, `D-I`). `ref_moderation_status` is left `None` for its Phase-2 owner.
  Do not read this node's completion as CC-1 being closed for the char-ref leg.
- [ ] **CC-2 PII redaction** — inherited: descriptions derive from `redacted_text` via `analyze`, and
  `analyze`'s descriptive-label convention means neither a real name nor a `<PERSON_1>` placeholder
  reaches an image prompt. ⚠️ Carries the same caveat — `input_gate` is a pass-through stub and
  Presidio is not a dependency anywhere in `backend/` today.
- [ ] **CC-4 Security** — writes to Supabase Storage and emits a **path**, never a URL; signing is the
  reader's job. The open RLS gap (`0001_jobs_table.sql`) is unchanged by this node, neither closed nor
  widened.
- [ ] **CC-7 Reproducibility** — **not satisfied, and unsatisfiable as designed.** A fixed seed makes
  the three draws identical and the re-roll a no-op (§4). Two runs of the same story produce different
  references. Same family as `story-analyzer`'s unseeded extraction; recorded here, not closed here.
- [ ] CC-6, CC-8 — N/A. This node renders no UI and produces no narration.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Every model call mocked. **No assertion touches image or verdict quality** — that is Tier B by
definition.

**Provider seam** — patch `pipeline.char_bible.text_to_image`, `.judge`, and the Storage client:

- **Pass on first draw:** one `text_to_image` call, one `judge` call, verdict returned unchanged
- **Re-roll:** fail → fail → pass yields **3** draws, and the **third** image's bytes are uploaded
- **Exhaustion best-of:** three failing verdicts with `attributes_present` of lengths `1, 3, 2` →
  the **second** draw's bytes are uploaded (guards the ranking key)
- **Tie → earliest:** lengths `2, 2, 2` → the **first** draw's bytes are uploaded
- **Cap:** never more than 3 `text_to_image` calls, however many verdicts fail
- **Judge hard failure:** `judge` raises → the first draw is accepted, the returned verdict is `None`,
  and **no re-roll happens** (exactly one `text_to_image` call)
- **Image hard failure:** `text_to_image` raises → the exception **propagates** (guards ADR-025)
- **Upload target:** path is exactly `{story_id}/ref-{char_id}.png`
- **Data URI:** the value passed to `judge` starts with `data:image/png;base64,` — **not** `http`
  (guards invariant 5 and the CC-4 posture)
- **Draw count:** the count the helper reports equals the number of `text_to_image` calls

**Node, helper mocked** — patch `pipeline.char_bible.mint_reference`:

- **2-reference cap:** a 3-character roster calls the helper exactly **twice**, for `c0` and `c1`
  (guards invariant 1)
- **Full list returned:** `len(result["characters"]) == 3` and `c2` is byte-identical to input —
  guards invariant 2, the reducer trap
- **Cost:** `image_count` equals prior + draws made, and `regen_count` / `usd_estimate` are
  **preserved**, not reset (guards invariant 4)
- **Empty roster:** zero characters → helper never called, and the node does **not** raise
- **One character:** exactly one helper call
- **Idempotency:** a character that already has a `canonical_ref_image` is skipped, and a roster where
  both are already set makes zero helper calls (guards invariant 6)
- **Cap-then-filter ordering:** a 3-character roster where `c0` already has a reference calls the
  helper **once, for `c1` only** — never for `c2`. Guards the §4 trap where filtering before capping
  slides the window and mints a third canonical reference against ADR-004.
- **`ref_moderation_status` untouched:** still `None` on every returned character
- **Partial-return (ADR-024):** result keys are exactly `{"characters", "cost"}`, and `state` is
  unmutated afterwards
- **Style fallback:** `style.prompt_fragment = None` → the helper receives
  `settings.default_style_fragment`; when set, the state value wins

**Pure functions** — no mocks:

- `best_draw` — ranking by `len(attributes_present)`; ties return the lowest index; all-empty returns
  `0`
- `reference_prompt` — contains each populated description axis; falls back to `Character.name` on a
  fully empty description; always contains the style fragment

**Graph** — patch the single helper and assert the references survive
`input_gate → analyze → segment → char_bible` (one patch point per node, MASTER_SPEC §6 rule 1).

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

Two questions, both offline on the story corpus with real models, never in CI.

**Reference fidelity** — does the canonical reference depict the character a human reads in the story?
Feeds **Objective 3** (expert validation: visual presentation, visual style consistency). Per
MASTER_SPEC §6 this is a *pipeline behaviour exercised inside that leg*, **not** an evaluation leg of
its own — do not construct a separate instrument for it.

**The measurement ADR-028 is buying** — the reference generator's real hit rate across *ordinary*
characters. ADR-028's 25% figure is `n = 4` on one invented chimera's hardest feature, and it flags
the rate across ordinary characters as unmeasured. Persisted `ref_verdict` values are what will
measure it, at zero marginal cost.

⚠️ **`RefVerdict` is a slot, not a validated signal** — the same caveat ADR-028 attaches to
`anatomy_intact`. Whether `google/gemma-3-27b-it` reliably notices that a reference is off-spec is
unknown. **Validate `matches_description` against the scorer's eye in Phase 1 before treating the
persisted rate as a number**, or the measurement above measures the judge instead of the generator.

## 8. Linked decisions & open questions

**Depends on:** ADR-002 (strict `json_schema` + `require_parameters`) · ADR-004 (max 2 canonical
references, v1) · ADR-007 as amended by ADR-028 (style rides the reference; the reference is checked,
not assumed) · ADR-010 (always something shippable; best-of over a failed loop) · ADR-022 (style is a
prompt fragment, frozen before the reference is drawn) · ADR-023 amendment, D-F (schema home) and D-G
(id minting) · ADR-024 (partial-return, no mutation, reducer scope) · ADR-025 (failure taxonomy, cost
breaker, at-least-once re-pay) · ADR-028 (the whole acceptance loop) · MASTER_SPEC §2 node-I/O table,
§5 CC registry, §6 test seam.

**Closes:** `story-analyzer` §8's handoff — *"is species-only enough to draw a canonical reference
from, or should that character be refused?"* **The answer is draw anyway, never refuse** (§4). The
character described least is the one that most needs an anchor, and refusing would guarantee its drift
while telling the child nothing.

**Corrected 2026-07-30, when this spec was written** (AGENTS.md *Definition of Done* — finding-change
grep; both live in docs marked `built`, so they were fixed on discovery rather than deferred to the
build):

- `docs/specs/story-analyzer.md` §5 CC-3 — its arithmetic read *"at most 9 reference draws
  (3 characters × ADR-028's 3-draw cap)"*. ADR-004 caps canonical references at **2**, so the real
  pre-scene ceiling is **6**. The character cap and the reference cap are different numbers. Struck
  through in place, since the superseded figure is part of that spec's record.
- `docs/MASTER_SPEC.md` §2 node-I/O — the `char_bible` row listed `ref_moderation_status` as an output
  of this node. It is not; it is written by the Phase-2 char-ref moderation node, which had no row of
  its own. The row now reads `canonical_ref_image`, `ref_verdict`, `cost.image_count`, and a separate
  row was added for the Phase-2 gate.

**Hands off — named here, owned elsewhere:**

- **PRD flow step 7 (reveal + confirm)** → **`D-I`, opened in `DECISION_BACKLOG.md` by this spec.**
  The PRD promises the child sees the moderated reference and gets a lightweight "try again" before
  full generation. **ADR-024's canonical graph has no such interrupt and `graph.py` runs straight
  through.** Three things are undefined: whether the confirm is a graph interrupt or a separate
  invocation; whose budget a child's "try again" spends (a fresh 3 draws? the remainder?); and how it
  accounts against CC-3. Given ADR-028's own ⚠️ that ~42% of books still ship an off-spec reference,
  that button is arguably the *real* mitigation — so this gap is load-bearing, not cosmetic. It
  changes the graph shape ADR-024 froze and touches the `jobs` table, which makes it an ADR session,
  never something settled inline while building a module (AGENTS.md).
- **`cost.image_count` for scene images** → **`image-generator`**. This spec starts the field because
  this node makes a job's first images; `generate_scene` does not write it today and CC-3's breaker
  cannot trip until it does.
- **Deterministic-path idempotency** (skip the paid call when the Storage asset already exists) →
  **`image-generator`**, per ADR-025 Decision 3, which names it an optional sanctioned upgrade. It
  would also shrink this node's widened mid-node re-pay window (§4). Not absorbed here.
- **Character dedup** → still **unowned**, documented ceiling. This spec sharpens the consequence
  (§4) without taking ownership.
- **The three-preset `style_presets` dict, `style_preset_id` resolution, and ADR-022's binding
  aesthetic acceptance condition** → **`style-presets`**. This node consumes one fragment and authors
  one default.

**Open:**

- ⚠️ **Base64 payload size to the judge** (§4). Unverified until the first real call. If OpenRouter
  rejects a ~1.9 MB body, the fallback needs a signed-URL helper in `app/db.py` — small, but it is a
  new effect and a CC-4 surface, so it should be a deliberate change rather than a hotfix.
- **CC-7 seed reproducibility** — unsatisfiable as designed (§5), not merely unimplemented. Any future
  attempt to seed this node must explain how the re-roll stays a re-roll.
- ⚠️ **`RefVerdict` is unvalidated** (§7). Validate before trusting the persisted rate.

## 9. Definition of done

Per AGENTS.md *Definition of Done*. This module is done when **all** of the following hold:

1. `backend/pipeline/char_bible.py` implements §4 — `reference_prompt` and `best_draw` (pure), the
   `mint_reference` effect helper, and a node that selects, maps, bumps `cost`, and partial-returns.
   The `# ponytail: stub` comment and its spec pointer are removed.
2. `settings.default_style_fragment` exists in `backend/app/config.py`, holding ADR-022's `cel`
   fragment, and is added to `backend/.env.example` as an override.
3. Every §6 assertion exists and passes in `backend/tests/test_char_bible_node.py`.
4. Backend verify is green and **its output is shown, not claimed**:
   `uv run ruff check . && uv run pytest` from `backend/`.
5. **Status line above flips to `built`** with the commit range, per the spec lifecycle
   (MASTER_SPEC §7).
6. **The finding-change grep is run** and every hit fixed in the same change. Known surface:
   - `docs/product/DECISION_BACKLOG.md` — tick the `character-bible` line and replace the
     *"Recommended next session"* block. *(The `D-I` row and the spec-written note landed 2026-07-30.)*
   - `docs/WORKFLOW.md` §"Right now" — currently names this spec as the next action.
   - `AGENTS.md` *Validation Notes* — drop `character-bible` from the remaining-Phase-1 list; and
     *Project Context*, which lists `char_bible` among the pass-through stubs.
   - *(`docs/specs/story-analyzer.md` §5 and `docs/MASTER_SPEC.md` §2 were corrected 2026-07-30 when
     this spec was written — see §8. Confirm they still read true; no further edit expected.)*
7. **No new file is added to the status surface** (AGENTS.md's nine-file table). This spec points at
   `PHASE_05_RESULTS.md` and asserts no probe numbers of its own.

**Not done** if: any §6 test is skipped; `backend/contracts/` is modified; the returned `characters`
list is partial; `cost` is rebuilt rather than copied-and-bumped; the reference cap is enforced only
by prompt text; the reveal gap (§8) is silently implemented instead of logged as `D-I`; or a §8
handoff is absorbed into this node instead of being left to its owner.

# Feature Spec — scene setting & subject binding

**Status:** built · a2714f8–1f39ba0 · **Phase:** 2 · **Owner nodes:** `backend/pipeline/analyze.py`,
`segment.py`, `prompt_optimizer.py`, `generate_scene.py`, `consistency_check.py`
**Derived from:** MASTER_SPEC §2 · **Rationale:** ADR-035 (surface 5), ADR-023 §8 (additive),
ADR-010, ADR-004, issues #23, #32

> **Deviation from "one spec = one module", declared not smuggled.** This spec changes five nodes
> because it addresses one *artifact class* — what the image model draws when it is given more
> than one subject — and that artifact is produced by the prompt, gated by the judge, and fed by
> two upstream nodes. Splitting it into five specs would put the rationale in five places and
> leave no single document that says why the prompt has the shape it has. Precedent:
> `moderation-stack.md`, `input-gate-hardening.md`.

---

## 1. Purpose

Three defects observed in production books, one root cause each:

| # | Defect | Root cause | Fix class |
|---|---|---|---|
| **D1** | Backgrounds change page to page in the same place | `locations[]` is minted by `analyze` and read by **nothing** | wiring |
| **D2** | Attributes bleed between characters (a star's legs wearing another character's trousers) | `build_prompt` emits the image roll and the attribute lines as two unbound blocks; no non-human anatomy guard on the scene path | prompt shape |
| **D3** | A character is drawn twice, often once smaller | (a) duplicate `char_id` sends the same reference twice; (b) residual model compositing, currently **undetected** | determinism + measurement |

D3 is deliberately **not** fully solved here. See §4.4 and §8.

---

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

Two additive fields. Both `Optional`/defaulted → **no `schema_version` bump**
(`story-memory-contract.md:217`; precedent `VlmVerdict.anatomy_intact`,
`Character.ref_verdict_prompt_version`).

```python
class Scene(BaseModel):
    ...
    location_id: Optional[str] = None    # set by segment, consumed by build_prompt

class VlmVerdict(BaseModel):
    ...
    anatomy_intact: bool = True
    subjects_unique: bool = True         # NEW — declared LAST, ADR-004 order untouched
```

- **`analyze`** — reads `input.redacted_text`; writes `locations[]` (unchanged shape, better
  descriptions).
- **`segment`** — reads `locations[]`; writes `scenes[].location_id`, and deduplicates
  `scenes[].characters_present`.
- **`prompt_optimizer`** — pure; reads a `Location`, writes nothing.
- **`generate_scene`** — reads `scenes[].location_id` + `locations[]`; writes
  `scenes[].prompt` (unchanged field, new content).
- **`consistency_check`** — writes `scenes[].attempts[].vlm_verdict.subjects_unique`.

**Invariants**

1. `build_prompt` invariant 1 (style fragment always present) — unchanged.
2. `build_prompt` invariant 2 **widens**: never invents detail beyond `text_excerpt`, the present
   characters' populated description axes, **and the scene's location**. This restatement is
   mandatory in `prompt-optimizer.md`; leaving it unwidened makes the spec lie.
3. `characters_present` contains no duplicate `char_id`. New, and enforced in `segment`.
4. `referenced_characters` remains the single source of roll order across `generate_scene`,
   `regenerate` and `output_mod`. The **relative order of the characters it returns is unchanged**;
   the roll's *text* changes (§4.2), and a repeated `char_id` is removed (§4.3). Removing a
   duplicate cannot reorder the survivors — `dict.fromkeys` preserves first-seen order — so
   "Image N is X" still names `ref_paths[N-1]` on all three consumers.
5. `passed` is unchanged: `same_character and anatomy_intact`. `subjects_unique` does **not** gate.

---

## 3. Position in the system map

No new nodes, **no new edges**. ADR-003 is untouched: every change is inside an existing node
body or in a pure helper. The `consistency_check` pass/fail branch keeps its current condition.

---

## 4. Behavior & edge cases

### 4.1 D1 — setting consistency

**`analyze.EXTRACTION_PROMPT`** gains one sentence:

> Describe each location by what is permanently there — not the weather, the lighting, the time of
> day, any damage, or what happens there.

`ExtractedLocation.description` was **`str | None`** here: making it required looked like it would
force invention, contradicting the same prompt's rule for character axes ("leave them empty rather
than inventing details"). **Superseded by `setting-consistency.md` §4.1**, which makes the transient
field a required non-blank `str` and resolves the tension by instructing the prompt to fill missing
detail once with neutral, child-safe permanent features. The persisted `Location.description` stays
`Optional[str]` for checkpoint compatibility.

**`segment`** gains `location_name: str | None = None` on `ExtractedScene`, a location roster in
`SEGMENTATION_PROMPT`, and name → `loc_id` mapping using the same pattern as the character path
(unknown name → warn + `None`).

**Carry-forward runs last**, over the final scene list in order:

- `location_name` null → inherit the previous scene's `location_id`
- `s0` null → `locations[0].loc_id` if any, else `None`

**Edge cases**

| Case | Behavior |
|---|---|
| Story names no locations | every `location_id` is `None`; no `Setting:` line; identical to today |
| Model returns a location not in the roster | warn, `None`, carry-forward fills it |
| Every scene null | all inherit `locations[0]` — one setting for the book, the honest degradation |
| Location description contradicts the excerpt ("that night" vs a sunny description) | excerpt is emitted **after** the setting line, so it is the later and more specific assertion; §4.5 records this as reduced, not eliminated |
| `repair()` / `merge_thin()` restructure scenes | `location_name` must propagate through **all eight** `ExtractedScene(...)` constructions; on a merge take `a.location_name or b.location_name` |

The last row is where a bug will hide. There are **eight** construction sites — seven in `repair()`
(`segment.py:76` clamp, `:89` de-overlap, `:97` floor, `:103`/`:109`/`:113` leading/interior/trailing
gap-fill, `:133` the `MAX_SCENES` merge) and one in `merge_thin()` (`:170`). A missed one silently
drops the field on exactly the messy stories that need repair most, and no existing test would catch
it. The `:97` floor case constructs with `characters_present=[]` and correctly gets
`location_name=None`; carry-forward then supplies `locations[0]`.

### 4.2 D2 — attribute binding

**`build_prompt`** gains a `location: Location | None` parameter and emits:

```
Image 1 is Ana - girl; red shirt; jeans.
Image 2 is the star - yellow; tiny.
<REFERENCE_CLAUSE>

<plain _describe lines for present characters with NO canonical reference>

<SUBJECT_COUNT_CLAUSE>
<NON_HUMAN_CLAUSE>

Setting: the beach - golden sand, palm trees, blue water

<text_excerpt>

<style fragment>
```

- **The roll fold is the whole D2 fix.** Today the roll (`"Image 1 is Ana."`) and the attribute
  line (`"Ana - girl; red shirt; jeans"`) are separate blocks the model must associate. Folded,
  each reference image and its attributes are one sentence. This is a **net token reduction**, not
  an addition — it is the only change here that reduces prompt dilution rather than adding to it.
- `_describe` is unchanged; the roll is `f"Image {n} is {_describe(...)}."`. A character with no
  populated axes yields `"Image 1 is Ana."` — byte-identical to today.
- **`NON_HUMAN_CLAUSE`** — wording adapted from `char_bible.REFERENCE_PROMPT`, with the tail
  replaced by "unless described above" and the article widened `the` → `a`: `char_bible` prompts
  one character at a time, so "*the* character" has a referent there and none here, where the
  scene prompt names several. Emitted **unconditionally**, for the same reason `char_bible` made it
  unconditional: branching on species needs a word list that is wrong the first time a child
  writes something not on it, and the clause is a no-op for a person.
- **`SUBJECT_COUNT_CLAUSE`** — `"This illustration contains exactly N characters: Ana and the
  star."` A whole-canvas count is structurally different from the per-character "draw each
  character exactly once" already in `REFERENCE_CLAUSE`.

**Both new clauses sit OUTSIDE `REFERENCE_CLAUSE`**, because the roll and its clause are omitted
entirely on the text-to-image path (`prompt_optimizer.py:212-217`) and both guards must apply there
too. Placing them inside would make them silently inert on every ref-less scene.

**Edge cases**

| Case | Behavior |
|---|---|
| `characters_present` empty (after the missing-`char_id` filter) | no roll, no count clause, no non-human clause — all three would reference nothing |
| `N == 1` | `"exactly 1 character"` — pluralization handled, no `1 characters` |
| `char_id` present but absent from `characters` | already warned + skipped today; **the count must be computed after that filter**, or it asserts a number the prompt does not name |
| A character present but with no canonical reference | keeps a plain `_describe` line below the roll; still counted in `N` |
| No references at all | no roll; count and non-human clauses still emitted |

### 4.3 D3(a) — duplicate `char_id`, the deterministic half

`segment.py:196-201` builds `char_ids` with `.extend(name_to_ids[name])` and never deduplicates,
and `name_to_ids` maps one name to a **list**. Two independent paths to a repeated `char_id`:

1. the segmentation model returns the same name twice in `characters_present`;
2. `analyze` mints two characters with the same name — it takes `analysis.characters[:3]` and never
   checks for a collision.

`referenced_characters` then iterates that list without deduplicating, so `ref_paths` carries the
same Storage path twice, `_fal_ref_url`'s cache returns the same fal URL twice, and the roll asserts
*"Image 1 is the star. Image 2 is the star."* Handed one image as two subjects, a second instance
at a different scale is the expected output.

**Fix:** deduplicate in `segment` (`dict.fromkeys`, order-preserving), and defensively in
`referenced_characters` so a checkpoint written before this change cannot reproduce it on resume.
Fully deterministic, testable with no model.

`build_prompt` deduplicates on the same key when it builds `present`. This is a **third** site, not
a redundant one: `present` is derived from `characters_present` directly rather than from
`referenced_characters`, and it is what `SUBJECT_COUNT_CLAUSE` counts. Without it, a pre-change
checkpoint would assert *"exactly 2 characters: the star and the star."*

> This is a **hypothesis with a mechanism**, not a confirmed diagnosis of any specific book. It is
> worth fixing regardless — sending one image as two subjects is wrong on its own terms — but the
> Definition of Done requires checking a real trace before claiming it was the cause.

### 4.4 D3(b) — residual duplication, measured not gated

`consistency_check.JUDGE_PROMPT` gains a uniqueness question, asked after anatomy and before the
failure reasons, so the wire order still matches the schema
(`providers._assert_field_order` rejects a provider that answers out of order).

**The wording must scope to the character, not to the noun.** `REFERENCE_CLAUSE` already draws this
distinction — *"the stars" in "she looked up at the stars" names no character and stays drawable*.
A question phrased "is there more than one star" fails a legitimate night sky.

- fold: `subjects_unique=all(v.subjects_unique for v in verdicts)` — worst-wins, like the others
- `_rank` gains one position: `(1, same_character, anatomy_intact, subjects_unique, style_match)`,
  and the unchecked tuple widens to `(0, 0, 0, 0, 0)`
- `passed` is **unchanged**
- the existing per-scene log line gains `subjects_unique`

**Why not gate.** Gating means more regenerations, and issue #26 is open and already critical: prod
job `f4d0fd74` burned **500s of a 900s** timeout on a **7**-scene book with 2 regenerations, and
each regeneration costs ~40s. At `MAX_SCENES=15` the straight-line extrapolation already exceeds the
timeout before any of these extra retries. Cost is not the constraint — `IMAGE_BUDGET = 39` is
already provisioned for two attempts on every scene — **latency is**.

Ranking still buys a free improvement: when a retry fires for some *other* reason, best-of now
prefers the non-duplicated attempt at no extra draw. Precedent for record-and-rank-without-gating is
`style_match`, in this same file (`consistency_check.py:159`).

Gating is a **follow-up decision**, made once the measured rate exists and #26 is closed. See §8.

### 4.5 Risks carried, stated not solved

1. **Unmeasurable.** Seven prompt changes ship together — `analyze`'s extraction prompt,
   `segment`'s segmentation prompt, the roll fold, the count clause, the non-human clause, the
   setting line, and the judge's uniqueness question — with no eval harness (there is no
   `eval/`; `backend/spikes/phase_05.py` is the probe script). If output regresses we cannot
   attribute it. The only real mitigation is that the roll fold is reversible inside one function.
2. **Location descriptions are unjudged.** There is no `ref_verdict` equivalent, and a wrong
   description repeats onto **every** page in that location — a worse blast radius than a wrong
   character description, which costs one page. This is the one new failure mode this spec creates.
   Accepted deliberately: a location judge is a new paid VLM call per book, which is an ADR.
3. **Setting-vs-excerpt conflict is reduced, not eliminated.** "The beach turned to ice" still
   fights its own location description.
4. **Attribute bleeding is reduced, not fixed.** Qwen-Image-Edit composites; nothing here changes
   the model.
5. **D3 is measured, not fixed.** After this ships, duplicated pages still reach the child. The
   deliverable is a number and a free ranking preference, not a guarantee.
6. **A location name is not redacted.** `providers.py:310-327` deliberately excludes `LOCATION`
   from the allowlist (spaCy calling "The Lost Little Star" an ORGANIZATION put
   `<ORGANIZATION> upon a time` into a caption, prod job `e94cc400`). A real place a child names
   already survives redaction and already reaches the generator via `text_excerpt`. This spec
   **repeats** that exposure across more pages; it does not create it. Not a new CC-2 surface, but
   it is a wider one.
7. **`consistency_check.JUDGE_PROMPT` is unversioned**, unlike `char_bible`'s. Adding a question can
   shift the answers to the questions already there. Mitigated cheaply, not fully — see §8.

### 4.6 Blast radius

| File | Change |
|---|---|
| `backend/contracts/story_memory.py` | +2 additive fields; ADR-010 rank comment widened |
| `docs/specs/story-memory-contract.md` | mirrors both, same rank comment |
| `backend/pipeline/analyze.py` | +1 prompt sentence |
| `backend/pipeline/segment.py` | +1 boundary field, roster, mapping, carry-forward, dedup, **8 constructor sites** |
| `backend/pipeline/prompt_optimizer.py` | roll fold, 2 new clauses, `filtered_location`, `build_prompt` signature |
| `backend/pipeline/generate_scene.py` | resolve + pass the location (~2 lines) |
| `backend/pipeline/consistency_check.py` | judge question, fold, `_rank`, log, prompt-version constant |
| `docs/specs/story-analyzer.md`, `scene-segmentation.md`, `prompt-optimizer.md`, `image-generator.md`, `consistency-checker.md` | behavior changed → updated in the same change |

**Not touched, deliberately:** `regenerate.py` and `output_mod.py`. Both wrap the stored prompt
string (`correct_prompt` appends, `_soften_prompt` prepends) and neither calls `build_prompt` —
verified, `build_prompt` has exactly one caller (`generate_scene.py:77`). `FailureReason` is frozen
at 7 (ADR-028) and gains nothing. `IMAGE_BUDGET` is unchanged and cannot trip: this spec adds zero
image calls and zero judge calls.

---

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-2 PII redaction** — no new surface; a wider repetition of an existing accepted one (§4.5.6).
- [x] **CC-3 Cost control** — zero new image calls, zero new judge calls. `subjects_unique` rides
      the existing per-character judge call. `IMAGE_BUDGET` untouched.
- [x] **CC-5 Observability** — `location_id` and `subjects_unique` both reach the existing per-scene
      log lines; the scene judge prompt gains a version constant.
- [x] **CC-10 Checkpointing / resumability** — both fields are additive with defaults, so a
      checkpoint written before this change deserializes. A scene judged before the change carries
      `subjects_unique=True` by default and therefore reads as non-duplicated; this is the same
      shape `anatomy_intact` had at its own introduction and is accepted.
- [ ] CC-1, CC-4, CC-6, CC-7, CC-8, CC-9 — untouched.

---

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Models mocked. No assertion on generated content.

**`segment`**
1. `location_name` maps to `loc_id`; a name not in the roster is dropped with a warning.
2. Carry-forward fills a null from the previous scene.
3. `s0` null takes `locations[0]`; with no locations, every `location_id` is `None`.
4. `location_name` survives clamp, de-overlap, floor, all **three** gap-fills, the `MAX_SCENES`
   merge, and `merge_thin` — **one assertion per constructor site, eight in total**.
5. On a merge, `a.location_name or b.location_name` wins.
6. **A repeated name in `characters_present` yields one `char_id`.**
7. **Two roster characters sharing a name do not both land in one scene's `characters_present`.**

**`prompt_optimizer`**
8. The roll folds the description: `"Image 1 is Ana - girl; red shirt; jeans."`
9. A character with no populated axes still yields `"Image 1 is Ana."`
10. Present characters without a reference keep plain lines below the roll.
11. Roll order still matches `referenced_characters` order.
12. `SUBJECT_COUNT_CLAUSE` and `NON_HUMAN_CLAUSE` appear on **both** the reference and the
    text-to-image paths.
13. `N` counts present characters after the missing-`char_id` filter, and reads `1 character`.
14. `characters_present` empty → none of the three clauses appear.
15. `filtered_location` drops a forbidden word from the description (`"glowing cave"` under
    `no glow`) and leaves the **name** untouched.
16. `location=None` emits no `Setting:` line.
17. `referenced_characters` deduplicates a repeated `char_id`.

**`consistency_check`**
18. `subjects_unique=False` on any per-character verdict folds to `False`.
19. `subjects_unique=False` alone does **not** flip `passed`.
20. `_rank` prefers a unique attempt over a duplicated one when the higher keys tie.
21. Unchecked ranks below every checked attempt with the widened tuple.

**Contract**
22. A checkpoint blob lacking `location_id` and `subjects_unique` deserializes, with the documented
    defaults.

---

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

There is no eval harness. Every claim in §1 is currently unfalsifiable outside a manual read of a
production job, which is the limitation this project already carries from Probe 1 (single-rater,
non-blind — see `PHASE_05_RESULTS.md`).

What this spec adds toward closing that: `subjects_unique` is the **first machine-readable
duplicate-rate signal in the pipeline**. Once N books have run, `scenes[].attempts[].vlm_verdict`
yields a rate, which is what a gating decision (§8) needs and what nobody has today.

D1 and D2 remain eyeball-only. That is stated, not hidden.

---

## 8. Linked decisions & open questions

**Depends on:** ADR-003 (no new edges — satisfied), ADR-004 (reason-then-score field order —
`subjects_unique` declared last), ADR-010 (best-of), ADR-023 §8 (additive fields), ADR-028
(`FailureReason` frozen at 7 — untouched), ADR-035 (style filtering — this spec adds **surface 5**,
location descriptions).

**Not an ADR.** Both contract fields are additive with defaults, which §8 of the contract spec
explicitly permits without an ADR or a `schema_version` bump.

**Open questions — flagged, not guessed:**

1. **Should `subjects_unique` eventually gate?** Deferred by decision, not oversight. Blocked on
   (a) a measured duplicate rate from this spec's telemetry and (b) issue #26. Revisit when both
   exist.
2. **`consistency_check.JUDGE_PROMPT` has no version field**, unlike `char_bible`'s
   `JUDGE_PROMPT_VERSION`, and that omission has already cost this project one discarded
   measurement series. This spec adds a **module constant plus the existing log line** —
   deliberately not a persisted `Attempt` field, which would be a third contract change for a
   problem that logs already make traceable. Marked `ponytail:` with the upgrade path. **The
   underlying gap deserves its own issue.**
3. **`analyze` does not check for duplicate character names.** §4.3 fixes the *consequence* in
   `segment`. Whether `analyze` should also disambiguate at its own boundary is a separate
   question and is not settled here.
4. **A location judge** — rejected for now (§4.5.2), and the reason is cost, not merit. If wrong
   location descriptions turn out to be common, this is the first thing to reconsider.

---

## 9. Definition of Done

Per AGENTS.md — completion is not claimed without proof.

**Must pass, with output shown:**

```bash
cd backend && uv run ruff check . && uv run pytest
cd frontend && pnpm lint && pnpm test      # expected untouched; run to prove it
```

Run 2026-08-13: `ruff check` → **All checks passed**; `pytest` → **643 passed, 55 skipped,
6 deselected**. `pnpm lint` → clean; `pnpm test` → **34 files, 238 passed** (frontend untouched,
as expected).

**Must be true:**

- [x] All 22 assertions in §6 exist and pass. Test 4 has one assertion **per constructor site** —
      a single combined test does not satisfy it. *Eight separate per-site tests exist at
      `backend/tests/test_segment_node.py:213-277`.*
- [x] Every test was seen **failing first** (AGENTS.md §4, TDD scope: this has branches and loops).
      *Claimed by the implementing commits, and not independently re-verifiable after the fact —
      the red state leaves no artifact.*
- [x] The five specs in §4.6 are updated **in the same change**. `prompt-optimizer.md`'s
      invariant 2 explicitly names the location.
- [x] `grep -rn` sweep for anything asserting the old prompt shape or `build_prompt`'s arity.
      *`build_prompt` still has exactly one production caller (`generate_scene.py:82`); the
      `location` parameter defaults to `None`, so the pre-existing 4-argument test call sites in
      `test_output_mod_node.py` and `test_regenerate_node.py` stay valid.*
- [x] No new graph edge; `git diff main...HEAD -- backend/pipeline/graph.py` is **empty**.
- [x] `passed`'s definition in `consistency_check.py` is byte-identical to before
      (`main:161` == `HEAD:181`).
- [x] `referenced_characters` returns its survivors in the same **relative order** as before, and
      `build_prompt`'s roll index still matches `generate_scene`'s `ref_paths` index (invariant 4).
- [ ] One real job run end to end, with the Langfuse trace read, confirming: a `Setting:` line
      present on every page of a multi-location story, and the roll folded. **NOT DONE.** The spec
      is marked built on the deterministic evidence above; this item is carried as outstanding, not
      satisfied. See the reporting block below.

**Must be reported, not silently omitted:**

- The §4.3 duplicate-`char_id` hypothesis remains **a mechanism that was fixed on principle**. It
  was **not** confirmed against a real trace, and must not be reported as the cause of any observed
  book.
- **No `subjects_unique` data point exists yet.** The first duplicate-rate measurement arrives with
  the first real run; the §8.1 gating decision stays blocked until then.
- D1 and D2 improvements are **neither measured nor eyeballed** — no job has been run against this
  code. §7's limitation stands undiminished.

**Explicitly NOT in scope, and not to be added mid-implementation:**

- gating on `subjects_unique` (§8.1)
- an eval harness
- any `FailureReason` change (frozen, ADR-028)
- chaining a previous scene's image as an extra reference — rejected: it breaks the
  `referenced_characters` ordering contract shared by three modules and compounds drift page over
  page
- reducing the number of references sent per scene — rejected: incoherent without also changing
  `characters_present`, which would make `character_absent` fire for characters deliberately withheld

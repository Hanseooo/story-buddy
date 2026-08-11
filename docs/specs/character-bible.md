# Feature Spec — character-bible

**Status:** built (2026-07-30, `901f50b..1cca83a`) · **Phase:** 1 · **Owner node:** `backend/pipeline/char_bible.py`
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
- **Writes:** `characters[]` (the **full** list, with `canonical_ref_image` and `ref_verdict` set on minted characters), `cost.image_count`
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

Linear. **No conditional edge.** ADR-003's branch points are moderation pass/fail, consistency
pass/fail, and the reveal confirm/try-again (ADR-029, Phase 2); this node *branches* at none of them.
It does become the **target** of the reveal's `"try_again"` edge in Phase 2 (§8) — a destination, not a
router, so this section is unchanged in substance.

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

   **The targeted retry path is exempt from this cap-then-filter step entirely.** When
   `state.reference_retry` is set, `char_bible` takes a second, earlier branch (`kid-flow-pause-lifecycle.md`
   §4.5) that overwrites the named character's `canonical_ref_image` unconditionally, whether or not
   it already has one. Invariant 6's skip is for the first-pass path only.
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
    if not verdict.contradictions:      # ADR-034 — derived, never the judge's own boolean
        return _upload(image), verdict, draws
    candidates.append((image, verdict))

image, verdict = candidates[best_draw([v for _, v in candidates])]
return _upload(image), verdict, draws   # a FAILING verdict, persisted — loud, never a placeholder
```

**Cap of 3, not ADR-010's 1**, because the blast radius differs: a bad scene is one page, a bad
reference is every page (ADR-028).

**Acceptance is `not verdict.contradictions`** (ADR-034, amending ADR-028 Decision 3 — the predicate
only; the in-node loop, the cap and the best-of fallback are unchanged). The judge is asked to
enumerate one entry per contradicted attribute, and the code counts the list. `matches_description` is
still requested and still persisted, but **nothing branches on it**: prod job `b9506307` set it TRUE on
a verdict whose own `differences_observed` read *"This is a contradiction"*, shipping a flat teal star
against a description reading `star; glowing; tiny`. `reveal` reads the same predicate — see
`kid-flow-pause-lifecycle` §4.3; the two must stay in lockstep or a reference the gate rejected would
still offer the child the full chip list.

**Best-of ranks on fewest `contradictions`**, then `len(attributes_present)`, ties → earliest draw.
`attributes_present` was the sole key until ADR-034 and it is measurably noisy — the same verdict
listed `"glowing"` for a flat image and `"secondary character"`, which is a `notes` value and not a
visual attribute at all. It is demoted rather than dropped: between two draws that contradict the
description equally often, it is the better of the two remaining signals. This is `char_bible`'s own
rule over `RefVerdict` and is **unrelated** to `regeneration-controller`'s lexicographic scene rule
over `VlmVerdict` — different schema, different question. Do not unify them.

### Two `providers.py` calls, two failure policies — deliberate

This is the first node in the codebase where two provider calls get **different** ADR-025 treatment.
Stated loudly so nobody "fixes" the inconsistency later:

| Call | Failure | Why |
|---|---|---|
| `text_to_image` | **Raises** → job `failed`, `provider_error` | No artifact. There is nothing to ship, so ADR-025 Decision 1 applies as written. |
| `judge` | **Degrades** → accept the draw, `ref_verdict = None` | The artifact exists and is paid for. The *check* failed. An unchecked reference is precisely what ADR-007 shipped before ADR-028 amended it — it is not a placeholder and not a broken page, so ADR-010's "always something shippable" governs and ADR-025's "never a partial book" rationale does not bite. |

`ref_verdict = None` stays honest and is distinguishable from a *failed* verdict
(a non-empty `contradictions`). The cost is real and recorded: for that book, ADR-028's stated
Phase-1 measurement — the reference generator's true hit rate — silently reverts to unmeasured.

### No seed, by necessity

`providers.text_to_image` accepts a seed, but a **fixed seed makes all three draws identical** and the
re-roll a no-op. Draws are therefore independent and unseeded. CC-7 is unsatisfied here as a direct
consequence of the mechanism, not an oversight — see §5.

### Prompts (D-F: transient, so they live beside their node)

Two module-level constants. Neither introduces a contract type; `RefVerdict` already lives in
`backend/contracts/` because `StoryMemory` embeds it (D-F, ADR-023 amendment).

`reference_prompt` renders the `CharacterDescription` axes (`species`, `colours`, `body_features`,
`clothing`, `notes`) plus the style fragment, and asks for a single character reference **shown in
full** on a plain neutral background. Per ADR-022 the fragment **names a medium and its physical
artifacts** — it never says "beautiful", "8k", or "highly detailed".

The judge prompt shows the drawn image and the description it should depict, and asks for
`differences_observed`, then `contradictions`, then `matches_description`. ADR-004's reason-then-score
ordering applies to **every** judge call; `RefVerdict` declares the fields in that order and
`providers._assert_field_order` enforces it on the wire. ADR-034 put the gate in the **middle**
deliberately: the judge must enumerate the defects before it is allowed to score.

#### The question is contradiction, not difference (amended 2026-08-11)

The prompt originally asked the judge to *"describe every difference you observe between the image and
the description"*. **Prod job `4cb31620` falsified the "species-only" edge case above**: `c0` rendered
to `the narrator - girl; the protagonist` and every one of the 3 draws came back
`matches_description = False`. The judge's own `differences_observed` is the evidence — *"the
description is incredibly brief… the image offers a lot of details **not present in the
description**"* — followed by a list of hair and clothing.

None of that contradicts *a girl who is the protagonist*. A text-to-image model cannot draw a girl
with no hair and no clothes, so **unlisted details are unavoidable**, which means under the old
wording a thin description could not pass at *any* draw count on *any* model. The predicted ceiling
was backwards: instead of collapsing to 1 draw, the loop paid for all 3 and persisted a failing
verdict.

The prompt now states that details the description omits are **not** differences, and asks for ways
the image *contradicts a stated attribute*. This restores ADR-028's actual target — off-spec on a
stated feature — and leaves reason-then-score intact.

⚠️ **Verdicts are not comparable across this change.** The ADR-028 hit rate measured before
2026-08-11 measured the judge's tolerance for sparse descriptions, not the generator. Treat the
persisted series as starting here, exactly as §7's ⚠️ warned it might have to.

#### `JUDGE_PROMPT_VERSION` — so the next change segments the series instead of resetting it

The reset above was avoidable, and only avoidable once. `matches_description` is simultaneously a
product gate (it drives re-rolls, which cost draws) and the capstone's measurement instrument, and
the prompt behind it is under active development. Nothing recorded *which* prompt produced a given
verdict, so a wording change that alters what FALSE means invalidates every prior verdict rather
than partitioning them.

`char_bible.JUDGE_PROMPT_VERSION` (now `3`; `2` asked for the verdict as a boolean, `1` is everything
before 2026-08-11) is stamped onto
`Character.ref_verdict_prompt_version` on every write of `ref_verdict`, in both the first-pass and
the ADR-029 targeted-redraw paths — the targeted path judges with the same prompt, so leaving it
unstamped would make the retries an unlabelled subset and defeat the point. **Bump it whenever the
wording changes what a FALSE verdict means.**

It is on `Character`, not on `RefVerdict`, because `RefVerdict` is passed to `providers.judge` as
`response_format`: a field there becomes a required model output under strict `json_schema`, and
the judge would be asked to state its own prompt version.

#### v3: the verdict is enumerated, not asserted (ADR-034, 2026-08-11)

v2 asked for prose and then for a boolean, and that is not the same as asking the model to *check*.
Prod job `b9506307` character `c1` — *"the star - star; glowing; tiny; secondary character"* — came
back with:

```json
"differences_observed": "The description states the star is 'tiny', but the image depicts the star
   as a significant size relative to the image frame. This is a contradiction.",
"matches_description": true,
"attributes_present": ["star", "glowing", "secondary character"]
```

ADR-004's ordering **worked** — the reason was emitted first, and `providers._assert_field_order`
confirmed it on the wire. Ordering makes the model reason before it scores; it does not make the
score follow the reasoning. The gate accepted a reference the judge had just declared contradictory,
and every scene prompt then re-asserted `glowing; tiny` against a flat teal star. The edit model
resolved that conflict a different way per scene — reference wins, description wins, or **both get
drawn** — which is the duplicate-star symptom reported in issue #23.

v3 asks for **one list entry per contradicted attribute** and the code derives acceptance from the
list's length. The boolean survives as an observation so the disagreement rate stays measurable
(ADR-034 Decision 2 — removing it would be breaking, and the rate is worth having).

⚠️ **The loop had never fired before this.** Job `b9506307` shows `cost.image_count = 11` against 7
scenes with `regen_count = 2` → 9 scene draws → **2 reference draws for 2 characters**, both accepted
first try. ADR-028's *"typical case ≈ $0"* held because nothing had ever failed the gate, not because
the references were good. Expect the typical case to move toward ADR-028's stated **+$0.14 worst
case** now that the gate can reject. The cap of 3 is unchanged.

⚠️ **Verdicts are not comparable across v2 → v3 either.** The v2 series measured a boolean the model
set inconsistently with its own reasoning; treat the persisted series as restarting at version `3`.

##### What v3 was measured to do, and what it was not (2026-08-11, n=2 on one reference)

`ref-c1-1.png` and `ref-c0-1.png` were re-judged under v3 — no redraw, the existing artifacts. What
the two calls establish:

- ✅ **The mechanism works on the wire.** `contradictions` is populated, and
  `providers._assert_field_order` passes with the field inserted mid-schema (relative order is what
  it checks, so an insertion cannot break it). No deterministic test can reach this — they all mock
  the provider.
- ✅ **The gate now overrides the boolean on the real artifact.** c1 returned two contradictions
  *alongside* `matches_description: true`, and the gate rejected. That is the production bug,
  reproduced and neutralised.
- ✅ **No false positive on the control.** c0 (Ana) returned `contradictions: []`. This matters more
  than it looks now that a false positive costs real re-rolls.
- ⚠️ **The judge is non-deterministic here.** Of two calls on c1, one returned an **empty** list and
  would have accepted. The gate is probabilistic, not a guarantee; 3 draws give it three chances,
  but this reference can still slip through. n=2 on one character — do not quote it as a rate.
- ❌ **v3 still does not catch the defects that actually break the book.** c1's `differences_observed`
  names *"the star with legs and a face"* — the anthropomorphising failure — in prose, and does not
  list it as a contradiction, because the prompt says unlisted details are not contradictions and
  the description never said "no legs". `attributes_present` still claims `"glowing"` for a flat teal
  image. **ADR-034 fixed the reason–score inconsistency; it did not make the judge see more.**

The two contradictions it *did* name were `tiny` (arguably unjudgeable in an isolated reference,
where framing sets apparent size) and `secondary character` (a `notes` value — the finding that
produced the `notes=False` divergence above).

#### Visually-thin descriptions get a neutral floor in the draw prompt only

The judge fix made a thin description *passable*; it did not make the reference *good*. `analyze`'s
`EXTRACTION_PROMPT` says "leave them empty rather than inventing details", so `colours`,
`body_features` and `clothing` routinely arrive all-empty — `c0` above was drawn from a role noun,
and every page of the book inherits that one reference.

When no **visual** axis is populated, `reference_prompt` appends
`char_bible.THIN_DESCRIPTION_FILLER` (*"a friendly children's picture-book character"*). Keyed on
the visual axes rather than on how many fields are set: `c0` had two populated axes (`species`,
`notes`) and still specified nothing drawable, because species and notes are identity, not
appearance.

⚠️ **The filler reaches the draw prompt and never the judge prompt.** This is one of **two**
sanctioned divergences from `_describe`'s shared output, and both run the same direction: the draw
prompt may know more than the judge, never less. If the judge saw the filler it would become a
*stated* attribute, and draws would start failing over our invention — reintroducing the bug fixed
above from the opposite end. ADR-028 measures the generator against the **story**, never against our
filler. Covered by `test_enrichment_reaches_the_draw_prompt_but_never_the_judge_prompt`.

⚠️ **`notes` reaches the draw prompt and never the judge prompt** — the second divergence,
`_describe(..., notes=False)`, added with ADR-034 and for its sake. `notes` is free prose, not a
visual attribute, and post-ADR-034 the gate re-rolls on whatever the judge lists as contradicted.
Re-judging `b9506307`'s `ref-c1-1.png` under v3 returned *"secondary character - The image does not
provide cues as to this character's role"* as a contradiction: **unclearable by any redraw**, so the
character would exhaust all 3 draws on every job forever. `reveal._chips` already excludes `notes`
for the same reason (*"free prose, not an attribute, and not a thing a child can tap"*). The
generator keeps it — "secondary character" is useful framing for a drawing. Covered by
`test_notes_reaches_the_draw_prompt_but_never_the_judge_prompt`.

This is safe for the ADR-029 targeted redraw, which overwrites `notes` with the tapped chip: chips
are drawn from the **visual** axes, so the tapped attribute still reaches the judge through its own
axis. The `notes` copy is emphasis for the generator, not the judge's only sight of it.

**A third divergence should prompt someone to ask whether sharing `_describe` still pays.** Two is
still cheaper than two prompts that can drift into describing different characters; a third is the
point where the flag list is the design.

Rejected alternative: letting `analyze` invent the missing detail. It produces richer references but
writes fiction into the contract the judge measures against, and invents facts about a child's own
story — the extraction prompt is built around not doing that.

#### Non-humanoid subjects: the prompt stopped asking for a human body (amended 2026-08-11)

`c1` of the same prod job `4cb31620` is the **true** negative alongside `c0`'s false one: *"the star"*
was drawn as a smiling mascot with arms and legs, and the judge correctly failed it. §7 attributes the
reference hit rate to the generator (`fal_image_model`, ADR-001's named seam) — **and half of this
particular failure was authored here.**

The prompt asked for *"a single **full-body** character reference of one character, **standing**,
facing forward"*. That is a human anatomy instruction, sent for every character including the ones
with no legs: a model told to draw a star *standing* must invent legs to comply. Two changes:

1. ~~"full-body … standing"~~ → **"shown in full"**. Same framing — the reference needs the whole
   character, not a portrait — without asserting an anatomy.
2. An explicit guard: *"If the character is not a person, draw it as the kind of thing it actually is
   — give it no human body and no human face unless the description above says so."*

**The guard is unconditional, not species-aware.** Branching on species means a word list deciding
that "star" and "jeepney" are non-humanoid while "girl" is not — wrong the first time a child writes
something not on it, and there is no structural signal to key on the way the thin-description filler
keys on the visual axes. The clause is a no-op for a person or an animal, which is what makes the
branchless version the correct lazy one.

⚠️ **Draw prompt only**, on the same one-directional rule as the filler above and for the same
reason: the judge must keep measuring the generator against the **story**, never against our
instructions to the generator. Covered by `test_the_non_humanoid_guard_never_reaches_the_judge_prompt`.

**Consequence for §7's owed validation:** a `fal_image_model` swap must now be measured *after* this
change. Evaluating a new model against the old prompt would have charged the generator for a defect
the prompt was requesting.

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
| **Species-only description** | **Draw anyway, never refuse.** A thin description is exactly when an anchor matters most — consistency across scenes comes from *having* a reference, not from the reference matching the child's mental image (ADR-010). ADR-028 targets *off-spec on a stated feature*; a thin description states none. This closes `story-analyzer` §8's richness handoff. ~~Ceiling: with one attribute `matches_description` is near-vacuously true, so the loop de facto collapses to 1 draw for that character.~~ **Falsified in production, amended 2026-08-11** — see below. Since that date the draw prompt also appends `THIN_DESCRIPTION_FILLER` when no visual axis is populated, so the generator gets a neutral floor rather than a role noun; the judge still sees only what the story stated. |
| **Fully empty description** | The contract permits it (`CharacterDescription` is all-Optional) even though `analyze`'s LLM boundary requires `species` — a resumed pre-`story-analyzer` checkpoint could carry one. The prompt floors to `Character.name`. |
| **`style.prompt_fragment` is `None`** | Falls back to `settings.default_style_fragment`. Nothing writes `style` today; the fallback is the normal path in Phase 1, not an error path. |
| **All 3 draws fail** | Best-of by fewest `contradictions`, then `len(attributes_present)`, ties → earliest (ADR-034). The **failing verdict is persisted** — never a failed job, never a placeholder, the same policy ADR-010 sets for scenes (ADR-028). |
| **All `attributes_present` empty** | `best_draw` returns `0`. Deterministic, never arbitrary. |
| **`contradictions` empty but `matches_description` FALSE** | **Accepted.** ADR-034: only the list gates. The judge naming no contradicted attribute *is* the pass, whatever it then asserts. |
| **`contradictions` non-empty but `matches_description` TRUE** | **Rejected, re-rolled.** The prod `b9506307` shape, and the reason ADR-034 exists. |
| **Judge hard failure** | Accept the current draw, `ref_verdict = None`, stop re-rolling. See the two-policies table above. |
| **`text_to_image` hard failure** | Raises → job `failed` with an ADR-025 `failure_reason`. No character gets a reference; never a partial roster. No node-level retry — the OpenAI SDK / fal helper bounded retry is the entire policy (ADR-025 Decision 1). |
| **Image-model self-refusal** | Surfaces as a provider error → same as above. Knowingly blunt: ADR-025 classes content-refusal as *not* a resilience concern and hands soften-and-retry to `self-refusal-fallback` (Phase 2). |
| **Resume mid-node** | All-or-nothing. LangGraph checkpoints *after* the node, so a crash inside it re-pays **up to 6 draws** on resume. ADR-025 accepted at-least-once re-pay sized as *"a rare crash, cents of cost"* — for this node that window is materially wider. Flagged, not absorbed; the fix ADR-025 sanctions (deterministic path + skip-if-exists) is owned by `image-generator` (§8). |
| **Re-entry after success** | Invariant 6: any character with a `canonical_ref_image` is skipped. Zero draws, zero cost. |
| **Prompt injection via the description** | The description derives from child text and enters an image prompt. `input_gate` moderates the text **first** — CC-1's ordering is the mitigation and it is a graph edge, not something this node re-implements. Strict `json_schema` constrains the *shape* of the judge's reply, not content. Defence-in-depth, same posture as `analyze`. |
| **Base64 payload size** | A 1024² PNG is ~1.4 MB raw, ~1.9 MB base64-encoded, and `providers._run_fal` hardcodes `output_format: "png"`. **Recorded as a build-time risk, not assumed fine.** Verify the judge accepts it on the first real call; if OpenRouter rejects the body, the fallback is a Storage upload plus a new signed-URL helper in `app/db.py` (§8). |

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-3 Cost control** — writes `cost.image_count` (invariant 4) and supplies the number ADR-025
  Decision 4 left unstated: the breaker bound `max_scenes × 2 + prelude` has ~~**`prelude = 6`**
  (2 references × 3 draws)~~ → **`prelude = 9`, corrected by ADR-029 (2026-07-31)**: 2 references × 3
  draws **+ 3 reveal taps × 1 draw**. The 6 was written *"on the assumption of exactly one
  machine-driven pass"*, and D-I removed that assumption. This node's own ceiling is still 6 — the
  extra 3 are spent by the Phase-2 `reveal` loop re-entering this node in targeted mode.
  ⚠️ **One inaccuracy in ADR-025 to record, not amend.** ADR-025 states the domain-level breaker and
  `recursion_limit` *"share one number"*. They no longer track together: ADR-028's loop is
  node-internal, so it consumes **zero** super-steps (`recursion_limit`'s `fixed_prelude` is
  unaffected) while adding up to 6 to `image_count`. The two preludes are different units. Neither
  bound is wrong; the claim that they are the same number is.
- [x] **CC-5 Observability** — the helper logs, per character: draws made, each verdict's
  `contradictions`, `matches_description` and `attributes_present`, and which draw won. A wrong
  character downstream traces back to a specific reference and a specific draw. The boolean is
  logged beside the list it no longer controls **on purpose**: the two disagreeing is the ADR-034
  failure, and this line is where it becomes visible in production.
- [x] **CC-9 Failure states** — a missing reference is **not** a failure and must never fail the job.
  Only a `text_to_image` hard failure does, through the ADR-025 `failure_reason` enum.
- [x] **CC-10 Checkpointing** — idempotent re-entry (invariant 6), one partial-return, no partial
  writes. The widened mid-node re-pay window is stated in §4 rather than hidden behind this tick.
- [ ] **CC-1 Moderation ordering** — **not satisfied, but now owned.** No image from this node reaches
  a child *today*. The surface where one would — PRD §8 flow step 7's reveal — is the `reveal` node
  decided in **ADR-029**, which ships in Phase 2 *behind* the char-ref moderation gate precisely so
  this ordering holds by construction. `ref_moderation_status` is left `None` for that Phase-2 owner.
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
- **Contradiction overrides the boolean (ADR-034):** a verdict with a non-empty `contradictions` and
  `matches_description=True` — the prod `b9506307` shape — does **not** end the loop; the next draw is
  taken and its bytes are uploaded
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

- `best_draw` — fewest `contradictions` wins even when it shows the fewest attributes; equal
  contradiction counts fall through to `len(attributes_present)`; ties return the lowest index;
  all-empty returns `0`
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
unknown. **Validate `contradictions` against the scorer's eye in Phase 1 before treating the
persisted rate as a number**, or the measurement above measures the judge instead of the generator.

ADR-034 narrowed this caveat without closing it. What v3 fixes is measured: the judge *noticing* a
defect no longer depends on it also scoring itself correctly. What is **not** measured is whether
`gemma-3-27b-it` populates a list more faithfully than it sets a boolean — a judge that under-reports
into `contradictions` fails open exactly like the boolean did, just less visibly.

✅ **This warning fired, 2026-08-11.** Prod job `4cb31620` returned FALSE on all 3 draws for `c0`
purely because the description was sparse — the measurement was measuring the judge, exactly as
warned. Two consequences for anyone reading the persisted series:

1. **Filter on `ref_verdict_prompt_version`.** Verdicts stamped `1` (or unstamped, i.e. everything
   before this date) answer a different question from those stamped `2`. Do not pool them.
2. **The validation above is still owed** and is now the gate on quoting *any* hit rate. What
   changed is only that a future prompt revision costs a partition instead of the whole series.

Note that `c1` in the same job was a **true** negative — the generator drew a humanoid mascot for a
character described as a star, which contradicts a stated attribute. One judge, one job, both a
false and a true negative: further evidence that the instrument needs the human check above, in
both directions.

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

- **PRD flow step 7 (reveal + confirm)** → **`D-I`, opened by this spec — closed 2026-07-31 as
  ADR-029.** The reveal is a dedicated, **effect-free** `reveal` node holding an `interrupt()`, sitting
  after the Phase-2 char-ref moderation gate, with a pure `route_reveal` looping `"try_again"` back
  into **this node**. Two consequences land here, both Phase-2 build work, neither changing the code
  this spec ships today:
  - **This node gains a targeted mode.** When `reference_retry` is set it makes exactly **one**
    `text_to_image` call for that `char_id` with the tapped attribute restated, **one** `judge` call,
    overwrites `canonical_ref_image` / `ref_verdict` **unconditionally** (no best-of — the child is
    the judge), bumps `image_count` by 1, and clears `reference_retry`. Invariant 6 needs no
    exception: the targeted mode overwrites rather than skips.
  - **CC-3's `prelude` is 9, not 6** (§5, struck through in place).
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

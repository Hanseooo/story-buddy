# ADR-028 — Image acceptance: identity taxonomy frozen, composition on the verdict, reference gated in-node

**Status:** Accepted (2026-07-29) · resolves **D-H** (DECISION_BACKLOG) · **amends ADR-007** (the canonical
reference is no longer assumed correct by construction) · resolves the **best-of ranking signal** ADR-024 handed
to `regeneration-controller` · **ADR-003 and ADR-024 are unamended** — see Decision 3

**Context:** Phase 0.5 measured four defects that no gate in the pipeline can name, and they are not the same
kind of defect:

| Defect | Where | On which model |
|---|---|---|
| Detached "astral projection" puddle reflection, scored `identity = 1` | Run 2, scene 9 | **`qwen-image-edit-2511` — the shipping editor** |
| Body merged into scenery: ~20–25% floor, 60% *behind*, 80% *inside* | Run 3 | `omnigen-v2` — the **declined** rung 1 |
| Duplicated tail, correctly scored 0 on both diagnostics | Run 3, item 43 | `omnigen-v2` |
| Canonical reference off-spec on the character's defining feature, **3 draws in 4** | Run 2 setup | **`fal-ai/qwen-image` — the shipping reference generator** |

**The evidence is asymmetric, and D-H's scope note had the asymmetry inverted.** The fusion numbers come from a
model that was measured and then declined (ADR-001, 2026-07-29), and Qwen's own fusion rate is unmeasured —
`fused` did not exist when Run 2 was scored and Run 2's images were deleted during Run 3 setup. The *reference*
failure, by contrast, was produced by `fal-ai/qwen-image`, which the escalation never touched and which ships.
So the composition question rests on contaminated evidence and the reference question does not.

**One correction to the record, because it was load-bearing in the backlog.** D-H stated *"ADR-001's own
suggestion is to widen `fused` to anatomy wrong: merged, missing, **or** duplicated."* ADR-001 says no such
thing. The sentence is `PHASE_05_RESULTS.md:504` and it is about **the probe's scoring columns, conditional on a
Phase-3 instrument keeping them** — not about `FailureReason`. No ADR has ever proposed extending the enum. D-H
read as though a decision doc already leaned one way; it did not, and this ADR is not overturning one.

**One qualification recorded honestly.** The scorer's recollection is that Qwen's fusion rate is **0%**, on the
grounds that a `fused` column would have been added mid-run had fusion been visible. That reasoning is supported
by the record rather than merely asserted: in Run 2, with no column for it and no reason to look, the scorer
*did* notice and write down an out-of-taxonomy composition defect (the puddle reflection). The notice-and-record
behaviour was demonstrably active. It remains a recollection, not a measurement, and ADR-001 qualification 2's
instruction stands — verify it in Phase 1 at zero marginal cost. **This ADR is built so the answer does not
change any of its three decisions**, which is the property that let it be written before the number exists.

**Decision:**

### 1. `FailureReason` is frozen at seven values, permanently. It is the *identity* taxonomy.

`story-memory-contract` §4 said *"extend only in Phase 1, never during Phase-2.5 annotation."* This is Phase 1,
and the answer is **no** — recorded as a decision with a reason so it is not reopened by reflex.

The seven values answer one question: *is this the right character, and if not, which described attribute is
wrong?* Every value names an attribute of the **character** that a regeneration prompt can restate
(`judge-finetune.md` §4 pairs each with its correction). Anatomy and composition are not attributes of the
character; they are properties of the **rendering**. A body merged into a mushroom is the right character drawn
wrongly, and `failure_reasons` is unreachable on that image anyway — reasons ground a `different_character`
verdict, and a fused-but-recognisable body scores `same_character = True`.

The cost of the alternative is not a schema bump. The seven values are enumerated **verbatim in the capstone
manuscript sources** — `methodology.md:158-159`, `research_instruments.md:62-63` and `:148-150`,
`evaluation_instruments_brief.md:143-145`, partially in `model_finetuning.md:25` and
`research_direction_and_goals.md:104` — as well as ADR-023 Decision 4, ADR-018, `judge-finetune.md` §4 and
`annotation-surface.md`. An enum change is a manuscript edit, and it would put a rendering-defect label inside
the closed set that Objective 4's F1 is computed over.

### 2. Composition rides `VlmVerdict` as one additive boolean.

```python
class VlmVerdict(BaseModel):
    differences_observed: str
    same_character: bool
    attributes_present: list[str] = Field(default_factory=list)
    style_match: bool = False
    anatomy_intact: bool = True   # merged, missing, or duplicated body parts
```

- **Declared last**, so ADR-004's `differences_observed`-before-`same_character` ordering is untouched and
  `providers._assert_field_order` (`providers.py:68-85`) keeps passing unchanged.
- **Additive with a default → no `schema_version` bump** (`story-memory-contract` §3), so no restart path and no
  capstone edit. This is the whole reason the composition question is cheap and the taxonomy question is not.
- **It also closes ADR-024's flagged gap.** ADR-024 Handoffs and `story-memory-contract` §8 both record that
  ADR-010's *"keep the higher-scoring image"* is undefined because `VlmVerdict` carries no scalar. It now
  carries a third boolean, so best-of is a **lexicographic order over `same_character` → `anatomy_intact` →
  `style_match`** with no scalar and no new concept. The ranking *rule* stays owned by
  `regeneration-controller`; this ADR only supplies something to rank on.
- **A boolean, not a score.** A scalar invites the judge to rate, and VLM judges are a weak rating instrument
  (ADR-004). Widen it only if a measured tie forces it.

Two limits, stated here so they are not discovered later:

1. **`anatomy_intact` does not cover scene fidelity.** Run 2's puddle rendered as a detached mirror image beside
   the character: the anatomy was intact and the scene was wrong. That defect remains uninstrumented and is
   deliberately not solved here — it needs a different question, not a wider one.
2. **The field is a slot, not a validated signal.** Whether `google/gemma-3-27b-it` reliably sees a merged body
   is unknown. Probe 3 is encouraging (long specific `differences_observed`; a correct unprompted
   `style_match=False` on a real cross-model pair) but it is not evidence. Validate against the scorer's eye in
   Phase 1.

### 3. The canonical reference is accepted inside `char_bible` — bounded re-roll, best-of fallback, no new edge.

ADR-007 states that style and identity ride on a reference which is correct *because it was generated from the
description*. Run 2 falsified that: `fal-ai/qwen-image` produced an off-spec reference on the character's single
defining feature in **3 of 4 draws**, and nothing caught it. In production that is a whole book of the wrong
character. **This ADR amends ADR-007: the reference is checked, not assumed.**

`char_bible` draws a reference, calls the judge against the `CharacterDescription`, and:

- accepts the first draw whose verdict passes;
- otherwise re-rolls, to a **cap of 3 draws total**;
- on exhaustion keeps the draw with the most `attributes_present` and persists the verdict — never a failed job,
  never a placeholder, the same policy ADR-010 already sets for scenes.

The return schema is a small dedicated model, not a reused `VlmVerdict` (see Alternatives). It lives in
`backend/contracts/` because `StoryMemory` embeds it (D-F, ADR-023 amendment):

```python
class RefVerdict(BaseModel):
    differences_observed: str          # ADR-004's reason-then-score applies to every judge call
    matches_description: bool
    attributes_present: list[str] = Field(default_factory=list)   # the best-of ranking key

class Character(BaseModel):
    ...
    ref_verdict: Optional[RefVerdict] = None    # ref_moderation_status unchanged
```

**Why this needs no ADR-003 or ADR-024 amendment.** D-H assumed an acceptance gate would be a *third conditional
edge* against ADR-003's two branch points. It is not. ADR-003 constrains the **graph**; ADR-024 §4 constrains
**routers**. Neither speaks to node internals. A node that re-rolls its own output and returns once adds no edge,
no router, and no branch — the graph shape is identical. The premise that blocked this question was wrong.

**Cap of 3, not ADR-010's 1**, because the blast radius differs: a bad scene is one page, a bad reference is
every page. Cost is bounded — one judge call per draw (`gemma-3-27b-it`, negligible) plus up to two extra image
draws at $0.02–0.035, against ADR-004's cap of 2 canonical refs per book. Worst case ≈ **+$0.14 on a $0.30–0.65
book**; typical case ≈ $0, since a passing first draw costs one judge call (CC-3).

⚠️ **This gate makes the failure loud. It does not fix the rate.** At the measured 25% draw quality, 3 draws
still ship an off-spec reference roughly **42%** of the time — visibly now, with the verdict persisted, instead
of silently. The fix for the *rate* is the seam ADR-001 already names: swap `fal_image_model`, which touches
neither the editor nor the consistency mechanism. Do not mistake this decision for a solution to the generator.

⚠️ **25% is a worst case, not a mean.** n = 4, on one invented chimera's hardest feature; Pip's reference was
on-spec on the first draw (`PHASE_05_RESULTS.md:162`). The rate across ordinary characters is unmeasured, and
`Character.ref_verdict` is what will measure it.

**Consequences:**

- **The `job_state.py` port is unblocked.** Both types D-H froze — `FailureReason` and `VlmVerdict` — live in the
  file that migration creates, which is why this ADR had to precede it. It now does.
- **No capstone document changes.** That is the point of Decision 1, and it is the largest practical difference
  between the options considered.
- **`story-memory-contract` is edited in the same change** (§2 schema, §4 freeze made permanent, §6 assertions,
  §8 the ADR-010 ranking deferral marked resolved). Its `approved` status and frozen shape survive: every change
  is additive.
- **Phase 1 gains two measurements it did not have**: Qwen's real fusion rate (via `anatomy_intact`) and the
  reference generator's real hit rate across ordinary characters (via `ref_verdict`). Both at zero marginal
  cost, both currently resting on n = 4 or on recollection.
- **ADR-001 qualification 3 is partially answered.** It recorded that the OmniGen2 identity cascade *"has no
  trigger yet… and no composition check anywhere in this plan."* There is now a composition field and a
  reference check. This does **not** approve a runtime auto-cascade, which that amendment explicitly withholds.
- **Consequences to build** (not this session — `CLAUDE.md §1`): the two contract types; `char_bible`'s
  draw-judge-re-roll loop and its prompt; the two new §6 assertions; `regeneration-controller`'s lexicographic
  best-of rule.

**Alternatives:**

- **Widen `wrong_body_feature` to cover merged/missing/duplicated parts** (doc-only, no version bump) — rejected,
  and it is the option that quietly damages the research. `judge-finetune.md` §4 pairs the value with the
  correction *"restate the countable feature,"* which is right for two-eyes-instead-of-three and wrong for a body
  fused into scenery. Annotators would tick one box for an identity error and a rendering error, the finetune
  would learn a mixed class, and Objective 4's F1 would be computed over a label meaning two things — while
  silently contradicting four capstone files that already define the value.
- **Add an eighth `FailureReason` value (`anatomy_malformed`)** — rejected. It is Decision 2 **plus** a breaking
  change, not an alternative to it: the value is unreachable at `same_character = True` unless `VlmVerdict` gains
  the field anyway. It would cost a `schema_version` bump, a worker restart path, four capstone edits, an ADR-023
  Decision 4 amendment and a changed annotation checkbox set — to name a defect believed to occur ~0% of the time
  on the shipping model.
- **Defer the whole item until Phase 1 measures Qwen's fusion rate** — rejected, and it defers the wrong question.
  The taxonomy freeze does not need that number; a 0% rate strengthens Decision 1 rather than changing it.
  Meanwhile deciding after the port pays the 12-consumer migration twice, and deciding after Phase-2.5 labelling
  opens invalidates every collected label (`methodology.md:160`).
- **Widen ADR-024's existing char-ref moderation gate** from *"is it safe"* to *"is it safe and on-spec"* —
  rejected, though it is the only option that literally leaves ADR-003's branch count untouched. The semantics
  genuinely differ: a moderation failure is terminal (ADR-025 — job `failed`, CC-9 screen) while a fidelity
  failure should retry. Making it retry means adding a loop-back edge, which is a third edge in substance while
  presenting itself as none.
- **Reuse `VlmVerdict` as the reference-check schema** — rejected on cost grounds that are small but real.
  `same_character` would have to mean "matches the description", `style_match` would be meaningless, and it would
  put verdicts from a different task, with one image instead of two, under the one schema that is a Phase-2.5
  finetune training target (`judge-finetune.md` §6.1 requires the training target and production schema to
  round-trip). Three fields beside it is cheaper than the ambiguity.
- **A scalar composition score instead of a boolean** — rejected. It defines nothing ADR-010 needs that a
  lexicographic order does not already give, and it asks a weak rating instrument to rate (ADR-004).

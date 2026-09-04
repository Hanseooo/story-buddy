# ADR-052 — An object's description is permanent appearance; per-scene change lives on the scene

**Status:** Accepted (2026-09-02; owner accepted the design in session before implementation) ·
**extends ADR-040** to the structured object surface
it explicitly exempted · **amends ADR-023** (one additive `Scene` field; `StoryMemory` remains the
single state source) · **does not amend ADR-004, ADR-010, ADR-025, ADR-028, ADR-034, ADR-047,
ADR-049, or ADR-050** · no judge-prompt, provider, pipeline-shape, or legacy-checkpoint change

## Context

Every paid measurement this project has taken — nine bundles, 128 draws — ran on synthetic corpus
stories, seven of the nine on `syn-001`. `methodology.md:178` assigns expert validation to the
**donated** stories only. No generated page from the set experts will actually score had ever been
inspected.

A throwaway probe on 2026-09-02 closed that gap: one donated-shaped story (`syn-901`, two
eleven-year-old cousins, a kitchen they leave and return to, and a plain bamboo fan they paint with
sampaguita flowers), 5 scenes, 14 images, USD 0.42, `cel`, prompt v7, code at `096554e`. The bundle
is deliberately **outside** `data/judge/` — it is not a corpus artifact, carries no `code_commit`
freeze claim, and must never be annotated. The story text is reproduced in §Evidence so the run is
repeatable.

`analyze` extracted the fan as:

```json
{"obj_id": "obj0", "name": "bamboo fan", "owner_char_id": "c2",
 "description": "Plain, brown, dusty, later painted with white sampaguita flowers."}
```

`build_prompt` renders visible objects verbatim (`prompt_optimizer.py:317-320`):

```python
f"{obj.name}, {obj.description}" if obj.description else obj.name
```

`StoryObject.description` is a single `Optional[str]` (`contracts/story_memory.py:107-111`) with no
scene dimension, so **every** page carrying `obj0` in `objects_present` receives both states of the
fan at once. Page s1 — the rainy yard, two pages before any paint exists in the story — shows the
fan already painted with white sampaguita flowers. Pages s2 and s4 show it painted, correctly, for
the wrong reason: the prompt says so everywhere.

The generator is not at fault and neither is the judge. The scene-constraint judge reads the
generation prompt as its `{constraints}` (ADR-047), so it was asked whether a painted fan appears on
a page whose prompt demanded a painted fan. It answered yes. **The check cannot catch this class of
error, because the contradiction is inside the constraint.**

### Why this is ADR-040's problem, arriving one surface later

ADR-040 removed `CharacterDescription.notes` from scene prompts on the finding that *"optional,
unconstrained analyzer prose can describe narrative function rather than appearance"*, and it closed
by ruling that *"structured visible objects and location data retain their existing ownership of
props, holder relations, and setting."* That trust is now falsified: the same narrative prose
reappeared **inside** the structured object surface. `"later painted with…"` is a plot event wearing
a schema's clothes.

The analyze prompt already states the correct rule for locations and never states it for objects
(`analyze.py:195`):

> Describe each location by what is permanently there — not the weather, the lighting, the time of
> day, any damage, or what happens there.
>
> For each object, provide a stable physical description …

"Stable physical description" is an unenforced adjective. The permanence rule spelled out for
locations was never spelled out for objects, and never validated for either.

### Why tightening the description alone is insufficient

Restricting `description` to permanent facts (`"a plain brown bamboo fan"`) fixes pages s0 and s1
and breaks pages s3 and s4, which must show the fan painted. The story's own point is that the
object changes. A permanence rule with no place to put the change trades a too-early state for a
too-late one. Both halves are required, or neither is worth shipping.

### What the instrument does with this

The expert validation instrument scores prop and setting continuity in 4 of its 15 closed items —
**B3** (objects essential to the story appear as written), **B4** (settings), **D3** (recurring
backgrounds), **D4** (recurring props) — and the open-ended form asks Question 4 directly: *"Across
pages, what unexpected changes, if any, occur in recurring characters, props, settings, or drawing
style?"* A prop that arrives in its final state pages early is the exact answer that question
solicits. Donated story `g5-s4` is built on a stick that a child imagines into a sword; under the
current shape that sword is drawn on page one.

## Decision

1. **`StoryObject.description` is permanent physical appearance only.** The same rule the analyze
   prompt already gives locations: not the weather, the lighting, the time of day, damage, use, or
   what happens to the object during the story. The analyze prompt states this for objects in the
   same words it states it for locations.

2. **Per-scene change is carried by a new additive field, `Scene.object_states: dict[str, str]`,**
   mapping `obj_id` to that scene's departure from the permanent description. It is written only
   where a scene's state actually differs; an object that never changes never appears in it. The
   field defaults to `{}`, so every existing checkpoint and persisted `StoryMemory` loads unchanged.

3. **`segment` owns it,** because `segment` already assigns `Scene.objects_present` and
   `Scene.visual_direction` — the per-scene facts. `analyze` continues to own the permanent
   description and gains no scene dimension.

4. **`build_prompt` renders the overlay after the permanent description** for objects in
   `objects_present`, and omits it when absent:

   ```
   Visible objects:
   bamboo fan, a plain brown bamboo fan with a bamboo handle, painted with white sampaguita flowers
   ```

   An `obj_id` present in `object_states` but absent from `objects_present` is dropped with a
   warning, matching the existing missing-`obj_id` path at `prompt_optimizer.py:312`.

5. **No judge change.** The constraint judge reads the assembled prompt (ADR-047). Once the prompt
   states the correct per-page state, the existing structured-contradiction machinery (ADR-049)
   checks it with no new call, no new field, and no new cost.

## Consequences

- One additive contract field, one analyze-prompt paragraph, one segment output, one render branch.
  No new model call, and no change to `MAX_DRAWS`, the gating predicate, `_rank`, or
  `FailureReason`.
- The corpus freeze is untouched: no intake record changes, and `intake_sha256` is unaffected. The
  change lands in `code_commit`, so it must be committed **before** the next campaign starts, never
  during one.
- A new failure mode becomes possible: `segment` may write a state the story does not support, or
  miss one it does. That is a text-model error on a typed field, which is checkable; the current
  shape produces an error that is structurally uncheckable.
- Locations are **not** covered. `Location` has the same text-only shape, and the probe showed the
  kitchen's cabinets and appliances changing across all three of its kitchen pages (D3). That is a
  separate decision on separate evidence and is deliberately out of scope here.

## Rejected alternatives

**Put an ordered state list on `StoryObject`.** Rejected: it needs a scene index to be read, and
`contracts/story_memory.py` states that scene list order *is* the contract precisely so that no
second source of order truth exists (*"There is deliberately no `Scene.order` field — it would be a
second source of truth"*). A per-object state list reintroduces exactly that.

**Reject temporal words in object descriptions ("later", "then", "becomes") in the validator.**
Rejected: brittle against paraphrase, and it deletes the information rather than relocating it. The
story genuinely contains a change; the schema needs somewhere to put it.

**Let the constraint judge catch it.** Rejected: it cannot. The judge's constraints *are* the prompt
(ADR-047), so a contaminated prompt produces a self-consistent verdict. This is the `b9506307`
lesson from ADR-050 in a different place — a check measured against a spec that is already wrong
reports success.

**Wait for the donated stories before deciding.** Rejected: the defect is structural, not
story-specific. Any story whose prop changes hits it, and `g5-s4` is such a story. Waiting
re-photographs a failure already photographed.

## Evidence

- Probe bundle: `scratchpad/probe_out/runs/syn-901/` (throwaway; outside `data/judge/`).
- Page showing the fan painted before it is painted: `scene/…_s1-2.png`.
- Probe story text, reproduced for repeatability:

  > Mila and Tala were cousins and they were both eleven. Mila had short hair and Tala always wore a
  > red hair tie. One rainy afternoon they were bored in Lola's kitchen and Tala found an old bamboo
  > fan behind the rice bin. It was plain and brown and a little dusty. They ran out to the yard to
  > shake the dust off it but the rain was still falling so they came back inside. Lola said the fan
  > belonged to her mother and nobody had used it in years. Mila got the paints from the cabinet and
  > they painted white sampaguita flowers all over the fan, one flower each, taking turns. Tala got
  > paint on her red hair tie and Mila laughed at her. When it dried they fanned Lola with it at the
  > kitchen table. Lola said it was prettier now than when it was new.

## Verification

Re-run the same probe (~USD 0.42) after implementation and read page s1. The fan is unpainted there
and painted on s3 and s4, or this ADR did not work. The check is the page, not the verdict — a
passing verdict on this failure is what produced the defect in the first place.

## Observations recorded but not decided

The same probe showed both cousins assigned `clothing: ["plain clothes"]` and drawn in the identical
beige shirt on all five pages. `"plain clothes"` satisfies
`ExtractedDescription.complete_visual_profile`'s humanoid-clothing check (`analyze.py:50-54`) while
carrying no discriminating information, and it is not in `_DESCRIPTION_PLACEHOLDERS`
(`contracts/story_memory.py:18`: `none`, `unknown`, `unspecified`, `neutral`). This is a plausible
D1/D2 mechanism on one story's evidence and is **not** decided here.

A related first reading — that `colours: ["red hair tie"]` proved the `colours` axis needed a type
check — was withdrawn: all thirteen `colours` values across the nine existing bundles contain a
colour term, `"red hair tie"` included, so such a check would pass it and change nothing. The
observed defect (the tie's colour re-bound to the hair) is generator ambiguity on one noun phrase,
on one image, and no contract change is justified by it.

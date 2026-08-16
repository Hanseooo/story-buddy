# ADR-040 — Narrative notes do not enter scene image prompts

**Status:** Accepted (2026-08-16; owner approved) · **resolves D-M** · **amends ADR-039
Decision 4 and its deferred broader-removal alternative** · **amends ADR-035's assignment of
filtered `notes` to the scene-prompt surface** · no `StoryMemory`, pipeline-shape, provider, or
legacy-checkpoint rewrite

**Context:** ADR-039 removed `CharacterDescription.notes` from canonical-reference draws because
the field is optional, unconstrained analyzer prose and can describe narrative function rather
than appearance. It deliberately retained `notes` in scene prompts pending separate evidence.

Production job `9517f79c-9f9d-46c6-958a-2213c054316c` supplies that evidence. Its scene prompt
described Andres as *"The protagonist, a child who builds a robot"* while separately describing
the selected moment and the robot. The same narrative role and action therefore competed with the
typed identity axes, reference images, visible-object roster, and scene direction.

ADR-035's all-or-nothing `notes` filter cannot fix this class of conflict. It removes a note only
when the active style fragment forbids one of its words; ordinary narrative prose such as
*"the protagonist"* survives unchanged. Retaining that prose would make a visual-only scene prompt
claim false and preserve a second, untyped authority over what the image depicts.

**Decision:**

1. Every newly assembled scene base prompt omits `CharacterDescription.notes` for both referenced
   and unreferenced characters. The typed `species`, `colours`, `body_features`, and `clothing`
   axes define textual character identity; canonical reference images reinforce appearance.
2. `Scene.visual_direction` remains the sole persisted authority for the selected drawable moment,
   pose, expression, viewpoint, and framing. Structured visible objects and location data retain
   their existing ownership of props, holder relations, and setting. Narrative notes are not a
   fallback for any of these surfaces.
3. Corrected scene attempts derive from the stored clean `Scene.prompt`, so omitting notes from the
   base also omits them from every retry. A correction may restate only the existing structured
   identity, anatomy, lettering, style, and scene-constraint signals; it does not recover notes or
   prior prompt history.
4. A sparse typed description does not re-enable `notes`. Fresh analyzer output must satisfy the
   existing visual-discriminator floor; canonical references remain the stronger appearance signal
   for referenced characters. A drawable fact found only in `notes` is an upstream extraction miss
   to correct at the typed boundary, not permission to restore a second prompt authority.
5. `CharacterDescription.notes` remains stored in `StoryMemory`. Removing or repurposing the field
   would be an unnecessary contract migration and would rewrite neither legacy checkpoints nor
   already stored prompt provenance. A resumed scene reuses its existing `Scene.prompt` and
   `Attempt.prompt`; this decision applies when a new base prompt is assembled.
6. ADR-029 targeted canonical-reference redraws are unchanged. They read the child-selected
   `ReferenceRetry.attribute` directly and append its explicit instruction; stored narrative
   `CharacterDescription.notes` is not transport for that attribute.
7. ADR-035 continues filtering typed character axes, object descriptions, location descriptions,
   correction values, and reveal chips against style prohibitions. Its all-or-nothing filtering of
   `CharacterDescription.notes` no longer governs a normal image-prompt surface after this decision.

**Consequences:**

- A narrative role, relationship, or action can no longer compete with the structured scene moment
  or summon a related story object through a character-description line.
- Referenced and text-only characters now use the same appearance-only textual projection. A third
  character without a canonical reference still relies on the typed discriminator floor rather
  than unconstrained prose.
- A useful visible trait placed only in `notes` will not reach a scene draw. This is accepted because
  the same trait was already absent from the canonical-reference draw and judge; visually stable
  identity belongs in the typed axes, while moment-specific visibility belongs in
  `Scene.visual_direction` or the structured object/location data.
- Character-free scenes remain valid: objects, direction, setting, and style can describe them
  without a character note or excerpt fallback.
- There is no schema-version bump, new validator, model call, provider change, node, graph edge,
  image attempt, budget change, moderation-order change, or pre-registered judge change.
- The production failure is targeted evidence for removing a contradictory prompt source, not a
  population-level quality claim. The `visual-prompt-reliability` Tier-B run remains the retention
  gate for essential-fact loss and other regressions.

**Alternatives:**

- **Retain style-filtered `notes` in scene prompts.** Rejected because ADR-035 filters rendering
  prohibitions, not narrative roles or actions; the observed contamination survives.
- **Heuristically keep only visual phrases from `notes`.** Rejected because free prose has no closed
  visual vocabulary. A rule list or another model call would introduce an unreliable classifier
  while preserving duplicate identity ownership.
- **Split `notes` into typed visual and narrative fields.** Rejected because the existing typed
  appearance axes already own stable visual identity. A contract migration would add no missing
  authority and would widen checkpoint and consumer compatibility work.
- **Restore notes only for unreferenced or visually thin characters.** Rejected because the most
  weakly grounded scene would then receive the least constrained prose. The analyzer's typed floor
  and the feature's regression check are the correct controls.

**Escape hatch:** To restore narrative notes to a normal image prompt or change their contract
meaning, write a new ADR and flag it to a human. Do not add a fallback at a call site.

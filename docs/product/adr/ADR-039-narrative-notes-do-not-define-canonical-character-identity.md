# ADR-039 — Narrative notes do not define canonical character identity

**Status:** Accepted (2026-08-15; owner approved) · **amends ADR-034's "draw still receives notes"
follow-on** · **supersedes ADR-035's targeted-path and unreachable-reinjection conclusions** ·
**clarifies ADR-029's targeted restatement** · no `StoryMemory`, pipeline-shape, or provider change

**Context:** `CharacterDescription.notes` is optional, unconstrained free prose produced by the analyzer. It can
describe narrative function rather than appearance. In the reported end-to-end run, the human
protagonist's notes said that he *"builds and names the robot"*. The canonical-reference prompt
rendered that sentence beside sparse placeholder-like visual axes, and Qwen-Image generated the
human as a robot. A redraw later produced a human, showing that the stored species was usable but
the normal draw prompt contained competing subject instructions.

ADR-034 deliberately removed `notes` from the reference judge while retaining it in the draw
prompt. ADR-035 then kept and style-filtered `notes` on the reference-draw and scene-draw surfaces.
Those decisions prevent an unclearable judge contradiction and a style-prohibition bypass, but they
still allow narrative actions, relationships, and story objects to contaminate the canonical image
that anchors every scene.

**Decision:**

1. A normal canonical-reference draw describes identity only with the character's `name`, `species`,
   and the three drawable appearance axes: `colours`, `body_features`, and `clothing`. It does not
   render `CharacterDescription.notes`.
2. The reference judge remains unchanged and continues to receive the same identity projection without
   `notes`. The normal draw and judge therefore agree on the story-derived identity attributes;
   only the existing draw-only thin-description filler may add non-judged presentation guidance.
3. An ADR-029 targeted redraw reads `ReferenceRetry.attribute` directly and appends
   `Be sure to include: <attribute>.` unconditionally, even when the selected attribute already
   appears in an identity axis. This is the explicit restatement ADR-029 requires. The targeted path
   does not overwrite or use `CharacterDescription.notes` as transport.
4. `notes` remains stored in `StoryMemory`, remains subject to ADR-035's all-or-nothing style filter,
   and remains available to scene-prompt construction. This ADR is intentionally limited to the
   canonical-reference draw; changing scene prompts requires separate evidence and a new decision.

**Consequences:**

- Narrative roles such as *"the protagonist"* or *"builds and names the robot"* can no longer make
  the canonical portrait depict a role, action, or related object instead of the character.
- A visually meaningful phrase placed only in `notes`, such as *"always smiling"*, no longer guides
  the canonical reference. That is accepted: visual facts belong in the typed visual axes. Prompt
  guidance can reduce model misses, but no semantic validator is added that could turn imperfect
  extraction into a terminal child-facing failure.
- Legacy checkpoints or analyzer misses with empty visual axes produce the existing neutral
  thin-description filler. Existing stored canonical references remain idempotently skipped, so
  this decision does not silently redraw an in-progress book.
- ADR-035's `notes` filtering remains meaningful for scene prompts. On the canonical-reference
  surface it becomes defense in depth before an axis that is no longer rendered.
- There is no schema-version bump, model or provider swap, new model call, additional image spend,
  moderation-order change, PII-policy change, or change to the pre-registered consistency judge.
  `JUDGE_PROMPT_VERSION` and `ref_verdict_prompt_version` do not change because the judge already
  excluded `notes`; only the draw prompt changes.
- The observed Andres failure is a targeted product repro, not evidence of a population-level
  quality improvement. Any capstone claim about frequency or effect size still belongs in the
  offline eval harness.
- The targeted-redraw regression must use a chip that is already present in `species`, `colours`,
  `body_features`, or `clothing`. A synthetic attribute absent from the description does not prove
  that the ordinary reveal path receives explicit emphasis.

**Alternatives:**

- **Keep `notes` in the reference draw and strengthen the visual axes only.** Rejected because a
  concrete human description can still compete with an instruction mentioning a robot; it reduces
  the trigger without removing it.
- **Split `notes` into typed visual and narrative fields.** Rejected because the existing visual
  axes already own appearance, while a contract migration would widen the change across every
  consumer and old checkpoint.
- **Heuristically keep only "visual" words from `notes`.** Rejected because free prose has no closed
  vocabulary; an allowlist or another model call would add a second unreliable classifier.
- **Remove `notes` from every image prompt.** Deferred. Scene excerpts already provide narrative
  context, but the reported failure proves only canonical-reference contamination. Broader removal
  may discard useful scene composition guidance and needs its own evidence.

**Escape hatch:** To change this decision, write a new ADR and flag it to a human — do not implement
the change first.

# ADR-041 — Character names are not canonical visual identity

**Status:** Accepted (2026-08-17; owner acceptance required before implementation) · **amends
ADR-039 Decisions 1–2 and ADR-034's reference-judge subject** · **amends ADR-029's empty-chip
fallback** · no Presidio,
`StoryMemory`, pipeline-shape, provider, model, or retry-policy change

**Context:** Presidio classified the fictional robot name `Bolt` as `PERSON` and deterministically
pseudonymized it to `Leo`, as required by ADR-011's privacy posture. The downstream analyzer retained
`species="robot"`, but the canonical-reference prompt described the subject using `Leo` plus sparse
facts such as `small` and `metal construction`. Production observations then included a robot with a
human face and another with a lion-like face.

The name-to-face causal link is plausible but not proven without a paid controlled ablation. Two
structural facts are proven: ADR-039 currently places `Character.name` in the canonical visual
projection, and ADR-034's judge deliberately ignores unlisted details. A human or lion-like face can
therefore compete during generation and remain invisible to acceptance when the persisted canon
does not state a face/interface design.

The pipeline already has one authorized invention point: `analyze` fills missing permanent visual
facts in a strict structured result, then persists the typed character axes. Adding a later
free-form prompt writer would create a second authority over identity, another failure boundary, and
another call while still seeing the same pseudonym.

**Decision:**

1. `Character.name` remains text/UI identity and binding metadata. It is not physical appearance and
   is not directly concatenated into newly assembled normal and targeted canonical-reference draw
   prompts or their reference-judge subjects for fresh validated analysis. Decision 8 is the sole
   legacy exception.
2. Presidio remains enabled and is not bypassed based on fictional status under ADR-011. This decision neither preserves
   fictional names nor changes captions, exports, reveal display names, scene roster mapping, or
   stored `Character.name`.
3. The existing analyzer LLM remains the single authority allowed to fill missing permanent visual
   detail. Its node-local strict schema requires a concrete whole-subject `body_plan` and a concrete
   `face_or_interface` for every fresh character. Each is a trimmed, non-placeholder, single-line
   value capped at 120 Unicode code points because it also becomes a child-facing reveal chip.
4. `analyze` folds those two values into the existing `CharacterDescription.body_features` in a
   deterministic order and discards the transient fields. No persisted field or schema version is
   added.
5. Analyzer guidance treats names, pronouns, dialogue, occupations, actions, and emotions as
   non-appearance evidence. Explicit story morphology wins; missing morphology is filled once with
   neutral, child-safe, species-appropriate visible facts. `smiled` alone does not authorize a human
   face.
   No deterministic name-string filter is added because names such as `Blue`, `Tiny`, `Star`, and
   `Bolt` may also be explicit visual facts; the prompt assembler removes the direct identifier
   channel and Tier-B observes semantic echoes.
6. Canonical generation and judging consume the same persisted physical axes. The existing
   non-human draw guard remains defense in depth; no separate judge-only anatomy rule or species
   allowlist is added.
7. The reference judge prompt version changes from 5 to 6 because the assessed subject changes. Results from
   earlier prompt versions do not pool with the new series.
8. Existing minted references remain skipped. A contract-legal legacy description retains the name
   fallback only when its name-free `species`/visual-axis projection is empty after placeholder and
   ADR-035 reference filtering, so resume does not gain a new terminal failure. This exception does
   not apply to fresh validated analysis. If reveal filtering removes every chip, the fixed
   `overall physical appearance` chip replaces the name fallback for fresh and legacy characters.
9. Scene prompts and scene judges remain unchanged. If a correct reference later drifts because a
   pseudonym remains on those surfaces, D-P will decide deterministic neutral aliases across the
   complete scene path.
10. Judge exceptions, three-rejected-draw fallback, reveal tap cap/pause semantics, draw caps, and
    best-of policy remain unchanged. D-Q separately owns any decision to make canonical-reference
    failure fail closed.
11. No second prompt-writing LLM is added. A structured canon critic/repair call may be reconsidered
    only after Tier-B evidence repeatedly locates the failure in analyzer canon rather than Fal,
    judging, or scene editing.
12. This change lands before Objective-4 pair creation. Pre- and post-ADR-041 reference distributions
    are not silently pooled; existing pairs, if any, are versioned/preserved or regenerated before
    labelling and the distribution change is disclosed. The pre-registered scene-judge model,
    schema, endpoint, and held-out rules do not change.

**Consequences:**

- The canonical prompt assembler no longer supplies human- or animal-coded pseudonyms as visual
  priors to fresh reference generation or acceptance; the Jamie/Bolt check verifies `Leo` is absent.
- A malformed human/lion face is judgeable as a contradiction because the persisted canon now
  states the intended face/interface and body plan.
- The change stays behind the existing `CharacterDescription` seam. Downstream modules learn no new
  contract and checkpoints remain schema-version 1.
- Fresh analyzer structured output is stricter. Invalid output may use `structured_text`'s existing
  single schema re-ask; the successful path adds no call, latency, or spend.
- Character names still reach scene prompts. This ADR makes no claim that all image-generation
  surfaces are name-free.
- The generator and judge remain probabilistic. Three rejected draws or a judge outage can still
  admit an off-spec reference under existing policy.
- Shapeshifters and permanent transformations remain outside one-reference canon.
- A three-fixture Gouache Tier-B check is required before claiming the design works for the reported
  failure. It is targeted product validation, not a population-level or per-style capstone result.

**Alternatives:**

- **Add a second free-form prompt-writing LLM.** Rejected. It sees the same redacted identity, adds
  another authority and failure boundary, and cannot inspect the image it is meant to improve.
- **Strengthen prompt prose without structured morphology.** Rejected because the current shallow
  discriminator floor can still pass without a judgeable body or face design.
- **Persist new morphology fields or `is_person`.** Rejected until the transient structured design
  measurably fails; the existing `body_features` contract can carry the facts.
- **Disable or context-gate Presidio for fictional names.** Rejected here because it weakens the
  child-facing privacy guarantee and does not repair sparse morphology.
- **Remove names from every model-facing surface now.** Deferred to D-P. Scene generation needs a
  complete deterministic alias design across reference rolls, directions, corrections, and judges;
  the reported failure proves the canonical path first.
- **Fail the book when reference acceptance is unavailable or all draws contradict canon.** Deferred
  to D-Q because it trades completion behavior for fidelity and amends frozen resilience policy.

**Escape hatch:** Restoring names to fresh canonical-reference model calls, adding another visual
prompt authority, persisting new morphology fields, or changing reference failure behavior each
requires a superseding ADR and owner acceptance before implementation.

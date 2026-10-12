# ADR-069 — Character redraw chips are emphasis choices, not judge-detected defects

**Status:** Accepted (2026-10-12), owner agreement in the combined #118/#119 design session.
Amends ADR-029 Decision 2's chip selection, ADR-034's reveal/gate lockstep, and ADR-041's
standalone morphology-chip promise only. Generation, reference acceptance, replacement,
moderation and spend policies are unchanged.

## Context

The reveal concatenates stored visual axes. A committed synthetic capture in
`docs/product/evidence/bundles/probe_out3/memory.json` contains `human` both as species
and as a body feature. Generic and overlapping suggestions make the requested emphasis
unclear. The owner's private screenshots illustrate this concern but do not establish
a submitted trait or a controlled before/after sequence.

Today a selected trait emphasizes an existing desired detail in a fresh text-to-image
draw. The previous picture is not supplied. The new safe picture replaces the old one,
even if its reference-quality verdict is negative. This is a reinterpretation attempt,
not a localized correction or a guarantee of preserved identity.

## Decision

1. Reveal chips are eligible emphasis choices from the existing style-filtered canon.
   They do not claim to be detected defects. Their availability does not depend on
   `ref_verdict`, `contradictions`, `matches_description` or `attributes_present`.
   The reference-mint acceptance predicate and judge remain unchanged.
2. Deduplicate after style filtering, comparing trimmed, case-folded text and preserving
   first occurrence and the exact offered string. Never mutate the stored description
   or substitute a label in the existing `attribute` request.
3. Suppress the exact vague labels `skin tone`, `average height`, `warm clothing`,
   `casual clothes`, `plain clothes`, and `traditional or warm clothes` in chip scope.
   For an explicitly `human` species only, also suppress `human`, `bipedal human`,
   `human face`, `human body`, `humanoid body`, `child's humanoid body`,
   `adult's humanoid body`, `child's body`, and `adult's body`. Straight and curly
   apostrophes are equivalent for this comparison. `is_humanoid` is not sufficient
   human context. Unknown phrases and specific values remain available, including
   an explicitly human-faced robot. This is a finite projection rule, not semantic
   synonym matching or a second author of canonical identity.
4. If no eligible choice survives, retain `overall physical appearance`. Present it
   as a general new-picture attempt rather than a concrete detail correction.
5. Explain the consequence before dispatch: “We'll make a new picture and try to show
   [detail]. It will replace this picture. Other details may change.” For the general
   fallback: “We'll try a new picture of [name]. It will replace this picture. Other
   details may change.” Selection is free. Only explicit `Redraw [name]` submits.

## Alternatives and consequences

- Keeping judge-derived missing choices is smaller, but hides retry choices according
  to a noisy observation and makes the child's options vary with the verdict.
- Semantic ranking, inferred replacement values and extraction-prompt changes would
  introduce unverified interpretation. They are not part of this decision. Exact
  duplicate removal does not claim to solve every semantic overlap.
- Image-conditioned correction may address unchanged identity more directly, but
  needs separately approved evidence and an ADR for the generation mechanism. Selected
  intent persistence through moderation also needs a separate state-contract decision.
- An old/new chooser or automatic quality rejection would change ADR-029's replacement
  policy. Neither is selected.

The existing confirm API, server-owned shared three-redraw allowance, explicit paid
dispatch, reference-quality failure policy, moderation before display, checkpoint
resume, signed images and accessibility/recovery states remain authoritative.
The current server validates membership and claims `awaiting_confirm` without a pause
revision token: a delayed request whose trait is still offered can claim a later pause.
This decision preserves existing safeguards, not comprehensive stale-request rejection.

## Verification

Use the committed synthetic capture for duplicate regression, and extend existing
reveal tests for verdict-independent choices, contextual human suppression, preserved
nonhuman morphology, post-filter collisions and fallback. Keep existing confirm,
targeted redraw, replacement, cap and moderation tests. Extend process-page tests for
concrete and general wording while retaining free selection and explicit exact dispatch.
Deterministic tests establish projection and control flow, not improved visual quality.

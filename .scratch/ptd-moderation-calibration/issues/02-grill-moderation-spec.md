# 02 — Grill: moderation policy and teacher-held runs → spec

**Status:** done
**Type:** grilling
**Progress:** done — design/ADR and scoped implementation authorization accepted (2026-10-27)
**Blocked by:** None for specification completion or the accepted synthetic-only, feature-off build scope. Audit 01 remains open for calibration evidence and release.
**Conflict verdict:** Owner accepted ADR-080 and moderation-stack §9.9 on 2026-10-27, including the synthetic-only, feature-off build exception. No repeat verdict is required for that scope.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Decide

- The written policy text and which layers get it.
- Whether the layer combination changes.
- Whether a teacher-held run is built. If it is: where it pauses, what each person sees, the time
  limit, and the off-by-default setting it sits behind.
- The ADR amendment and ethics note each choice needs.

## Output

- An amendment to `docs/specs/moderation-stack.md`, with a new ADR drafted for any change to ADR-011
  or ADR-003.
- Build tickets `03` onward, each `Blocked by` this ticket.

## Comments

### Accepted specification handoff (2026-10-27; current)

The owner explicitly replied **“accept all”** to the completed
[moderation-stack §9.9](../../../docs/specs/moderation-stack.md#99-technical-completion-proposal-2026-10-27),
[ADR-080](../../../docs/product/adr/ADR-080-teacher-held-moderation-and-exact-content-clearance.md),
and authorization for synthetic-only, feature-off implementation while audit 01 stays open.
The design interview, technical contracts and ADR acceptance are complete. This specification
ticket is done. Earlier draft/interview comments below are historical.

Accepted contracts cover hold/status/schema, exact content and private evidence, review interrupt,
authenticated commands, serialized decisions/dispatch, checkpoint recovery, generation fencing,
withdrawal, bounded replacements, policy/theme definitions, queue/focus/copy, writing recovery,
lifecycle compatibility, rollout and verification seams. No further interview or repeat conflict
verdict is required before implementing that accepted scope.

Ticket 05 is ready for implementation. Tickets 06–15 retain only their predecessor-implementation
dependencies and implementation-time checks. Ticket 13's criteria reference precedes ticket 07's
allow action. The accepted exception removes audit 01 as a prerequisite for that synthetic-only,
feature-off build work; it does not finish the audit or waive its evidence requirements.

Audit 01 remains open. Changed classifier prompts, paid replay, production enablement and
real-child use are not authorized. Educator/ethics/consent, applicable erasure workflows and hosted
verification remain release gates. Owner acceptance is not external approval. No implementation,
migration, paid call or deployment was performed to record this verdict.
### Draft synthesized (2026-10-26)

The owner invoked han-to-spec and paused further run investigation. The outcome contract is
saved in [moderation-stack §9](../../../docs/specs/moderation-stack.md#9-moderation-calibration-and-teacher-held-stories):
eight user stories, eighteen addressable acceptance criteria, twelve shared rules, an edge-case
table, rationale/evidence, proposed verification seams, twelve open decisions and a source-coverage
index. Researcher access is the accepted ADR-079 companion amendment in research-run-browser.

Readiness remains **Draft**, not ready-for-build. Policy criteria, exact hold/resume and retention
contracts, required moderation ADR amendments, audit evidence and verification-seam confirmation
remain blockers. Audit 01 and this ticket remain open. No new build tickets or implementation.

### Resumed interview amended (2026-10-26)

The owner confirmed resumed Q1–Q19 and the UX recap, then authorized this documentation amendment.
The updated contract is [moderation-stack §9](../../../docs/specs/moderation-stack.md#9-moderation-calibration-and-teacher-held-stories),
including draft ages-10–12 policy boundaries (§9.5.1), release confirmation/withdrawal, child stop,
same-intent replacements with fresh consistency checks, grouped text-only optional review before
paid generation, and policy-version/ordinary-disable behavior. §9.8 maps every resumed answer.

No existing school policy or educator/ethics reviewer was identified. The complete rubric and
review, necessary ADR drafts/acceptance, privacy/retention, exact resume/withdrawal contracts and
verification remain blockers. Settled choices have been removed from the unresolved portions of
OD-01–OD-11, without closing the remaining gates. OD-12 is still pending. Existing ticket references
are aligned; no new tickets or accepted ADR changes. This remains Draft, audit 01 and ticket 02
remain open, and no implementation or paid replay was performed.

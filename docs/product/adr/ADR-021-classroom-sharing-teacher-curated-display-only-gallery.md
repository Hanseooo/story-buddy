# ADR-021 — Classroom sharing: teacher-curated, display-only gallery of approved storybooks

**Status:** Accepted (2026-07-10) · revised 2026-07-20 (peer reflection and the child-facing Story Map
cut, gallery made display-only) · revised 2026-07-20 (later same day) — structured reflection questions
reinstated, following ADR-017's reversal · **revised 2026-07-21 — reflection reinstatement reversed.**
Owner call: only the **storybook itself** is peer-visible. The gallery is **display-only again** — no
reflection prompt, comment, or scoring surface of any kind. The child-facing Story Map stays cut.
**depends on ADR-017**

**Context:** Student authors benefit from an authentic audience — their book seen by classmates, not read
once and shelved. The original design delivered this through an in-app peer loop: classmates typed
fixed-prompt reflections and the author saw a Story Map. The 2026-07-20 tightening cut this because the
child no longer operated the app at all; ADR-017's reversal briefly reinstated a bounded reflection
feature the same day. That reinstatement is now reversed: the gallery delivers the authentic-audience
benefit through the storybook alone, with no additional child-typed, peer-visible surface. No evaluation leg
depends on this feature — the study carries no reader-comprehension study (ADR-008, revised 2026-07-25).

**Decision:**

1. **Sharing is classroom-scoped and teacher-gated.** A book enters the gallery only after the teacher
   **manually** approves it (ADR-017 — no auto-approve). Not public, not link-based, not cross-classroom.
2. **The gallery is display-only.** Classmates browse and read/listen to approved books. There is no
   reflection prompt, comment, reply, or scoring surface of any kind — reading the storybook is the only
   peer interaction.
3. **No additional moderation surface.** With no reflection text, no new input-moderation pass is needed
   beyond the storybook's own pipeline (ADR-011); the already-moderated generated book is the only
   peer-visible artifact.

**Consequences:**
- No new consent-language question is opened beyond the account itself (ADR-017) — there is no
  gallery-specific typed-input surface to weigh.
- The gallery is a **product feature, not a measurement instrument.** No evaluation leg depends on it
  (ADR-008, revised 2026-07-25).
- **Post-October** unaffected — the gallery still sits off the October type-A critical path (roadmap
  §0.8).
- No reflection route, schema field, or moderation tier ships. `PRD_v2.md`, `USER_FLOW.md`,
  `ROUTE_MAP.md`, `ethics_and_safety.md` need propagation to drop reflection references.

**Alternatives:**
- **Structured, teacher-toggled reflection questions** (the 2026-07-20 later-same-day reinstatement) —
  reversed. Reopened a child-authored, peer-visible typed-content surface and its consent/moderation
  weight for a feature no evaluation leg needed.
- **Free-form, unbounded peer reflection** (the original design) — rejected. Open-ended peer prompts are
  the unkindness/uncomparable-response problem this ADR exists to avoid.
- **Child-facing Story Map** — still cut. No motivation for it returned.
- **Automated story-quality scoring / "is your story good enough?"** — rejected. Hostile to the child,
  and a second research contribution that would dilute the first.
- **"What happens next?" continuation** — deferred to Phase 4.
- **Public sharing** — see ADR-017.

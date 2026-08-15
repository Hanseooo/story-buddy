# ADR-017 — Setting: teacher-managed classroom; child holds an issued account and operates the app; teacher reviews manually (auto-approve deferred)

**Status:** Accepted (2026-07-10) · revised 2026-07-20 (tightened to teacher-only operation, child never
touches the tool) · **revised 2026-07-20 (later same day)** — **reversed again.** The child now holds a
**teacher-issued account** and operates the app directly (inputs their own story, sees their own gallery
entry); the teacher's role narrows from sole operator to **account issuer + reviewer**. Driver: giving
the child ownership of authoring their own story is a stated UX goal, and the account model below
(teacher-issued, classroom-gated, no self-serve signup) keeps the consent/moderation posture this ADR
exists to protect. · **revised 2026-07-21** — auto-approve clarified as **deferred to Future Work**
(manual review only, no toggle); see ADR-021 for the reversal of its own reflection-question
reinstatement — the gallery is display-only, storybooks are the only peer-visible artifact. ·
**supersedes the auth *role model* in ADR-006** · **drives ADR-008, ADR-011, ADR-021**

**Context:** The respondents are **Grade 5–6 students in the Philippines** (ages 10–12), and the product
gains **peer sharing**. The original design had a parent account holding nested kid profiles, and listed
teacher/classroom as out of scope (PRD §4). The 2026-07-20 revision then moved to a teacher-only-operator
model specifically to keep the child off the account/moderation surface entirely.

That model is now reversed for UX reasons: a child who never touches the tool doesn't get to *author*
their own book or *own* their own gallery presence, and both are core to the product's value to the
child. The two original pressures — social-network failure modes, and PH Data Privacy Act consent —
still apply and still shape the decision below; they just no longer rule out child accounts outright.
**The gate moves from "child has no account" to "child's account can only exist inside a teacher-issued
classroom, with no self-serve path in or out."**

**Decision:** **The child gets a teacher-issued, classroom-scoped account. The teacher stops being the
sole operator and becomes the account issuer and reviewer.**

- A **teacher or BEED (education) student** signs up, creates a **classroom**, and gets a **classroom
  code**. They create each **student account**: nickname + an initial password the teacher sets.
- **The child logs in** with the classroom code + nickname + password. **They can change their password**
  during onboarding or from settings. **No self-serve signup, no email on the account, no code that works
  outside a classroom the teacher created.**
- **Password reset is teacher-initiated only**, from a classroom admin screen. There is no email-based
  self-service recovery — student accounts carry no email to recover to.
- **The child inputs their own story directly**, in their own account. It routes through input moderation
  and PII redaction unchanged (ADR-011 point 5) — child-entered text gets no lighter a bar than
  operator-entered text got.
- **The teacher reviews every generated book before it's visible — manual approve/reject only.** An
  **auto-approve** toggle is deliberately **deferred to Future Work**: skipping the human backstop
  removes a safety layer and cannot ship without an ethics re-review. The automated moderation stack
  (ADR-011) still runs on every book regardless, unchanged and non-negotiable.
- **RLS isolates by classroom.** Supabase, Auth, Storage, Realtime, and the RLS posture (ADR-006) are
  otherwise unchanged — only the role names and the isolation boundary move.
- **Sharing terminates at the classroom.** Not public, not link-based, not cross-classroom. Inside the
  classroom it is a **teacher-curated, display-only gallery of approved storybooks** — the storybook
  itself is the only peer-visible artifact; there is no reflection or comment surface (ADR-021).
- **The parent's role is consent-giver**, which is where the law puts them. A child-held account with a
  password raises the consent bar back up from the teacher-only-operator model — this is a Session 4 /
  `ethics_and_safety.md` propagation item, not resolved by this ADR.
- **Scope is Grade 5–6, and it is derived from the study's needs, not chosen for convenience.**
  They write independently (so the story is unambiguously the child's); DepEd's medium of instruction is
  English by Grade 4 (so: one language, one moderation regime, one TTS voice); they are pre-adolescent
  (age-appropriate content). Remove any boundary and a specific study or safety property breaks.

**Consequences:**
- The child now authenticates and inputs their own story — more moderation surface, more consent
  weight, and a real password-reset support burden the teacher owns. This is a deliberate trade against
  the 2026-07-20 tightening, made for child UX/ownership.
- RLS still means something — classroom isolation is a real, testable boundary (Tier A tests) — but it
  now also isolates one child's account from another's within the classroom, not just adult-owned rows.
- **No public mode ever, and no self-serve signup ever.** See Alternatives. The classroom-code gate is
  the whole safety argument; removing it removes the argument.
- **A classroom is just a container with an adult owner.** A tutoring centre owns one; a parent owns one
  with a single member. Same table, same policy, no second mode. Publishing *outside* the container is
  the PDF export (ADR-013) — the child shares the artifact, not the platform.
- At N ≈ 8–15 the study cannot stratify by age anyway. A tight band is a delimitation, not an apology.
- Downstream docs (`PRD_v2.md`, `ROUTE_MAP.md`, `RESEARCH_PROTOCOL.md`, `ethics_and_safety.md`,
  `research_instruments.md`) still describe the teacher-only-operator model and need propagation — not
  done as part of this ADR edit.

**Alternatives:**
- **Two modes (classroom-scoped + public-scoped)** — rejected, firmly. It doubles the RLS model, the
  consent regime, and the spec set (violating CLAUDE.md §6's ban on parallel structures), and an ethics
  board will not approve a public mode for content authored by minors. The underlying worry — "is this only useful in a classroom?" — is answered
  by the container argument above, at zero cost.
- **Fully open student accounts, no teacher-issued gate, self-serve signup** — still rejected. This is
  the social-network failure mode the original ADR named; nothing about the UX motivation for this
  reversal requires removing the gate, only removing "the child never touches the tool."
- **Teacher-only operator, child never touches the tool** (the 2026-07-20 tightening) — superseded by
  this revision. Simpler and lower-surface, but at the cost of the child's ownership of their own story
  and gallery presence.
- **Keep parent accounts and add sharing** — rejected. Sharing between unlinked families is the hardest
  version to make safe and the hardest to get approved.
- **Researcher-run sessions only, no real accounts** — rejected as a *product* decision, but adopted as
  the *recruitment* posture: the researcher occupies the teacher role during the study. Same code path, no
  throwaway mode, and no school partnership is required to reach N ≈ 8–15.

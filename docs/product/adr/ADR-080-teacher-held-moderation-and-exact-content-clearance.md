# ADR-080 — Teacher-held moderation and exact-content clearance

**Status:** Accepted (2026-10-27), owner explicitly said “accept all” in response to the design,
ADR and synthetic-only, feature-off build authorization. Ticket 05's scene hold and enabling
contracts are implemented; teacher inspection/decisions and later subjects remain pending. This acceptance does
not claim audit completion, educator/ethics approval or authorization to enable real-child use.

**Amendments:** ADR-003/024 and ADR-029 (a dedicated moderation pause alongside child
reveal); ADR-011 (first-flag holds and policy-based exact-content teacher clearance);
ADR-023 (defaulted additive contract fields); ADR-025 (held/stopped outcomes, bounded replacement
and fenced continuation); ADR-006/017 (private review records and guarded image delivery);
ADR-030 (no public traces for teacher-review jobs); ADR-044 (quiescent held/stopped deletion);
ADR-059 (private pre-graph title holds). Narrows teacher-review-and-approval invariants 8, 9, 11
and 12 for safety holds only. Earlier ADR files remain historical records; this amendment takes
precedence for teacher-review mode within the scope below.

## Context

The owner selected a child wait/leave/return experience and contextual teacher review at the
first actual flag, before automatic moderation redraw. Teachers may allow exact content only
when it meets a written policy, request one bounded picture replacement or stop. Children can
stop a held story while preserving writing. The policy targets Grade 5–6/ages 10–12. All optional
themes default off and are grouped once on submitted text before paid image generation.

Current code fails flags, reserves the only interrupt for child reveal, treats every worker
interrupt as `awaiting_confirm`, clears flagged reference paths, and lets a child read all Storage
objects under their own job prefix. A UI-only hold would therefore be unsafe. Current raw job
storage/public traces cannot be reused for private flagged-review evidence. Audit 01 is open;
the supplied defense run has not been independently diagnosed and no calibration improvement
has been measured. ADR-079's researcher inspection authority does not authorize teacher decisions.

## Decision

1. **Preserve baseline and capture mode.** Add server setting
   `enable_teacher_moderation_review=False`. Capture `baseline` or `teacher_review_v1` at authorized
   submission intake and persist it. Disabling affects later intake only; existing captured jobs
   and holds drain normally. It is not an emergency switch. New schema/config failure cannot
   silently downgrade a captured teacher-review submission.
2. **Add one dedicated pause and one replacement node.** `moderation_review` has no side effects
   before/after its `interrupt()`. Flag evidence is checkpointed through StoryMemory. The worker
   publishes a teacher hold only from durable evidence and distinguishes it from child reveal.
   `moderation_replace` performs one authorized same-intent draw. Routers remain pure and human
   decisions are explicit typed inputs, not an autonomous orchestrator.
3. **Use exact subjects and private records.** Bind every review/decision to immutable text/image
   hash, review ID, subject ID, policy/settings versions and generation epoch. A private
   `job_moderation_reviews` table holds evidence and immutable decisions, with RLS and no browser
   grants. Do not store teacher evidence in `jobs.reveal`, Realtime-visible error fields or public
   metrics. New contract fields are defaulted and appended; schema version stays 1, baseline
   defaults preserve old checkpoints. Exact proposed names/types are in the linked spec.
4. **Either classifier flag holds.** Preserve layer order, short circuit, existing primary-error
   fallback and backstop-error failure. No voting or new provider/model. An automated label is
   advisory; allow confirms that inspected exact content meets the current written criterion.
   Prohibited content, failed privacy processing, missing checks and provider refusals cannot be
   approved through a safety exception. Teacher release is recorded as `teacher_allowed`, never
   rewritten as an automated pass. Later assets are independently checked.
5. **Serialize decisions and fence work.** Job-row transactions serialize competing commands.
   A durable pending dispatch plus deterministic RQ identity and one per-job Postgres advisory
   lock prevents duplicate continuations. Epoch checks before/after paid effects and publication
   reject stale workers. Unknown enqueue outcomes reconcile/retry the same recorded action.
   Keep ADR-025's stated provider-success/upload-crash billing limitation visible. No new queue,
   scheduler or general workflow framework.
6. **Withdraw whole-book clearance.** Owner teachers can withdraw an earlier exact-content allow.
   Atomically create a new review, advance epoch, set `awaiting_teacher` and clear editorial
   timestamps. Deny subsequent child/gallery/PDF reads and further paid work. An in-flight call
   may complete privately; it cannot publish through the old epoch. After quiescence, inject the
   review at the latest checkpoint using the dedicated review node, preserving saved continuation.
   Later release never auto-restores sharing. Already viewed/downloaded bytes cannot be recalled.
7. **Guard every feature-job image.** Deny browser Storage access to these job prefixes, including
   direct signing of guessed attempt paths. Child/teacher product reads use authenticated,
   no-store backend image responses bound to exact authorized assets, with authorization checked
   again before response. Internal Storage reads retain private signed URLs through providers.py.
   Researcher reads retain ADR-079's authenticated projection/exclusions and no decision authority.
   Do not expose signed Storage bearer links to children as a withdrawal shortcut.
8. **Privacy precedes persistence.** In the new mode, redact title/story before database, RQ,
   checkpoint, tracing or classification. `jobs.input_text` and `Input.raw_text` contain only
   processed text. Preserve title-redaction acknowledgement. A title flag creates a private
   pre-graph review; allow starts that never-started graph once. No public Langfuse traces for
   teacher-review jobs; baseline D-R remains separately open. Review history is deleted with its
   job, not retained indefinitely for research.
9. **Retain spend and quality policy.** A scene replacement consumes its one existing moderation
   redraw slot in addition to existing consistency attempts; no increase to `IMAGE_BUDGET`.
   It preserves scene intent, approved refs/style and source prompt, receives a fresh consistency
   judgment and safety check, and cannot select a previously rejected candidate. Finalize that
   fresh replacement with its actual passing/failing/unchecked quality result under existing
   degraded-quality policy, with no further consistency redraw. This proposes resolving D-N.
   Reference replacement uses the existing one-per-book moderation-redraw allowance and reference
   judgment, not a new scene judge. Provider refusal fails honestly. No generic safety softening.
10. **Preserve complete child recovery and deletion.** Add `awaiting_teacher` and terminal `stopped`.
    Leave differs from confirmed stop; stop retains processed writing for a new submission.
    Implement ADR-044's quiescence marker before this lifecycle ships; held/stopped quiescent jobs
    join its deletion states. Deletion removes private review rows too. No new TTL, active-job
    deletion, teacher deletion or retained audit copy. Inactive/moved children cannot resume.
11. **Separate safety and editorial review.** Teachers inspect flagged pictures only after explicit
    reveal, see criteria/evidence, and use distinct safety actions in Books/Needs your help.
    Children see neutral waiting/stopped status only. Editorial three-state decisions retain their
    existing purpose; recovery applies to resumable holds, not arbitrary historical failures.
    Ordinary classroom-sharing approval remains a separate action after safe completion.

## Consequences and release gates

This is a cross-cutting implementation across contracts, graph, worker, authenticated routes,
schema/RLS, image delivery and UI. The off-by-default mode protects baseline behavior, but does
not remove the need for real graph/transaction/RLS verification. Guarded delivery adds authorized
backend reads to the existing browser-read design to support exact-content confidentiality and
withdrawal. No dependency or deployed service is added.

The owner accepted this record and the concrete spec on 2026-10-27. Audit 01 remains open and is
required before changed classifier criteria/prompts are adopted; the build exception below removes
it as a prerequisite for synthetic-only, feature-off implementation. Educator/ethics review and consent/retention disclosures,
plus hosted access/lifecycle verification, precede real-child enablement. There is currently no
identified external reviewer or recorded approval. Draft policy and measured efficacy are distinct.

**Accepted build authorization (2026-10-27):** permit ticket 05 and its successors in
dependency order to implement these contracts using synthetic data with the feature disabled by
default, while audit 01 stays open. This is an explicit exception to the blanket ticket-02 audit
dependency for that build work only. It does not authorize changed classifier prompts, paid
replay, production enablement or real-child use. The owner accepted both design and this exception;
downstream implementation follows its predecessor-ticket dependencies. Ticket 13's criteria UI precedes ticket
07's allow command; implementing policy reference does not authorize prompt calibration.

## Alternatives

- Generalize child `reveal`: fewer named nodes, but mixes private teacher evidence and authority
  with a child interrupt that currently fails toward progress on unknown input. Rejected.
- Restart after teacher approval: avoids durable resume work but risks repeated spend, lost
  completed scenes and new content that was never approved. Rejected.
- Separate workflow service/event framework: can manage suspension but duplicates existing
  Postgres/RQ/LangGraph capabilities and adds an operational surface. Rejected.
- Hide images in UI and retain browser signing: less code, but current prefix-wide permission
  exposes the flagged attempt and signed URLs are bearer grants. Rejected.

## Verification and sources

[moderation-stack §9.9](../../specs/moderation-stack.md#99-technical-completion-proposal-2026-10-27)
is the single source for accepted fields, commands, transitions, privacy, policy, UX and tests.
Verify through authenticated HTTP/UI into the real graph with providers mocked at the outer
boundary; prove transactions/RLS with disposable database integration, not stubbed race assertions.
No implementation, live access checks or paid replay was performed to write this record.

Sources: owner interview and 2026-10-27 request to finish ticket 02; existing graph/worker/provider
and Storage-policy code; ADR-003/006/011/017/023–025/029/030/044/059/079; specs linked from
moderation-stack §9.7. Supabase documents [Storage RLS](https://supabase.com/docs/guides/storage/security/access-control)
and [private delivery/signed links](https://supabase.com/docs/guides/storage/serving/downloads).

**Owner verdict:** Accepted explicitly on 2026-10-27: “accept all.” Applies to ADR-080,
moderation-stack §9.9 and the synthetic-only, feature-off build exception. This is owner design
acceptance, not external ethics approval or evidence that the feature has been built or validated.

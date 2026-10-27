# ptd-moderation-calibration: map

**Phase:** [Post technical defense](../post-technical-defense/map.md), rank 2

**Conflict gate:** ADR-011 (moderation stack and ordering), the `AGENTS.md` child-safety rules ("no
unmoderated generated image reaches a child"; "the child never sees a moderation category"), and
ADR-003 (`reveal` holds the baseline graph's only `interrupt()`). The owner explicitly accepted
ADR-080 and §9.9 on 2026-10-27, including synthetic-only, feature-off build work. Do not ask for
the same conflict verdict again within that scope. Real-child release gates remain.

Panel suggestions: better rubrics for rejecting text and images, because moderation was too strict at
the defense, and the teacher decides whether a flagged run continues.

## Tickets

| # | Ticket | Type | Progress | Blocked by |
|---|---|---|---|---|
| 01 | [Audit: why moderation over-refuses](issues/01-audit-moderation-false-alarms.md) | research | open | — |
| 02 | [Grill: moderation policy and teacher-held runs → spec](issues/02-grill-moderation-spec.md) | grilling | done — design/ADR accepted | — (accepted build exception; audit 01 remains open) |
| 03 | [Any researcher can open failed and unapproved runs](issues/03-researchers-inspect-failed-runs.md) | task | open | — |
| 04 | [phase_05 text probe reads the current setting](issues/04-phase05-probe-setting-name.md) | task | open | — |
| 05 | [Flagged scene picture holds; child leaves and returns](issues/05-hold-flagged-scene-picture.md) | task | done, merged | — |
| 06 | [Teacher inspects a held story in Needs your help](issues/06-teacher-inspects-held-story.md) | task | ready for agent | — (05 merged) |
| 07 | [Teacher allows the exact held picture; run resumes](issues/07-teacher-allows-held-picture.md) | task | open | 06, 13 |
| 08 | [Teacher or child stops a held story, writing kept](issues/08-teacher-stops-held-story.md) | task | open | 06 |
| 09 | [Teacher requests a replacement picture within budget](issues/09-teacher-requests-replacement-picture.md) | task | open | 07 |
| 10 | [Flagged character reference holds](issues/10-hold-flagged-character-reference.md) | task | open | 07, 08, 09 |
| 11 | [Flagged story text holds; teacher can allow unchanged](issues/11-hold-flagged-story-text.md) | task | open | 07, 08 |
| 12 | [Flagged title holds instead of 422](issues/12-hold-flagged-title.md) | task | open | 11 |
| 13 | [Review criteria and per-hold explanation](issues/13-review-criteria-and-hold-explanation.md) | task | open | 06 |
| 14 | [Optional classroom review themes](issues/14-optional-classroom-review-themes.md) | task | ready for agent | — (05 merged) |
| 15 | [Accepted theme holds once per submission](issues/15-accepted-theme-holds-once.md) | task | open | 07, 14 |

**Current handoff (2026-10-27):** the owner explicitly said **“accept all”** to
[moderation-stack §9.9](../../docs/specs/moderation-stack.md#99-technical-completion-proposal-2026-10-27),
[ADR-080](../../docs/product/adr/ADR-080-teacher-held-moderation-and-exact-content-clearance.md)
and synthetic-only, feature-off implementation while audit 01 remains open. Ticket 02 is done as
an accepted specification handoff. Ticket 05 is merged into `feat/account-onboarding` at
`b03cc3f` (2026-10-28), including private persistence, guarded delivery and checkpoint-only recovery.
Tickets 06/14 can use those contracts now; other successors retain their dependencies.
See moderation-stack §9.10 for verification limits. Do not repeat the conflict verdict, design
acceptance or product interview.

Tickets 03–15 were written on 2026-10-26. The accepted §9.9 contracts now govern 05–15.
The audit-dependency exception applies only to synthetic-only build work with the feature
disabled by default. Audit 01 still owns AC-17/18, OD-09 and §7's replay evidence. Changed
classifier prompts, paid replay, production enablement and real-child use are not authorized.
Educator/ethics/consent, applicable erasure and hosted-verification gates remain for real-child use.
The accepted D-N/replacement design addresses #78 through ticket 09; current code's unchecked
retry is not fixed by acceptance. The baseline backstop-error policy remains a separate decision.
## Answers

### Interview decisions (2026-10-26; specification only)

- The owner opened discussion of changes to ADR-011, ADR-003 and child-safety rules, with
  investigation informing choices. This is not acceptance of a moderation amendment or build work.
- UX takes priority. A safety flag on submitted text or a generated picture should automatically
  hold the story for teacher inspection. The child can leave and return without losing the held
  story; the flagged image stays hidden pending a decision. Review starts at the first safety
  flag, before any automatic moderation redraw. Agreed release/recovery choices and remaining
  contracts are in moderation-stack §9 (updated below). Service errors are not safety verdicts.
- The owner wants a teacher to be able to release the exact flagged image after inspection.
  The resumed interview settles proposed boundaries, confirmation and withdrawal in
  moderation-stack §9.2/§9.5.1; exact release/withdrawal contracts and review remain blockers.
- Flagged titles join flagged story text, character references and scene images in the same
  teacher-help experience. The owner opened the additional ADR-059 conflict for specification:
  title moderation currently rejects before a job exists. Privacy checks must succeed before
  any held submission is stored. The storage/lifecycle design and ADR amendment are still pending.
- A moderation hold has no new automatic review deadline. It remains waiting until the teacher
  acts, the child confirms stop, or the story is deleted under the existing lifecycle. The child
  can leave and return. Leaving does not cancel the hold. The bookshelf clearly identifies
  waiting-for-teacher stories.
  This does not exempt held stories from existing deletion or retention rules.
- For a held picture, teacher actions include allowing that exact picture, requesting a replacement
  picture, or stopping the story. A replacement is paid generation within the existing image budget,
  undergoes moderation, and returns to teacher review on its first safety flag. Replacement
  generation is unavailable when the budget is exhausted. Custom appearance instructions and
  child-directed redraws remain in rank 4. No extra retry budget has been approved.
- For held text, the teacher may allow the exact flagged title or story to continue unchanged;
  the child need not rewrite it solely to satisfy an automated flag. PII redaction still applies,
  and generated pictures still undergo their own moderation. The written safety policy
  is now proposed in moderation-stack §9.5.1. Complete rubric review and exact release contracts
  remain unresolved.
- The owner selected teacher judgment against a written safety policy: automated safety flags are
  advisory and may be overturned when the material meets that policy. No automated flag category
  is an unconditional veto. This does not authorize genuinely prohibited material or bypass PII
  redaction, provider refusals, access controls or checks on subsequent generated assets.
  Agreed draft policy and confirmation/withdrawal behavior are in moderation-stack §9;
  complete policy review, evidence and exact contracts remain blockers.
- The owner selected B1: a small set of predefined, optional classroom review triggers, rather
  than free-text custom rules. These add teacher review and cannot disable shared safety checks,
  privacy checks or provider restrictions. Exact definitions and detection criteria remain
  undecided. Distinguish a shared safety flag from a classroom-preference review trigger for the
  teacher; the child receives neutral waiting copy in either case. The owner requests an edge-case
  review before specification completion and an explicit basis for what is flagged or allowed.
- Teachers get both an accessible Review criteria reference and a criterion-specific explanation
  for each held story. Missing recorded reasoning is stated as unavailable, not invented. The
  reference distinguishes shared safety criteria from optional classroom review triggers; children
  continue to see neutral waiting copy rather than safety categories.
- The owner resolved the leniency proposal as fewer optional classroom review triggers (Q14 A).
  Teachers can disable extra classroom review triggers; shared safety criteria, privacy checks and
  provider restrictions remain unchanged. No alternative safety-rubric modes or free-text rules
  are in scope. The owner selected these optional trigger themes: mild suspense/spooky settings;
  non-graphic fighting, arguments or bullying in a story; and sadness, loss or separation. These
  request teacher review rather than label the story unsafe. Exact definitions, exceptions and
  detection verification remain pending. All three optional triggers start off; teachers enable
  the extras they want (Q20 A). Shared safety checks still apply. This default is separate from
  the parent roadmap's requirement to ship the entire new feature disabled initially.
- An optional theme accepted by the teacher does not repeatedly hold the same unchanged submission
  for that theme (Q16 A). New shared-safety flags still create holds on their exact content.
- Optional classroom switches are captured for each submission (Q21 A). Changes affect new
  submissions only; existing stories retain their original optional settings. A setting change
  does not silently release an existing hold or start paid generation. This is not a decision
  about emergency changes to shared safety requirements.
- Teacher inspection includes story text and available pictures for context, not only a flag label.
  The owner requests forward compatibility with rank 3: inspection/content presentation is shared
  context, while moderation resolution and editorial feedback remain distinct responsibilities.
- Held stories appear in the existing classroom Books area in a distinct Needs your help queue
  (Q17 A), rather than a separate moderation dashboard. Safety-hold actions and completed-book
  editorial actions remain visibly and behaviorally distinct. Queue ordering/counts remain to be
  specified; this does not merge safety release with classroom-sharing approval.
- Stop this story ends the current generation run after confirmation (Q18 A). It does not delete
  the child's writing, which remains subject to the existing lifecycle. The child receives neutral
  stopped-story copy, can return to the bookshelf, and can reuse the writing through the existing
  new-submission flow. No reopening of stopped runs or guarantee of carrying pictures into a new
  submission is included. Teacher feedback and a structured revision cycle remain rank 3's work.
- Flagged pictures are initially hidden from the teacher behind a warning and an explicit Show
  picture to review action (Q19 A). Story context and the recorded reason remain visible. If the
  exact held picture cannot load, allowing that picture is unavailable. The child cannot use the
  teacher reveal action to access flagged content.
- ADR-079 is accepted: all researchers may inspect the full existing projected run viewer for
  failed and unapproved runs. Its access amendment is specified in `docs/specs/research-run-browser.md`;
  implementation is pending. Researcher inspection grants no teacher decision authority.
- Run `314fafc9` is a candidate investigation case, not a verified false alarm. The owner supplied
  job metadata and a checkpoint inventory through step 15. Decoded state, pictures, classifier
  reasons and worker/trace evidence remain uninspected. No replay or paid probe has been approved.
- The owner paused further investigation and invoked han-to-spec. The initially synthesized Draft was
  `docs/specs/moderation-stack.md` §9: US-01–08, AC-01–18, SH-01–12, edge cases and OD-01–12.
  Readiness blockers are explicit, including verification-seam confirmation. This does not finish
  audit 01 or authorize implementation; build tickets were later requested separately (see Tickets).

### Resumed interview agreement (2026-10-26; documentation amendment only)

The owner confirmed resumed Q1–Q19 and the UX recap, then requested the spec amendment.
[moderation-stack §9](../../docs/specs/moderation-stack.md#9-moderation-calibration-and-teacher-held-stories)
is the source of truth for the updated acceptance criteria, policy boundaries, edge cases and
remaining gates; §9.8 distinguishes resumed questions from the earlier interview numbers.

The proposal retains either-flag holds, adds criterion confirmation and clearance withdrawal,
lets children stop while retaining writing, and groups text-only optional themes before paid
generation. Replacements preserve scene intent and get fresh scene-consistency judgments.
The ordinary rollout switch leaves existing holds resolvable; shared-policy updates govern future
checks/releases with historical provenance. The agreed draft rubric is for ages 10–12.

The owner prioritized UX and existing patterns over further controls/frameworks. No new reviewer
service, mandatory written justification, per-picture optional-theme screening or creative
instructions. Complete policy/educator/ethics review, ADR amendments, privacy/retention,
resume/withdrawal contracts and verification remain blockers. No implementation, paid replay or
new tickets are authorized by this amendment; audit 01 and ticket 02 remain open.

### Scope boundary for the specification

- Rank 2 owns moderation evidence, written safety policy, flag handling, teacher inspection and
  resolution of safety holds, and the child states needed to wait, leave, return and recover.
  Necessary plain-language copy and accessibility belong to those states.
- Rank 3 owns editorial review feedback, comments and text highlights. Rank 2 does not add those
  tools. A safety hold is distinct from approval to share a completed book with classmates.
- Rank 4 owns child appearance prompts, custom prompts and instructions for rejected page images.
  Rank 2 does not add creative editing controls.
- Rank 5 owns general pipeline speed improvements; rank 2 measures moderation behavior and its
  observed cost or delay without taking on general performance work.
- Ranks 1, 6, 7 and 8 retain onboarding, roster views, AI-assisted editorial review and story
  construction quality respectively. Researcher access under ADR-079 supports investigation;
  it does not introduce AI-assisted review or automatic gallery approval.
- The parent phase requires conflicting features to be off by default and ethics re-review before
  real-child use. Teacher-review invariants about hidden review states and no recovery authority
  need explicit, narrowly scoped amendments for safety holds; editorial behavior is not redesigned.
- Audit ticket 01 is still open. Historical observations and uninspected runs do not establish
  present false-alarm rates or justify a classifier/prompt change. No implementation in this session.

### Edge cases to resolve before specification completion

- Exact withdrawal/containment contracts after a mistaken release; complete policy definitions
  and review; missing/unreliable classifier reasoning. Agreed UX is moderation-stack AC-10/AC-19.
- A teacher decision applies only to the exact held text/image version; changed or replacement
  content needs its own checks. Double clicks, two tabs, stale decisions and interrupted requests
  must not duplicate paid work or release a different asset.
- Resume preserves completed work and does not re-bill earlier draws; an unavailable checkpoint
  must not silently restart the book. Historical failed runs are not automatically resumable holds.
- A primary classifier error, backstop error, malformed response or missing verdict is distinct
  from an actual safety flag. fal may refuse before an image exists, leaving no picture to release.
- A failed privacy check prevents persistence. Flagged titles currently have no job, and flagged
  reference paths are cleared by existing code; preserving reviewable evidence needs explicit design.
- A held picture cannot be loaded, signed, or inspected; budget is exhausted; a replacement flags
  again; or a later scene creates another hold after an earlier teacher release.
- No teacher acts, the child leaves/returns, the classroom owner loses access, a student is removed,
  or the story/classroom is deleted while a review or generation is pending.
- The teacher or child stops the held story: child copy and recovery contracts must be defined
  without adding rank 3 comments/highlights or rank 4 creative controls. Child stop retaining
  writing is agreed; stop/release races and held-state deletion compatibility remain unresolved.
- Waiting/error/empty/disabled states, phone layouts, keyboard/focus and return navigation; flagged
  content stays hidden from the child before authorized release. Safety release is not gallery approval.
- Off-by-default behavior, existing jobs, setting changes during a hold, and ethics re-review before
  real-child use. No time-based automatic release or exemption from existing deletion rules.

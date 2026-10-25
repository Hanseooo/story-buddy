# Post technical defense: map

**Opened:** 2026-10-25 · **Milestone:** November 2026 (final defense or manuscript deadline, not yet
confirmed) · **Freeze point:** tag `technical-defense-2026-10` on `3049323`, the version the panel saw.

This is the context record for the phase. It holds the panel's suggestions, the decisions made about
them on 2026-10-25, and the ranked epics. Findings live in each epic's audit ticket, not here.

## Panel suggestions

Recorded as the owner reported them after the technical defense. All came from the panel except the
two marked *owner*.

- **Onboarding for children.** A forced password change after the teacher-issued secret word, plus
  other first-use UX where it helps.
- **Current password.** Changing a password asks for the current one.
- **Roster card/table toggle.** Teachers adding and managing students can switch between cards and a
  table. Cards stay the default on mobile.
- **AI-assisted approval.** The teacher reviews only the books the AI is unsure about. It is a toggle,
  so the teacher can keep reviewing everything.
- **Moderation rubrics.** Text and image moderation was too strict during the defense.
- **Feedback on approve and reject.** "Reject" sounds harsh to a child. Children see feedback, and
  teachers can comment on stories.
- **Highlights with tooltips** *(owner)*. Teachers highlight or underline phrases and attach a note
  ("change this phrase to…"). Must work on mobile.
- **Child control over appearance.** The child can prompt adjustments to a character's appearance,
  and can say how a rejected page image should look.
- **Teacher decides on moderation flags.** A flagged run waits for the teacher to let it continue or
  stop, because the pipeline raises false alarms.
- **Custom prompts.** Whether letting the child write prompts is a good idea at all.
- **Story construction quality.** How the model analyzes the story and builds the page text.
- **Speed.** Can the pipeline be faster? *(owner)* False alarms versus infrastructure is one
  hypothesis to test, not the frame of the investigation.

## Decisions (2026-10-25)

1. **UX first, no scope creep.** Each epic builds only what its spec asks for.
2. **Audit before build.** Every epic starts with `01`, a `Type: research` audit, then `02`, a
   `Type: grilling` session that ends in a spec. Build tickets are written only after the spec
   exists.
3. **Audits cost $0 by default.** A paid probe is proposed with its cost and approved by the owner
   one at a time.
4. **Every audit ends with** findings labelled *measured* or *inferred*, options with their
   tradeoffs, a cost estimate, and a go/no-go.
5. **Pipeline changes are allowed after the freeze tag.** Each one gets a row in
   `docs/capstone/research-changelog.md`, because the evaluated corpus and audits describe the
   pipeline as it was at defense.
6. **Items that conflict with an accepted ADR or the child-safety rules get their full version.**
   They are built behind a setting that is off by default. An ethics re-review comes before real
   children use them.
7. **Conflict gate.** A ticket with a `Conflict gate:` line touches an accepted ADR or a child-safety
   rule. Before any grill, brainstorm, design or build on it, the agent names the conflict to the
   owner and waits for the owner's verdict. `AGENTS.md` carries a temporary pointer to this rule.

## Epics, ranked

The rank orders building. Audits read code and data, so a lower-ranked audit can run whenever there is
time.

| Rank | Epic | Covers | Conflict gate | Waits on |
|---|---|---|---|---|
| 1 | [ptd-account-onboarding](../ptd-account-onboarding/map.md) | Forced password change, current password, first-use onboarding | — | — |
| 2 | [ptd-moderation-calibration](../ptd-moderation-calibration/map.md) | Written moderation policy, false-alarm rate, teacher-held flagged runs | ADR-011, child-safety rules | — |
| 3 | [ptd-review-feedback](../ptd-review-feedback/map.md) | Gentler wording, feedback children see, teacher comments, highlights | Teacher-review spec §12–13 | — |
| 4 | [ptd-child-creative-control](../ptd-child-creative-control/map.md) | Appearance prompts, child input on a rejected page, custom prompt verdict | ADR-029 §2, ADR-069 | Rank 2's audit, before any child free text ships |
| 5 | [ptd-pipeline-speed](../ptd-pipeline-speed/map.md) | Where a run's time goes and what shortens it | — | — |
| 6 | [ptd-roster-views](../ptd-roster-views/map.md) | Card/table toggle for teachers | — | — |
| 7 | [ptd-ai-assisted-review](../ptd-ai-assisted-review/map.md) | AI sorts the review queue; teacher reviews the unsure books | ADR-017, teacher-review spec | Rank 2's audit, rank 3's spec |
| 8 | [ptd-story-quality](../ptd-story-quality/map.md) | How `analyze` and `segment` read the story and build pages | ADR-013, only if the child's words would be rewritten | — |

## Workflow per epic

1. Claim `01`, run the audit, append `## Answer`, resolve it, and summarize it in the epic's map.
2. The owner reads the audit. A no-go closes the epic as `wontfix` with the reason.
3. Run `02`. A gated epic starts with the conflict warning. The grill ends in a spec: an amendment
   to the existing spec named in the ticket, or a new one from `docs/specs/TEMPLATE.md`.
4. Write the build tickets from the spec as `03` onward, each `Blocked by` `02`.
5. Build, verify on the real app, and add a changelog row if the pipeline changed.

## Closing the phase

The phase closes when every epic is built or closed `wontfix`. Then remove the conflict-gate line from
`AGENTS.md` and mark this map closed.

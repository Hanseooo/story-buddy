# ADR-082 — Magic pencil: child edits and other versions

**Status:** Accepted (2026-11-01) · the owner opened the ADR-029 §2 / ADR-069 conflict gate, took every
recommendation in the interview and the spec, and approved the spec. Synthetic-only and off by default;
ethics re-review before real children; pencil free text ships only after `ptd-moderation-calibration`
audit 01. Implemented behind the setting (tickets 03–11, 2026-11-03); migrations 0027–0032 not yet
applied and the US-01–US-05 browser pass pending.

**Amends:** ADR-029 §2 (what a reveal change is, and the unconditional overwrite) and ADR-069 (chips are
the only child input; the description is never extended). Specified by
[`docs/specs/magic-pencil.md`](../../specs/magic-pencil.md).

## Context

A reveal tap is one fresh text-to-image draw that overwrites the reference (ADR-029 §2). It can fix the
chosen detail and break others; the owner saw a "blue shirt" draw turn the skin blue. Pages cannot be
changed by the child at all. The defense panel asked for child control over appearance and pages.

Evidence (`docs/capstone/model-probes-2026-10.md`): editing the shipped reference with change-phrased
instructions fixed 5 of 9 count misses and carried onto 5 of 6 pages; editing with only the chip's
wording fixed 2 of 9 (2026-11-01). The reference checker wrongly fails about 4 in 10 clean
references. Children's own wording is untested, and the owner chose not to fund more probes.

## Decision

1. **Other versions.** Unchosen reference draws are kept, and a character's earlier pictures in the
   book stay available. Every scene attempt is already kept. A child may pick any of these; each is
   moderated before display, once, and a failure is skipped without a hold.
2. **Pencil.** The child writes a change (about 200 characters, any language, sent as written after
   PII redaction and moderation). The current picture is edited once; the child keeps the result or
   goes back. This replaces ADR-029 §2's unconditional overwrite for the pencil. "Draw again" still
   overwrites, but the old picture remains a version.
3. **No checker on the child's choice.** Pencil results get moderation, not the consistency or
   reference judge.
4. **Child changes extend canon for this book.** A kept character pencil text is stored apart from the
   analysed description and rendered into later scene prompts through ADR-035's style filter. This
   amends ADR-069's "not a second author of canonical identity" for the child only; machine
   interpretation still never rewrites the description.
5. **Allowance.** 3 character goes shared by "Draw again" and the pencil (unchanged prelude); 5 page
   pencils per book inside `IMAGE_BUDGET`.
6. **Scope.** Only on jobs submitted in `teacher_review_v1` with the new setting on, so every flag has
   an ADR-080 hold. A page change returns an approved or rejected book to pending.
7. **Baseline fix.** A moderation redraw of a tapped reference in a baseline job keeps the tapped chip
   (closes `reference-moderation-retry.md` §8.1). Not behind the setting.

## Alternatives rejected

- A blank custom prompt that draws a new picture: discards the story and canon; prompts are an adult
  skill.
- A tap that edits with only the chip's wording: failed its screen, 2 of 9.
- Pausing the run per page at its retry cap: more waiting, and ADR-003 keeps one pause point.
- Judging pencil results: brings back checker false alarms on what the child asked for.
- Translating Filipino/Taglish text first: a second model rewriting the child's words.

## Consequences

- The pencil ships unmeasured on children's wording; every use is logged so real use can measure it.
- New job-owned table for pencil logs and kept pictures; additive `StoryMemory` fields with defaults.
- The evaluated corpus, stage audit and judge dataset describe the pipeline without these tools;
  `build_corpus` never exercises them. Each pipeline change gets a `research-changelog.md` row.

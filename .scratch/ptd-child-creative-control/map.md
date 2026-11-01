# ptd-child-creative-control: map

**Phase:** [Post technical defense](../post-technical-defense/map.md), rank 4

**Conflict gate:** ADR-029 §2 (the reveal redraw is a fresh draw) and ADR-069 (redraw chips are
emphasis choices). Before any grill, brainstorm, design or build here, name the conflict to the owner
and wait for the verdict.

**Waits on:** the `ptd-moderation-calibration` audit, before any free text from a child ships.

Panel suggestions: the child prompts adjustments to a character's appearance, the child says how a
rejected page image should look, and a verdict on whether custom prompts are a good idea.

## Tickets

| # | Ticket | Type | Progress | Blocked by |
|---|---|---|---|---|
| 01 | [Audit: what a child can change today](issues/01-audit-child-creative-control.md) | research | resolved | — |
| 02 | [Grill: appearance and page input → spec](issues/02-grill-creative-control-spec.md) | grilling | resolved | 01 (rank 2's audit gates shipping free text only, owner 2026-11-01) |
| 03 | [Baseline: flagged "Draw again" redraw keeps the chip](issues/03-baseline-redraw-keeps-tapped-chip.md) | task | resolved | — |
| 04 | ["Draw again" is undoable: character versions at the reveal](issues/04-draw-again-undoable-at-reveal.md) | task | resolved | — |
| 05 | [Unchosen first-round pictures, moderated on open](issues/05-unchosen-draws-moderated-on-open.md) | task | resolved | — |
| 06 | [Character magic pencil at the reveal](issues/06-character-pencil-at-reveal.md) | task | open | 04 |
| 07 | [Held character pencil result: replacement re-runs the edit](issues/07-held-character-pencil-replacement.md) | task | open | 06 |
| 08 | [Kept character change reaches later pages](issues/08-kept-change-reaches-later-pages.md) | task | open | 06 |
| 09 | [Other versions of a page on the finished book](issues/09-page-other-versions.md) | task | open | 04 |
| 10 | [Page magic pencil on the finished book](issues/10-page-pencil-on-finished-book.md) | task | open | 09 |
| 11 | [Held page pencil result: replacement re-runs the edit](issues/11-held-page-pencil-replacement.md) | task | open | 10 |

**Build tickets (2026-11-01).** Cut from [`docs/specs/magic-pencil.md`](../../docs/specs/magic-pencil.md).
Owner rulings at breakdown: OD-07 (page pencil holds reuse `job_moderation_reviews`, job stays
`complete`) and OD-08 (a stop on a held character pencil text ends only the request), recorded in
spec §7. Release gates unchanged: off by default, synthetic-only, free text ships after rank 2 audit 01.

## Answers

**01 (2026-11-01).** [Audit](issues/01-audit-child-creative-control.md#answer-2026-11-01-0-no-model-calls):
today a child controls only 3 chip redraws at the reveal and no pages. Recommended: keep the
child's chip through a moderation flag (A1), make taps edits of the reference if a $0.27 screen
passes (A2), and a chips-only redraw of a finished page (P1), all behind the off-by-default
setting. Free text and custom prompts: no-go for this milestone, mainly because a child's text
would change the reference but not the description the pages are drawn from. Owner has not ruled.

**02 (2026-11-01, resolved).** Spec approved and ADR-082 accepted. Owner opened the gate and agreed the magic pencil (other versions
plus a write-a-change edit, at "Meet your characters" and on the finished book). Draft spec:
[`docs/specs/magic-pencil.md`](../../docs/specs/magic-pencil.md). The A2 screen failed, 2 of 9.

**03 (2026-11-01, resolved).** [Answer](issues/03-baseline-redraw-keeps-tapped-chip.md#answer-2026-11-01):
a flagged "Draw again" picture in baseline is redrawn once from the tap's recorded prompt, chip kept;
untapped flags and teacher-review unchanged.

**04 (2026-11-01, resolved).** [Answer](issues/04-draw-again-undoable-at-reveal.md#answer-2026-11-01):
behind `ENABLE_MAGIC_PENCIL` on teacher-review jobs, "Draw again" keeps the replaced picture and the
child can choose it back at no image or go cost. Table `job_picture_records` added. No browser pass;
teacher-allowed pictures are never kept as versions (a teacher can withdraw only the current one).

**05 (2026-11-01, resolved).** [Answer](issues/05-unchosen-draws-moderated-on-open.md#answer-2026-11-01):
feature jobs keep the mint's unchosen draws; opening "Other versions" moderates each once in the API.
Flags hidden with no hold, errors not stored. Migration 0028. No browser pass.

# 01 — Audit: teacher student views

**Status:** ready-for-agent
**Type:** research
**Progress:** open
**Blocked by:** None
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Question

Which teacher screens list students as cards, and what would a card/table toggle need on each?

## Starting evidence (2026-10-25)

- After adding students, the login slips render as a card grid
  (`frontend/app/classroom/[classroomId]/add/page.tsx:196`), with a two-column print layout.
- The bulk-add preview is already a table (`add/page.tsx:247`), so a table pattern exists to reuse.
- The class roster is `frontend/app/classroom/[classroomId]/page.tsx`. Its layout was not checked.

## Investigate

- Every teacher screen that lists students or books, and which ones the panel meant.
- The row actions each table needs (reset, remove, restore), and their keyboard reach.
- Where the chosen view is remembered (per device is enough unless the audit says otherwise).
- `DESIGN.md` and `docs/MOBILE_GUIDELINES.md` rules for tables on narrow screens.

## Edge cases the answer must cover

- Printing the slips stays cards, whatever the view.
- A table on a phone: the toggle hidden, or a table that scrolls?
- A class of 40+ students.

## Done when

- Findings are labelled *measured* or *inferred*, with file references.
- Options with tradeoffs, cost estimate and a go/no-go.

## Comments

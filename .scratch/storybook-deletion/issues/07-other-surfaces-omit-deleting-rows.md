# 07 — Teacher, gallery and research surfaces omit deleting rows

**Source spec:** `docs/specs/storybook-deletion.md` §4.3, §6, §9.33
**Implementation plan:** not required — implement directly.
**Blocked by:** 01
**Status:** ready-for-agent

## What to build

The moment a book enters deletion it silently disappears from every non-owner surface — peer gallery,
teacher review and books, and research metrics — and a teacher can no longer approve or reject it.

RLS already revokes access (ticket 01); this ticket makes the application queries agree explicitly, so
a surface never depends on a policy alone to hide a row, and a teacher never sees an approve/reject
control that will affect zero rows.

Teacher surfaces lose the child-owned row without ceremony — no tombstone, no "deleted by student"
notice.

## Acceptance criteria

- [ ] Peer gallery queries exclude `deleting` rows.
- [ ] Teacher review and books queries exclude `deleting` rows and expose no approve/reject control for them.
- [ ] Research metrics queries exclude `deleting` rows.
- [ ] `pnpm lint && pnpm test` green from `frontend/`, output shown; backend suite green if backend queries changed.

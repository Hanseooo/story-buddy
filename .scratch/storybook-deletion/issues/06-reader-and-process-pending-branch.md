# 06 — Reader and process routes: deletion-pending branch

**Source spec:** `docs/specs/storybook-deletion.md` §4.2, §9.32
**Implementation plan:** not required — implement directly.
**Blocked by:** 05
**Status:** ready-for-agent

## What to build

A child who is already sitting on a book's reader or process page when it enters deletion sees the
same pending state as on the bookshelf, with a way back, instead of a half-rendered book.

Both routes branch on the deletion-pending result added to `useJob.classify` in ticket 05 and render
the pending state plus a return-to-bookshelf action. They never render captions, images, retry,
confirm or review actions for a `deleting` job.

## Acceptance criteria

- [ ] Reader route renders the deletion-pending state with a return-to-bookshelf action and no book content.
- [ ] Process route does the same and offers no retry or confirm action.
- [ ] `pnpm lint && pnpm test` green from `frontend/`, output shown.

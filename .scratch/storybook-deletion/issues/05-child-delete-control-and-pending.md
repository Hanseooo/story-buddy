# 05 — Child delete control, confirmation, and pending/retry state

**Source spec:** `docs/specs/storybook-deletion.md` §4.2, §4.3, §9.27–31
**Implementation plan:** required — write `docs/specs/plans/storybook-deletion-05-child-surface.md` first, then a lighter agent implements it.
**Blocked by:** 03
**Status:** ready-for-agent

## What to build

A child can delete one of their own finished, failed or paused books from the bookshelf, is warned
once that it is irreversible and that approved books also leave the class gallery, and then watches a
clear pending card that either disappears on its own or offers a retry — never a raw backend error.

- Complete, failed and `paused` cards expose a keyboard-accessible delete button separate from the
  card link, with a 44px target and the existing `ConfirmDialog`'s native dialog semantics and focus
  handling. `paused` is the frontend bucket for persisted `status='awaiting_confirm'` — not a sixth
  database status. Queued/running cards expose no delete.
- Cancel changes nothing. Confirm calls the authenticated FastAPI DELETE exactly once.
- After `202` the card becomes a non-navigable `Deleting…` card.
- While a tombstone exists the surface reselects that job every two seconds while the page is active.
  A missing row removes the card. Still present after ten seconds → the card offers
  `Try deleting again`, which repeats the same DELETE; polling continues while the page is active.
- `404` after a retry means cleanup already finished → remove the card. `409` keeps the original book
  state and explains that a book still being made cannot be deleted yet. On `503` or any uncertain
  response the client reselects the row: `deleting` enters pending UI, any other status preserves the
  original book. Other errors follow the same reselect rule and stay retryable.
- `useJob.classify` gains an explicit deletion-pending result instead of falling through to failure.
- The bookshelf's Realtime subscription handles the `deleting` UPDATE; final removal is confirmed by
  the bounded reselect above, **not** by a filtered DELETE subscription.

Failure states get the same design care as success states: a failed book gets the same delete control
and the same kid-legible pending copy as a completed one.

## Acceptance criteria

- [ ] Only complete, failed and `paused` cards expose delete; clicking it does not follow the card link.
- [ ] Cancel changes nothing; confirm calls authenticated FastAPI DELETE once.
- [ ] `202` renders non-navigable pending UI; reselecting a missing row removes the card.
- [ ] Pending retry repeats DELETE; `404` removes the card; `409` restores and explains the original state.
- [ ] `503` or an uncertain response reselects the row and renders pending when it is `deleting`; failures stay retryable with no raw error text.
- [ ] `useJob.classify` returns an explicit deletion-pending result.
- [ ] `pnpm lint && pnpm test` green from `frontend/`, output shown.

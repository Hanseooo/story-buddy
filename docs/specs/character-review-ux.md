# Feature Spec — Understandable character redraws

**Status:** implemented 2026-09-10; interaction design approved 2026-09-09.
**Owner:** `frontend/app/s/[profileId]/process/[jobId]/page.tsx`, existing reveal view.
**Derived from:** [pause lifecycle](kid-flow-pause-lifecycle.md),
[reader and wait states](kid-flow-reader-and-wait-states.md),
[ADR-029](../product/adr/ADR-029-the-character-reveal-an-effect-free-pause-node-a-child.md),
[ADR-041](../product/adr/ADR-041-character-names-are-not-canonical-visual-identity.md),
[DESIGN](../../DESIGN.md).

## 1. Purpose and accepted decisions

A child understands that a trait asks for a new picture emphasizing that detail.
Selecting a trait spends nothing. An explicit **Redraw [name]** starts the redraw,
which replaces the current picture and may change other details. Preserve existing
worker-provided suggestions and the shared three-redraw budget. Continue uses
**Use these characters**, avoiding a claim that the pictures are perfect.

No old/new chooser, undo after dispatch, typed correction, additional traits, prompt
change, extra draw, new modal, or changed moderation/acceptance policy. This spec owns
the reveal interaction amendment; backend pause/retry contracts remain authoritative.

## 2. Existing contract and corrected assumptions

`backend/pipeline/reveal.py:_project_reveal` provides `characters[]` with `char_id`,
`name`, `image_path`, `chips`, plus book-wide `taps_left`. `_chips` supplies missing
visual axes when available, otherwise all filtered visual axes; when no axes survive,
ADR-041 supplies `overall physical appearance`. These are suggestions, not a definitive
list of defects. The earlier discussion's “only missing traits” description was too
narrow. Keep this actual behavior unchanged.

`backend/pipeline/char_bible.py:_mint_targeted` generates a new picture from the
description with `Be sure to include: [attribute]`, replaces the chosen character's
reference, updates its verdict/cost, and clears its moderation status. The generated
picture passes through character moderation before another reveal. Other details can
change; no improvement is guaranteed and no earlier picture is offered back.

Keep `POST /jobs/{id}/confirm` unchanged:

- redraw: `{action: "try_again", char_id, attribute}`;
- continue: `{action: "confirm", char_id: null, attribute: null}`.

The server owns allowed attributes, pause claiming, resume enqueue, and the cap.
Local selection is ephemeral UI state, not another persisted contract. Existing
row refresh/subscription behavior remains the source of job progress.

## 3. Screen and interaction

Keep character pictures/names prominent and use existing Cobalt Playroom components
and tokens. Show the book title as context per [story titles](story-titles.md) §5.
Instruction: **“Choose a detail you want us to try drawing again.”**

1. Each supplied trait is a native button with visible selected styling and
   `aria-pressed`. Allow one selection across the screen: a character ID and trait.
   Selecting another replaces it. Selecting the same trait again clears it.
2. No request, counter decrement, or picture change occurs on selection.
3. Under the selected character, show:
   **“We'll draw a new picture, paying extra attention to [trait]. Other details may change.”**
   Place **Redraw [name]** next to this explanation. It is unavailable without a
   valid selection. A visible **Cancel** clears selection without a request.
4. Show **“3 redraws left for this book”**, **“2 redraws left for this book”**, or
   **“1 redraw left for this book”**, using server `taps_left`, with supporting text
   “Shared by all your characters.” Never imply a per-character allowance.
5. Redraw activation dispatches the existing request once. Immediately disable
   trait/redraw/continue submissions and announce **“Redrawing [name]…”**. Retain
   local pending identity while the existing page transitions through queued/running.
   After a refresh without that context, use truthful generic character progress.
6. After the next authoritative reveal, clear selection, show the newly moderated
   picture, and display the returned allowance. Do not decrement locally or show a
   success claim merely because the confirm request returned HTTP 200.
7. **Use these characters** sends confirm and proceeds. If a selection is still
   present, this uses the current pictures and discards the unsubmitted selection;
   state nearby “Continue with the pictures shown.” It never implicitly redraws.
8. **Back to bookshelf** stays available. Leaving does not cancel accepted backend
   work. A not-yet-submitted selection is discarded and may be chosen again on return.

No old-image/new-image comparison. While waiting, any retained old moderated picture
is visibly labeled as the previous picture, not the result. Never show an unmoderated
replacement, even as a preview.

## 4. Empty, capped, error, and stale states

| State | Required behavior |
|---|---|
| `taps_left == 0` | Explain “No redraws left for this book. You can use these characters or go back to your bookshelf.” No redraw control; continue and exit remain. |
| Empty chips on an otherwise valid character | Defensive UI: “No suggested changes are available for this character.” Keep continue/exit. Do not invent traits or change `_chips`; normal backend fallback is nonempty. |
| No characters | Preserve backend skip-reveal behavior; do not introduce an empty confirmation screen. |
| Picture signing/loading failure | Show an inline image error and retry the read. Do not spin indefinitely, spend a redraw, or silently confirm pictures the child cannot inspect. Keep exit available; disable continue until required pictures load. |
| Confirm/redraw request fails | Show “We couldn't send that choice. Please try again.” Refresh the row before enabling another submission; retain selection only if it is still offered in the same pause. |
| Server already accepted the action | Follow refreshed queued/running/terminal state, do not resubmit automatically. HTTP success may mean another tab claimed the pause. |
| New reveal / trait removed / budget consumed in another tab | Clear invalid selection, use current chips and allowance, and explain that the character choices updated when needed. |
| Generated replacement is blocked | Follow the existing terminal failure path and the specific character-picture explanation in `story-failure-recovery-ux.md`. Never reveal that image. |

If a failed request cannot be reconciled because row refresh also fails, keep an
inline read-retry action and exit. Do not encourage a second paid action against an
unknown pause. Preserve existing server race/idempotency handling without redesign.

## 5. Keyboard, focus, and accessibility

Trait buttons support Tab, Enter, and Space. Enter/Space selects only; it must not
also trigger redraw. Escape clears an unsubmitted selection, without cancelling
accepted work or intercepting unrelated page controls. Cancel provides the same
operation for touch users. Selection is conveyed through text/state, not color alone.

After selection, keep focus on the trait; put explanation and redraw next in sensible
reading/tab order. Pending status uses a polite live region. On replacement, focus
the updated character heading when focus would otherwise be lost; do not steal focus
from a child actively navigating elsewhere. Failed dispatch announces an alert.
Retain visible focus, 44px targets, reduced motion, mobile wrapping of long trait/name
text, and usability at 200% zoom. No hover-only instructions.

## 6. Cross-cutting checklist

- [x] CC-1: existing moderation before initial/replacement display.
- [x] CC-3: explicit paid action, server allowance, no increased retry budget.
- [x] CC-4: same closed-set endpoint and signed images, no free-text prompt channel.
- [x] CC-5: no new logging of names/traits, existing request telemetry retained.
- [x] CC-6/CC-8/CC-9: understandable consequences, accessible states and recovery.
- [x] CC-10: existing paused job/resume path, current row wins over stale selection.
- CC-2/CC-7: no new authored content, seed, judge, or research changes.

## 7. Verification and completion

Extend the existing `process/[jobId]/page.test.tsx` tests. Replace the old expectation
that tapping a chip posts immediately. First show the new interaction test failing
against that behavior, then implement. Reuse existing reveal fixtures and mock the
network boundary, not internal selection helpers.

Main path: selecting a trait makes zero requests; explicit redraw sends exactly the
existing payload; duplicate activation while pending sends no second request; a new
reveal clears selection and displays server allowance. Critical failure path: failed
dispatch followed by a refreshed already-consumed pause does not spend another redraw.
Extend existing cases for cap, confirm payload, image-read error, and empty chips as
needed rather than creating new test infrastructure. Existing backend reveal/confirm
tests remain evidence that the contract and cap are unchanged.

Manual QA covers one/two characters, one/zero attempts, long traits, Cancel/Escape,
keyboard-only use, slow redraw, failed image reads, and returning from bookshelf.
The child should be able to explain that a new picture will replace this one and that
the allowance is shared. Do not assert the image actually improves in deterministic
tests or add a new model-quality evaluation claim.

When implemented, update `kid-flow-reader-and-wait-states.md` §4.2 to point here for
interaction rules and retire immediate-tap UI requirements/tests. Do not alter
`kid-flow-pause-lifecycle.md` or ADR-029 backend mechanics to fit a UI preference.
Run from `frontend/`: `pnpm lint`, `pnpm build`, `pnpm test`. If backend code changes
are proposed, stop and establish why this frontend-only contract needs that expansion.

**Next gate:** manual QA — one/two characters, one/zero attempts, long traits, Cancel/Escape,
keyboard-only use, slow redraw, failed image reads, and returning from bookshelf.

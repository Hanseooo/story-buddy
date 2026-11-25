# UI audit: items deferred after the batch 1-4 review

Status: needs-triage
Type: task
Progress: open

The UI/UX audit (2026-11-25) shipped in batches 1-4 plus the review fixes of 2026-11-26 (see
CHANGELOG). These items were checked against the code and left open on purpose.

## Open P1s (user-visible)

- **`/book` for a paused or in-flight job** gets no `router.replace` to the process screen.
- **`useJob.ts` sends `readFailed` to "terminal-failure"**, so a failed read shows the failed-book screen.
- **Tablet `StudentHeader` links** lack `min-h-11` and `aria-current`.
- **`/write` keyboard squeeze** on phones.
- **HeldStory header is not sticky**, so its only way out scrolls off-screen.
- **`BookReviewDialog`** enables decisions before pages load, and its toast can cover the footer.
- **Roster Remove** drops focus to `<body>`.
- **`RowMenu` and `ClassroomSwitcher`** have no Escape and no focus handling.

## Batch 5 candidates (no user-visible defect today)

- **One shared Dialog.** The book-page confirms, the `/write` dialogs, the reset slip and the fullscreen picture repeat
  the open, close and focus-return code. The `/write` "Start over" dialog matches `ConfirmDialog`.
  `docs/MOBILE_GUIDELINES.md` prefers bottom sheets; none of the dialogs is one.
- **Toast class.** Four teacher pages repeat the same toast class and use `z-50` while `--z-toast` exists.
- **Show-password toggle.** The same markup appears in login, signup and join.
- **Ring overrides.** 13 files override the global focus outline with `outline-none ring-*`. The audit asked for them to be removed. A
  `globals.css` rule now gives them the two-tone ring instead.

## Left as is, with reasons

- **Page-version confirms focus "Change page N" first.** This follows `docs/specs/magic-pencil.md`
  SH-07: "Opening a tool moves focus to its first control". The book page tests assert it. The change
  is reversible: the teacher re-approves it.
- **Drawing bar stops at (n-1)/n.** The worker reports `min(done+1, n)`, and the screen moves on
  once the last picture is done.
- **Fullscreen picture alt is "Picture for page N".** The page caption is already read next to it.
- **Known deferrals:** viewport-fit=cover; the sessionStorage signed-URL cache on retry; avatar
  category names; `isolate` in the student layout; the display-name `<label>`.

## Comments

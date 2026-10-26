# Show and remember the student navigation introduction

**Status:** needs-info
**Type:** task
**Progress:** open
**Parent:** [Ticket 02](02-grill-onboarding-spec.md)
**What to build:** Eligible students see one short dismissible introduction, remembered across devices and retained through reset/restoration.
**Source criteria:** [Account onboarding](../../../docs/specs/account-onboarding.md) US-05 AC-14–AC-16, dismissal preservation in AC-02, SH-03–SH-07, OD-05.
**Scope:** Approved introduction route, eligibility/routing, caller-owned dismissal, save failure and accessible exits.
**Out of scope:** Password completion/enforcement and persistence foundation, owned by 05. Navigation redesign, authoring tutorials and guided tours.
**Complexity:** Medium — eligibility, concurrent dismissal, failure recovery and shared-device separation interact.
**Blast radius:** Local — bounded student introduction using the approved profile interface.
**Unblocks:** [07](07-verify-hosted-onboarding-rollout.md).

## Context

The existing `/welcome` is a public role chooser. It is not the authenticated introduction. See spec US-05, OD-05 and ADR-074/077.

## Read first

- `docs/specs/account-onboarding.md` — US-05, OD-05 and accepted routing contract from 03.
- `frontend/components/StudentTabBar.tsx` — `StudentTabBar`: Bookshelf/Gallery/Profile vocabulary.
- `frontend/app/s/[profileId]/layout.tsx` — `StudentLayout`: student identity and shell.
- `frontend/app/s/[profileId]/settings/page.tsx` — password and Log out destinations.
- Migration 0021 public.dismiss_student_introduction() — caller-owned monotonic RPC, implemented.

## Behavior this changes

First trusted completion adds the introduction before the own bookshelf. No existing introduction tests were identified.

## Acceptance criteria

- [ ] Explain Bookshelf, Gallery and Profile, including password change and Log out, using approved copy and audience styling.
- [ ] Provide “Go to my bookshelf” and the approved alternative dismissal control, both leading to the student's own shelf.
- [ ] Persist caller-owned dismissal independently of password-required state. Verify cross-device retention and isolation between students sharing a browser.
- [ ] Reset/restore preserves dismissal. Legacy eligibility follows 03's accepted initialization rule without interrupting rollout access.
- [ ] Dismissal failure follows the approved retry/continue behavior, announces persistence uncertainty and never claims a false save or blocks password completion.
- [ ] Pending/disabled, loading/error, focus/announcements, Tab/Enter/Escape, visible focus and 44px targets satisfy SH-03–SH-06. Provide required async route loading/error files.
- [ ] Preserve safe redirects, identity/expiry/logout behavior and existing empty shelf/gallery states.

## Guidance

Reuse the trusted persistence seam from 05. Browser memory cannot establish cross-device dismissal.

## Verification

Exercise rendered content/exits and persistence failure using existing infrastructure and failing-test-first. Verify independent students and devices against real saved state.

**Targeted:** `pnpm exec vitest run 'app/s/[profileId]/introduction/Introduction.test.tsx'` from `frontend/`.
**Full suite:** Frontend `pnpm lint`, `pnpm build`, `pnpm test` at the batch gate. Backend `uv run ruff check .`, `uv run pytest` if this slice changes its persistence boundary.

## Blocked by

[03](03-approve-onboarding-contracts.md): approved UI/dismissal contract.
[05](05-enforce-required-password-replacement.md): trusted completion/dismissal foundation.

## Comments

### Implementation update - 2026-10-26

Introduction route and component now explain the three destinations, save either exit through caller-owned dismiss_student_introduction(), and provide explicit continuation after a save failure. Eligibility excludes legacy 0/0 and already-dismissed students. Reset/restore preserve dismissal. Loading/error/logout and pending states ship. Device/accessibility and real cross-device acceptance remain open.

Commands and measured results: account-onboarding spec section 1. Acceptance checkboxes remain open for the stated evidence limits. No commit or hosted deployment was made.

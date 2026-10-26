# Enforce required password replacement with recoverable completion

**Status:** needs-info
**Type:** task
**Progress:** open
**Parent:** [Ticket 02](02-grill-onboarding-spec.md)
**What to build:** New/reset/restored students remain blocked across every product boundary until trusted replacement completes, including recovery after partial failure.
**Source criteria:** [Account onboarding](../../../docs/specs/account-onboarding.md) US-01 AC-01–AC-05, US-02 AC-06–AC-08, required-flow AC-09/AC-10, US-04 AC-12/AC-13, SH-01–SH-08, §7 generator recommendation.
**Scope:** Approved migration/backfill, provisioning/reset/restore, middleware, required/recovery UI, trusted completion, API/RLS/Storage/Realtime enforcement and applicable real-boundary checks. Include protected dismissal storage/interface needed by 06.
**Out of scope:** Ordinary settings forms, owned by 04. Introduction UI, owned by 06. Worker cancellation, draft deletion, new image transport and research changes.
**Complexity:** High — Auth/profile coordination, concurrent resets and recovery must preserve one security invariant.
**Blast radius:** System-wide — affects student entry, product requests, direct database access and private assets.
**Unblocks:** [06](06-student-navigation-introduction.md), [07](07-verify-hosted-onboarding-rollout.md).

## Context

Navigation currently admits authenticated students without onboarding state. FastAPI and direct Supabase access have independent enforcement boundaries. Lifecycle, recovery and enforcement form one complete slice under ADR-073–078. Introduction eligibility/routing must leave the complete batch compatible with 06 before release.

## Read first

- `backend/app/classrooms.py` — `_create_one`, `reset_student`, `restore_student`: lifecycle writes.
- `backend/app/wordlist.py` — `mint_password`: shared issued-word generator.
- `frontend/middleware.ts` — `middleware`, `guardRequest`: page entry.
- `frontend/app/s/[profileId]/layout.tsx` — `StudentLayout`: identity reads and friendly recovery.
- `backend/app/main.py` — `create_storybook`, `confirm_job`, `update_avatar`: privileged product operations.
- `backend/app/pdf_export.py` — `download_pdf`: download release boundary.
- `supabase/migrations/0008_authorization_surface.sql` — student policies, reviewed with subsequent migrations.
- `backend/tests/test_rls_isolation.py` — classroom/profile/image policy precedents.

## Behavior this changes

AC-01/AC-06 overturn unconditional authenticated entry asserted in `frontend/middleware.test.ts`. Lifecycle assertions in `backend/tests/test_main.py` must include protected requirement state. Existing RLS own/peer access remains available only after completion or legacy exemption.

## Acceptance criteria

- [ ] New accounts require replacement. Existing accounts remain exempt until reset/restore. Every later reset/restore reinstates the requirement and preserves dismissal and unrelated profile facts.
- [ ] Handle failed provisioning/reset/restore according to 03's approved ordering contract without accidental product access.
- [ ] Use standard-library `secrets` for issued-word choices and digits while preserving the current word list and `word-word-NN` format.
- [ ] Required UI identifies the student, explains replacement and teacher recovery, requires current-word proof and a distinct acceptable replacement, and exposes visible Log out.
- [ ] Middleware redirects blocked deep links, bookmarks, Back and hostile `next` attempts without loops. Missing/invalid/unavailable state fails closed with retry/logout.
- [ ] Current profile authority denies blocked product API operations, direct product data, new signatures and newly authorized Realtime events, including old sessions. Check before side effects and download release.
- [ ] Direct profile writes, editable metadata, browser state, submitted target IDs and stale JWT claims cannot clear or bypass the requirement.
- [ ] After a confirmed password save but failed completion, remain blocked and permit now-current-password retry without another change. Reconcile unknown outcomes using approved durable evidence.
- [ ] Replays, lost responses, refresh and concurrent tabs cannot grant premature access. Older completion cannot clear a newer reset.
- [ ] Apply SH-02–SH-07 credential handling, hidden labeled controls, pending/disabled states, safe errors, keyboard/focus/announcements, audience styling, expiry recovery and shared-device logout safeguards. Provide required async route loading/error states.
- [ ] Preserve running jobs/checkpoints and drafts. Do not replay interrupted paid actions. Preserve existing role/classroom restrictions after completion.
- [ ] Verify ADR-078: old image links retain only original expiry within one hour of issuance, with no renewal while blocked. Exercise actual signing and Realtime boundaries.
- [ ] Establish the approved per-profile dismissal persistence/interface for 06 without making dismissal a security prerequisite.

## Guidance

The profile upsert follows Auth creation because the trigger can initially see empty metadata. Policies are permissive in combination. Updating only one student policy or only middleware cannot establish enforcement. No necessary prefactor was identified. Schema/API/auth work requires the approvals obtained by 03, not merely ticket publication.

## Verification

Use failing-test-first at rendered UI/middleware and FastAPI boundaries, mocking only outer services. Exercise real policies, signing and sockets in an authorized disposable environment. Default-skipped RLS tests do not establish acceptance.

**Targeted:** Frontend: `pnpm exec vitest run middleware.test.ts 'app/join/[code]/page.test.tsx' app/auth/signout/route.test.ts lib/signedUrls.test.ts`, plus new required-flow tests. Backend: `uv run pytest tests/test_main.py tests/test_avatar.py tests/test_pdf_export.py tests/test_rls_isolation.py`, plus selected completion tests. Run each from its project directory.
**Full suite:** Frontend `pnpm lint`, `pnpm build`, `pnpm test`. Backend `uv run ruff check .`, `uv run pytest`. Real authorization evidence is also required before this slice closes.

## Blocked by

[03](03-approve-onboarding-contracts.md): approved protocol/schema/API/enforcement/UI contracts. Real-boundary acceptance also requires separately authorized test access.

## Comments

### Generator subset implemented — 2026-10-26

At the owner's instruction to implement immediately, `mint_password` now uses `secrets.choice` and `10 + secrets.randbelow(90)`. Word list and `word-word-NN` format are preserved. Existing generator/provisioning/restore checks: `uv run pytest tests/test_main.py -k 'mint_password or bulk_create or restore'` → 6 passed, 56 deselected. No new test was added for the mechanical RNG replacement.

The required-flow lifecycle, state schema, completion protocol and authorization work remain unimplemented and blocked by 03. This subset does not resolve the ticket.

Full backend checks: `uv run ruff check .` passed. `uv run pytest` reported 1,514 passed, 87 skipped, 6 deselected and 6 failed in `tests/test_pdf_export.py`. Those PDF cases returned 503 while expecting 200, 409 or 404 because the PDF renderer raised `OSError`. Independent `uv run python -c "import weasyprint"` confirmed `cannot load library 'libgobject-2.0-0': error 0x7e`. No PDF code or system dependency was changed. An initial sandbox import check failed on uv cache initialization; the approved unsandboxed import reached the missing-library error. Skipped suites do not establish RLS or hosted enforcement.

### Implementation update - 2026-10-26

Migration 0021, banned-first provisioning, versioned reset/restore, caller-owned password/state endpoints, required screen with lost-response reconciliation, middleware/API/RLS/Storage gates and export recheck are implemented. The real local SQL tests cover completion, stale/direct writes, reset/restore, private-RPC denial and Storage gating. Actual Auth, independent-connection races, signing and sockets remain unverified.

Commands and measured results: account-onboarding spec section 1. Acceptance checkboxes remain open for the stated evidence limits. No commit or hosted deployment was made.

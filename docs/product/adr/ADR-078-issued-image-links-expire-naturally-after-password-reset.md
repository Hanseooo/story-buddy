# ADR-078 — Issued image links expire naturally after password reset

**Status:** Accepted (2026-10-26), owner confirmation during account-onboarding blocker review.

**Context:** [ADR-073](./ADR-073-students-replace-teacher-issued-passwords-before-product-access.md)
requires product restriction after a teacher reset, including existing sessions. The existing student
image helper and gallery issue signed URLs with a one-hour lifetime. A profile gate can deny new
signatures but cannot make an already issued URL consult current profile state. The owner accepted
natural expiry after this limitation and the alternative transport change were explained.

**Decision:** Narrow ADR-073's reset boundary for previously issued image links only. Once reset
establishes required-change state, deny new authorized product operations, including protected
page/data/API access, new image signatures and newly authorized Realtime product events. Previously
issued image links may continue to retrieve their image until their original expiry, at most one
hour after issuance. Reset neither extends nor renews those links. Already delivered or cached bytes
cannot be recalled. Required password change and logout remain available.

Keep [ADR-006](./ADR-006-supabase-for-auth-db-storage-realtime.md)'s private Storage and signed-URL
delivery. Do not introduce an authenticated image proxy for this feature. The exception does not
permit new links, public buckets, broader classroom access, product navigation or password-gate
bypass. It does not change the existing moderation and asset-authorization requirements.

**Rationale and tradeoffs:** Retain the existing delivery mechanism and avoid extra image-request
latency and transport scope. Accept bounded access to images through links obtained before reset.
This is not a claim of immediate asset revocation or remote deletion of downloaded content.

**Verification required:** After a reset, test that an existing link remains usable only until its
original expiry, fresh signatures and protected product operations are denied, and product access
returns only after trusted password completion. Exercise old sessions and actual Realtime sockets.
The decision does not establish implemented or hosted behavior.

**Sources:** [Account-onboarding spec](../../specs/account-onboarding.md),
`frontend/lib/signedUrls.ts`, `frontend/app/s/[profileId]/gallery/page.tsx`, and
[Supabase private downloads](https://supabase.com/docs/guides/storage/serving/downloads)
(reviewed 2026-10-26). No code, schema, Auth setting or API changed with this record.

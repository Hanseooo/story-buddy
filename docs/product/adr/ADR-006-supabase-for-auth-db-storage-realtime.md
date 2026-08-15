# ADR-006 — Supabase for Auth + DB + Storage + Realtime

**Status:** Accepted · ⚠️ **the auth *role model* below (parent → kid) is superseded by ADR-017**
(teacher → classroom → student). The platform choice, RLS posture, and everything else stand.

**Context:** Need parent accounts, kid profiles, generated-image storage, live progress, and strict data isolation for a children's product — fast, solo.

**Decision:** Use **Supabase** for Postgres (app data + LangGraph checkpoints), **Auth** (classroom-scoped accounts — teacher/BEED-student issuer, child/student rows as the current role model; originally parent accounts + kid profiles, see status line), **Storage** (images + PDFs via signed URLs), and **Realtime** (job progress). Enforce **Row-Level Security** so a classroom's data is isolated from every other classroom, and a child's account from another child's within it.

**Consequences:** Large portion of the stack handled by one service; RLS gives DB-layer data isolation (correct design + strong paper point). Vendor dependency on Supabase.

**Alternatives:** Roll-your-own auth/storage — more control, much more work, weaker safety story. Firebase — comparable but less Postgres/RLS-native.

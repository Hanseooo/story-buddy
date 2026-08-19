# 02 — Annotation UI Hardening, Server Invariants & 3-Tier Blinding Verification

**What to build:**
Harden the Next.js `/annotate` route and server actions (`frontend/app/(research)/annotate/`). Fix broken imports (`createSupabaseServerClient`), correct role checks on `profiles.role`, enforce server-side validation invariants, implement per-annotator pseudo-random presentation order, and restrict adjudicators from ordinary annotator queues (`Annotator A != Annotator B != Adjudicator`).

**Key Architectural Invariants:**
1. **Server-Side Invariant Validation:**
   - `same_character = true` REQUIRES `failure_reasons = []`.
   - `same_character = false` REQUIRES `failure_reasons.length >= 1`.
   - `anatomy_intact` (bool) and `text_free` (bool) must be explicitly provided (no undefined values).
   - Double-submit handled with first-write-wins idempotency (`ON CONFLICT DO NOTHING`).
2. **Distinct Role Isolation:**
   - Adjudicator accounts (`profiles.is_adjudicator = true`) are blocked from submitting ordinary annotations on `/annotate`.
3. **Reproducible Randomized Presentation:**
   - Replace sequential `ORDER BY created_at` in `getNextPair()` with reproducible pseudo-random or hash-shuffled ordering per annotator to prevent context/expectancy effects.
4. **Strict Blinding Payload:**
   - Server actions return ONLY `{ pair: { id, canonical_signed_url, scene_signed_url } }`.
   - `char_id`, `split`, `is_pilot`, `is_constructed_negative`, and storage paths are never delivered to the client.

**Blocked by:** 00-preflight-migration-verification (can develop against mocked `getNextPair()` until 01 completes)

**Status:** ready-for-agent

### Checklist & Assertions:
- [ ] Fix Supabase client imports to use `createSupabaseServerClient` and query `profiles.role`.
- [ ] Block `is_adjudicator = true` users from `/annotate`.
- [ ] Implement server-side validation for `same_character`, `failure_reasons`, `anatomy_intact`, and `text_free`.
- [ ] Implement randomized/shuffled pair assignment per annotator in `getNextPair()`.
- [ ] Handle UI states: queue-empty/done state, loading transitions, keyboard shortcuts (1-7, A, T, Enter), and double-submit prevention.
- [ ] **3-Tier Test Suite:**
  - *Tier 1 (UI / Component Tests - Vitest):* Verify form state transitions, disabled checkboxes when Same Character, done state, and assert NO metadata (`char_id`, `split`, story titles, model verdicts) in DOM.
  - *Tier 2 (Server Action Unit Tests - Vitest):* Verify allowlisted payload, invariant rejection, and signed URL generation.
  - *Tier 3 (DB / RLS Integration Tests - pytest):* Verify ordinary researchers cannot SELECT `research_pairs`, cannot view other annotators' rows, and cannot update `is_adjudicator`.

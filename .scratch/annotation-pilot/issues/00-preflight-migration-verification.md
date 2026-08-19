# 00 — Preflight Migration & Environment Verification

**What to build / verify:**
Before executing implementation tickets, verify that the database schema, RLS policies, storage bucket, and test accounts are correctly established in Supabase. In this repository, SQL migrations are not self-applying; this checklist guarantees the underlying foundation matches all architectural assumptions.

**Blocked by:** None — must be verified before running tickets 01, 02, and 08.

**Status:** ready-for-agent

### Checklist & Assertions:
- [ ] **Migration 0014 (`0014_annotations.sql`):**
  - Verify `annotations` table exists with columns: `pair_id` (text), `annotator_id` (uuid), `same_character` (bool), `anatomy_intact` (bool), `text_free` (bool), `failure_reasons` (text[]), `created_at` (timestamptz).
  - Verify primary key is composite `(pair_id, annotator_id)`.
  - Verify closed 7-item check constraint `annotations_failure_reasons_closed`.
  - Verify own-rows RLS policy for `auth_role() = 'researcher'`.
- [ ] **Migration 0016 (`0016_research_pairs_and_adjudicator.sql`):**
  - Verify `profiles.is_adjudicator` (boolean, default false) exists.
  - Verify `research_pairs` table exists with `id`, `char_id`, `split`, `is_constructed_negative`, `status`.
  - Verify adjudicator read-all policy on `annotations`.
- [ ] **Migration 0017 (`0017_research_pair_blinding.sql`):**
  - Verify `canonical_storage_path` and `scene_storage_path` exist on `research_pairs`.
  - Verify `is_pilot` (boolean, default false) exists on `research_pairs`.
  - Verify legacy `canonical_image_url` and `scene_image_url` are dropped.
  - Verify direct `SELECT` policy on `research_pairs` is revoked for ordinary researchers.
  - Verify `profiles` update policy is restricted to service role only.
- [ ] **Test Accounts Provisioning:**
  - Provision **Annotator A**: `role = 'researcher'`, `is_adjudicator = false`
  - Provision **Annotator B**: `role = 'researcher'`, `is_adjudicator = false`
  - Provision **Adjudicator**: `role = 'researcher'`, `is_adjudicator = true`
- [ ] **Storage Bucket Verification:**
  - Verify private bucket `private_assets` exists with RLS enabled (signed URLs only, no public reads).

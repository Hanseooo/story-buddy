-- 0017_research_pair_blinding.sql
-- Resolves data blinding requirements for the annotator flow
-- Removes direct SELECT access to research_pairs for ordinary researchers
-- Transitions from persistent URLs to storage paths to enforce signed-URL usage
-- Adds is_pilot flag for safer development/testing

-- 1. Modify research_pairs schema
ALTER TABLE research_pairs
  DROP COLUMN canonical_image_url,
  DROP COLUMN scene_image_url,
  ADD COLUMN canonical_storage_path text NOT NULL DEFAULT '',
  ADD COLUMN scene_storage_path text NOT NULL DEFAULT '',
  ADD COLUMN is_pilot boolean NOT NULL DEFAULT false;

-- Remove the default now that columns are added
ALTER TABLE research_pairs
  ALTER COLUMN canonical_storage_path DROP DEFAULT,
  ALTER COLUMN scene_storage_path DROP DEFAULT;

-- 2. Revoke direct SELECT policy from ordinary researchers
-- We drop the permissive policy that allows researchers to read everything including char_id
DROP POLICY IF EXISTS "researchers read research_pairs" ON research_pairs;

-- 3. Adjudicator flag protection
-- No ordinary researcher should be able to make themselves an adjudicator.
-- Since profiles currently has NO update policies for anyone, it is already safe.
-- But let's add a restrictive policy just to be explicit that NO ONE can update it via API except service role.
-- (Supabase implicitly denies UPDATE if no policy exists, so this is just documentation/hardening).
CREATE POLICY "service_role only updates profiles"
  ON profiles FOR UPDATE TO authenticated
  USING (false) WITH CHECK (false);

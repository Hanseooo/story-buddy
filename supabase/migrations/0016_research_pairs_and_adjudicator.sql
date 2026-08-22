-- 0016_research_pairs_and_adjudicator.sql
-- Resolves DECISION_BACKLOG D-K (Where the pair queue lives)
-- Resolves DECISION_BACKLOG D-L (How an adjudicator is identified)

-- 1. Identify Adjudicators (D-L)
-- We add an is_adjudicator flag to profiles. Only researchers should have this set to true.
ALTER TABLE profiles ADD COLUMN is_adjudicator boolean NOT NULL DEFAULT false;

-- Add the missing read-all policy for adjudicators on the existing annotations table
CREATE POLICY "adjudicators read all annotations"
  ON annotations FOR SELECT TO authenticated
  USING (
    auth_role() = 'researcher' AND 
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND is_adjudicator = true)
  );


-- 2. The Pair Queue (D-K)
-- A new table to hold the queue of image pairs to be annotated.
-- id is text to match annotations.pair_id (which is opaque and minted by python script)
CREATE TABLE research_pairs (
  id text PRIMARY KEY,
  canonical_image_url text NOT NULL,
  scene_image_url text NOT NULL,
  char_id text NOT NULL, 
  split text NOT NULL CHECK (split IN ('train', 'val', 'test')),
  is_constructed_negative boolean NOT NULL DEFAULT false,
  status text NOT NULL DEFAULT 'pending', -- pending, partially_annotated, complete, conflicted, adjudicated
  created_at timestamptz DEFAULT now()
);

ALTER TABLE research_pairs ENABLE ROW LEVEL SECURITY;

-- All researchers need to read the pairs to fetch their next assignment
CREATE POLICY "researchers read research_pairs" 
  ON research_pairs FOR SELECT TO authenticated 
  USING (auth_role() = 'researcher');

-- Service role or specifically authorized scripts will insert pairs, so no insert policy is strictly needed for the UI.
-- However, we will allow adjudicators to update status if needed.
CREATE POLICY "adjudicators update research_pairs"
  ON research_pairs FOR UPDATE TO authenticated
  USING (
    auth_role() = 'researcher' AND 
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND is_adjudicator = true)
  );

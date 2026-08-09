-- 0009: add avatar_id to profiles.
-- Null is the default and stays meaningful: it renders the letter avatar.
-- No CHECK constraint — the allowed set changes as the set is curated;
-- validation is at the API boundary (regex) and at render (AVATAR_IDS allowlist).
alter table profiles add column avatar_id text;

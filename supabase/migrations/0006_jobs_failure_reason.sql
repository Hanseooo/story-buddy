alter table jobs
  add column if not exists failure_reason text;
-- null is valid for rows created before this migration (pre-enum rows fall to retry in the UI,
-- per spec §4.2 invariant 3). No check constraint: unknown future values must not be DB-rejected.

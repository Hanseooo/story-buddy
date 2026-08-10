alter table jobs
  add column image_count       integer,
  add column regen_count       integer,
  add column ref_retry_count   integer,
  add column scenes_total      integer,
  add column scenes_passed     integer,
  add column scenes_failed     integer,
  add column scenes_unchecked  integer,
  add column usd_estimate      numeric(8,4),
  add column langfuse_trace_url text;

-- supabase/migrations/0002_jobs_style_preset_id.sql
-- style-presets spec: additive, non-breaking nullable column.
-- Existing rows default to NULL; the worker resolves NULL → "cel" (ADR-022's flagship default).
alter table jobs
  add column if not exists style_preset_id text
    check (style_preset_id in ('cel', 'comic', 'gouache'));

-- supabase/migrations/0015_add_cut_paper_style_preset.sql
-- ADR-042 §10: promote cut_paper as the third selectable preset.
-- The existing constraint enumerates values; this replaces it to include cut_paper.
-- Existing rows are untouched — comic, cel, gouache, and null all remain valid.
alter table jobs
  drop constraint if exists jobs_style_preset_id_check;

alter table jobs
  add constraint jobs_style_preset_id_check
    check (style_preset_id in ('cel', 'comic', 'gouache', 'cut_paper'));

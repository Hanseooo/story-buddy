-- C3-13 / #98: allow the pixel trial preset. The API only accepts it when ENABLE_PIXEL_STYLE is
-- set (backend/app/config.py), so this widens what the table can hold, not what users can pick.
-- Existing rows are untouched — comic, cel, gouache, cut_paper, and null all remain valid.
alter table jobs
  drop constraint if exists jobs_style_preset_id_check;

alter table jobs
  add constraint jobs_style_preset_id_check
    check (style_preset_id in ('cel', 'comic', 'gouache', 'cut_paper', 'pixel'));

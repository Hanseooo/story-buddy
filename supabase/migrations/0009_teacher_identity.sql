-- 0009_teacher_identity.sql
-- spec: docs/specs/teacher-privileged-writes-and-identity.md §4.1, §4.5
-- Part 1: trigger fix. Part 2 appends the revoke/grant block.

-- ── 1. Repair handle_new_user ─────────────────────────────────────────────────
-- Two load-bearing changes from 0007:
--   • coalesce(app_meta ->> 'role', 'teacher'): absent app_metadata → teacher.
--     raw_user_meta_data is client-controlled so it is never read for role.
--   • display_name is role-conditional: profiles_role_shape requires NULL for
--     students; an unconditional fallback would break provisioning.

create or replace function public.handle_new_user() returns trigger
  language plpgsql security definer set search_path = '' as $$
declare
  v_role text := coalesce(new.raw_app_meta_data ->> 'role', 'teacher');
begin
  insert into public.profiles (id, role, classroom_id, nickname, display_nickname, display_name)
  values (new.id,
          v_role,
          (new.raw_app_meta_data ->> 'classroom_id')::uuid,
          new.raw_app_meta_data ->> 'nickname',
          new.raw_app_meta_data ->> 'display_nickname',
          case when v_role = 'student' then null
               else coalesce(new.raw_app_meta_data  ->> 'display_name',
                             new.raw_user_meta_data ->> 'display_name',
                             split_part(new.email, '@', 1))
          end);
  return new;
end $$;

-- ── 2. Narrow jobs UPDATE surface ────────────────────────────────────────────
-- RLS cannot restrict which columns an UPDATE touches (0008:50).
-- Column privileges are checked before policies; this makes S3-8 true in the
-- database rather than by convention. service_role is unaffected — the revoke
-- names authenticated only, and service_role bypasses both layers.

revoke update on public.jobs from authenticated;
grant  update (approved_at) on public.jobs to authenticated;

-- Backfill profiles for auth.users rows created while on_auth_user_created was
-- absent. The trigger fires on INSERT only, so applying 0007/0009 to a project
-- that already has users leaves those accounts permanently profile-less —
-- they authenticate fine and then fail every RLS-scoped read.
--
-- The projection mirrors handle_new_user() in 0009 line for line, so backfilled
-- rows are indistinguishable from trigger-created ones. Keep them in sync: a
-- divergence here shows up as a role or display_name that only reproduces for
-- accounts made during the drift window.

insert into public.profiles
  (id, role, classroom_id, nickname, display_nickname, display_name)
select
  u.id,
  coalesce(u.raw_app_meta_data ->> 'role', 'teacher'),
  (u.raw_app_meta_data ->> 'classroom_id')::uuid,
  u.raw_app_meta_data ->> 'nickname',
  u.raw_app_meta_data ->> 'display_nickname',
  case
    when coalesce(u.raw_app_meta_data ->> 'role', 'teacher') = 'student' then null
    else coalesce(
           u.raw_app_meta_data  ->> 'display_name',
           u.raw_user_meta_data ->> 'display_name',
           split_part(u.email, '@', 1)
         )
  end
from auth.users u
left join public.profiles p on p.id = u.id
where p.id is null
on conflict (id) do nothing;

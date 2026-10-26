-- supabase/migrations/0021_account_onboarding.sql
-- docs/specs/account-onboarding.md §7; ADR-073–ADR-078.
-- Account-onboarding transaction boundary. Deploy only with the matching server
-- password/reset paths. Existing direct Auth password updates will be rejected.
-- Local SQL checks do not establish hosted Auth compatibility.
begin;

alter table public.profiles
  add column password_reset_version bigint not null default 0,
  add column password_completed_version bigint not null default 0,
  add column introduction_dismissed_at timestamptz,
  add constraint profiles_password_versions check (
    password_completed_version >= 0 and password_reset_version >= password_completed_version
  );

create schema onboarding_private;
revoke all on schema onboarding_private from public, anon, authenticated;
create table onboarding_private.password_operations (
  profile_id uuid primary key references public.profiles(id) on delete cascade,
  operation_id uuid not null unique,
  kind text not null check (kind in ('change', 'reset', 'restore')),
  reset_version bigint not null
);
alter table onboarding_private.password_operations enable row level security;
revoke all on onboarding_private.password_operations from public, anon, authenticated;

-- Only the server reserves an operation, before checking the current password.
-- A new reservation invalidates earlier work. A pending reset cannot be replaced
-- by a student change: its old password could still be valid in Auth.
create function public.begin_password_operation(p_user_id uuid, p_kind text)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  p public.profiles%rowtype;
  prior_kind text;
  receipt uuid := gen_random_uuid();
begin
  if p_kind is null or p_kind not in ('change', 'reset', 'restore') then
    raise check_violation using message = 'invalid_password_operation';
  end if;
  select * into p from public.profiles where id = p_user_id for update;
  if not found or (p.removed_at is not null and p_kind <> 'restore')
    or (p.role = 'student' and p.classroom_id is null)
    or (p_kind <> 'change' and p.role <> 'student') then
    raise check_violation using message = 'account_unavailable';
  end if;
  select kind into prior_kind from onboarding_private.password_operations where profile_id = p_user_id;
  if p_kind = 'change' and prior_kind in ('reset', 'restore') then
    raise check_violation using message = 'password_reset_pending';
  end if;
  if p_kind in ('reset', 'restore') then
    update public.profiles set password_reset_version = password_reset_version + 1
      where id = p_user_id returning * into p;
  end if;
  insert into onboarding_private.password_operations values (p_user_id, receipt, p_kind, p.password_reset_version)
    on conflict (profile_id) do update set operation_id = excluded.operation_id,
      kind = excluded.kind, reset_version = excluded.reset_version;
  return receipt;
end $$;
revoke all on function public.begin_password_operation(uuid, text) from public, anon, authenticated;
grant execute on function public.begin_password_operation(uuid, text) to service_role;

-- Auth writes the password and metadata in separate statements inside one
-- transaction. Inspect the final row at commit, never an HTTP acknowledgement or
-- an external audit log. A fresh server-only receipt must accompany the write.
create function onboarding_private.finish_password_operation()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  p public.profiles%rowtype;
  op onboarding_private.password_operations%rowtype;
  receipt text;
begin
  select * into p from public.profiles where id = new.id for update;
  if not found then
    raise check_violation using message = 'password_operation_required';
  end if;
  select * into op from onboarding_private.password_operations where profile_id = new.id for update;
  if not found or op.reset_version <> p.password_reset_version then
    raise check_violation using message = 'password_operation_required';
  end if;
  select case when op.kind = 'change'
    then raw_user_meta_data ->> 'storybuddy_password_operation'
    else raw_app_meta_data ->> 'storybuddy_password_operation' end
    into receipt from auth.users where id = new.id;
  if receipt is distinct from op.operation_id::text then
    raise check_violation using message = 'password_operation_required';
  end if;
  if op.kind = 'change' then
    if p.removed_at is not null then
      raise check_violation using message = 'account_unavailable';
    end if;
    update public.profiles set password_completed_version = op.reset_version where id = new.id;
  elsif op.kind = 'restore' then
    update public.profiles set removed_at = null where id = new.id;
  end if;
  delete from onboarding_private.password_operations where profile_id = new.id;
  return null;
end $$;
revoke all on function onboarding_private.finish_password_operation() from public, anon, authenticated;
create constraint trigger storybuddy_password_committed
  after update of encrypted_password on auth.users
  deferrable initially deferred for each row
  when (old.encrypted_password is distinct from new.encrypted_password)
  execute function onboarding_private.finish_password_operation();

-- All existing student product policies use auth_role(). Keep the own identity
-- row available while denying product policies, including Storage and Realtime
-- SELECT authorization, against current database state.
create or replace function public.auth_role() returns text
language sql stable security definer set search_path = '' as $$
  select case when role = 'student' and (
    removed_at is not null or classroom_id is null or password_completed_version < password_reset_version
  ) then null else role end from public.profiles where id = auth.uid()
$$;
alter policy "students read own profile" on public.profiles using (id = auth.uid());

create function public.dismiss_student_introduction() returns void
language plpgsql security definer set search_path = '' as $$
begin
  update public.profiles set introduction_dismissed_at = coalesce(introduction_dismissed_at, now())
    where id = auth.uid() and role = 'student' and removed_at is null
      and classroom_id is not null and password_completed_version > 0
      and password_completed_version = password_reset_version;
  if not found then
    raise check_violation using message = 'introduction_unavailable';
  end if;
end $$;
revoke all on function public.dismiss_student_introduction() from public, anon;
grant execute on function public.dismiss_student_introduction() to authenticated;

commit;

create table classrooms (
  id         uuid primary key default gen_random_uuid(),
  code       text not null unique,
  name       text not null,
  owner_id   uuid not null,              -- FK added below, after profiles exists
  created_at timestamptz not null default now()
);

create table profiles (
  id               uuid primary key references auth.users(id) on delete cascade,
  role             text not null check (role in ('teacher','student','researcher')),
  classroom_id     uuid references classrooms(id) on delete cascade,
  nickname         text,   -- students only; normalized; IS the email localpart
  display_nickname text,   -- students only; what the teacher typed, what peers see
  display_name     text,   -- teachers and researchers
  created_at       timestamptz not null default now(),
  constraint profiles_role_shape check (
    (role = 'student'
       and classroom_id is not null and nickname is not null
       and display_nickname is not null and display_name is null)
    or
    (role in ('teacher','researcher')
       and classroom_id is null and nickname is null
       and display_nickname is null and display_name is not null)
  )
);

alter table classrooms
  add constraint classrooms_owner_fk
  foreign key (owner_id) references profiles(id) on delete cascade;

create unique index profiles_classroom_nickname
  on profiles (classroom_id, nickname) where role = 'student';

create function public.handle_new_user() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, role, classroom_id, nickname, display_nickname, display_name)
  values (new.id,
          new.raw_app_meta_data ->> 'role',
          (new.raw_app_meta_data ->> 'classroom_id')::uuid,
          new.raw_app_meta_data ->> 'nickname',
          new.raw_app_meta_data ->> 'display_nickname',
          new.raw_app_meta_data ->> 'display_name');
  return new;
end $$;

create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

create function public.handle_profile_deleted() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  delete from auth.users where id = old.id;
  return old;
end $$;

create trigger on_profile_deleted after delete on public.profiles
  for each row execute function public.handle_profile_deleted();

create function public.auth_role() returns text
  language sql stable security definer set search_path = ''
  as $$ select role from public.profiles where id = auth.uid() $$;

create function public.auth_classroom_id() returns uuid
  language sql stable security definer set search_path = ''
  as $$ select classroom_id from public.profiles where id = auth.uid() $$;

alter table classrooms enable row level security;
alter table profiles   enable row level security;
-- ponytail: no policies here. Default-deny is correct until S3 writes them;
-- 0007 and S3's policy migration ship together (spec §7 ⑤).

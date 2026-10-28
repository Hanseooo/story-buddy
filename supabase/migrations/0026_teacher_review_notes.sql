-- ADR-081 / teacher-review-and-approval §14. Teacher API only in this slice.
begin;
alter table public.classrooms
  add column review_notes_enabled boolean not null default false;
-- 0008 already allows classroom reads but no browser writes. Keep those policies.

create table public.job_review_notes (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs(id) on delete cascade,
  author_id uuid not null references public.profiles(id),
  body text not null,
  scene_id text,
  anchor jsonb,
  seen_at timestamptz,
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp()
);
create unique index job_review_notes_one_book on public.job_review_notes(job_id) where scene_id is null;
alter table public.job_review_notes enable row level security;
revoke all on public.job_review_notes from public, anon, authenticated;
grant all on public.job_review_notes to service_role;

-- PostgREST upsert cannot infer a partial index without its predicate. This
-- service-only function also serializes writes against the classroom switch.
-- SECURITY INVOKER: callers gain no privileges, even if grants later drift.
create function public.teacher_review_note(
  p_job_id uuid, p_teacher_id uuid, p_operation text, p_body text default null
) returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
  book public.jobs;
  classroom public.classrooms;
  note public.job_review_notes;
begin
  select * into book from public.jobs where id=p_job_id for update;
  if not found then
    return jsonb_build_object('status',404,'detail','not found');
  end if;
  select * into classroom from public.classrooms
    where id=book.classroom_id and owner_id=p_teacher_id for update;
  if not found then
    return jsonb_build_object('status',404,'detail','not found');
  end if;
  if p_operation not in ('GET','PUT','DELETE') or p_operation is null then
    return jsonb_build_object('status',422,'detail','invalid_operation');
  end if;
  if p_operation <> 'GET' and not classroom.review_notes_enabled then
    return jsonb_build_object('status',409,'detail','notes_disabled');
  end if;
  if p_operation='PUT' then
    if book.status <> 'complete' then
      return jsonb_build_object('status',422,'detail','book_not_complete');
    end if;
    -- Length is validated by FastAPI from MAX_REVIEW_NOTE_CHARS. The function
    -- is service-only, not a second public input boundary.
    insert into public.job_review_notes(job_id,author_id,body)
      values(p_job_id,p_teacher_id,p_body)
      on conflict (job_id) where scene_id is null do update
      set body=excluded.body, author_id=excluded.author_id,
          seen_at=null, updated_at=clock_timestamp()
      returning * into note;
  elsif p_operation='DELETE' then
    delete from public.job_review_notes where job_id=p_job_id and scene_id is null returning * into note;
    if not found then
      return jsonb_build_object('status',404,'detail','not found');
    end if;
    return jsonb_build_object('status',200,'note',null);
  else
    select * into note from public.job_review_notes where job_id=p_job_id and scene_id is null;
    if not found then
      return jsonb_build_object('status',404,'detail','not found');
    end if;
  end if;
  return jsonb_build_object('status',200,'note',to_jsonb(note));
end $$;
revoke all on function public.teacher_review_note(uuid,uuid,text,text) from public, anon, authenticated;
grant execute on function public.teacher_review_note(uuid,uuid,text,text) to service_role;
commit;

-- ADR-080: the serialized control worker anchors a withdrawal exactly once.
begin;
create or replace function public.protect_moderation_review() returns trigger
language plpgsql set search_path = '' as $$
declare mutable_fields text[] := array['decision','actor_id','decided_at','decision_policy_version',
  'confirmed_criteria','request_id','decision_epoch','dispatch_state','dispatch_kind','dispatch_error_code'];
begin
  if old.withdraws_review_id is not null and old.decision is null
     and old.checkpoint_id is null and new.checkpoint_id is not null
     and old.return_node = 'pending' and new.return_node in ('output_mod','generate_scene','consistency_check','reveal','compose','__end__')
     and (to_jsonb(new) - array['checkpoint_id','return_node']) = (to_jsonb(old) - array['checkpoint_id','return_node']) then
    return new;
  end if;
  if (to_jsonb(new) - mutable_fields) is distinct from (to_jsonb(old) - mutable_fields)
     or (old.decision is not null and
       (to_jsonb(new) - array['dispatch_state','dispatch_error_code']) is distinct from
       (to_jsonb(old) - array['dispatch_state','dispatch_error_code'])) then
    raise exception 'moderation review is immutable';
  end if;
  return new;
end $$;
commit;

-- supabase/migrations/0034_jobs_judge_choice.sql
-- judge-selector spec AC-10, ADR-087: the identity-judge choice, saved on the job at submit (SH-06).
-- Additive and non-breaking: existing rows take the default and read as 'gemma'.
alter table jobs
  add column if not exists judge_choice text not null default 'gemma'
    -- keep in sync with JUDGE_CHOICES in backend/app/config.py
    check (judge_choice in ('gemma', 'qwen_base', 'qwen_finetuned'));

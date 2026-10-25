# 01 — Audit: where a run's time goes

**Status:** ready-for-agent
**Type:** research
**Progress:** open
**Blocked by:** None
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Question

How long does a story take from submit to finished book, split by stage, and which causes account for
most of that time?

## Starting evidence (2026-10-25)

- Production records no per-stage timing. `jobs` has `created_at` and `updated_at`
  (`supabase/migrations/0001_jobs_table.sql`).
- The worker uses Langfuse (`backend/worker/run_job.py`). Span timings are a likely $0 source.
  *Inferred*, confirm what the traces hold.
- LangGraph checkpoints in Postgres may carry timestamps per step. *Inferred*.
- *Measured* (2026-10-11): 185 of 335 scene draws in the 30 synthetic books were redraws
  (`docs/capstone/research-changelog.md`).
- *Measured* (B6): 120 s primary-moderation timeouts happened 15+ times.
- Infrastructure: Northflank, Singapore, FastAPI web plus RQ worker plus Redis (`docs/TECH_STACK.md:42`).

## Candidate causes

Test each one against the data. None is assumed.

- Redraw loops (consistency retries, moderation redraws).
- Moderation timeouts, retries and false alarms that force redraws.
- Scenes running one after another.
- Provider queues and cold starts (fal, OpenRouter).
- Network distance between Singapore and the providers.
- Worker CPU (Presidio and spaCy are resident).
- Queueing when a whole class submits at once with one worker.
- Time the child spends at the reveal pause, which is human time. Report it separately from machine
  time.

## Edge cases the answer must cover

- A classroom burst of about 30 submissions at the end of a lesson.
- A run that resumes from a checkpoint after a crash.

## Done when

- A per-stage time breakdown on real runs, labelled *measured*, with run count and source.
- The causes ranked by share of time, with the ones the data could not test marked *inconclusive*.
- Options to shorten the top causes, each with tradeoffs, spend effect and any ADR it touches.
- Cost estimate and a go/no-go.

## Comments

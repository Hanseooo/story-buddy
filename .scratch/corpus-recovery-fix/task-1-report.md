# Task 1 — Corpus checkpoint recovery repair

## Scope

- Fixed point inspected: `1ea981d916f1667f43fe735530d17a7792617203`.
- Changed only `backend/finetune/build_corpus.py`, `backend/tests/test_finetune_corpus.py`, and `docs/specs/research-corpus-operations.md` for commit.
- Did not read `.env` files or access/mutate `syn-001`, provider APIs, Postgres, Storage, GPUs, or paid services.

## Root cause

Ticket 7 added checkpoint validation but `run_story()` still passed `_initial_state(story)` to every stream call. On an ordinary existing LangGraph thread this writes the fresh empty channels into the checkpoint, erasing recovered characters, locations, objects, timeline, scenes, and cost.

The builder also always reserved the entire story draw allowance. A resumed story with persisted attempts was therefore rejected even when its remaining draw allowance fit the campaign reserve.

## TDD evidence

1. Added a real `StateGraph` compiled with `MemorySaver`, preloaded a checkpoint with all affected channels, and interrupted at a reveal node.
2. Added budget regressions for prior completed, failed, and uncertain attempts plus the exact prior-limit boundary.
3. RED command:

   ```text
   cd backend && uv run pytest tests/test_finetune_corpus.py -k "ordinary_checkpoint or recovery_reserves_only or recovery_blocks_another_provider"
   4 failed, 1 passed
   ```

   The checkpoint test lost `characters`; each reserve test stopped before making its permitted remaining call.
4. Minimal implementation: use `None` only when the thread has checkpoint values; otherwise use `_initial_state(story)`. Calculate reserve from `max(story_draw_limit - persisted_attempted, 0)`; the existing event seam remains the hard limit.
5. GREEN command:

   ```text
   cd backend && uv run pytest tests/test_finetune_corpus.py -k "ordinary_checkpoint or recovery_reserves_only or recovery_blocks_another_provider"
   5 passed, 54 deselected
   ```

## Verification

- `cd backend && uv run pytest tests/test_finetune_corpus.py` — 59 passed.
- `cd backend && uv run ruff check .` — all checks passed.
- `cd backend && uv run pytest` — 1304 selected tests passed; 6 deselected and database-dependent tests skipped as configured.
- `git diff --check -- <three scoped files>` — clean.

## Review

- The real checkpoint regression proves channel preservation and that the reveal interrupt reaches the existing `Command(resume=CONFIRM)` continuation.
- Fresh fake corpus threads retain initial-state input coverage. Existing ordinary checkpoint threads now use `None`.
- Recovery retains prior telemetry, charges all terminal categories conservatively, permits only the remaining reserve, and blocks a provider attempt at the existing per-story limit.
- No architecture, dependency, schema, checkpoint reset, historical-fork, or retry-policy changes were introduced.

# Task 1: Repair corpus checkpoint recovery after Ticket 7

Fixed point: `1ea981d916f1667f43fe735530d17a7792617203`

## Requirements

1. Follow TDD. First add and run a focused regression that fails because `run_story()` sends `_initial_state(story)` into an existing checkpoint and overwrites checkpointed channels.
2. Use a compiled LangGraph `StateGraph` with `MemorySaver` (or an equally real in-process checkpointer path), not only an argument-recording fake. Prove checkpointed characters, locations, objects, timeline, scenes, and cost survive ordinary continuation.
3. Fresh corpus threads must receive `_initial_state(story)`.
4. Existing ordinary checkpoint threads must receive `None`, which the installed LangGraph runtime treats as continuation without mapping fresh input writes.
5. Reveal interrupts must continue through the existing `Command(resume=CONFIRM)` behavior. Add only the minimum test needed if existing coverage does not prove this distinction.
6. Add and observe a failing budget regression: recovery must reserve only `story_draw_limit - prior_attempted`, never decrement prior telemetry, and still charge completed, failed, and uncertain attempts conservatively. The next provider attempt remains blocked when prior attempted calls already equal the story limit.
7. Implement the minimum fix in `backend/finetune/build_corpus.py` and deterministic tests in `backend/tests/test_finetune_corpus.py`.
8. Update `docs/specs/research-corpus-operations.md` in the same change to state the ordinary-checkpoint input and remaining-reserve behavior.
9. Do not add a checkpoint reset, historical-fork CLI, provider retry, new dependency, schema change, or new architecture.
10. Do not touch or delete the existing `syn-001` filesystem, Storage assets, Postgres checkpoints, billing evidence, `.env`, secrets, held-out data, or unrelated dirty files. Make no provider, database, Storage, GPU, or paid calls.

## Verification

From `backend/`:

- Focused RED and GREEN commands targeting the new regression(s).
- `uv run pytest tests/test_finetune_corpus.py`
- `uv run ruff check .`
- `uv run pytest`

Commit only the three scoped implementation/test/spec files. Write the full implementation and TDD report to `.scratch/corpus-recovery-fix/task-1-report.md`.

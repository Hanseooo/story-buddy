# SDD ledger — plan: .scratch/corpus-recovery-fix/task-1-brief.md

Fixed point: 1ea981d916f1667f43fe735530d17a7792617203
Branch: main

| Tasks/interfaces checked | Producer | Consumer | Finding |
|---|---|---|---|
| Task 1 resume input | persisted LangGraph checkpoint | `run_story()` first stream call | Requirements distinguish fresh input, ordinary continuation, and interrupt resume consistently. |
| Task 1 recovery reserve | persisted per-story telemetry | campaign preflight and Fal event sink | Remaining reserve and cumulative spend share the existing counters; no contradictory requirement found. |
| Task 1 documentation | implementation and tests | operator recovery protocol | Owning spec must describe both behavior changes in the same commit. |

Task 1 preflight: clean. Existing `syn-001` recovery is deliberately out of scope and remains untouched.

Task 1: complete (commits 1ea981d..0b04569, task review and two-axis final review clean)

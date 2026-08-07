# Auth S1 — Sentinel Retirement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire the `dev-classroom` / `dev-profile` sentinel strings: widen the jobs SELECT, read real UUIDs from the row, delete the two settings fields, and update the affected tests.

**Architecture:** Three surgical file changes — `run_job.py` SELECT + constructor call, `config.py` field deletion, test assertion update. Nothing new is built; two things are deleted.

**Tech Stack:** Python 3.12 / uv / pytest.

## Global Constraints

> ⚠️ **BLOCKED — do not execute until S3 has applied the `jobs` ALTER:**
> ```sql
> alter table jobs
>   add column profile_id   uuid not null references profiles(id)   on delete cascade,
>   add column classroom_id uuid not null references classrooms(id) on delete cascade,
>   add column approved_at  timestamptz;
> ```
> Without those columns, the widened SELECT in Task 1 fails at runtime.

- `backend/contracts/` is frozen — no changes.
- The ~13 test files that use `"dev-classroom"` as a fixture string literal are **unchanged** — it is a valid `str` for `StoryMemory.classroom_id`, just not from `settings`. Only the two sentinel *settings fields* retire.
- Spec §6.4 lists exactly which lines change. Don't touch anything else.

---

## File Map

| Action | Path | Change |
|--------|------|--------|
| Modify | `backend/worker/run_job.py` | Widen SELECT (line ~85), read from row (lines ~99-100) |
| Modify | `backend/app/config.py` | Delete `dev_classroom_id` and `dev_profile_id` fields |
| Modify | `backend/tests/test_run_job.py` | Update mock + replace sentinel assertion (test 13) |
| Modify | `backend/tests/test_story_memory.py` | Delete sentinel value assertions (test 13) |
| Modify | `backend/tests/test_config.py` | Add test 14 (settings has no sentinel attributes) |

---

### Task 1: Widen SELECT and read from the row

**Files:**
- Modify: `backend/worker/run_job.py`
- Modify: `backend/tests/test_run_job.py`

**Interfaces:**
- Consumes: `jobs.profile_id` and `jobs.classroom_id` columns (added by S3's policy migration — must exist before this task runs).

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_run_job.py`, add this constant near the top (after existing imports):

```python
_FAKE_CLASSROOM_ID = "11111111-1111-1111-1111-111111111111"
_FAKE_PROFILE_ID = "22222222-2222-2222-2222-222222222222"
```

Update the existing `_fake_supabase` helper to return provenance fields (the widened SELECT will ask for them):

```python
def _fake_supabase(style_preset_id: str | None = None, truncated: bool = False) -> MagicMock:
    fake = MagicMock()
    select_chain = fake.table.return_value.select.return_value.eq.return_value.single.return_value
    select_chain.execute.return_value.data = {
        "input_text": "A dog runs in a field.",
        "style_preset_id": style_preset_id,
        "truncated": truncated,
        "profile_id": _FAKE_PROFILE_ID,
        "classroom_id": _FAKE_CLASSROOM_ID,
    }
    return fake
```

Replace the body of `test_run_storybook_job_constructs_story_memory_with_dev_provenance` (which asserts sentinel strings) with assertions against the row's UUID values. Rename it to reflect the intent:

```python
def test_run_storybook_job_constructs_story_memory_from_row():
    """spec §9 test 13: classroom_id and profile_id come from the job row, not settings."""
    fake_supabase = _fake_supabase()
    fake_checkpointer_cm = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    initial_state = fake_graph.stream.call_args.args[0]
    assert initial_state.classroom_id == _FAKE_CLASSROOM_ID
    assert initial_state.profile_id == _FAKE_PROFILE_ID
    assert initial_state.story_id == "job-1"
```

- [ ] **Step 2: Run the new test to confirm it fails**

```
cd backend && uv run pytest tests/test_run_job.py::test_run_storybook_job_constructs_story_memory_from_row -v
```

Expected: FAIL — `initial_state.classroom_id` is `"dev-classroom"`, not the fake UUID.

- [ ] **Step 3: Update `run_job.py`**

Two spots in `run_storybook_job`:

**Line ~85 — widen the SELECT:**
```python
# Before:
row = supabase.table("jobs").select("input_text, style_preset_id, truncated").eq("id", job_id).single().execute()

# After:
row = supabase.table("jobs").select("input_text, style_preset_id, truncated, profile_id, classroom_id").eq("id", job_id).single().execute()
```

**Lines ~99-100 — read from row, not settings:**
```python
# Before:
        classroom_id=settings.dev_classroom_id,
        profile_id=settings.dev_profile_id,

# After:
        classroom_id=row.data["classroom_id"],
        profile_id=row.data["profile_id"],
```

- [ ] **Step 4: Run the test to confirm it passes**

```
cd backend && uv run pytest tests/test_run_job.py::test_run_storybook_job_constructs_story_memory_from_row -v
```

Expected: PASS.

- [ ] **Step 5: Run the full `test_run_job.py` to confirm no regressions**

```
cd backend && uv run pytest tests/test_run_job.py -v
```

Expected: all green. Every other test uses `_fake_supabase()` which now returns the provenance fields — they should all still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/worker/run_job.py backend/tests/test_run_job.py
git commit -m "feat(auth-s1): run_job reads profile_id/classroom_id from job row (spec §9 test 13)"
```

---

### Task 2: Delete sentinel settings from `config.py`

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/tests/test_config.py`

**Interfaces:**
- Deletes: `dev_classroom_id: str` and `dev_profile_id: str` from `Settings`.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_config.py`, add at the end:

```python
def test_settings_has_no_dev_classroom_id():
    """spec §9 test 14: sentinel is retired."""
    assert not hasattr(settings, "dev_classroom_id")


def test_settings_has_no_dev_profile_id():
    """spec §9 test 14: sentinel is retired."""
    assert not hasattr(settings, "dev_profile_id")
```

- [ ] **Step 2: Run the new tests to confirm they fail**

```
cd backend && uv run pytest tests/test_config.py -v
```

Expected: 2 new tests FAIL (`settings` still has the attributes).

- [ ] **Step 3: Delete the two sentinel lines from `config.py`**

Remove these lines and their comment from `backend/app/config.py`:

```python
    # Phase-1 dev provenance sentinels (ADR-023 amendment 2026-07-22b). The worker supplies
    # story_id = job_id; these two stand in until `auth-and-classroom` lands. Swapping them for
    # real selection is a value change at one call site — never a contract change.
    dev_classroom_id: str = "dev-classroom"
    dev_profile_id: str = "dev-profile"
```

- [ ] **Step 4: Verify no remaining references to `dev_classroom_id` or `dev_profile_id`**

```bash
grep -rn "dev_classroom_id\|dev_profile_id" backend/
```

Expected: zero matches.

- [ ] **Step 5: Run the full backend suite**

```
cd backend && uv run ruff check . && uv run pytest
```

Expected: all green. (The `settings` import in `run_job.py` survives — it is still used for model IDs, style presets, and other settings.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat(auth-s1): retire dev_classroom_id / dev_profile_id from settings (spec §9 test 14)"
```

---

### Task 3: Delete `test_dev_provenance_sentinels_exist` from `test_story_memory.py`

**Files:**
- Modify: `backend/tests/test_story_memory.py`

**Interfaces:**
- Deletes: the entire `test_dev_provenance_sentinels_exist` function (lines 150–156). It imports `settings` and asserts the two sentinel values; once the settings fields are gone this test will fail with `AttributeError`.

The `_minimal()` fixture in `test_story_memory.py` passes `classroom_id="dev-classroom"` and `profile_id="dev-profile"` as **literal strings** — those stay. Only the function that asserts `settings.dev_classroom_id == "dev-classroom"` is removed.

- [ ] **Step 1: Delete the function**

Remove these exact lines from `backend/tests/test_story_memory.py` (lines 150–156):

```python
def test_dev_provenance_sentinels_exist():
    """Phase-1 sentinels (ADR-023 amendment 2026-07-22b). Replaced by real selection when
    `auth-and-classroom` lands — a value swap at one site in worker/run_job.py, no contract change."""
    from app.config import settings

    assert settings.dev_classroom_id == "dev-classroom"
    assert settings.dev_profile_id == "dev-profile"
```

Also remove the blank line immediately before the function if it creates a double-blank gap.

- [ ] **Step 2: Run the suite**

```
cd backend && uv run pytest tests/test_story_memory.py -v
```

Expected: all tests in the file PASS (the deleted function no longer appears).

- [ ] **Step 3: Run the full CI check**

```
cd backend && uv run ruff check . && uv run pytest
```

Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_story_memory.py
git commit -m "test(auth-s1): delete test_dev_provenance_sentinels_exist (spec §6.4)"
```

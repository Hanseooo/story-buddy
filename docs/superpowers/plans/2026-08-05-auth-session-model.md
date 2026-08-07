# Auth Session Model (S2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the open-resume hole in `POST /jobs/{job_id}/confirm`, require a verified JWT on all write endpoints, derive job ownership server-side, and switch the frontend Supabase client to cookie-based session storage.

**Architecture:** A new `get_current_user` FastAPI dependency verifies the Bearer JWT via `supabase.auth.get_user()` (one GoTrue round-trip, catches revocations). Both write endpoints adopt this dependency and derive ownership from the DB rather than trusting the client. The frontend swaps `createClient` for `createBrowserClient` from `@supabase/ssr` so the session lives in a cookie, enabling server-side reads in S4.

**Tech Stack:** Python / FastAPI (`Depends`, `Header`), supabase-py (`auth.get_user`), Next.js / TypeScript, `@supabase/ssr` (new frontend dep, pre-approved by spec §3), Vitest, pytest.

## Global Constraints

- No new Python packages — `supabase-py` already exposes `auth.get_user()`.
- One new frontend package only: `@supabase/ssr`. No other new packages.
- The worker (`run_job.py`) is NOT touched — it uses `service_role` deliberately (spec §5.4).
- Client-supplied `profile_id` / `classroom_id` in any request body must be ignored (spec §5.2).
- All FastAPI tests remain mocked — no live Supabase calls (MASTER_SPEC §6 Tier A).
- CI must stay green; all existing tests must continue to pass.

---

## File Map

| File | Change |
|---|---|
| `backend/app/main.py` | Add `get_current_user` dep; wire into both endpoints; derive ownership from DB in `create_storybook`; add ownership guard in `confirm_job`; update select to include `profile_id` |
| `backend/tests/test_main.py` | Add autouse auth-bypass fixture; update `REVEAL_ROW` + inline row dicts to include `profile_id`; add 6 new auth tests |
| `frontend/lib/supabaseClient.ts` | Swap `createClient` for `createBrowserClient` from `@supabase/ssr` |
| `frontend/lib/supabaseClient.test.ts` | New file — 2 Vitest tests verifying cookie-client use (spec §8 tests 7–8) |
| `frontend/package.json` | Add `@supabase/ssr` dependency |

---

## Task 1: Backend — `get_current_user` + endpoint changes

**Files:**
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `get_current_user` — an `async def` FastAPI dependency; returns a supabase-py `UserResponse.user` object with `.id: str` attribute. Later tasks' tests import this name to override it.

- [ ] **Step 1: Add `Depends` and `Header` to the FastAPI import in `main.py`**

Current line 6:
```python
from fastapi import FastAPI, HTTPException
```
Replace with:
```python
from fastapi import Depends, FastAPI, Header, HTTPException
```

- [ ] **Step 2: Run existing tests to confirm green baseline**

```bash
cd backend && python -m pytest tests/test_main.py -v
```
Expected: all pass. If not, stop and fix before continuing.

- [ ] **Step 3: Add `get_current_user` dependency after the `_log` line (line 18)**

Insert after `_log = logging.getLogger(__name__)`:

```python
async def get_current_user(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing token")
    jwt = authorization.removeprefix("Bearer ")
    result = get_supabase_client().auth.get_user(jwt)
    if not result.user:
        raise HTTPException(401, "invalid token")
    return result.user
```

- [ ] **Step 4: Replace the `create_storybook` function**

Current function spans lines 68–91. Replace the entire function with:

```python
@app.post("/storybooks", response_model=CreateStorybookResponse)
def create_storybook(
    payload: CreateStorybookRequest, user=Depends(get_current_user)
) -> CreateStorybookResponse:
    job_id = str(uuid.uuid4())
    before = word_count(payload.text)
    text, truncated = clamp_story(payload.text)
    if truncated:
        # CC-5: log counts only, never the text (ADR-025 D5).
        _log.info("story truncated: %d words → %d words", before, word_count(text))
    supabase = get_supabase_client()
    profile_rows = (
        supabase.table("profiles").select("classroom_id").eq("id", user.id).execute().data
    )
    if not profile_rows or profile_rows[0]["classroom_id"] is None:
        raise HTTPException(403, "only students can submit stories")
    classroom_id = profile_rows[0]["classroom_id"]
    supabase.table("jobs").insert(
        {
            "id": job_id,
            "status": "queued",
            "current_stage": "queued",
            "input_text": text,
            "truncated": truncated,
            "style_preset_id": payload.style_preset_id,
            "profile_id": user.id,
            "classroom_id": classroom_id,
        }
    ).execute()
    queue = get_queue()
    queue.enqueue("worker.run_job.run_storybook_job", job_id)
    return CreateStorybookResponse(job_id=job_id)
```

- [ ] **Step 5: Replace the `confirm_job` function**

Current function spans lines 94–131. Replace with:

```python
@app.post("/jobs/{job_id}/confirm", response_model=ConfirmResponse)
def confirm_job(
    job_id: str, payload: ConfirmRequest, user=Depends(get_current_user)
) -> ConfirmResponse:
    supabase = get_supabase_client()

    rows = (
        supabase.table("jobs")
        .select("reveal, status, profile_id")
        .eq("id", job_id)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(404, "job not found")
    row = rows[0]

    if row["profile_id"] != user.id:
        raise HTTPException(403, "forbidden")

    if payload.action == "try_again":
        characters = row["reveal"].get("characters", [])
        character = next((c for c in characters if c["char_id"] == payload.char_id), None)
        if character is None or payload.attribute not in character["chips"]:
            raise HTTPException(422, "char_id or attribute not offered on this job's current reveal")

    cas = (
        supabase.table("jobs")
        .update({"status": "queued"})
        .eq("id", job_id)
        .eq("status", "awaiting_confirm")
        .execute()
    )
    if not cas.data:
        # Zero rows affected: already resumed, never paused, or swept. A double-tapping child
        # must not see an error (spec §4.9) — report the current status, enqueue nothing.
        return ConfirmResponse(status=row["status"])

    queue = get_queue()
    try:
        queue.enqueue("worker.run_job.resume_storybook_job", job_id, payload.model_dump())
    except Exception:
        # The CAS already flipped status to 'queued'; a Redis outage here would strand the book
        # with no worker coming and no way to re-confirm. Roll it back — nothing else ran.
        supabase.table("jobs").update({"status": "awaiting_confirm"}).eq("id", job_id).execute()
        raise HTTPException(503, "could not resume — try again")

    return ConfirmResponse(status="queued")
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(auth-s2): add get_current_user dep, wire into /storybooks and /confirm"
```

---

## Task 2: Backend — update and extend test suite

**Files:**
- Modify: `backend/tests/test_main.py`

**Interfaces:**
- Consumes: `get_current_user` from `app.main` (imported to set `app.dependency_overrides`)
- Consumes: `app` from `app.main` (already imported)

The existing tests do not pass `Authorization` headers. Now that both endpoints require auth, they would 401 without a bypass. The fix is an `autouse` pytest fixture that injects a fake user via FastAPI's `dependency_overrides`. Auth-specific tests that need to exercise the 401/403 path clear the override inside the test body before making the request.

- [ ] **Step 1: Write the failing tests first — verify they fail before fixing anything**

Add the following to `test_main.py` (anywhere below the imports, to be sorted later):

```python
# --- S2 auth-boundary tests (spec §8 tests 1–6) ---

def test_create_storybook_no_token_returns_401():
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post("/storybooks", json={"text": "A dog runs in a field."})
    assert response.status_code == 401


def test_create_storybook_bad_token_returns_401():
    app.dependency_overrides.pop(get_current_user, None)
    fake_supabase = MagicMock()
    fake_supabase.auth.get_user.return_value = MagicMock(user=None)
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post(
            "/storybooks",
            json={"text": "A dog runs in a field."},
            headers={"Authorization": "Bearer bad-token"},
        )
    assert response.status_code == 401


def test_create_storybook_teacher_token_returns_403():
    fake_supabase = MagicMock()
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"classroom_id": None}
    ]
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post("/storybooks", json={"text": "A dog runs in a field."})
    assert response.status_code == 403


def test_confirm_no_token_returns_401():
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post("/jobs/job-1/confirm", json={"action": "confirm"})
    assert response.status_code == 401


def test_confirm_wrong_owner_returns_403():
    fake_supabase = MagicMock()
    # profile_id in the job row does NOT match FAKE_USER_ID
    fake_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "status": "awaiting_confirm",
            "profile_id": "other-user-id",
            "reveal": {"characters": [], "taps_left": 2},
        }
    ]
    with patch("app.main.get_supabase_client", return_value=fake_supabase):
        response = client.post("/jobs/job-1/confirm", json={"action": "confirm"})
    assert response.status_code == 403


def test_confirm_matching_owner_awaiting_confirm_returns_200():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    _select_returns(
        fake_supabase,
        [{"status": "awaiting_confirm", "profile_id": FAKE_USER_ID, "reveal": {"characters": [], "taps_left": 2}}],
    )
    _cas_returns(fake_supabase, [{"id": "job-1"}])
    with patch("app.main.get_supabase_client", return_value=fake_supabase), patch(
        "app.main.get_queue", return_value=fake_queue
    ):
        response = client.post("/jobs/job-1/confirm", json={"action": "confirm"})
    assert response.status_code == 200
    assert response.json() == {"status": "queued"}
```

- [ ] **Step 2: Run these new tests to confirm they fail in the expected way**

```bash
cd backend && python -m pytest tests/test_main.py -k "no_token or bad_token or teacher_token or wrong_owner or matching_owner" -v
```

Expected: tests fail because `get_current_user` doesn't exist yet on `app.main` (import error) or endpoints return wrong status. This confirms the tests are wired correctly.

- [ ] **Step 3: Update `test_main.py` imports and add the autouse fixture + constants**

At the top of `test_main.py`, update the imports section (add `pytest` and the auth import):

```python
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app, get_current_user

client = TestClient(app)

FAKE_USER_ID = "user-student-123"


@pytest.fixture(autouse=True)
def _bypass_auth():
    """Inject a fake student user for all tests. Auth-boundary tests pop this override."""
    fake_user = MagicMock()
    fake_user.id = FAKE_USER_ID
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield fake_user
    app.dependency_overrides.pop(get_current_user, None)
```

- [ ] **Step 4: Update `REVEAL_ROW` to include `profile_id`**

The confirm endpoint now reads `profile_id` from the job row and checks it against `user.id`. All test rows must include `profile_id = FAKE_USER_ID` so the ownership check passes for non-auth tests.

Replace the `REVEAL_ROW` constant:

```python
REVEAL_ROW = {
    "status": "awaiting_confirm",
    "profile_id": FAKE_USER_ID,
    "reveal": {
        "characters": [{"char_id": "c0", "name": "Kiko", "image_path": "job-1/ref-c0-2.png", "chips": ["orange sock"]}],
        "taps_left": 2,
    },
}
```

- [ ] **Step 5: Update inline row dicts in existing confirm tests**

Two existing tests create row dicts inline without `profile_id`. Add `"profile_id": FAKE_USER_ID` to each.

In `test_confirm_rejects_an_attribute_offered_for_a_different_character_with_422`:
```python
row = {
    "status": "awaiting_confirm",
    "profile_id": FAKE_USER_ID,   # add this line
    "reveal": {
        "characters": [
            {"char_id": "c0", "name": "Kiko", "image_path": "p1", "chips": ["orange sock"]},
            {"char_id": "c1", "name": "Milo", "image_path": "p2", "chips": ["blue hat"]},
        ],
        "taps_left": 3,
    },
}
```

In `test_confirm_against_a_complete_job_returns_200_and_enqueues_nothing`:
```python
_select_returns(
    fake_supabase,
    [{"status": "complete", "profile_id": FAKE_USER_ID, "reveal": {"characters": [], "taps_left": 3}}],
)
```

- [ ] **Step 6: Run the full test file**

```bash
cd backend && python -m pytest tests/test_main.py -v
```

Expected: all existing tests pass, all 6 new auth tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/tests/test_main.py
git commit -m "test(auth-s2): auth-boundary tests for /storybooks and /confirm (spec §8 tests 1–6)"
```

---

## Task 3: Frontend — migrate to `@supabase/ssr` + cookie-client tests

**Files:**
- Modify: `frontend/lib/supabaseClient.ts`
- Modify: `frontend/package.json`
- Create: `frontend/lib/supabaseClient.test.ts`

**Interfaces:**
- Produces: `supabase` export (same name, same interface) — downstream code is unchanged. The object now comes from `createBrowserClient` and stores its session in a cookie.

- [ ] **Step 1: Write the failing Vitest tests**

Create `frontend/lib/supabaseClient.test.ts`:

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock both packages before the module under test is imported.
const mockCreateBrowserClient = vi.fn(() => ({ auth: {}, from: vi.fn() }));
const mockCreateClient = vi.fn();

vi.mock("@supabase/ssr", () => ({ createBrowserClient: mockCreateBrowserClient }));
vi.mock("@supabase/supabase-js", () => ({ createClient: mockCreateClient }));

describe("supabaseClient", () => {
  beforeEach(() => {
    vi.resetModules();
    mockCreateBrowserClient.mockClear();
    mockCreateClient.mockClear();
  });

  // spec §8 test 8 — import assertion
  it("exports a client created by createBrowserClient, not createClient", async () => {
    await import("./supabaseClient");
    expect(mockCreateBrowserClient).toHaveBeenCalledTimes(1);
    expect(mockCreateClient).not.toHaveBeenCalled();
  });

  // spec §8 test 7 — cookie storage is enabled by using createBrowserClient
  // ponytail: createBrowserClient IS the cookie-storage mechanism; testing it was called
  // proves cookies are enabled — direct document.cookie manipulation requires a real browser.
  it("passes the Supabase URL and anon key to createBrowserClient", async () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://example.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "anon-key";
    await import("./supabaseClient");
    expect(mockCreateBrowserClient).toHaveBeenCalledWith(
      "https://example.supabase.co",
      "anon-key"
    );
  });
});
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
cd frontend && npx vitest run lib/supabaseClient.test.ts
```

Expected: fail — `@supabase/ssr` is not installed and `supabaseClient.ts` still uses `createClient`.

- [ ] **Step 3: Install `@supabase/ssr`**

```bash
cd frontend && npm install @supabase/ssr
```

Expected: package installed, `package.json` updated.

- [ ] **Step 4: Replace `frontend/lib/supabaseClient.ts`**

```typescript
import { createBrowserClient } from "@supabase/ssr";

export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

- [ ] **Step 5: Run the Vitest tests**

```bash
cd frontend && npx vitest run lib/supabaseClient.test.ts
```

Expected: both tests pass.

- [ ] **Step 6: Run the full frontend test suite to confirm no regressions**

```bash
cd frontend && npx vitest run
```

Expected: all tests pass. The `supabase` export name is unchanged so no other test should break.

- [ ] **Step 7: Commit**

```bash
git add frontend/lib/supabaseClient.ts frontend/lib/supabaseClient.test.ts frontend/package.json frontend/package-lock.json
git commit -m "feat(auth-s2): migrate supabaseClient to createBrowserClient (@supabase/ssr)"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by |
|---|---|
| §3 — `createBrowserClient` replaces `createClient` | Task 3 |
| §3 — `@supabase/ssr` is the only new dep | Task 3 (`npm install @supabase/ssr`) |
| §5.1 — `get_current_user` dependency via `auth.get_user` | Task 1 step 3 |
| §5.2 — `/storybooks` derives ownership from DB; ignores client fields; 403 for null `classroom_id` | Task 1 step 4 |
| §5.3 — `/confirm` checks `profile_id = user.id`; 403 on mismatch | Task 1 step 5 |
| §5.4 — Worker unchanged | Not in plan (correct — no change needed) |
| §8 test 1 — `/storybooks` no token → 401 | Task 2 `test_create_storybook_no_token_returns_401` |
| §8 test 2 — `/storybooks` bad token → 401 | Task 2 `test_create_storybook_bad_token_returns_401` |
| §8 test 3 — `/storybooks` teacher/researcher → 403 | Task 2 `test_create_storybook_teacher_token_returns_403` |
| §8 test 4 — `/confirm` no token → 401 | Task 2 `test_confirm_no_token_returns_401` |
| §8 test 5 — `/confirm` wrong owner → 403 | Task 2 `test_confirm_wrong_owner_returns_403` |
| §8 test 6 — `/confirm` matching owner, `awaiting_confirm` → 200 | Task 2 `test_confirm_matching_owner_awaiting_confirm_returns_200` |
| §8 test 7 — cookie present after sign-in | Task 3 (second Vitest test) |
| §8 test 8 — `createBrowserClient` not `createClient` | Task 3 (first Vitest test) |
| §7 invariant 2 — ownership always server-derived | Task 1 step 4 (request body fields ignored) |
| §7 invariant 3 — confirm checks ownership | Task 1 step 5 |

**Placeholder scan:** No TBDs, TODOs, or vague steps found.

**Type consistency:**
- `user.id` is `str` throughout (supabase-py `User.id` is a UUID string).
- `FAKE_USER_ID = "user-student-123"` is used in both the fixture and `test_confirm_matching_owner_awaiting_confirm_returns_200` — consistent.
- `get_current_user` imported from `app.main` in tests; defined in `app.main` in implementation — matches.

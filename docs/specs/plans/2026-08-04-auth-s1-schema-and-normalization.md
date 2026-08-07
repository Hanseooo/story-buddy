# Auth S1 — Schema & Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the identity schema (migration 0007), nickname normalization (Python + TypeScript), and DB-level tests so S2 can name a subject and S3 can scope a policy.

**Architecture:** A single migration creates `classrooms` and `profiles` with triggers (atomic profile creation, cascade deletion to `auth.users`) and exposes `auth_role()` / `auth_classroom_id()` as security-definer helper functions. Nickname normalization lives in two standalone modules sharing the same 14-vector test table from spec §5.1. DB-level constraint and trigger tests require a local Supabase instance with the migration applied; they skip automatically when `SUPABASE_DB_URL` is not set so CI stays green.

**Tech Stack:** Supabase Postgres (migrations), Python 3.12 / uv / pytest / psycopg3, TypeScript / Vitest.

## Global Constraints

- Migration number is `0007` — this plan claims it. Do not create a different migration that uses 0007.
- `backend/contracts/` is frozen — zero changes to `StoryMemory`, `story_memory.py`, or any contract file.
- Migration enables RLS on both new tables with **zero** policies. Default-deny is correct; `0007` and S3's policy migration ship together or not at all (spec §7 ③).
- Normalization algorithm must produce identical output across Python and TypeScript. The §5.1 table is the shared contract; both test suites assert against the same 14 rows.
- Sentinel retirement (`config.py`, `run_job.py`, tests 12–14) is **not** in this plan — it lives in `2026-08-04-auth-s1-sentinel-retirement.md` and is blocked until S3 adds the `jobs` columns.
- DB test helper creates real rows in a local Supabase instance; each test runs inside a transaction rolled back on teardown. The trigger tests (9–11) use the Supabase admin API instead (transactions cannot span admin API calls).

---

## File Map

| Action | Path | What it is |
|--------|------|------------|
| Create | `supabase/migrations/0007_identity_and_classrooms.sql` | The full schema migration |
| Create | `backend/app/nickname.py` | Python normalization (creation path) |
| Create | `backend/tests/test_nickname.py` | §5.1 pass/reject vectors for Python |
| Create | `frontend/lib/nickname.ts` | TypeScript normalization (login path) |
| Create | `frontend/lib/nickname.test.ts` | §5.1 pass/reject vectors for TypeScript |
| Create | `backend/tests/test_auth_schema.py` | §9 tests 4–11 (schema constraints + triggers) |

---

### Task 1: Python nickname normalization

**Files:**
- Create: `backend/app/nickname.py`
- Create: `backend/tests/test_nickname.py`

**Interfaces:**
- Produces: `normalize_nickname(raw: str) -> str` — raises `ValueError` on any rejection. Used by S2's teacher-creates-student path. **If this and the TypeScript version drift, children stop being able to log in.**

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_nickname.py
import pytest
from app.nickname import normalize_nickname

# Spec §5.1 — transcribed verbatim. Do not edit without updating the TypeScript suite too.
PASS_VECTORS = [
    ("Juan", "juan"),
    ("MARIA", "maria"),
    ("Ana Mae", "ana-mae"),
    ("  Juan  Dela   Cruz ", "juan-dela-cruz"),
    ("Niño", "nino"),
    ("José-María", "jose-maria"),
    ("Kim  -  Lee", "kim-lee"),
    ("--Jun--", "jun"),
    ("R2D2", "r2d2"),
]

REJECT_VECTORS = [
    "Juan!",    # illegal character survives step 4
    "J",        # under 2 characters after normalization
    "a" * 33,   # over 32 characters after normalization
    "😀",       # non-[a-z0-9-] survives
    "ᜃᜌ",     # Baybayin — non-[a-z0-9-] survives
]


@pytest.mark.parametrize("raw,expected", PASS_VECTORS)
def test_normalize_nickname_pass(raw, expected):
    assert normalize_nickname(raw) == expected


@pytest.mark.parametrize("raw", REJECT_VECTORS)
def test_normalize_nickname_rejects(raw):
    with pytest.raises(ValueError):
        normalize_nickname(raw)
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd backend && uv run pytest tests/test_nickname.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.nickname'`

- [ ] **Step 3: Implement `normalize_nickname`**

```python
# backend/app/nickname.py
import re
import unicodedata


def normalize_nickname(raw: str) -> str:
    """Spec §5 — four-step pipeline. Raises ValueError at creation time; never at login."""
    # Step 1: NFKD + strip combining marks (Niño → Nino, José → Jose)
    nfkd = unicodedata.normalize("NFKD", raw)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Step 2: lowercase, trim outer whitespace, collapse whitespace runs to a single hyphen
    lowered = stripped.lower().strip()
    hyphened = re.sub(r"\s+", "-", lowered)
    # Step 3: collapse repeated hyphens, strip leading/trailing hyphens
    collapsed = re.sub(r"-{2,}", "-", hyphened).strip("-")
    # Step 4: reject if any character outside [a-z0-9-] survives, or length is out of range
    if not collapsed or re.search(r"[^a-z0-9-]", collapsed):
        raise ValueError(f"nickname {raw!r} cannot be normalized to a valid form")
    if len(collapsed) < 2:
        raise ValueError(f"nickname {raw!r} normalizes to under 2 characters")
    if len(collapsed) > 32:
        raise ValueError(f"nickname {raw!r} normalizes to over 32 characters")
    return collapsed
```

- [ ] **Step 4: Run tests to confirm they pass**

```
cd backend && uv run pytest tests/test_nickname.py -v
```

Expected: 14 PASS (9 pass vectors + 5 reject vectors).

- [ ] **Step 5: Run the full backend suite to confirm no regressions**

```
cd backend && uv run ruff check . && uv run pytest
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/app/nickname.py backend/tests/test_nickname.py
git commit -m "feat(auth-s1): Python nickname normalization + §5.1 test vectors"
```

---

### Task 2: TypeScript nickname normalization

**Files:**
- Create: `frontend/lib/nickname.ts`
- Create: `frontend/lib/nickname.test.ts`

**Interfaces:**
- Produces: `normalizeNickname(raw: string): string` — throws on rejection. `composeStudentEmail(nickname: string, classroomCode: string): string` — the exact address passed to Supabase `signInWithPassword` at login (S4).
- The 14 vectors in this test suite must produce the same output as Task 1's Python suite for every row.

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/lib/nickname.test.ts
import { describe, expect, it } from "vitest";
import { composeStudentEmail, normalizeNickname } from "./nickname";

// Spec §5.1 — transcribed verbatim. Do not edit without updating the Python suite too.
const PASS_VECTORS: [string, string][] = [
  ["Juan", "juan"],
  ["MARIA", "maria"],
  ["Ana Mae", "ana-mae"],
  ["  Juan  Dela   Cruz ", "juan-dela-cruz"],
  ["Niño", "nino"],
  ["José-María", "jose-maria"],
  ["Kim  -  Lee", "kim-lee"],
  ["--Jun--", "jun"],
  ["R2D2", "r2d2"],
];

const REJECT_VECTORS = [
  "Juan!",       // illegal character survives
  "J",           // under 2 characters
  "a".repeat(33), // over 32 characters
  "😀",          // non-[a-z0-9-] survives
  "ᜃᜌ",        // Baybayin — non-[a-z0-9-] survives
];

describe("normalizeNickname", () => {
  it.each(PASS_VECTORS)("normalizes %s → %s", (raw, expected) => {
    expect(normalizeNickname(raw)).toBe(expected);
  });

  it.each(REJECT_VECTORS)("rejects %s", (raw) => {
    expect(() => normalizeNickname(raw)).toThrow();
  });
});

describe("composeStudentEmail", () => {
  it("composes the login address from a raw nickname and classroom code", () => {
    expect(composeStudentEmail("Juan Dela Cruz", "k4m7pq")).toBe(
      "juan-dela-cruz@k4m7pq.students.storybuddy.invalid"
    );
  });
});
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd frontend && pnpm exec vitest run lib/nickname.test.ts
```

Expected: `Cannot find module './nickname'`

- [ ] **Step 3: Implement `normalizeNickname` and `composeStudentEmail`**

```typescript
// frontend/lib/nickname.ts
// Spec §5 — four-step pipeline. Must stay in sync with backend/app/nickname.py.

export function normalizeNickname(raw: string): string {
  // Step 1: NFKD + strip combining marks (\p{M} = Unicode Mark category)
  const nfkd = raw.normalize("NFKD").replace(/\p{M}/gu, "");
  // Step 2: lowercase, trim outer whitespace, collapse whitespace runs to a single hyphen
  const lowered = nfkd.toLowerCase().trim();
  const hyphened = lowered.replace(/\s+/g, "-");
  // Step 3: collapse repeated hyphens, strip leading/trailing hyphens
  const collapsed = hyphened.replace(/-{2,}/g, "-").replace(/^-+|-+$/g, "");
  // Step 4: reject if any character outside [a-z0-9-] survives, or length is out of range
  if (!collapsed || /[^a-z0-9-]/u.test(collapsed)) {
    throw new Error(`nickname "${raw}" contains characters that cannot be normalized`);
  }
  if (collapsed.length < 2) {
    throw new Error(`nickname "${raw}" normalizes to under 2 characters`);
  }
  if (collapsed.length > 32) {
    throw new Error(`nickname "${raw}" normalizes to over 32 characters`);
  }
  return collapsed;
}

export function composeStudentEmail(nickname: string, classroomCode: string): string {
  return `${normalizeNickname(nickname)}@${classroomCode}.students.storybuddy.invalid`;
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```
cd frontend && pnpm exec vitest run lib/nickname.test.ts
```

Expected: 15 PASS (9 pass vectors + 5 reject vectors + 1 email composition test).

- [ ] **Step 5: Run the full frontend suite**

```
cd frontend && pnpm lint && pnpm test
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/nickname.ts frontend/lib/nickname.test.ts
git commit -m "feat(auth-s1): TypeScript nickname normalization + §5.1 test vectors"
```

---

### Task 3: Migration `0007_identity_and_classrooms.sql`

**Files:**
- Create: `supabase/migrations/0007_identity_and_classrooms.sql`

**Interfaces:**
- Produces: `classrooms` table, `profiles` table, `handle_new_user()` trigger, `handle_profile_deleted()` trigger, `public.auth_role()` and `public.auth_classroom_id()` helper functions.
- Consumed by: S3's policy migration, which names `auth_role()` and `auth_classroom_id()` as the subjects in every policy expression.

**Apply this migration before running Tasks 4 and 5.**

- [ ] **Step 1: Write the migration file**

```sql
-- supabase/migrations/0007_identity_and_classrooms.sql

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
-- 0007 and S3's policy migration ship together (spec §7 ③).
```

- [ ] **Step 2: Apply to local Supabase**

```bash
supabase db push
```

Verify the tables and triggers exist:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ('classrooms','profiles');

SELECT trigger_name FROM information_schema.triggers
WHERE event_object_schema IN ('public','auth')
  AND trigger_name IN ('on_auth_user_created','on_profile_deleted');
```

Expected: 2 table rows, 2 trigger rows.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/0007_identity_and_classrooms.sql
git commit -m "feat(auth-s1): migration 0007 — classrooms, profiles, triggers, helper functions"
```

---

### Task 4: Schema constraint tests (spec §9, tests 4–8)

**Files:**
- Create: `backend/tests/test_auth_schema.py`

**Interfaces:**
- Consumes: `classrooms` and `profiles` tables (Task 3 migration applied).
- Requires: `SUPABASE_DB_URL` env var pointing at a local Supabase instance. Tests skip automatically when the var is absent.
- Produces: the first half of `test_auth_schema.py` (tests 4–8); Task 5 appends the trigger tests.

Each test runs inside a transaction that is rolled back on teardown — the DB is clean after every test.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_auth_schema.py
"""Schema constraint and trigger tests (spec §9 tests 4–11).
Requires a local Supabase instance with migration 0007 applied.
Set SUPABASE_DB_URL to run; tests skip automatically when it is absent.
"""
import os
import uuid

import psycopg
import pytest

_DB_URL = os.environ.get("SUPABASE_DB_URL")
_skip = pytest.mark.skipif(not _DB_URL, reason="SUPABASE_DB_URL not set")


@pytest.fixture(scope="module")
def conn():
    c = psycopg.connect(_DB_URL)
    c.autocommit = False
    yield c
    c.close()


@pytest.fixture(autouse=True)
def rollback(conn):
    yield
    conn.rollback()


def _auth_user(conn) -> uuid.UUID:
    uid = uuid.uuid4()
    conn.execute(
        "INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, raw_app_meta_data)"
        " VALUES (%s, %s, 'x', now(), '{}'::jsonb)",
        (uid, f"{uid}@schema-test.invalid"),
    )
    return uid


def _teacher(conn) -> uuid.UUID:
    uid = _auth_user(conn)
    conn.execute(
        "INSERT INTO profiles (id, role, display_name) VALUES (%s, 'teacher', 'Test Teacher')",
        (uid,),
    )
    return uid


def _classroom(conn, owner_id: uuid.UUID, code: str = "tst001") -> uuid.UUID:
    cid = uuid.uuid4()
    conn.execute(
        "INSERT INTO classrooms (id, code, name, owner_id) VALUES (%s, %s, %s, %s)",
        (cid, code, "Test Class", owner_id),
    )
    return cid


# ── Tests 4–8: schema constraints ────────────────────────────────────────────

@_skip
def test_student_without_classroom_id_violates_role_shape(conn):
    """spec §9 test 4."""
    uid = _auth_user(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO profiles (id, role, nickname, display_nickname)"
            " VALUES (%s, 'student', 'juan', 'Juan')",
            (uid,),
        )


@_skip
def test_teacher_with_classroom_id_violates_role_shape(conn):
    """spec §9 test 5."""
    uid = _auth_user(conn)
    cid = uuid.uuid4()
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO profiles (id, role, classroom_id, display_name)"
            " VALUES (%s, 'teacher', %s, 'Ms. Santos')",
            (uid, cid),
        )


@_skip
def test_duplicate_nickname_same_classroom_violates_unique_index(conn):
    """spec §9 test 6."""
    owner = _teacher(conn)
    cid = _classroom(conn, owner)

    uid1 = _auth_user(conn)
    conn.execute(
        "INSERT INTO profiles (id, role, classroom_id, nickname, display_nickname)"
        " VALUES (%s, 'student', %s, 'juan', 'Juan')",
        (uid1, cid),
    )

    uid2 = _auth_user(conn)
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(
            "INSERT INTO profiles (id, role, classroom_id, nickname, display_nickname)"
            " VALUES (%s, 'student', %s, 'juan', 'Juan')",
            (uid2, cid),
        )


@_skip
def test_same_nickname_different_classroom_is_allowed(conn):
    """spec §9 test 7."""
    owner = _teacher(conn)
    cid1 = _classroom(conn, owner, code="cls001")
    cid2 = _classroom(conn, owner, code="cls002")

    uid1 = _auth_user(conn)
    conn.execute(
        "INSERT INTO profiles (id, role, classroom_id, nickname, display_nickname)"
        " VALUES (%s, 'student', %s, 'juan', 'Juan')",
        (uid1, cid1),
    )
    uid2 = _auth_user(conn)
    conn.execute(
        "INSERT INTO profiles (id, role, classroom_id, nickname, display_nickname)"
        " VALUES (%s, 'student', %s, 'juan', 'Juan')",
        (uid2, cid2),
    )
    # No exception = test passes


@_skip
def test_invalid_role_violates_check_constraint(conn):
    """spec §9 test 8."""
    uid = _auth_user(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO profiles (id, role, display_name) VALUES (%s, 'admin', 'Hacker')",
            (uid,),
        )
```

- [ ] **Step 2: Run without `SUPABASE_DB_URL` to confirm auto-skip**

```
cd backend && uv run pytest tests/test_auth_schema.py -v
```

Expected: 5 tests SKIP.

- [ ] **Step 3: Run with `SUPABASE_DB_URL` set and migration applied**

```
cd backend && SUPABASE_DB_URL="<your-local-db-url>" uv run pytest tests/test_auth_schema.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_auth_schema.py
git commit -m "test(auth-s1): schema constraint tests §9 tests 4–8"
```

---

### Task 5: Trigger tests (spec §9, tests 9–11)

**Files:**
- Modify: `backend/tests/test_auth_schema.py` (append three more tests)

**Interfaces:**
- Consumes: `handle_new_user()` and `handle_profile_deleted()` triggers (Task 3 migration). Uses `settings.supabase_url` + `settings.supabase_service_role_key` to call the Supabase admin API, which is the correct way to create rows in `auth.users`.
- Depends on: `SUPABASE_DB_URL` (direct Postgres for assertions) + valid `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` settings.

**Why admin API, not direct SQL for tests 9–11:** Creating a user in `auth.users` via raw SQL skips GoTrue's hash and metadata handling. The trigger relies on `raw_app_meta_data` populated by GoTrue at creation — direct SQL can only partially simulate that. The admin API is the right insertion surface.

- [ ] **Step 1: Add the trigger tests to `test_auth_schema.py`**

Add this import at the top of `backend/tests/test_auth_schema.py`:

```python
from supabase import create_client
from app.config import settings
```

Add these three tests **after** the existing constraint tests:

```python
# ── Tests 9–11: triggers ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin():
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _create_admin_user(admin, app_metadata: dict) -> str:
    """Returns the new user's id (str UUID)."""
    resp = admin.auth.admin.create_user({
        "email": f"{uuid.uuid4()}@trigger-test.invalid",
        "password": "Password123!",
        "email_confirm": True,
        "app_metadata": app_metadata,
    })
    return resp.user.id


@_skip
def test_insert_auth_user_creates_profile_row(admin, conn):
    """spec §9 test 9: handle_new_user trigger fires on auth.users insert."""
    uid_str = _create_admin_user(admin, {"role": "teacher", "display_name": "Trigger Teacher"})
    uid = uuid.UUID(uid_str)

    row = conn.execute(
        "SELECT role, display_name FROM profiles WHERE id = %s", (uid,)
    ).fetchone()
    assert row is not None, "trigger did not create a profiles row"
    assert row[0] == "teacher"
    assert row[1] == "Trigger Teacher"

    admin.auth.admin.delete_user(uid_str)  # cleanup; triggers cascade


@_skip
def test_delete_profile_row_deletes_auth_user(admin, conn):
    """spec §9 test 10: handle_profile_deleted trigger fires on profiles delete."""
    uid_str = _create_admin_user(admin, {"role": "teacher", "display_name": "Delete Me"})
    uid = uuid.UUID(uid_str)

    # Verify profile exists
    assert conn.execute("SELECT 1 FROM profiles WHERE id = %s", (uid,)).fetchone() is not None

    # Delete the profile — trigger should cascade to auth.users
    conn.execute("DELETE FROM profiles WHERE id = %s", (uid,))
    conn.commit()

    auth_row = conn.execute("SELECT 1 FROM auth.users WHERE id = %s", (uid,)).fetchone()
    assert auth_row is None, "handle_profile_deleted did not delete the auth.users row"


@_skip
def test_delete_classroom_cascades_to_profiles_and_auth_users(admin, conn):
    """spec §9 test 11: cascade chain — classroom → profiles → auth.users via trigger."""
    # Create a teacher (owner)
    teacher_id = _create_admin_user(admin, {"role": "teacher", "display_name": "Cascade Owner"})

    # Create a classroom owned by the teacher
    cid = uuid.uuid4()
    code = "csc001"
    conn.execute(
        "INSERT INTO classrooms (id, code, name, owner_id) VALUES (%s, %s, %s, %s)",
        (cid, code, "Cascade Class", uuid.UUID(teacher_id)),
    )
    conn.commit()

    # Create a student in that classroom
    student_email = f"juan@{code}.students.storybuddy.invalid"
    student_resp = admin.auth.admin.create_user({
        "email": student_email,
        "password": "Password123!",
        "email_confirm": True,
        "app_metadata": {
            "role": "student",
            "classroom_id": str(cid),
            "nickname": "juan",
            "display_nickname": "Juan",
        },
    })
    student_id = student_resp.user.id

    # Verify student profile exists
    assert conn.execute(
        "SELECT 1 FROM profiles WHERE id = %s", (uuid.UUID(student_id),)
    ).fetchone() is not None

    # Delete the classroom — cascade: classroom → profiles → (trigger) auth.users
    conn.execute("DELETE FROM classrooms WHERE id = %s", (cid,))
    conn.commit()

    # Both the profile and auth.users row must be gone
    assert conn.execute(
        "SELECT 1 FROM profiles WHERE id = %s", (uuid.UUID(student_id),)
    ).fetchone() is None, "cascade did not delete student profile"
    assert conn.execute(
        "SELECT 1 FROM auth.users WHERE id = %s", (uuid.UUID(student_id),)
    ).fetchone() is None, "trigger did not delete student auth.users row"

    # Cleanup teacher
    admin.auth.admin.delete_user(teacher_id)
```

- [ ] **Step 2: Run the full test file with DB access**

```
cd backend && SUPABASE_DB_URL="<your-local-db-url>" uv run pytest tests/test_auth_schema.py -v
```

Expected: 8 tests PASS (5 constraint + 3 trigger).

- [ ] **Step 3: Run the full CI check to confirm no regressions**

```
cd backend && uv run ruff check . && uv run pytest
```

All 8 DB tests skip without `SUPABASE_DB_URL`. The pure normalization tests (Task 1) still run and must be green.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_auth_schema.py
git commit -m "test(auth-s1): trigger tests §9 tests 9–11 (cascade + auth.users cleanup)"
```

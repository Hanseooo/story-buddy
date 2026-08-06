"""
Tier-A classroom isolation tests (spec §6 — auth-authorization-surface.md).

Covers tests 1–25 (jobs, classrooms, profiles) and 28–33 (storage).
Realtime tests 26–27 are backed by the same SELECT policies as tests 1–4;
they require a WebSocket client and are out of scope for this pytest suite.

Requires a local Supabase instance with migrations 0007 + 0008 applied.
Set SUPABASE_DB_URL to the local DB URL to run. In CI the env var resolves
to a non-connectable dummy and all tests skip automatically.

Local run:
  cd backend
  SUPABASE_DB_URL=postgresql://postgres:postgres@localhost:54322/postgres \\
  uv run pytest tests/test_rls_isolation.py -v
"""

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg
import pytest

_DB_URL = os.environ.get("SUPABASE_DB_URL")
_skip = pytest.mark.skipif(not _DB_URL, reason="SUPABASE_DB_URL not set")


# ── Connection ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def conn():
    try:
        c = psycopg.connect(_DB_URL, connect_timeout=3)
    except Exception:
        pytest.skip("SUPABASE_DB_URL unreachable — set a real URL to run RLS tests")
    c.autocommit = False
    yield c
    c.close()


@pytest.fixture(autouse=True)
def rollback(conn):
    yield
    conn.rollback()


# ── Raw insert helpers (run as superuser, triggers suppressed where noted) ────


def _auth_user(conn, suffix: str) -> uuid.UUID:
    uid = uuid.uuid4()
    conn.execute("SET LOCAL session_replication_role = replica")
    conn.execute(
        "INSERT INTO auth.users"
        " (id, email, encrypted_password, email_confirmed_at, raw_app_meta_data)"
        " VALUES (%s, %s, 'x', now(), '{}'::jsonb)",
        (uid, f"{uid}@{suffix}.rls-test.invalid"),
    )
    conn.execute("SET LOCAL session_replication_role = DEFAULT")
    return uid


def _profile(
    conn,
    uid: uuid.UUID,
    role: str,
    *,
    classroom_id=None,
    nickname=None,
    display_nickname=None,
    display_name=None,
):
    conn.execute(
        "INSERT INTO profiles"
        " (id, role, classroom_id, nickname, display_nickname, display_name)"
        " VALUES (%s, %s, %s, %s, %s, %s)",
        (uid, role, classroom_id, nickname, display_nickname, display_name),
    )


def _classroom(conn, owner_id: uuid.UUID, code: str, name: str) -> uuid.UUID:
    cid = uuid.uuid4()
    conn.execute(
        "INSERT INTO classrooms (id, code, name, owner_id) VALUES (%s, %s, %s, %s)",
        (cid, code, name, owner_id),
    )
    return cid


def _job(
    conn, profile_id: uuid.UUID, classroom_id: uuid.UUID, *, approved: bool = False
) -> uuid.UUID:
    jid = uuid.uuid4()
    conn.execute(
        "INSERT INTO jobs"
        " (id, status, input_text, profile_id, classroom_id, approved_at)"
        " VALUES (%s, 'complete', 'test story', %s, %s, %s)",
        (
            jid,
            profile_id,
            classroom_id,
            datetime.now(timezone.utc) if approved else None,
        ),
    )
    return jid


def _storage_obj(conn, job_id: uuid.UUID):
    conn.execute(
        "INSERT INTO storage.objects (bucket_id, name) VALUES ('storybook-images', %s)",
        (f"{job_id}/scene_1.png",),
    )


# ── RLS query helpers (SET LOCAL role + JWT per-transaction) ──────────────────


def _as_user(conn, uid: uuid.UUID):
    """Switch current transaction to run as the given authenticated user."""
    conn.execute("SET LOCAL ROLE authenticated")
    conn.execute(
        "SELECT set_config('request.jwt.claims', %s, true)",
        (json.dumps({"sub": str(uid), "role": "authenticated"}),),
    )


def _as_anon(conn):
    conn.execute("SET LOCAL ROLE anon")


def _select_jobs(conn, uid: uuid.UUID, job_id: uuid.UUID) -> list:
    _as_user(conn, uid)
    return conn.execute("SELECT id FROM jobs WHERE id = %s", (job_id,)).fetchall()


def _update_job_approval(conn, uid: uuid.UUID, job_id: uuid.UUID) -> int:
    _as_user(conn, uid)
    return conn.execute(
        "UPDATE jobs SET approved_at = now() WHERE id = %s", (job_id,)
    ).rowcount


def _select_classrooms(conn, uid: uuid.UUID, cid: uuid.UUID) -> list:
    _as_user(conn, uid)
    return conn.execute(
        "SELECT id FROM classrooms WHERE id = %s", (cid,)
    ).fetchall()


def _select_profiles(conn, uid: uuid.UUID, profile_id: uuid.UUID) -> list:
    _as_user(conn, uid)
    return conn.execute(
        "SELECT id FROM profiles WHERE id = %s", (profile_id,)
    ).fetchall()


def _select_storage(conn, uid: uuid.UUID, job_id: uuid.UUID) -> list:
    _as_user(conn, uid)
    return conn.execute(
        "SELECT name FROM storage.objects WHERE name = %s",
        (f"{job_id}/scene_1.png",),
    ).fetchall()


# ── Shared fixture ────────────────────────────────────────────────────────────


@dataclass
class RLSFixture:
    ta: uuid.UUID     # teacher A (owns cls_a)
    tb: uuid.UUID     # teacher B (owns cls_b)
    s1: uuid.UUID     # student in cls_a
    s2: uuid.UUID     # student in cls_a
    s3: uuid.UUID     # student in cls_b
    r: uuid.UUID      # researcher
    cls_a: uuid.UUID  # classroom A
    cls_b: uuid.UUID  # classroom B
    ba1: uuid.UUID    # job: authored by s1, approved
    ba2: uuid.UUID    # job: authored by s2, unapproved
    bb1: uuid.UUID    # job: authored by s3, approved


@pytest.fixture(scope="module")
def fx(conn) -> RLSFixture:
    """
    Fixture layout (spec §6):
      Classroom A: teacher TA, students S1 S2
      Classroom B: teacher TB, student S3
      Researcher R
      BA1: s1, approved  |  BA2: s2, unapproved  |  BB1: s3, approved
      Storage: {BA1}/scene_1.png, {BA2}/scene_1.png, {BB1}/scene_1.png
    All data is committed so it is visible to every test's transaction.
    Teardown deletes in reverse FK order.
    """
    # teachers and researcher (no classroom_id)
    ta = _auth_user(conn, "ta")
    tb = _auth_user(conn, "tb")
    r  = _auth_user(conn, "r")
    _profile(conn, ta, "teacher", display_name="Teacher A")
    _profile(conn, tb, "teacher", display_name="Teacher B")
    _profile(conn, r,  "researcher", display_name="Researcher R")
    conn.commit()

    # classrooms
    cls_a = _classroom(conn, ta, "rls-a", "RLS Classroom A")
    cls_b = _classroom(conn, tb, "rls-b", "RLS Classroom B")
    conn.commit()

    # students
    s1 = _auth_user(conn, "s1")
    s2 = _auth_user(conn, "s2")
    s3 = _auth_user(conn, "s3")
    _profile(conn, s1, "student", classroom_id=cls_a, nickname="s1", display_nickname="S1")
    _profile(conn, s2, "student", classroom_id=cls_a, nickname="s2", display_nickname="S2")
    _profile(conn, s3, "student", classroom_id=cls_b, nickname="s3", display_nickname="S3")
    conn.commit()

    # jobs
    ba1 = _job(conn, s1, cls_a, approved=True)
    ba2 = _job(conn, s2, cls_a, approved=False)
    bb1 = _job(conn, s3, cls_b, approved=True)
    conn.commit()

    # storage objects
    _storage_obj(conn, ba1)
    _storage_obj(conn, ba2)
    _storage_obj(conn, bb1)
    conn.commit()

    data = RLSFixture(
        ta=ta, tb=tb, s1=s1, s2=s2, s3=s3, r=r,
        cls_a=cls_a, cls_b=cls_b,
        ba1=ba1, ba2=ba2, bb1=bb1,
    )
    yield data

    # teardown — FK order: storage → jobs → classrooms → auth.users (cascades profiles)
    conn.execute(
        "DELETE FROM storage.objects WHERE name = ANY(%s)",
        ([f"{ba1}/scene_1.png", f"{ba2}/scene_1.png", f"{bb1}/scene_1.png"],),
    )
    conn.execute("DELETE FROM jobs WHERE id = ANY(%s)", ([ba1, ba2, bb1],))
    conn.execute("DELETE FROM classrooms WHERE id = ANY(%s)", ([cls_a, cls_b],))
    conn.execute(
        "DELETE FROM auth.users WHERE id = ANY(%s)",
        ([ta, tb, s1, s2, s3, r],),
    )
    conn.commit()

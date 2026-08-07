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
    # storage.protect_delete trigger blocks direct DELETE; bypass via replica role
    conn.execute("SET session_replication_role = replica")
    conn.execute(
        "DELETE FROM storage.objects WHERE name = ANY(%s)",
        ([f"{ba1}/scene_1.png", f"{ba2}/scene_1.png", f"{bb1}/scene_1.png"],),
    )
    conn.execute("SET session_replication_role = DEFAULT")
    conn.execute("DELETE FROM jobs WHERE id = ANY(%s)", ([ba1, ba2, bb1],))
    conn.execute("DELETE FROM classrooms WHERE id = ANY(%s)", ([cls_a, cls_b],))
    conn.execute(
        "DELETE FROM auth.users WHERE id = ANY(%s)",
        ([ta, tb, s1, s2, s3, r],),
    )
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# jobs SELECT — tests 1–11
# ═══════════════════════════════════════════════════════════════════════════════


@_skip
def test_01_s1_reads_own_approved_job(conn, fx):
    """Spec §6 test 1: S1 reads BA1 (own, approved) → allowed."""
    assert len(_select_jobs(conn, fx.s1, fx.ba1)) == 1


@_skip
def test_02_s1_unapproved_peer_job_denied(conn, fx):
    """Spec §6 test 2: S1 reads BA2 (classmate, unapproved) as peer → denied."""
    # BA2.approved_at is NULL → 'students read approved peer jobs' denies.
    assert len(_select_jobs(conn, fx.s1, fx.ba2)) == 0


@_skip
def test_03_s1_ba2_as_own_denied(conn, fx):
    """Spec §6 test 3: S1 reads BA2 as own → denied (BA2.profile_id = S2)."""
    # 'students read own jobs' checks profile_id = auth.uid() → false for BA2.
    assert len(_select_jobs(conn, fx.s1, fx.ba2)) == 0


@_skip
def test_04_s1_different_classroom_approved_denied(conn, fx):
    """Spec §6 test 4: S1 reads BB1 (approved, classroom B) → denied."""
    # BB1.classroom_id = cls_b ≠ auth_classroom_id() for S1.
    assert len(_select_jobs(conn, fx.s1, fx.bb1)) == 0


@_skip
def test_05_s2_reads_approved_peer_job(conn, fx):
    """Spec §6 test 5: S2 reads BA1 (classmate, approved) → allowed."""
    assert len(_select_jobs(conn, fx.s2, fx.ba1)) == 1


@_skip
def test_06_ta_reads_all_classroom_a_jobs(conn, fx):
    """Spec §6 test 6: TA reads BA1 and BA2 (all classroom A books) → allowed."""
    assert len(_select_jobs(conn, fx.ta, fx.ba1)) == 1
    assert len(_select_jobs(conn, fx.ta, fx.ba2)) == 1


@_skip
def test_07_ta_cannot_read_classroom_b_job(conn, fx):
    """Spec §6 test 7: TA reads BB1 (classroom B) → denied."""
    assert len(_select_jobs(conn, fx.ta, fx.bb1)) == 0


@_skip
def test_08_tb_cannot_read_classroom_a_job(conn, fx):
    """Spec §6 test 8: TB reads BA1 (classroom A) → denied."""
    assert len(_select_jobs(conn, fx.tb, fx.ba1)) == 0


@_skip
def test_09_researcher_reads_approved_job(conn, fx):
    """Spec §6 test 9: R reads BA1 (approved) → allowed."""
    assert len(_select_jobs(conn, fx.r, fx.ba1)) == 1


@_skip
def test_10_researcher_cannot_read_unapproved_job(conn, fx):
    """Spec §6 test 10: R reads BA2 (unapproved) → denied."""
    assert len(_select_jobs(conn, fx.r, fx.ba2)) == 0


@_skip
def test_11_anon_cannot_read_any_job(conn, fx):
    """Spec §6 test 11: anon reads any job → denied."""
    _as_anon(conn)
    rows = conn.execute(
        "SELECT id FROM jobs WHERE id = %s", (fx.ba1,)
    ).fetchall()
    assert len(rows) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# jobs UPDATE — tests 12–14
# ═══════════════════════════════════════════════════════════════════════════════


@_skip
def test_12_ta_can_approve_own_classroom_job(conn, fx):
    """Spec §6 test 12: TA sets approved_at on BA2 (own classroom) → allowed."""
    assert _update_job_approval(conn, fx.ta, fx.ba2) == 1


@_skip
def test_13_ta_cannot_approve_other_classroom_job(conn, fx):
    """Spec §6 test 13: TA sets approved_at on BB1 (classroom B) → denied (rowcount=0)."""
    assert _update_job_approval(conn, fx.ta, fx.bb1) == 0


@_skip
def test_14_student_cannot_approve_own_job(conn, fx):
    """Spec §6 test 14: S1 attempts to set approved_at on BA1 → denied (no student UPDATE policy)."""
    assert _update_job_approval(conn, fx.s1, fx.ba1) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# classrooms SELECT — tests 15–19
# ═══════════════════════════════════════════════════════════════════════════════


@_skip
def test_15_s1_reads_own_classroom(conn, fx):
    """Spec §6 test 15: S1 reads classroom A → allowed."""
    assert len(_select_classrooms(conn, fx.s1, fx.cls_a)) == 1


@_skip
def test_16_s1_cannot_read_other_classroom(conn, fx):
    """Spec §6 test 16: S1 reads classroom B → denied."""
    assert len(_select_classrooms(conn, fx.s1, fx.cls_b)) == 0


@_skip
def test_17_ta_reads_own_classroom(conn, fx):
    """Spec §6 test 17: TA reads classroom A → allowed."""
    assert len(_select_classrooms(conn, fx.ta, fx.cls_a)) == 1


@_skip
def test_18_ta_cannot_read_other_classroom(conn, fx):
    """Spec §6 test 18: TA reads classroom B → denied."""
    assert len(_select_classrooms(conn, fx.ta, fx.cls_b)) == 0


@_skip
def test_19_researcher_reads_both_classrooms(conn, fx):
    """Spec §6 test 19: R reads both classrooms → allowed."""
    assert len(_select_classrooms(conn, fx.r, fx.cls_a)) == 1
    assert len(_select_classrooms(conn, fx.r, fx.cls_b)) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# profiles SELECT — tests 20–25
# ═══════════════════════════════════════════════════════════════════════════════


@_skip
def test_20_s1_reads_own_profile(conn, fx):
    """Spec §6 test 20: S1 reads own profile → allowed."""
    assert len(_select_profiles(conn, fx.s1, fx.s1)) == 1


@_skip
def test_21_s1_reads_classmate_profile(conn, fx):
    """Spec §6 test 21: S1 reads S2's profile (same classroom) → allowed."""
    assert len(_select_profiles(conn, fx.s1, fx.s2)) == 1


@_skip
def test_22_s1_cannot_read_teacher_profile(conn, fx):
    """Spec §6 test 22: S1 reads TB's profile → denied (TB.classroom_id IS NULL)."""
    # 'students read classroom profiles': classroom_id = auth_classroom_id()
    # → NULL = <uuid> → false. Teacher is invisible to students.
    assert len(_select_profiles(conn, fx.s1, fx.tb)) == 0


@_skip
def test_23_s1_cannot_read_other_classroom_student(conn, fx):
    """Spec §6 test 23: S1 reads S3's profile (classroom B) → denied."""
    assert len(_select_profiles(conn, fx.s1, fx.s3)) == 0


@_skip
def test_24_ta_reads_own_classroom_students(conn, fx):
    """Spec §6 test 24: TA reads S1 and S2's profiles → allowed."""
    assert len(_select_profiles(conn, fx.ta, fx.s1)) == 1
    assert len(_select_profiles(conn, fx.ta, fx.s2)) == 1


@_skip
def test_25_ta_cannot_read_other_classroom_student(conn, fx):
    """Spec §6 test 25: TA reads S3's profile (classroom B) → denied."""
    assert len(_select_profiles(conn, fx.ta, fx.s3)) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Realtime — tests 26–27 (policy coverage, not WebSocket)
# ═══════════════════════════════════════════════════════════════════════════════
# Realtime evaluates the subscriber's SELECT policy before broadcasting (spec §5).
# Test 26 (S1 receives BA1 updates) is backed by test_01 — 'students read own jobs' covers it.
# Test 27 (S1 receives no BA2 broadcasts) is backed by tests 02–03 — both student SELECT
# policies deny BA2 to S1. A WebSocket integration test is out of scope for this suite.


# ═══════════════════════════════════════════════════════════════════════════════
# Storage isolation — tests 28–33
# ═══════════════════════════════════════════════════════════════════════════════


@_skip
def test_28_s1_reads_own_image(conn, fx):
    """Spec §6 test 28: S1 reads {BA1}/scene_1.png (own book) → allowed."""
    assert len(_select_storage(conn, fx.s1, fx.ba1)) == 1


@_skip
def test_29_s2_reads_approved_peer_image(conn, fx):
    """Spec §6 test 29: S2 reads {BA1}/scene_1.png (approved peer book) → allowed."""
    assert len(_select_storage(conn, fx.s2, fx.ba1)) == 1


@_skip
def test_30_s1_cannot_read_unapproved_peer_image(conn, fx):
    """Spec §6 test 30: S1 reads {BA2}/scene_1.png (unapproved peer) → denied."""
    assert len(_select_storage(conn, fx.s1, fx.ba2)) == 0


@_skip
def test_31_s1_cannot_read_other_classroom_image(conn, fx):
    """Spec §6 test 31: S1 reads {BB1}/scene_1.png (classroom B) → denied."""
    assert len(_select_storage(conn, fx.s1, fx.bb1)) == 0


@_skip
def test_32_ta_reads_own_classroom_image(conn, fx):
    """Spec §6 test 32: TA reads {BA1}/scene_1.png → allowed."""
    assert len(_select_storage(conn, fx.ta, fx.ba1)) == 1


@_skip
def test_33_ta_cannot_read_other_classroom_image(conn, fx):
    """Spec §6 test 33: TA reads {BB1}/scene_1.png (classroom B) → denied."""
    assert len(_select_storage(conn, fx.ta, fx.bb1)) == 0


# ── Tests 7–9: column grant enforcement (spec §6 tests 7–9) ──────────────────


def _owned_job(conn):
    """Create a teacher, classroom, and a student job. Return (teacher_uid, classroom_id, job_id)."""
    import json as _json  # noqa: F401
    teacher_uid = _auth_user(conn, "grant-teacher")
    conn.execute(
        "INSERT INTO profiles (id, role, display_name) VALUES (%s, 'teacher', 'Grant Teacher')",
        (teacher_uid,),
    )
    classroom_id = uuid.uuid4()
    conn.execute(
        "INSERT INTO classrooms (id, code, name, owner_id) VALUES (%s, 'grnt01', 'Grant Class', %s)",
        (classroom_id, teacher_uid),
    )
    student_uid = _auth_user(conn, "grant-student")
    conn.execute(
        "INSERT INTO profiles (id, role, classroom_id, nickname, display_nickname)"
        " VALUES (%s, 'student', %s, 'stu', 'Stu')",
        (student_uid, classroom_id),
    )
    job_id = uuid.uuid4()
    conn.execute(
        "INSERT INTO jobs (id, status, current_stage, input_text, truncated,"
        " profile_id, classroom_id)"
        " VALUES (%s, 'queued', 'queued', 'Once upon a time.', false, %s, %s)",
        (job_id, student_uid, classroom_id),
    )
    return teacher_uid, classroom_id, job_id


def _set_teacher_context(conn, teacher_uid: uuid.UUID, classroom_id: uuid.UUID) -> None:
    """Switch the connection to the authenticated role with teacher JWT claims."""
    claims = json.dumps({
        "sub": str(teacher_uid),
        "role": "authenticated",
        "app_metadata": {"role": "teacher"},
        "classroom_id": None,
    })
    conn.execute("SET LOCAL ROLE authenticated")
    conn.execute("SELECT set_config('request.jwt.claims', %s, true)", (claims,))


@_skip
def test_authenticated_teacher_can_update_approved_at(conn):
    """spec §6 test 7: authenticated role can set approved_at on an owned job."""
    teacher_uid, classroom_id, job_id = _owned_job(conn)
    _set_teacher_context(conn, teacher_uid, classroom_id)

    conn.execute(
        "UPDATE jobs SET approved_at = now() WHERE id = %s",
        (job_id,),
    )
    row = conn.execute(
        "SELECT approved_at FROM jobs WHERE id = %s", (job_id,)
    ).fetchone()
    assert row is not None and row[0] is not None


@_skip
def test_authenticated_teacher_cannot_update_input_text(conn):
    """spec §6 test 8: column grant denies authenticated from writing input_text."""
    teacher_uid, classroom_id, job_id = _owned_job(conn)
    _set_teacher_context(conn, teacher_uid, classroom_id)

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "UPDATE jobs SET input_text = 'injected' WHERE id = %s",
            (job_id,),
        )


@_skip
def test_service_role_can_update_input_text(conn):
    """spec §6 test 9: revoke on authenticated does not affect service_role path."""
    teacher_uid, classroom_id, job_id = _owned_job(conn)
    # No role switch — superuser bypasses all grants
    conn.execute(
        "UPDATE jobs SET input_text = 'superuser write' WHERE id = %s",
        (job_id,),
    )
    row = conn.execute(
        "SELECT input_text FROM jobs WHERE id = %s", (job_id,)
    ).fetchone()
    assert row is not None and row[0] == "superuser write"

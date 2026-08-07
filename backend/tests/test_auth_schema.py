"""Schema constraint and trigger tests (spec §9 tests 4–11).
Requires a local Supabase instance with migration 0007 applied.
Set SUPABASE_DB_URL to run; tests skip automatically when it is absent.
"""
import json
import os
import uuid

import psycopg
import pytest

_DB_URL = os.environ.get("SUPABASE_DB_URL")
_skip = pytest.mark.skipif(not _DB_URL, reason="SUPABASE_DB_URL not set")


@pytest.fixture(scope="module")
def conn():
    # ponytail: conftest always sets a dummy SUPABASE_DB_URL; skip if it can't connect
    try:
        c = psycopg.connect(_DB_URL, connect_timeout=3)
    except Exception:
        pytest.skip("SUPABASE_DB_URL unreachable — set a real URL to run schema tests")
    c.autocommit = False
    yield c
    c.close()


@pytest.fixture(autouse=True)
def rollback(conn):
    yield
    conn.rollback()


def _auth_user(conn) -> uuid.UUID:
    uid = uuid.uuid4()
    # ponytail: suppress handle_new_user trigger so constraint tests insert profiles manually
    conn.execute("SET LOCAL session_replication_role = replica")
    conn.execute(
        "INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, raw_app_meta_data)"
        " VALUES (%s, %s, 'x', now(), '{}'::jsonb)",
        (uid, f"{uid}@schema-test.invalid"),
    )
    conn.execute("SET LOCAL session_replication_role = DEFAULT")
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


# ── Tests 9–11: triggers ──────────────────────────────────────────────────────
# ponytail: uses direct SQL with raw_app_meta_data instead of the admin API;
# avoids a GoTrue key-format mismatch with the Python SDK while still exercising
# the trigger (which reads new.raw_app_meta_data, not GoTrue's enriched copy).

def _triggered_auth_user(conn, meta: dict) -> uuid.UUID:
    """Insert into auth.users WITH triggers enabled so handle_new_user fires."""
    uid = uuid.uuid4()
    conn.execute(
        "INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, raw_app_meta_data)"
        " VALUES (%s, %s, 'x', now(), %s::jsonb)",
        (uid, f"{uid}@trigger-test.invalid", json.dumps(meta)),
    )
    return uid


@_skip
def test_insert_auth_user_creates_profile_row(conn):
    """spec §9 test 9: handle_new_user trigger fires on auth.users insert."""
    uid = _triggered_auth_user(conn, {"role": "teacher", "display_name": "Trigger Teacher"})

    row = conn.execute(
        "SELECT role, display_name FROM profiles WHERE id = %s", (uid,)
    ).fetchone()
    assert row is not None, "trigger did not create a profiles row"
    assert row[0] == "teacher"
    assert row[1] == "Trigger Teacher"


@_skip
def test_delete_profile_row_deletes_auth_user(conn):
    """spec §9 test 10: handle_profile_deleted trigger fires on profiles delete."""
    uid = _triggered_auth_user(conn, {"role": "teacher", "display_name": "Delete Me"})

    assert conn.execute("SELECT 1 FROM profiles WHERE id = %s", (uid,)).fetchone() is not None

    # Delete the profile — trigger should cascade to auth.users
    conn.execute("DELETE FROM profiles WHERE id = %s", (uid,))
    conn.commit()

    assert conn.execute(
        "SELECT 1 FROM auth.users WHERE id = %s", (uid,)
    ).fetchone() is None, "handle_profile_deleted did not delete the auth.users row"


@_skip
def test_delete_classroom_cascades_to_profiles_and_auth_users(conn):
    """spec §9 test 11: cascade chain — classroom → profiles → auth.users via trigger."""
    # Create a teacher (owner) — trigger creates their profile
    teacher_uid = _triggered_auth_user(conn, {"role": "teacher", "display_name": "Cascade Owner"})
    conn.commit()

    # Create a classroom owned by the teacher
    cid = uuid.uuid4()
    code = "csc001"
    conn.execute(
        "INSERT INTO classrooms (id, code, name, owner_id) VALUES (%s, %s, %s, %s)",
        (cid, code, "Cascade Class", teacher_uid),
    )
    conn.commit()

    # Create a student in that classroom — trigger creates their profile
    student_uid = _triggered_auth_user(conn, {
        "role": "student",
        "classroom_id": str(cid),
        "nickname": "juan",
        "display_nickname": "Juan",
    })
    conn.commit()

    assert conn.execute(
        "SELECT 1 FROM profiles WHERE id = %s", (student_uid,)
    ).fetchone() is not None

    # Delete the classroom — cascade: classroom → profiles → (trigger) auth.users
    conn.execute("DELETE FROM classrooms WHERE id = %s", (cid,))
    conn.commit()

    assert conn.execute(
        "SELECT 1 FROM profiles WHERE id = %s", (student_uid,)
    ).fetchone() is None, "cascade did not delete student profile"
    assert conn.execute(
        "SELECT 1 FROM auth.users WHERE id = %s", (student_uid,)
    ).fetchone() is None, "trigger did not delete student auth.users row"

    # Cleanup teacher
    conn.execute("DELETE FROM auth.users WHERE id = %s", (teacher_uid,))
    conn.commit()

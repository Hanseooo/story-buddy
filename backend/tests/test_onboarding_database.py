"""Real database checks for the password/completion transaction boundary.

Use the isolated local Supabase database. No Auth credentials or provider calls.
The password and metadata UPDATE order follows Auth v2.188.1 UserUpdate.
"""
import os

import psycopg
import pytest
from psycopg.types.json import Jsonb

from tests.test_rls_isolation import _auth_user, _classroom, _job, _profile, _as_user, _storage_obj


@pytest.fixture
def db():
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("SUPABASE_DB_URL not set")
    try:
        # Local 17.6.1.106 crashes while adding hints to EXECUTE denials.
        # Disable hints for this connection only. ACLs and RLS stay unchanged.
        # https://github.com/supabase/postgres/issues/2112
        connection = psycopg.connect(url, connect_timeout=3, options="-c supautils.hint_roles=")
    except psycopg.OperationalError:
        pytest.skip("local Supabase unavailable")
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def student(db):
    teacher = _auth_user(db, "onboarding-teacher")
    _profile(db, teacher, "teacher", display_name="Teacher")
    classroom = _classroom(db, teacher, "ONBRD1", "Onboarding")
    child = _auth_user(db, "onboarding-student")
    _profile(db, child, "student", classroom_id=classroom,
             nickname="child", display_nickname="Child")
    return child, _job(db, child, classroom)


def operation(db, child, kind):
    return db.execute("select public.begin_password_operation(%s, %s)", (child, kind)).fetchone()[0]


def auth_update(db, child, receipt, kind, replacement):
    # These are opaque fixture values, not real password hashes or credentials.
    db.execute("update auth.users set encrypted_password = %s where id = %s", (replacement, child))
    column = "raw_user_meta_data" if kind == "change" else "raw_app_meta_data"
    db.execute(
        f"update auth.users set {column} = coalesce({column}, '{{}}'::jsonb) || %s where id = %s",
        (Jsonb({"storybuddy_password_operation": str(receipt)}), child),
    )
    db.execute("set constraints all immediate")
    db.execute("set constraints all deferred")


def test_password_commit_unlocks_only_its_reset_and_remembers_dismissal(db):
    child, job = student(db)
    _storage_obj(db, job)
    assert db.execute("select password_reset_version, password_completed_version from profiles where id = %s",
                      (child,)).fetchone() == (0, 0)
    reset = operation(db, child, "reset")
    auth_update(db, child, reset, "reset", "teacher-reset-fixture")
    assert db.execute("select password_reset_version, password_completed_version from profiles where id = %s",
                      (child,)).fetchone() == (1, 0)
    with db.transaction():
        _as_user(db, child)
        assert db.execute("select id from jobs where id = %s", (job,)).fetchall() == []
        assert db.execute("select id from profiles where id = %s", (child,)).fetchall() == [(child,)]
        assert db.execute("select id from classrooms").fetchall() == []
        assert db.execute("select name from storage.objects where name = %s", (f"{job}/scene_1.png",)).fetchall() == []
    db.execute("reset role")
    change = operation(db, child, "change")
    auth_update(db, child, change, "change", "chosen-password-fixture")
    assert db.execute("select password_reset_version, password_completed_version from profiles where id = %s",
                      (child,)).fetchone() == (1, 1)
    with db.transaction():
        _as_user(db, child)
        assert db.execute("select id from jobs where id = %s", (job,)).fetchall() == [(job,)]
        assert db.execute("select name from storage.objects where name = %s", (f"{job}/scene_1.png",)).fetchall() == [(f"{job}/scene_1.png",)]
        db.execute("select public.dismiss_student_introduction()")
    db.execute("reset role")
    dismissed = db.execute("select introduction_dismissed_at from profiles where id = %s", (child,)).fetchone()[0]
    reset = operation(db, child, "reset")
    auth_update(db, child, reset, "reset", "second-reset-fixture")
    assert db.execute("select password_reset_version, password_completed_version, introduction_dismissed_at "
                      "from profiles where id = %s", (child,)).fetchone() == (2, 1, dismissed)
    db.execute("update profiles set removed_at = now() where id = %s", (child,))
    restore = operation(db, child, "restore")
    auth_update(db, child, restore, "restore", "restored-password-fixture")
    assert db.execute("select password_reset_version, password_completed_version, removed_at, introduction_dismissed_at "
                      "from profiles where id = %s", (child,)).fetchone() == (3, 1, None, dismissed)


def test_direct_writes_and_changes_from_before_a_reset_cannot_complete_it(db):
    child, _ = student(db)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with db.transaction():
            _as_user(db, child)
            operation(db, child, "change")
    with db.transaction():
        _as_user(db, child)
        assert db.execute("update profiles set password_completed_version = 1 where id = %s", (child,)).rowcount == 0
    db.execute("reset role")
    stale = operation(db, child, "change")
    reset = operation(db, child, "reset")
    with pytest.raises(psycopg.errors.CheckViolation, match="password_operation_required"):
        with db.transaction():
            auth_update(db, child, stale, "change", "stale-change-fixture")
    # Do not permit verification against the old password while reset is pending.
    with pytest.raises(psycopg.errors.CheckViolation, match="password_reset_pending"):
        with db.transaction():
            operation(db, child, "change")
    auth_update(db, child, reset, "reset", "reset-fixture")
    with pytest.raises(psycopg.errors.CheckViolation, match="password_operation_required"):
        with db.transaction():
            auth_update(db, child, stale, "change", "late-change-fixture")
    with pytest.raises(psycopg.errors.CheckViolation, match="password_operation_required"):
        with db.transaction():
            db.execute("update auth.users set encrypted_password = 'direct-fixture' where id = %s", (child,))
            db.execute("set constraints all immediate")
    assert db.execute("select password_reset_version, password_completed_version from profiles where id = %s",
                      (child,)).fetchone() == (1, 0)

"""Tier-A tests for the `annotations` table (spec `docs/specs/annotation-surface.md` §6).

Requires a local Supabase instance with migrations 0007 + 0008 + 0014 applied.
Set SUPABASE_DB_URL to the local DB URL to run; in CI the var is unset and every
test skips automatically — same contract as `test_rls_isolation.py`.

Local run:
  cd backend
  SUPABASE_DB_URL=postgresql://postgres:postgres@localhost:54322/postgres \\
  uv run pytest tests/test_annotations_rls.py -v
"""

import json
import os
import uuid

import psycopg
import pytest

_DB_URL = os.environ.get("SUPABASE_DB_URL")

TAXONOMY = [
    "wrong_colour", "wrong_species", "wrong_body_feature", "wrong_clothing",
    "wrong_style", "different_face", "character_absent",
]

# The `adjudicate/` queue: pairs whose annotators DISAGREE on same_character.
# `count(distinct same_character) > 1` is the whole rule — a pair with one label
# so far has exactly one distinct value and is correctly absent, which is the
# false positive §6 names. Lives here rather than in a route because
# `adjudicate/` cannot be built until D-K and D-L are decided; the route lifts
# this string when it is.
DISAGREEMENT_SQL = """
    SELECT pair_id FROM annotations
    GROUP BY pair_id
    HAVING count(DISTINCT same_character) > 1
    ORDER BY pair_id
"""


@pytest.fixture(scope="module")
def conn():
    if not _DB_URL:
        pytest.skip("SUPABASE_DB_URL not set")
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


# ── Fixtures (superuser inserts; triggers suppressed on auth.users) ───────────


def _researcher(conn, name: str) -> uuid.UUID:
    uid = uuid.uuid4()
    conn.execute("SET LOCAL session_replication_role = replica")
    conn.execute(
        "INSERT INTO auth.users"
        " (id, email, encrypted_password, email_confirmed_at, raw_app_meta_data)"
        " VALUES (%s, %s, 'x', now(), '{}'::jsonb)",
        (uid, f"{uid}@annotations-test.invalid"),
    )
    conn.execute("SET LOCAL session_replication_role = DEFAULT")
    conn.execute(
        "INSERT INTO profiles (id, role, display_name) VALUES (%s, 'researcher', %s)",
        (uid, name),
    )
    return uid


def _student(conn) -> uuid.UUID:
    """A non-researcher, to prove the policies gate on role and not only on uid."""
    uid = uuid.uuid4()
    conn.execute("SET LOCAL session_replication_role = replica")
    conn.execute(
        "INSERT INTO auth.users"
        " (id, email, encrypted_password, email_confirmed_at, raw_app_meta_data)"
        " VALUES (%s, %s, 'x', now(), '{}'::jsonb)",
        (uid, f"{uid}@annotations-test.invalid"),
    )
    conn.execute("SET LOCAL session_replication_role = DEFAULT")
    cid = uuid.uuid4()
    conn.execute(
        "INSERT INTO classrooms (id, code, name, owner_id)"
        " VALUES (%s, %s, 'c', %s)",
        (cid, str(cid)[:8], _researcher(conn, "owner")),
    )
    conn.execute(
        "INSERT INTO profiles (id, role, classroom_id, nickname, display_nickname)"
        " VALUES (%s, 'student', %s, 'kid', 'Kid')",
        (uid, cid),
    )
    return uid


def _annotate(conn, pair_id: str, annotator_id: uuid.UUID, same: bool, reasons=()):
    """Superuser insert — sets up state without going through the policies."""
    conn.execute(
        "INSERT INTO annotations (pair_id, annotator_id, same_character, failure_reasons)"
        " VALUES (%s, %s, %s, %s)",
        (pair_id, annotator_id, same, list(reasons)),
    )


def _as_user(conn, uid: uuid.UUID):
    conn.execute("SET LOCAL ROLE authenticated")
    conn.execute(
        "SELECT set_config('request.jwt.claims', %s, true)",
        (json.dumps({"sub": str(uid), "role": "authenticated"}),),
    )


def _reset_role(conn):
    conn.execute("RESET ROLE")


# ── RLS isolation — the independence mechanism (§2.1, CC-4) ──────────────────


def test_annotator_reads_only_own_rows(conn):
    a, b = _researcher(conn, "A"), _researcher(conn, "B")
    _annotate(conn, "pair-1", a, True)
    _annotate(conn, "pair-1", b, False)

    _as_user(conn, a)
    rows = conn.execute("SELECT annotator_id FROM annotations").fetchall()
    assert rows == [(a,)]


def test_annotator_cannot_read_the_other_annotators_row(conn):
    a, b = _researcher(conn, "A"), _researcher(conn, "B")
    _annotate(conn, "pair-1", b, False)

    _as_user(conn, a)
    rows = conn.execute(
        "SELECT annotator_id FROM annotations WHERE annotator_id = %s", (b,)
    ).fetchall()
    assert rows == []


def test_annotator_cannot_insert_as_someone_else(conn):
    a, b = _researcher(conn, "A"), _researcher(conn, "B")

    _as_user(conn, a)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "INSERT INTO annotations (pair_id, annotator_id, same_character)"
            " VALUES ('pair-1', %s, true)",
            (b,),
        )


def test_annotator_can_insert_own_row(conn):
    a = _researcher(conn, "A")

    _as_user(conn, a)
    conn.execute(
        "INSERT INTO annotations (pair_id, annotator_id, same_character)"
        " VALUES ('pair-1', %s, false)",
        (a,),
    )
    assert conn.execute("SELECT count(*) FROM annotations").fetchone() == (1,)


def test_non_researcher_sees_nothing(conn):
    a = _researcher(conn, "A")
    kid = _student(conn)
    _annotate(conn, "pair-1", a, True)

    _as_user(conn, kid)
    assert conn.execute("SELECT count(*) FROM annotations").fetchone() == (0,)


def test_submitted_row_is_final_no_update_policy(conn):
    """§4: a submitted row is final; adjudication is the only correction path."""
    a = _researcher(conn, "A")
    _annotate(conn, "pair-1", a, True)

    _as_user(conn, a)
    assert conn.execute(
        "UPDATE annotations SET same_character = false WHERE pair_id = 'pair-1'"
    ).rowcount == 0


@pytest.mark.skip(
    reason="D-L: §2.1's 'researcher role with the adjudicator flag' has no "
           "schema representation yet — profiles carries no adjudicator column. "
           "Logged in DECISION_BACKLOG.md; 0014 grants no read-all policy."
)
def test_adjudicator_reads_all_rows(conn):
    raise AssertionError("unreachable until D-L is decided")


# ── Closed taxonomy (§2.1, judge-finetune.md §4, ADR-028: frozen at 7) ───────


def test_failure_reasons_rejects_value_outside_the_taxonomy(conn):
    a = _researcher(conn, "A")
    with pytest.raises(psycopg.errors.CheckViolation):
        _annotate(conn, "pair-1", a, False, reasons=["wrong_vibe"])


def test_failure_reasons_accepts_every_taxonomy_value(conn):
    a = _researcher(conn, "A")
    _annotate(conn, "pair-1", a, False, reasons=TAXONOMY)
    assert conn.execute(
        "SELECT failure_reasons FROM annotations"
    ).fetchone() == (TAXONOMY,)


def test_failure_reasons_accepts_empty(conn):
    a = _researcher(conn, "A")
    _annotate(conn, "pair-1", a, True)
    assert conn.execute("SELECT failure_reasons FROM annotations").fetchone() == ([],)


# ── The gating booleans default to "nothing wrong seen" (judge-finetune §5.2) ─


def test_gating_booleans_default_true(conn):
    a = _researcher(conn, "A")
    _annotate(conn, "pair-1", a, True)
    assert conn.execute(
        "SELECT anatomy_intact, text_free FROM annotations"
    ).fetchone() == (True, True)


def test_gating_booleans_are_storable_false(conn):
    a = _researcher(conn, "A")
    conn.execute(
        "INSERT INTO annotations"
        " (pair_id, annotator_id, same_character, anatomy_intact, text_free)"
        " VALUES ('pair-1', %s, true, false, false)",
        (a,),
    )
    assert conn.execute(
        "SELECT anatomy_intact, text_free FROM annotations"
    ).fetchone() == (False, False)


# ── Composite primary key (§4 edge cases) ────────────────────────────────────


def test_resubmission_is_not_a_second_row(conn):
    a = _researcher(conn, "A")

    _as_user(conn, a)
    for _ in range(2):
        conn.execute(
            "INSERT INTO annotations (pair_id, annotator_id, same_character)"
            " VALUES ('pair-1', %s, true) ON CONFLICT DO NOTHING",
            (a,),
        )
    assert conn.execute("SELECT count(*) FROM annotations").fetchone() == (1,)


def test_two_annotators_may_label_the_same_pair(conn):
    a, b = _researcher(conn, "A"), _researcher(conn, "B")
    _annotate(conn, "pair-1", a, True)
    _annotate(conn, "pair-1", b, False)
    assert conn.execute("SELECT count(*) FROM annotations").fetchone() == (2,)


# ── The adjudication queue (§6) ──────────────────────────────────────────────


def test_disagreement_query_returns_only_disagreeing_pairs(conn):
    a, b = _researcher(conn, "A"), _researcher(conn, "B")
    _annotate(conn, "agree", a, True)
    _annotate(conn, "agree", b, True)
    _annotate(conn, "disagree", a, True)
    _annotate(conn, "disagree", b, False)

    _reset_role(conn)
    assert conn.execute(DISAGREEMENT_SQL).fetchall() == [("disagree",)]


def test_disagreement_query_ignores_a_pair_with_one_label_so_far(conn):
    a = _researcher(conn, "A")
    _annotate(conn, "half-done", a, False)

    _reset_role(conn)
    assert conn.execute(DISAGREEMENT_SQL).fetchall() == []

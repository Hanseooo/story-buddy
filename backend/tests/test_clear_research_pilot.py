from types import SimpleNamespace

import pytest

from scripts.clear_research_pilot import (
    CONFIRMATION,
    CleanupError,
    execute_cleanup,
    main,
    plan_cleanup,
)


class Query:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.filters = {}
        self.window = (0, 999)
        self.operation = "select"

    def select(self, _columns):
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def in_(self, column, values):
        self.filters[column] = set(values)
        return self

    def range(self, start, end):
        self.window = (start, end)
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def execute(self):
        rows = self.client.rows[self.table]
        matches = [
            row
            for row in rows
            if all(
                row.get(column) in value if isinstance(value, set) else row.get(column) == value
                for column, value in self.filters.items()
            )
        ]
        if self.operation == "delete":
            self.client.mutations.append((self.table, tuple(row["id"] for row in matches)))
            if self.client.fail_table == f"{self.table}_raise":
                raise RuntimeError("connection lost")
            if self.client.fail_table == self.table:
                return SimpleNamespace(data=None, error="delete failed")
            self.client.rows[self.table] = [row for row in rows if row not in matches]
            return SimpleNamespace(data=matches, error=None)
        start, end = self.window
        return SimpleNamespace(data=matches[start : end + 1], error=None)


class Bucket:
    def __init__(self, client):
        self.client = client

    def list(self, prefix, options):
        offset = options["offset"]
        limit = options["limit"]
        direct = {}
        for path in self.client.objects:
            if not path.startswith(f"{prefix}/"):
                continue
            remainder = path.removeprefix(f"{prefix}/")
            name, separator, _rest = remainder.partition("/")
            direct[name] = {"name": name, "id": None if separator else path}
        return [direct[name] for name in sorted(direct)[offset : offset + limit]]

    def remove(self, paths):
        self.client.mutations.append(("storage", tuple(paths)))
        if self.client.fail_table == "storage":
            return SimpleNamespace(data=None, error="remove failed")
        for path in paths:
            self.client.objects.discard(path)
        return SimpleNamespace(data=paths, error=None)


class Storage:
    def __init__(self, client):
        self.client = client

    def from_(self, bucket):
        assert bucket == "private_assets"
        return Bucket(self.client)


class FakeSupabase:
    def __init__(self, fail_table=None):
        self.rows = {
            "research_pairs": [
                {
                    "id": "pilot-1",
                    "is_pilot": True,
                    "canonical_storage_path": "research/pilot/pilot-1/a.png",
                    "scene_storage_path": "research/pilot/pilot-1/b.png",
                },
                {
                    "id": "study-1",
                    "is_pilot": False,
                    "canonical_storage_path": "research/corpus/study-1/a.png",
                    "scene_storage_path": "research/corpus/study-1/b.webp",
                },
            ],
            "annotations": [
                {"id": "annotation-1", "pair_id": "pilot-1"},
                {"id": "annotation-2", "pair_id": "study-1"},
            ],
        }
        self.objects = {
            "research/pilot/pilot-1/a.png",
            "research/pilot/pilot-1/b.png",
            "research/pilot/orphan.png",
            "research/corpus/study-1/a.png",
        }
        self.mutations = []
        self.fail_table = fail_table
        self.storage = Storage(self)

    def table(self, name):
        return Query(self, name)


def test_plan_cleanup_is_read_only_and_counts_all_pilot_scopes():
    supabase = FakeSupabase()

    plan = plan_cleanup(supabase, page_size=2)

    assert plan.pair_ids == ("pilot-1",)
    assert plan.object_paths == (
        "research/pilot/orphan.png",
        "research/pilot/pilot-1/a.png",
        "research/pilot/pilot-1/b.png",
    )
    assert plan.annotation_count == 1
    assert supabase.mutations == []


def test_execute_cleanup_deletes_only_pilot_data_in_required_order():
    supabase = FakeSupabase()
    plan = plan_cleanup(supabase)

    execute_cleanup(plan, supabase, CONFIRMATION)

    assert [scope for scope, _ in supabase.mutations] == [
        "annotations",
        "research_pairs",
        "storage",
    ]
    assert supabase.rows["annotations"] == [{"id": "annotation-2", "pair_id": "study-1"}]
    assert supabase.rows["research_pairs"][0]["id"] == "study-1"
    assert supabase.objects == {"research/corpus/study-1/a.png"}


def test_confirmation_mismatch_performs_no_writes():
    supabase = FakeSupabase()
    plan = plan_cleanup(supabase)

    with pytest.raises(CleanupError, match="confirmation"):
        execute_cleanup(plan, supabase, "DELETE")

    assert supabase.mutations == []


@pytest.mark.parametrize("scope", ["annotations", "research_pairs", "storage"])
def test_partial_deletion_stops_and_reports_remaining_ids(scope):
    supabase = FakeSupabase(fail_table=scope)
    plan = plan_cleanup(supabase)

    with pytest.raises(CleanupError, match="remaining"):
        execute_cleanup(plan, supabase, CONFIRMATION)

    failed_index = [name for name, _ in supabase.mutations].index(scope)
    assert len(supabase.mutations) == failed_index + 1


def test_raised_deletion_failure_reports_remaining_ids():
    supabase = FakeSupabase(fail_table="annotations_raise")
    plan = plan_cleanup(supabase)

    with pytest.raises(CleanupError, match="remaining.*pilot-1"):
        execute_cleanup(plan, supabase, CONFIRMATION)


def test_final_verification_requires_all_three_scopes_to_be_empty():
    supabase = FakeSupabase()
    plan = plan_cleanup(supabase)
    original_remove = Bucket.remove

    def incomplete_remove(self, paths):
        original_remove(self, paths[:-1])
        return SimpleNamespace(data=paths[:-1], error=None)

    Bucket.remove = incomplete_remove
    try:
        with pytest.raises(CleanupError, match="remaining"):
            execute_cleanup(plan, supabase, CONFIRMATION)
    finally:
        Bucket.remove = original_remove


def test_main_defaults_to_dry_run(monkeypatch, capsys):
    supabase = FakeSupabase()
    monkeypatch.setattr("scripts.clear_research_pilot.get_supabase_client", lambda: supabase)

    assert main([]) == 0

    assert "annotations=1 pairs=1 objects=3" in capsys.readouterr().out
    assert supabase.mutations == []

"""Resolve immutable annotation rows and repair the queue's derived status cache."""
import itertools
from collections import defaultdict
from typing import Iterable, Literal, NamedTuple

from app.db import get_supabase_client
from finetune.manifest import ManifestError

ANNOTATIONS_TABLE = "annotations"
PAIRS_TABLE = "research_pairs"


class Consensus(NamedTuple):
    same_character: bool
    failure_reasons: list[str]
    anatomy_intact: bool = True
    text_free: bool = True
    adjudicated: bool = False


def _signature(row: dict) -> tuple:
    return (
        bool(row.get("same_character")),
        bool(row.get("anatomy_intact", True)),
        bool(row.get("text_free", True)),
        tuple(sorted(row.get("failure_reasons") or [])),
    )


def _partition(pair_id: str, rows: list[dict], adjudicators: set[str]) -> tuple[list[dict], list[dict]]:
    labels = [row for row in rows if row.get("annotator_id") is not None]
    ordinary = [row for row in labels if row["annotator_id"] not in adjudicators]
    adjudications = [row for row in labels if row["annotator_id"] in adjudicators]
    ordinary_ids = [row["annotator_id"] for row in ordinary]
    if len(ordinary_ids) != len(set(ordinary_ids)):
        raise ManifestError(f"Pair {pair_id} has duplicate annotator_ids for ordinary annotations.")
    if len(ordinary) > 2:
        raise ManifestError(f"Pair {pair_id} has >2 ordinary annotations.")
    if len(adjudications) > 1:
        raise ManifestError(f"Pair {pair_id}: multiple adjudicator rows.")
    return ordinary, adjudications


def fetch_annotations() -> list[dict]:
    page_size = 1000
    rows = []
    query = (
        get_supabase_client()
        .table(ANNOTATIONS_TABLE)
        .select("*")
        .order("pair_id")
        .order("annotator_id")
    )
    for start in itertools.count(0, page_size):
        page = query.range(start, start + page_size - 1).execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows


def fetch_adjudicator_ids() -> set[str]:
    data = get_supabase_client().table("profiles").select("id").eq("is_adjudicator", True).execute().data or []
    return {row["id"] for row in data}


def fetch_pilot_pairs() -> set[str]:
    data = get_supabase_client().table(PAIRS_TABLE).select("id").eq("is_pilot", True).execute().data or []
    return {row["id"] for row in data}


def resolve_annotations(
    rows: Iterable[dict], adjudicators: set[str], pilot_pairs: set[str]
) -> dict[str, Consensus]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["pair_id"] not in pilot_pairs:
            grouped[row["pair_id"]].append(row)

    resolved = {}
    for pair_id, pair_rows in grouped.items():
        ordinary, adjudications = _partition(pair_id, pair_rows, adjudicators)
        if len(ordinary) < 2:
            raise ManifestError(f"Pair {pair_id} has <2 ordinary annotations.")
        signatures = {_signature(row) for row in ordinary}
        if len(signatures) == 1:
            if adjudications:
                raise ManifestError(f"Pair {pair_id}: ordinary annotators agreed, but adjudicator row exists.")
            final_rows, adjudicated = ordinary, False
        else:
            if not adjudications:
                raise ManifestError(f"Pair {pair_id}: unresolved conflict (no adjudicator).")
            final_rows, adjudicated = adjudications, True

        reasons = []
        for row in final_rows:
            for reason in row.get("failure_reasons") or []:
                if reason not in reasons:
                    reasons.append(reason)
        resolved[pair_id] = Consensus(
            same_character=bool(final_rows[0].get("same_character")),
            failure_reasons=reasons,
            anatomy_intact=all(row.get("anatomy_intact", True) for row in final_rows),
            text_free=all(row.get("text_free", True) for row in final_rows),
            adjudicated=adjudicated,
        )
    return resolved


def reconcile_pair_status(
    rows: Iterable[dict], adjudicator_ids: set[str]
) -> dict[str, Literal["pending", "partially_annotated", "complete", "conflicted", "adjudicated"]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["pair_id"]].append(row)

    statuses = {}
    for pair_id, pair_rows in grouped.items():
        ordinary, adjudications = _partition(pair_id, pair_rows, adjudicator_ids)
        if len(ordinary) < 2:
            if adjudications:
                raise ManifestError(f"Pair {pair_id}: adjudication exists before two ordinary labels.")
            statuses[pair_id] = "pending" if not ordinary else "partially_annotated"
            continue
        conflicted = len({_signature(row) for row in ordinary}) > 1
        if not conflicted and adjudications:
            raise ManifestError(f"Pair {pair_id}: ordinary annotators agreed, but adjudicator row exists.")
        statuses[pair_id] = "adjudicated" if adjudications else "conflicted" if conflicted else "complete"
    return statuses


def repair_pair_statuses(supabase, current_rows: Iterable[dict], statuses: dict[str, str]) -> int:
    current = {row["id"]: row.get("status") for row in current_rows}
    by_status: dict[str, list[str]] = defaultdict(list)
    for pair_id, status in statuses.items():
        if current.get(pair_id) != status:
            by_status[status].append(pair_id)
    for status, pair_ids in by_status.items():
        response = supabase.table(PAIRS_TABLE).update({"status": status}).in_("id", sorted(pair_ids)).execute()
        if getattr(response, "error", None) is not None:
            raise RuntimeError(f"Supabase pair status update error: {response.error}")
    return sum(map(len, by_status.values()))


def _fetch_pair_status_rows(supabase) -> list[dict]:
    page_size = 1000
    rows = []
    query = supabase.table(PAIRS_TABLE).select("id,status").order("id")
    for start in itertools.count(0, page_size):
        response = query.range(start, start + page_size - 1).execute()
        if getattr(response, "error", None) is not None:
            raise RuntimeError(f"Supabase pair status query error: {response.error}")
        page = response.data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows


def reconcile_remote_status(supabase) -> tuple[dict[str, str], int]:
    current = _fetch_pair_status_rows(supabase)
    annotations = fetch_annotations()
    pair_ids = {row["id"] for row in current}
    unknown = {row["pair_id"] for row in annotations} - pair_ids
    if unknown:
        raise ManifestError(f"annotations reference unknown queue pairs: {sorted(unknown)}")
    rows = [{"pair_id": pair_id, "annotator_id": None} for pair_id in pair_ids]
    rows.extend(annotations)
    statuses = reconcile_pair_status(rows, fetch_adjudicator_ids())
    return statuses, repair_pair_statuses(supabase, current, statuses)

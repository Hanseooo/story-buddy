"""Dry-run-first cleanup for the research annotation pilot."""

import argparse
import itertools
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from app.db import get_supabase_client

BUCKET = "private_assets"
CONFIRMATION = "DELETE-RESEARCH-PILOT"
PILOT_PREFIX = "research/pilot/"


class CleanupError(RuntimeError):
    pass


@dataclass(frozen=True)
class CleanupPlan:
    pair_ids: tuple[str, ...]
    object_paths: tuple[str, ...]
    annotation_count: int


def _response_data(response: Any, operation: str) -> list[dict]:
    error = getattr(response, "error", None)
    if error is not None:
        raise CleanupError(f"{operation} failed: {error}")
    return getattr(response, "data", None) or []


def _pilot_pairs(supabase: Any, page_size: int) -> list[dict]:
    query = (
        supabase.table("research_pairs")
        .select("id,canonical_storage_path,scene_storage_path")
        .eq("is_pilot", True)
    )
    rows = []
    for start in itertools.count(0, page_size):
        page = _response_data(query.range(start, start + page_size - 1).execute(), "pilot pair query")
        rows.extend(page)
        if len(page) < page_size:
            return rows


def _annotation_count(supabase: Any, pair_ids: tuple[str, ...], page_size: int) -> int:
    if not pair_ids:
        return 0
    # `annotations` has no surrogate key; its identity is (pair_id, annotator_id, round).
    query = supabase.table("annotations").select("pair_id").in_("pair_id", pair_ids)
    count = 0
    for start in itertools.count(0, page_size):
        page = _response_data(query.range(start, start + page_size - 1).execute(), "pilot annotation query")
        count += len(page)
        if len(page) < page_size:
            return count


def _pilot_objects(supabase: Any, bucket: str, page_size: int) -> tuple[str, ...]:
    storage = supabase.storage.from_(bucket)
    paths = []
    directories = [PILOT_PREFIX.rstrip("/")]
    while directories:
        prefix = directories.pop()
        for offset in itertools.count(0, page_size):
            response = storage.list(
                prefix,
                {"limit": page_size, "offset": offset, "sortBy": {"column": "name"}},
            )
            entries = _response_data(response, "pilot object query") if hasattr(response, "data") else response or []
            for entry in entries:
                path = f"{prefix}/{entry['name']}"
                if not path.startswith(PILOT_PREFIX):
                    continue
                if entry.get("id") is None and entry.get("metadata") is None:
                    directories.append(path)
                else:
                    paths.append(path)
            if len(entries) < page_size:
                break
    return tuple(sorted(set(paths)))


def plan_cleanup(supabase: Any, bucket: str = BUCKET, page_size: int = 1000) -> CleanupPlan:
    pairs = _pilot_pairs(supabase, page_size)
    pair_ids = tuple(sorted(row["id"] for row in pairs))
    return CleanupPlan(
        pair_ids=pair_ids,
        object_paths=_pilot_objects(supabase, bucket, page_size),
        annotation_count=_annotation_count(supabase, pair_ids, page_size),
    )


def _remaining(plan: CleanupPlan) -> str:
    return (
        f"remaining annotations={plan.annotation_count} "
        f"pair_ids={list(plan.pair_ids)} object_paths={list(plan.object_paths)}"
    )


def _delete(call: Callable[[], Any], operation: str, supabase: Any, bucket: str) -> None:
    try:
        response = call()
        if getattr(response, "error", None) is not None:
            raise RuntimeError(response.error)
    except Exception as exc:
        raise CleanupError(
            f"{operation} failed ({exc}); {_remaining(plan_cleanup(supabase, bucket))}"
        ) from exc


def execute_cleanup(
    plan: CleanupPlan,
    supabase: Any,
    confirmation: str,
    bucket: str = BUCKET,
) -> None:
    if confirmation != CONFIRMATION:
        raise CleanupError(f"confirmation must equal {CONFIRMATION}")

    if plan.pair_ids:
        _delete(
            lambda: supabase.table("annotations").delete().in_("pair_id", plan.pair_ids).execute(),
            "annotation deletion",
            supabase,
            bucket,
        )
        _delete(
            lambda: supabase.table("research_pairs").delete().in_("id", plan.pair_ids).execute(),
            "pair deletion",
            supabase,
            bucket,
        )
    if plan.object_paths:
        _delete(
            lambda: supabase.storage.from_(bucket).remove(list(plan.object_paths)),
            "object deletion",
            supabase,
            bucket,
        )

    remaining = plan_cleanup(supabase, bucket)
    if remaining.annotation_count or remaining.pair_ids or remaining.object_paths:
        raise CleanupError(f"cleanup verification failed; {_remaining(remaining)}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", help=f"required for mutation: {CONFIRMATION}")
    parser.add_argument("--bucket", default=BUCKET)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    supabase = get_supabase_client()
    plan = plan_cleanup(supabase, args.bucket)
    print(
        f"annotations={plan.annotation_count} pairs={len(plan.pair_ids)} "
        f"objects={len(plan.object_paths)}"
    )
    if args.confirm is None:
        print(f"Dry run only. Re-run with --confirm {CONFIRMATION} after reviewing the exact scope.")
        return 0
    try:
        execute_cleanup(plan, supabase, args.confirm, args.bucket)
    except CleanupError as exc:
        print(exc)
        return 1
    print("annotations=0 pairs=0 objects=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

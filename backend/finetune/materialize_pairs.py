"""Upload immutable corpus assets and seed the blinded research pair queue."""
import argparse
import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
import sys
from typing import Any, Sequence

from PIL import Image, UnidentifiedImageError

from app.db import get_supabase_client
from finetune.build_dataset import pairs_from_memory
from finetune.corpus_io import (
    AssetRecord,
    CorpusError,
    RunBundle,
    load_completed_bundles,
    reconcile_declared_roster,
)
from finetune.dataset_selection import prepare_dataset_bundles
from finetune.manifest import ManifestError

log = logging.getLogger(__name__)

BUCKET = "private_assets"
PAIRS_TABLE = "research_pairs"
PAGE_SIZE = 1000
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "judge" / "corpus"


@dataclass(frozen=True)
class MaterializeSummary:
    uploaded: int
    skipped: int
    pairs_inserted: int


@dataclass(frozen=True)
class _Asset:
    path: str
    contents: bytes
    mime_type: str


def _image_details(contents: bytes) -> tuple[str, int, int]:
    if contents.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type = "image/png"
    elif contents.startswith(b"RIFF") and contents[8:12] == b"WEBP":
        mime_type = "image/webp"
    else:
        raise CorpusError("invalid image magic bytes")
    try:
        with Image.open(BytesIO(contents)) as image:
            image.load()
            return mime_type, image.width, image.height
    except (OSError, UnidentifiedImageError) as error:
        raise CorpusError("invalid image payload") from error


def read_verified_asset(asset: AssetRecord, root: Path) -> bytes:
    local = Path(asset.local_path)
    if not local.is_absolute():
        local = root / local
    if not local.is_file():
        raise CorpusError(f"missing completed asset: {local}")
    contents = local.read_bytes()
    mime_type, width, height = _image_details(contents)
    if (
        hashlib.sha256(contents).hexdigest() != asset.sha256
        or len(contents) != asset.byte_length
        or (mime_type, width, height) != (asset.mime_type, asset.width, asset.height)
    ):
        raise CorpusError(f"immutable bundle asset differs: {asset.storage_path}")
    return contents


def _validate_bundle(bundle: RunBundle, root: Path) -> list[tuple[_Asset, _Asset, dict]]:
    if (bundle.provenance == "synthetic" and bundle.split == "test") or (
        bundle.provenance == "donated" and bundle.split != "test"
    ):
        raise CorpusError(f"invalid provenance/split for {bundle.memory.story_id}")
    if bundle.declared_characters is None or bundle.declared_non_human is None:
        raise CorpusError(f"{bundle.memory.story_id}: missing declared roster")
    reconcile_declared_roster(
        bundle.declared_characters, bundle.declared_non_human, bundle.memory
    )

    assets: dict[str, tuple[AssetRecord, bytes]] = {}
    for asset in bundle.assets:
        if asset.storage_path in assets:
            raise CorpusError(f"duplicate completed asset path: {asset.storage_path}")
        if asset.kind == "ref" and asset.mime_type != "image/png":
            raise CorpusError("reference assets must be PNG")
        if asset.kind == "scene" and asset.mime_type != "image/webp":
            raise CorpusError("scene assets must be WebP")
        assets[asset.storage_path] = (asset, read_verified_asset(asset, root))

    pairs = []
    for pair in pairs_from_memory(bundle.memory):
        reference = assets.get(pair.ref_image)
        scene = assets.get(pair.scene_image)
        if reference is None or reference[0].kind != "ref" or scene is None or scene[0].kind != "scene":
            raise CorpusError(f"missing pair asset for {pair.pair_id}")
        row = {
            "id": pair.pair_id,
            "canonical_storage_path": f"research/corpus/{pair.pair_id}/a.png",
            "scene_storage_path": f"research/corpus/{pair.pair_id}/b.webp",
            "char_id": pair.char_id,
            "split": bundle.split,
            "is_constructed_negative": False,
            "is_pilot": False,
        }
        pairs.append((
            _Asset(row["canonical_storage_path"], reference[1], reference[0].mime_type),
            _Asset(row["scene_storage_path"], scene[1], scene[0].mime_type),
            row,
        ))
    return pairs


def _preflight(bundles: Sequence[RunBundle], root: Path) -> tuple[dict[str, _Asset], dict[str, dict]]:
    targets: dict[str, _Asset] = {}
    rows: dict[str, dict] = {}
    for bundle in bundles:
        for reference, scene, row in _validate_bundle(bundle, root):
            for target in (reference, scene):
                existing = targets.get(target.path)
                if existing is not None and existing.contents != target.contents:
                    raise CorpusError(f"storage path conflict: {target.path}")
                targets[target.path] = target
            existing_row = rows.get(row["id"])
            if existing_row is not None and existing_row != row:
                raise CorpusError(f"pair conflict: {row['id']}")
            rows[row["id"]] = row
    return targets, rows


def _fetch_pairs(supabase: Any) -> dict[str, dict]:
    columns = (
        "id, canonical_storage_path, scene_storage_path, char_id, split, "
        "is_constructed_negative, is_pilot"
    )
    query = supabase.table(PAIRS_TABLE).select(columns).order("id")
    rows: dict[str, dict] = {}
    for start in range(0, 2**31, PAGE_SIZE):
        response = query.range(start, start + PAGE_SIZE - 1).execute()
        if getattr(response, "error", None) is not None:
            raise RuntimeError(f"Supabase pair query error: {response.error}")
        page = response.data or []
        rows.update({row["id"]: row for row in page})
        if len(page) < PAGE_SIZE:
            return rows
    raise RuntimeError("research pair pagination overflow")


def _is_not_found(error: Exception) -> bool:
    return isinstance(error, FileNotFoundError) or "404" in str(error) or "not found" in str(error).lower()


def _materialize(bundles: Sequence[RunBundle], supabase: Any, bucket: str, root: Path) -> MaterializeSummary:
    targets, rows = _preflight(bundles, root)
    existing_rows = _fetch_pairs(supabase)
    for pair_id, row in rows.items():
        existing = existing_rows.get(pair_id)
        if existing is not None and any(existing.get(key) != value for key, value in row.items()):
            raise CorpusError(f"pair conflict: {pair_id}")

    storage = supabase.storage.from_(bucket)
    missing: list[_Asset] = []
    skipped = 0
    for target in targets.values():
        try:
            remote = storage.download(target.path)
        except Exception as error:
            if not _is_not_found(error):
                raise
            missing.append(target)
            continue
        if remote != target.contents:
            raise CorpusError(f"remote asset differs: {target.path}")
        skipped += 1

    pending = [row for pair_id, row in rows.items() if pair_id not in existing_rows]
    uploaded: list[_Asset] = []
    try:
        for target in missing:
            storage.upload(target.path, target.contents, {"content-type": target.mime_type})
            uploaded.append(target)
        if pending:
            response = supabase.table(PAIRS_TABLE).insert(pending).execute()
            if getattr(response, "error", None) is not None:
                raise RuntimeError(f"Supabase pair insert error: {response.error}")
    except Exception:
        safe_paths = []
        for target in uploaded:
            try:
                if storage.download(target.path) == target.contents:
                    safe_paths.append(target.path)
            except Exception:
                log.exception("materialize_pairs: cannot verify uploaded path for rollback: %s", target.path)
        if safe_paths:
            try:
                storage.remove(safe_paths)
            except Exception:
                log.exception("materialize_pairs: cannot roll back uploaded paths")
        raise
    return MaterializeSummary(uploaded=len(uploaded), skipped=skipped, pairs_inserted=len(pending))


def materialize(bundles: Sequence[RunBundle], supabase: Any, bucket: str = BUCKET) -> MaterializeSummary:
    return _materialize(bundles, supabase, bucket, DATA_DIR)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=DATA_DIR)
    parser.add_argument("--donated-intake", type=Path, default=None)
    parser.add_argument("--selection", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        bundles = load_completed_bundles(args.data)
        selected, _, _ = prepare_dataset_bundles(
            bundles, args.donated_intake, args.selection
        )
        summary = _materialize(selected, get_supabase_client(), BUCKET, args.data)
    except (CorpusError, ManifestError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(asdict(summary), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

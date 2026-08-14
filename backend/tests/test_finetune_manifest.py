"""§3.2 / §10 — the manifest record and the guards CI exists to run.

Character leakage across splits is the one mistake that is invisible in the metrics, so it
gets a test before it gets an implementation.
"""
import json

import pytest
from pydantic import ValidationError

from finetune.manifest import (
    ManifestError,
    ManifestRecord,
    read_manifest,
    validate_manifest,
    write_manifest,
)


def record(**overrides) -> ManifestRecord:
    base = dict(
        pair_id="p0",
        char_id="quill_007",
        split="train",
        provenance="synthetic",
        pair_type="pipeline",
        images=["ref/quill_007.png", "scene/quill_007_s03_a1.png"],
        differences_observed="Two eyes rather than three.",
        same_character=False,
        label=True,
        anatomy_intact=True,
        text_free=True,
        failure_reasons=["wrong_body_feature"],
    )
    base.update(overrides)
    return ManifestRecord(**base)


def test_images_must_be_exactly_two():
    with pytest.raises(ValidationError):
        record(images=["ref/a.png"])
    with pytest.raises(ValidationError):
        record(images=["ref/a.png", "scene/a.png", "scene/b.png"])


def test_failure_reasons_outside_the_closed_taxonomy_are_rejected():
    with pytest.raises(ValidationError):
        record(failure_reasons=["wrong_vibes"])


def test_guard_rejects_a_char_id_appearing_in_two_splits():
    records = [
        record(pair_id="p1", char_id="quill_007", split="train"),
        record(pair_id="p2", char_id="quill_007", split="val", provenance="synthetic"),
    ]
    with pytest.raises(ManifestError, match="quill_007"):
        validate_manifest(records)


def test_guard_rejects_a_synthetic_test_record():
    records = [record(pair_id="p1", char_id="bok_bok", split="test", provenance="synthetic")]
    with pytest.raises(ManifestError, match="provenance"):
        validate_manifest(records)


@pytest.mark.parametrize("split", ["val", "test"])
def test_guard_rejects_constructed_pairs_outside_train(split):
    provenance = "donated" if split == "test" else "synthetic"
    records = [record(pair_id="p1", char_id="bok_bok", split=split, provenance=provenance, pair_type="constructed")]
    with pytest.raises(ManifestError, match="constructed"):
        validate_manifest(records)


def test_guard_accepts_a_well_formed_manifest():
    records = [
        record(pair_id="p1", char_id="quill_007", split="train", pair_type="constructed"),
        record(pair_id="p2", char_id="bok_bok", split="val", provenance="synthetic"),
        record(pair_id="p3", char_id="tikbalang_2", split="test", provenance="donated"),
    ]
    validate_manifest(records)   # must not raise


def test_write_then_read_round_trips_and_validates(tmp_path):
    records = [record(pair_id="p1", char_id="a"), record(pair_id="p2", char_id="b", split="val")]
    path = tmp_path / "manifest.jsonl"
    write_manifest(path, records)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["char_id"] == "a"
    assert read_manifest(path) == records


def test_read_manifest_runs_the_guard(tmp_path):
    path = tmp_path / "manifest.jsonl"
    write_manifest(path, [record(pair_id="p1", char_id="a", split="train")], validate=False)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(record(pair_id="p2", char_id="a", split="val").model_dump_json() + "\n")

    with pytest.raises(ManifestError):
        read_manifest(path)


# --- the seam between build_corpus (writes the files) and build_dataset (names them) ---
# These two were built by separate agents and disagreed: the manifest carried Storage paths
# while the files on disk carry the flattened name. LLaMA-Factory resolves `images` against the
# filesystem, so the mismatch would surface as a corrupt training run, not an error.

def test_local_image_path_matches_build_corpus_layout(tmp_path):
    from finetune.build_corpus import download_images
    from finetune.manifest import local_image_path

    storage = "judge-01/s03-1.png"

    class _Char:
        canonical_ref_image = None

    class _Scene:
        final_image_ref = storage

    class _Storage:
        def from_(self, _bucket):
            return self

        def download(self, _path):
            return b"png"

    class _Supabase:
        storage = _Storage()

    download_images({"characters": [], "scenes": [_Scene()]}, tmp_path, _Supabase())

    written = [p for p in (tmp_path / "scene").iterdir()]
    assert len(written) == 1
    # the manifest's path must resolve to the file build_corpus actually wrote
    assert local_image_path(storage, "scene", root=tmp_path) == written[0].as_posix()


def test_local_image_path_is_posix_and_rooted_at_the_dataset_dir():
    from finetune.manifest import local_image_path

    assert local_image_path("judge-01/ref-c0-1.png", "ref") == "data/judge/ref/judge-01_ref-c0-1.png"

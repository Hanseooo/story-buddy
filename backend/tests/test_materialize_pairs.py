import hashlib
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from contracts.story_memory import Attempt, Character, Input, Scene, StoryMemory
from finetune import materialize_pairs as mp
from finetune.build_dataset import mint_pair_id
from finetune.corpus_io import AssetRecord, CorpusError, RunBundle
from finetune.manifest import ManifestError
from finetune.materialize_pairs import materialize


class Response:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error


class FakeBucket:
    def __init__(self, objects=None):
        self.objects = dict(objects or {})
        self.uploads = []
        self.removals = []

    def download(self, path):
        if path not in self.objects:
            raise FileNotFoundError(path)
        return self.objects[path]

    def upload(self, path, contents, options=None):
        self.uploads.append((path, contents, options))
        self.objects[path] = contents

    def remove(self, paths):
        self.removals.append(list(paths))
        for path in paths:
            self.objects.pop(path, None)


class FakeStorage:
    def __init__(self, bucket):
        self.bucket = bucket
        self.buckets = []

    def from_(self, bucket):
        self.buckets.append(bucket)
        return self.bucket


class FakePairsTable:
    def __init__(self, rows=None, insert_error=None):
        self.rows = list(rows or [])
        self.insert_error = insert_error
        self.ranges = []
        self.inserted = []
        self._window = (0, 999)
        self._pending = None

    def select(self, _columns):
        return self

    def order(self, _column):
        return self

    def range(self, start, end):
        self.ranges.append((start, end))
        self._window = (start, end)
        return self

    def insert(self, rows):
        self.inserted.append(rows)
        self._pending = rows
        return self

    def execute(self):
        if self._pending is not None and self.insert_error is not None:
            raise self.insert_error
        start, end = self._window
        if self._pending is not None:
            rows = self._pending
            self._pending = None
            self.rows.extend(rows)
            return Response(data=rows)
        return Response(data=self.rows[start : end + 1])


class FakeSupabase:
    def __init__(self, objects=None, rows=None, insert_error=None):
        self.bucket = FakeBucket(objects)
        self.storage = FakeStorage(self.bucket)
        self.pairs = FakePairsTable(rows, insert_error)

    def table(self, name):
        assert name == "research_pairs"
        return self.pairs


def image_bytes(image_format, color="purple"):
    output = BytesIO()
    Image.new("RGB", (2, 3), color).save(output, format=image_format)
    return output.getvalue()


def asset(storage_path, local_path, contents, kind):
    with Image.open(BytesIO(contents)) as image:
        image.load()
        width, height = image.size
    return AssetRecord(
        storage_path=storage_path,
        local_path=str(local_path),
        sha256=hashlib.sha256(contents).hexdigest(),
        mime_type="image/png" if kind == "ref" else "image/webp",
        width=width,
        height=height,
        byte_length=len(contents),
        kind=kind,
    )


def bundle(tmp_path, *, provenance="synthetic", split="train", include_roster=True):
    ref = image_bytes("PNG")
    scene = image_bytes("WEBP")
    ref_path = tmp_path / "ref.png"
    scene_path = tmp_path / "scene.webp"
    ref_path.write_bytes(ref)
    scene_path.write_bytes(scene)
    memory = StoryMemory(
        schema_version=1,
        story_id="story-1",
        classroom_id="classroom",
        profile_id="profile",
        input=Input(raw_text="A redacted story."),
        characters=[Character(char_id="char-1", name="Moss", canonical_ref_image="upstream/ref.png")],
        scenes=[
            Scene(
                scene_id="scene-1",
                text_excerpt="Moss waved.",
                characters_present=["char-1"],
                attempts=[Attempt(image_ref="upstream/scene.png")],
                final_image_ref="upstream/scene.png",
            )
        ],
    )
    return RunBundle(
        memory=memory,
        provenance=provenance,
        split=split,
        candidate_role="not_applicable" if provenance == "synthetic" else "primary",
        declared_characters=["Moss"] if include_roster else None,
        declared_non_human=[] if include_roster else None,
        run_metadata={},
        assets=[
            asset("upstream/ref.png", ref_path, ref, "ref"),
            asset("upstream/scene.png", scene_path, scene, "scene"),
        ],
    )


def expected_pair(run_bundle):
    pair_id = mint_pair_id("char-1", "upstream/scene.png")
    return {
        "id": pair_id,
        "canonical_storage_path": f"research/corpus/{pair_id}/a.png",
        "scene_storage_path": f"research/corpus/{pair_id}/b.webp",
        "char_id": "char-1",
        "split": run_bundle.split,
        "is_constructed_negative": False,
        "is_pilot": False,
    }


def test_materialize_quarantines_missing_roster_before_remote_mutation(tmp_path):
    supabase = FakeSupabase()

    with pytest.raises(CorpusError, match="missing declared roster"):
        materialize([bundle(tmp_path, include_roster=False)], supabase)

    assert supabase.storage.buckets == []
    assert supabase.pairs.ranges == []


def test_materialize_uploads_exact_bytes_and_inserts_blinded_deterministic_pair(tmp_path):
    run_bundle = bundle(tmp_path)
    supabase = FakeSupabase()

    summary = materialize([run_bundle], supabase)

    row = expected_pair(run_bundle)
    assert summary.uploaded == 2
    assert summary.skipped == 0
    assert summary.pairs_inserted == 1
    assert supabase.storage.buckets == ["private_assets"]
    assert supabase.bucket.objects[row["canonical_storage_path"]] == (tmp_path / "ref.png").read_bytes()
    assert supabase.bucket.objects[row["scene_storage_path"]] == (tmp_path / "scene.webp").read_bytes()
    assert supabase.pairs.inserted == [[row]]
    assert not {"label", "same_character", "failure_reasons"} & supabase.pairs.inserted[0][0].keys()


def test_materialize_paginates_existing_pairs_and_is_idempotent(tmp_path):
    run_bundle = bundle(tmp_path)
    supabase = FakeSupabase(rows=[{"id": f"old-{index}"} for index in range(1001)])

    first = materialize([run_bundle], supabase)
    second = materialize([run_bundle], supabase)

    assert first.uploaded == 2 and first.pairs_inserted == 1
    assert second.uploaded == 0 and second.skipped == 2 and second.pairs_inserted == 0
    assert supabase.pairs.ranges[:2] == [(0, 999), (1000, 1999)]
    assert len(supabase.bucket.uploads) == 2
    assert len(supabase.pairs.inserted) == 1


def test_existing_exact_remote_bytes_are_skipped_but_the_missing_row_is_inserted(tmp_path):
    run_bundle = bundle(tmp_path)
    row = expected_pair(run_bundle)
    supabase = FakeSupabase(
        objects={
            row["canonical_storage_path"]: (tmp_path / "ref.png").read_bytes(),
            row["scene_storage_path"]: (tmp_path / "scene.webp").read_bytes(),
        }
    )

    summary = materialize([run_bundle], supabase)

    assert summary.uploaded == 0 and summary.skipped == 2 and summary.pairs_inserted == 1


def test_remote_path_with_different_bytes_fails_before_any_write(tmp_path):
    run_bundle = bundle(tmp_path)
    row = expected_pair(run_bundle)
    supabase = FakeSupabase(objects={row["canonical_storage_path"]: image_bytes("PNG", "green")})

    with pytest.raises(CorpusError, match="remote asset differs"):
        materialize([run_bundle], supabase)

    assert supabase.bucket.uploads == []
    assert supabase.pairs.inserted == []


def test_existing_pair_id_with_different_paths_fails_before_any_write(tmp_path):
    run_bundle = bundle(tmp_path)
    row = expected_pair(run_bundle)
    supabase = FakeSupabase(rows=[{**row, "canonical_storage_path": "other/a.png"}])

    with pytest.raises(CorpusError, match="pair conflict"):
        materialize([run_bundle], supabase)

    assert supabase.bucket.uploads == []
    assert supabase.pairs.inserted == []


def test_existing_pair_id_with_different_metadata_fails_before_any_write(tmp_path):
    run_bundle = bundle(tmp_path)
    row = expected_pair(run_bundle)
    supabase = FakeSupabase(rows=[{**row, "split": "val"}])

    with pytest.raises(CorpusError, match="pair conflict"):
        materialize([run_bundle], supabase)

    assert supabase.bucket.uploads == []
    assert supabase.pairs.inserted == []


@pytest.mark.parametrize("change", ["missing", "hash", "length", "mime", "dimensions"])
def test_invalid_or_missing_local_inventory_fails_before_any_insert(tmp_path, change):
    run_bundle = bundle(tmp_path)
    changed = run_bundle.model_copy(deep=True)
    if change == "missing":
        (tmp_path / "ref.png").unlink()
    elif change == "hash":
        changed.assets[0].sha256 = "0" * 64
    elif change == "length":
        changed.assets[0].byte_length += 1
    elif change == "mime":
        changed.assets[0].mime_type = "image/webp"
    else:
        changed.assets[0].width += 1
    supabase = FakeSupabase()

    with pytest.raises(CorpusError):
        materialize([changed], supabase)

    assert supabase.bucket.uploads == []
    assert supabase.pairs.inserted == []


def test_self_consistent_wrong_asset_format_fails_before_any_insert(tmp_path):
    run_bundle = bundle(tmp_path)
    wrong_reference = image_bytes("WEBP")
    wrong_path = tmp_path / "wrong-reference.webp"
    wrong_path.write_bytes(wrong_reference)
    changed = run_bundle.model_copy(deep=True)
    changed.assets[0] = asset("upstream/ref.png", wrong_path, wrong_reference, "scene").model_copy(
        update={"kind": "ref"}
    )
    supabase = FakeSupabase()

    with pytest.raises(CorpusError, match="reference assets must be PNG"):
        materialize([changed], supabase)

    assert supabase.bucket.uploads == []
    assert supabase.pairs.inserted == []


@pytest.mark.parametrize(
    ("provenance", "split"),
    [("donated", "train"), ("synthetic", "test")],
)
def test_invalid_provenance_split_fails_before_any_insert(tmp_path, provenance, split):
    run_bundle = bundle(tmp_path, provenance=provenance, split=split)
    supabase = FakeSupabase()

    with pytest.raises(CorpusError, match="provenance"):
        materialize([run_bundle], supabase)

    assert supabase.bucket.uploads == []
    assert supabase.pairs.inserted == []


def test_incomplete_bundle_fails_before_any_insert(tmp_path):
    run_bundle = bundle(tmp_path)
    incomplete = run_bundle.model_copy(update={"assets": run_bundle.assets[:1]})
    supabase = FakeSupabase()

    with pytest.raises(CorpusError, match="missing pair asset"):
        materialize([incomplete], supabase)

    assert supabase.bucket.uploads == []
    assert supabase.pairs.inserted == []


def test_retry_bundle_materializes_only_the_finalized_scene(tmp_path):
    run_bundle = bundle(tmp_path)
    rejected = Attempt(image_ref="upstream/rejected-scene.png", passed=False)
    finalized = run_bundle.memory.scenes[0].attempts[0]
    scene = run_bundle.memory.scenes[0].model_copy(
        update={
            "attempts": [rejected, finalized],
            "final_image_ref": finalized.image_ref,
        }
    )
    run_bundle = run_bundle.model_copy(
        update={"memory": run_bundle.memory.model_copy(update={"scenes": [scene]})}
    )
    supabase = FakeSupabase()

    summary = materialize([run_bundle], supabase)

    assert summary.pairs_inserted == 1
    assert supabase.pairs.inserted == [[expected_pair(run_bundle)]]


def test_database_failure_removes_only_objects_uploaded_by_this_invocation(tmp_path):
    run_bundle = bundle(tmp_path)
    row = expected_pair(run_bundle)
    existing_reference = (tmp_path / "ref.png").read_bytes()
    supabase = FakeSupabase(
        objects={row["canonical_storage_path"]: existing_reference},
        insert_error=RuntimeError("database offline"),
    )

    with pytest.raises(RuntimeError, match="database offline"):
        materialize([run_bundle], supabase)

    assert supabase.bucket.objects[row["canonical_storage_path"]] == existing_reference
    assert supabase.bucket.removals == [[row["scene_storage_path"]]]


def test_materialize_cli_filters_bundles_before_remote_call(tmp_path):
    b1 = bundle(tmp_path)
    b2 = bundle(tmp_path)
    b2 = b2.model_copy(update={"memory": b2.memory.model_copy(update={"story_id": "story-2"})})

    fake_supabase = FakeSupabase()
    donated_path = Path("intake/donated.json")
    selection_path = Path("intake/selection.json")

    with (
        patch("finetune.materialize_pairs.load_completed_bundles", return_value=[b1, b2]),
        patch("finetune.materialize_pairs.prepare_dataset_bundles", return_value=([b1], None, None)) as mock_prep,
        patch("finetune.materialize_pairs.get_supabase_client", return_value=fake_supabase) as mock_get_client,
        patch("finetune.materialize_pairs._materialize", return_value=mp.MaterializeSummary(1, 0, 1)) as mock_mat,
    ):
        ret = mp.main([
            "--data", str(tmp_path),
            "--donated-intake", str(donated_path),
            "--selection", str(selection_path),
        ])

    assert ret == 0
    mock_prep.assert_called_once_with([b1, b2], donated_path, selection_path)
    mock_get_client.assert_called_once()
    mock_mat.assert_called_once_with([b1], fake_supabase, mp.BUCKET, tmp_path)


def test_materialize_cli_fails_before_supabase_when_preparation_fails(tmp_path):
    with (
        patch("finetune.materialize_pairs.load_completed_bundles", return_value=[]),
        patch("finetune.materialize_pairs.prepare_dataset_bundles", side_effect=ManifestError("preparation failed")),
        patch("finetune.materialize_pairs.get_supabase_client") as mock_get_client,
    ):
        ret = mp.main([
            "--data", str(tmp_path),
            "--donated-intake", "donated.json",
            "--selection", "selection.json",
        ])

    assert ret == 1
    mock_get_client.assert_not_called()

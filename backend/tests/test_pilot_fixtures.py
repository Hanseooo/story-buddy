"""Tests for visual pilot fixtures and seeding (Ticket 01).

Covers:
1. Meaningful visual fixture generation with Pillow (17 pairs / 34 images, 512x512 PNGs).
2. Strict opaque storage paths (research/pilot/<uuid>/a.png, b.png) and UUID char_ids.
3. Test-side expected manifest validation.
4. Atomic fail-loud seeding and rollback cleanup on storage or DB failure.
"""

import io
import re
import uuid
from unittest.mock import MagicMock

import pytest
from PIL import Image

from tests.fixtures.pilot_manifest import EXPECTED_PILOT_LABELS, TAXONOMY


UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
OPAQUE_PATH_A_REGEX = re.compile(r"^research/pilot/[0-9a-f-]{36}/a\.png$")
OPAQUE_PATH_B_REGEX = re.compile(r"^research/pilot/[0-9a-f-]{36}/b\.png$")


# ── Manifest Integrity Tests ──────────────────────────────────────────────────


def test_manifest_covers_all_17_pairs():
    assert len(EXPECTED_PILOT_LABELS) == 17


def test_manifest_labels_conform_to_taxonomy_and_invariants():
    for key, entry in EXPECTED_PILOT_LABELS.items():
        assert isinstance(entry["same_character"], bool), f"Invalid same_character in {key}"
        assert isinstance(entry["failure_reasons"], list), f"Invalid failure_reasons in {key}"
        assert isinstance(entry["anatomy_intact"], bool), f"Invalid anatomy_intact in {key}"
        assert isinstance(entry["text_free"], bool), f"Invalid text_free in {key}"

        for reason in entry["failure_reasons"]:
            assert reason in TAXONOMY, f"Reason {reason} in {key} is outside TAXONOMY"

        if entry["same_character"]:
            assert entry["failure_reasons"] == [], f"PASS case {key} must have empty failure_reasons"
        else:
            assert len(entry["failure_reasons"]) >= 1, f"FAIL case {key} must have >= 1 failure_reasons"


# ── Visual Fixture Generation Tests ──────────────────────────────────────────


def test_generate_pilot_images_produces_17_pairs():
    from scripts.generate_visual_pilot import generate_pilot_fixtures

    fixtures = generate_pilot_fixtures()
    assert len(fixtures) == 17
    assert set(fixtures.keys()) == set(EXPECTED_PILOT_LABELS.keys())


def test_generated_images_dimensions_format_and_visual_content():
    from scripts.generate_visual_pilot import generate_pilot_fixtures

    fixtures = generate_pilot_fixtures()
    seen_hashes = set()

    for key, fixture in fixtures.items():
        img_a = fixture.image_a
        img_b = fixture.image_b
        bytes_a = fixture.image_a_bytes
        bytes_b = fixture.image_b_bytes

        # Check dimensions and mode
        assert img_a.size == (512, 512), f"image_a in {key} is not 512x512"
        assert img_b.size == (512, 512), f"image_b in {key} is not 512x512"
        assert img_a.mode == "RGB", f"image_a in {key} is not RGB"
        assert img_b.mode == "RGB", f"image_b in {key} is not RGB"

        # Check PNG header magic bytes
        assert bytes_a[:8] == b"\x89PNG\r\n\x1a\n", f"image_a in {key} is not valid PNG"
        assert bytes_b[:8] == b"\x89PNG\r\n\x1a\n", f"image_b in {key} is not valid PNG"

        # Verify images are readable back by PIL
        reopened_a = Image.open(io.BytesIO(bytes_a))
        reopened_b = Image.open(io.BytesIO(bytes_b))
        assert reopened_a.size == (512, 512)
        assert reopened_b.size == (512, 512)

        # Check that images are not blank/monochrome
        colors_a = reopened_a.getcolors(maxcolors=512 * 512)
        colors_b = reopened_b.getcolors(maxcolors=512 * 512)
        assert len(colors_a) >= 5, f"image_a in {key} has too few distinct colors ({len(colors_a)})"
        assert len(colors_b) >= 5, f"image_b in {key} has too few distinct colors ({len(colors_b)})"

        # Distinct images across the entire set
        assert bytes_a not in seen_hashes, f"image_a in {key} is a duplicate"
        seen_hashes.add(bytes_a)
        assert bytes_b not in seen_hashes, f"image_b in {key} is a duplicate"
        seen_hashes.add(bytes_b)

    assert len(seen_hashes) == 34, "Expected 34 unique generated images"


# ── Opaque Storage Paths & UUID Invariants Tests ──────────────────────────────


def test_prepare_pilot_seed_records_uses_opaque_paths_and_uuids():
    from scripts.pilot_annotate_seed import prepare_pilot_seed_records

    records = prepare_pilot_seed_records()
    assert len(records) == 17

    seen_pair_ids = set()
    seen_char_ids = set()
    forbidden_tokens = ["ref", "scene", "wrong", "fail", "pass", "same", "diff", "absent", "case_"]

    for record in records:
        pair_id = record["id"]
        canonical_path = record["canonical_storage_path"]
        scene_path = record["scene_storage_path"]
        char_id = record["char_id"]

        # Valid UUID formats
        assert UUID_REGEX.match(pair_id), f"pair_id {pair_id} is not a valid UUID"
        assert UUID_REGEX.match(char_id), f"char_id {char_id} is not a valid UUID"

        assert pair_id not in seen_pair_ids
        seen_pair_ids.add(pair_id)
        assert char_id not in seen_char_ids
        seen_char_ids.add(char_id)

        # Opaque storage paths matching specification
        assert OPAQUE_PATH_A_REGEX.match(canonical_path), f"Invalid canonical path {canonical_path}"
        assert OPAQUE_PATH_B_REGEX.match(scene_path), f"Invalid scene path {scene_path}"
        assert canonical_path == f"research/pilot/{pair_id}/a.png"
        assert scene_path == f"research/pilot/{pair_id}/b.png"

        # No keyword leakages in paths or metadata
        for token in forbidden_tokens:
            assert token not in canonical_path.lower(), f"Leaked token '{token}' in {canonical_path}"
            assert token not in scene_path.lower(), f"Leaked token '{token}' in {scene_path}"
            assert token not in pair_id.lower(), f"Leaked token '{token}' in pair_id {pair_id}"
            assert token not in char_id.lower(), f"Leaked token '{token}' in char_id {char_id}"

        # Other invariant fields
        assert record["split"] == "val"
        assert record["status"] == "pending"
        assert record["is_constructed_negative"] is False
        assert record["is_pilot"] is True


# ── Seeding Atomicity & Fail-Loud Tests ────────────────────────────────────────


@pytest.mark.anyio
async def test_seed_pilot_pairs_happy_path(monkeypatch):
    from scripts.pilot_annotate_seed import seed_pilot_pairs

    mock_supabase = MagicMock()
    mock_storage_bucket = MagicMock()
    mock_supabase.storage.from_.return_value = mock_storage_bucket

    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_insert = MagicMock()
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = MagicMock(data=[{"id": str(uuid.uuid4())} for _ in range(17)], error=None)

    result = await seed_pilot_pairs(supabase=mock_supabase)

    assert len(result) == 17
    # 17 pairs * 2 images = 34 storage uploads
    assert mock_storage_bucket.upload.call_count == 34
    # 1 batch insert to research_pairs
    assert mock_table.insert.call_count == 1
    # No cleanup called on happy path
    assert mock_storage_bucket.remove.call_count == 0


@pytest.mark.anyio
async def test_seed_pilot_pairs_fails_loud_and_cleans_up_on_storage_error():
    from scripts.pilot_annotate_seed import seed_pilot_pairs

    mock_supabase = MagicMock()
    mock_storage_bucket = MagicMock()
    mock_supabase.storage.from_.return_value = mock_storage_bucket

    # Fail on the 3rd upload
    upload_calls = []

    def fake_upload(path, data, file_options=None):
        upload_calls.append(path)
        if len(upload_calls) == 3:
            raise RuntimeError("Simulated storage upload network error")
        return {"Key": path}

    mock_storage_bucket.upload.side_effect = fake_upload

    with pytest.raises(RuntimeError, match="Simulated storage upload network error"):
        await seed_pilot_pairs(supabase=mock_supabase)

    # Cleaned up the 2 files that succeeded before failure
    assert mock_storage_bucket.remove.call_count == 1
    cleaned_up_paths = mock_storage_bucket.remove.call_args[0][0]
    assert cleaned_up_paths == upload_calls[:2]

    # DB insert never called
    assert mock_supabase.table.call_count == 0


@pytest.mark.anyio
async def test_seed_pilot_pairs_fails_loud_and_cleans_up_on_db_insert_error():
    from scripts.pilot_annotate_seed import seed_pilot_pairs

    mock_supabase = MagicMock()
    mock_storage_bucket = MagicMock()
    mock_supabase.storage.from_.return_value = mock_storage_bucket

    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_insert = MagicMock()
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.side_effect = RuntimeError("Simulated DB connection failure")

    with pytest.raises(RuntimeError, match="Simulated DB connection failure"):
        await seed_pilot_pairs(supabase=mock_supabase)

    # All 34 images were uploaded before DB insert failed
    assert mock_storage_bucket.upload.call_count == 34

    # All 34 uploaded objects must be deleted from storage
    assert mock_storage_bucket.remove.call_count == 1
    cleaned_up_paths = mock_storage_bucket.remove.call_args[0][0]
    assert len(cleaned_up_paths) == 34

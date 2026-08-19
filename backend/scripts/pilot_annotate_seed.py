"""Seeding script for the research visual pilot pairs.

Generates 17 meaningful visual pilot pairs (34 512x512 PNG images) using Pillow,
uploads them to Supabase Storage ('private_assets') using opaque paths, and inserts
them into 'research_pairs' with atomic fail-loud semantics.

Architectural Invariants (Ticket 01, ADR-017, ADR-028):
1. Opaque Storage Paths: Strictly 'research/pilot/<uuid>/a.png' and 'research/pilot/<uuid>/b.png'.
2. Randomized UUID char_ids: Prevents pattern recognition or sequence leakage.
3. Mark Pilot Data: 'is_pilot = true' ensures strict exclusion from training dataset export.
4. Atomic / Fail-Loud Seeding: Any storage or DB failure raises immediately and rolls back
   any uploaded storage objects.
"""

import asyncio
import logging
import uuid
from typing import Any

from app.db import get_supabase_client
from scripts.generate_visual_pilot import generate_pilot_fixtures, PilotFixturePair

logger = logging.getLogger(__name__)

BUCKET_NAME = "private_assets"


def prepare_pilot_seed_records(
    fixtures: dict[str, PilotFixturePair] | None = None,
) -> list[dict[str, Any]]:
    """Prepares the 17 pilot seed record definitions with opaque UUIDs and paths.

    Returns a list of 17 records ready for seeding.
    """
    if fixtures is None:
        fixtures = generate_pilot_fixtures()

    records: list[dict[str, Any]] = []

    for _key, fixture in fixtures.items():
        pair_id = str(uuid.uuid4())
        char_id = str(uuid.uuid4())
        canonical_path = f"research/pilot/{pair_id}/a.png"
        scene_path = f"research/pilot/{pair_id}/b.png"

        records.append({
            "id": pair_id,
            "canonical_storage_path": canonical_path,
            "scene_storage_path": scene_path,
            "char_id": char_id,
            "split": "val",
            "status": "pending",
            "is_constructed_negative": False,
            "is_pilot": True,
            # Transient byte payloads for uploading; stripped before DB insert
            "_bytes_a": fixture.image_a_bytes,
            "_bytes_b": fixture.image_b_bytes,
        })

    return records


async def seed_pilot_pairs(supabase=None, bucket_name: str = BUCKET_NAME) -> list[dict[str, Any]]:
    """Generates, uploads, and seeds the 17 pilot pairs with atomic error rollback."""
    if supabase is None:
        supabase = get_supabase_client()

    logger.info("Generating 17 meaningful visual pilot fixture pairs...")
    fixtures = generate_pilot_fixtures()
    records = prepare_pilot_seed_records(fixtures)

    uploaded_paths: list[str] = []

    try:
        # 1. Atomic Storage Uploads
        logger.info("Uploading %d images to bucket '%s'...", len(records) * 2, bucket_name)
        storage_bucket = supabase.storage.from_(bucket_name)

        for record in records:
            path_a = record["canonical_storage_path"]
            bytes_a = record["_bytes_a"]
            storage_bucket.upload(path_a, bytes_a, {"content-type": "image/png"})
            uploaded_paths.append(path_a)

            path_b = record["scene_storage_path"]
            bytes_b = record["_bytes_b"]
            storage_bucket.upload(path_b, bytes_b, {"content-type": "image/png"})
            uploaded_paths.append(path_b)

        # 2. Database Insert
        db_payload = [
            {
                "id": r["id"],
                "canonical_storage_path": r["canonical_storage_path"],
                "scene_storage_path": r["scene_storage_path"],
                "char_id": r["char_id"],
                "split": r["split"],
                "status": r["status"],
                "is_constructed_negative": r["is_constructed_negative"],
                "is_pilot": r["is_pilot"],
            }
            for r in records
        ]

        logger.info("Inserting %d records into table 'research_pairs'...", len(db_payload))
        response = supabase.table("research_pairs").insert(db_payload).execute()

        if getattr(response, "error", None) is not None:
            raise RuntimeError(f"Supabase DB insert error: {response.error}")

        logger.info("Successfully seeded %d pilot pairs atomically!", len(db_payload))
        return db_payload

    except Exception as e:
        logger.error("Seeding failed with error: %s. Rolling back %d uploaded objects...", e, len(uploaded_paths))
        if uploaded_paths:
            try:
                supabase.storage.from_(bucket_name).remove(uploaded_paths)
                logger.info("Successfully cleaned up %d orphan storage objects.", len(uploaded_paths))
            except Exception as cleanup_err:
                logger.error("Failed to clean up storage objects during rollback: %s", cleanup_err)
        raise e


def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_pilot_pairs())


if __name__ == "__main__":
    main()

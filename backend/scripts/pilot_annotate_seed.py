import os
import sys
import uuid
import asyncio

# Ensure we can import backend code
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.supabase import get_service_client

async def main():
    print("Seeding pilot pairs for the Annotation UI...")
    supabase = get_service_client()
    
    # We need to generate tiny blank/colored PNGs and upload them to Supabase
    # We'll use a simple 1x1 transparent PNG data to keep it fast
    import base64
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAANSURBVBhXY3jP4PgfAAWpA52h+k/KAAAAAElFTkSuQmCC"
    png_bytes = base64.b64decode(tiny_png_b64)

    # 17 adversarial pairs for smoke testing and protocol breaking
    pair_definitions = [
        ("char_1", "same_1"), ("char_2", "same_2"), ("char_3", "same_3"),
        ("char_4", "wrong_col_1"), ("char_5", "wrong_col_2"),
        ("char_6", "wrong_body_1"), ("char_7", "wrong_body_2"),
        ("char_8", "wrong_cloth_1"), ("char_9", "wrong_cloth_2"),
        ("char_10", "wrong_style_1"), ("char_11", "wrong_style_2"),
        ("char_12", "diff_face_1"), ("char_13", "diff_face_2"),
        ("char_14", "wrong_spec_1"),
        ("char_15", "absent_1"),
        ("char_16", "ambiguous_1"), ("char_17", "ambiguous_2"),
    ]

    pairs = []
    bucket_name = "private_assets"

    for char_id, test_case in pair_definitions:
        pair_id = f"pilot-{uuid.uuid4()}"
        ref_path = f"pilot/{pair_id}/ref.png"
        scene_path = f"pilot/{pair_id}/scene_{test_case}.png"

        # Upload images to storage
        # If they already exist, we ignore the error
        try:
            supabase.storage.from_(bucket_name).upload(ref_path, png_bytes, {"content-type": "image/png"})
            supabase.storage.from_(bucket_name).upload(scene_path, png_bytes, {"content-type": "image/png"})
        except Exception as e:
            # Might already exist or fail, but we continue for the sake of the seed
            print(f"Storage upload note for {pair_id}: {e}")

        pairs.append({
            "id": pair_id,
            "canonical_storage_path": ref_path,
            "scene_storage_path": scene_path,
            "char_id": char_id,
            "split": "val",
            "status": "pending",
            "is_constructed_negative": False,
            "is_pilot": True
        })

    response = supabase.table("research_pairs").insert(pairs).execute()
    
    if hasattr(response, 'data') and response.data:
        print(f"Successfully seeded {len(response.data)} pilot pairs!")
    else:
        print(f"Failed to seed pairs. Result: {response}")

if __name__ == "__main__":
    asyncio.run(main())

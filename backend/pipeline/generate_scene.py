from app.db import get_supabase_client
from contracts.job_state import JobState
from providers import text_to_image

BUCKET = "storybook-images"


def generate_and_store(prompt: str, job_id: str) -> str:
    # ponytail: text-to-image, no character reference yet. Phase 1's char_bible node
    # produces the reference and this switches to providers.edit_image (ADR-007).
    image_bytes = text_to_image(prompt)

    path = f"{job_id}/scene-1.png"
    supabase = get_supabase_client()
    supabase.storage.from_(BUCKET).upload(
        path, image_bytes, {"content-type": "image/png", "upsert": "true"}
    )
    return path


def generate_scene(state: JobState) -> JobState:
    prompt = state["caption"] or state["input_text"]
    state["image_path"] = generate_and_store(prompt, state["job_id"])
    state["stage"] = "generate_scene"
    return state

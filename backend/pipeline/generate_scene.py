from app.db import get_supabase_client
from contracts.story_memory import Attempt, StoryMemory
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


def generate_scene(state: StoryMemory) -> dict:
    # ADR-024: loop position is the first scene with no final_image_ref — no cursor field.
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is None:
        return {}

    prompt = scene.caption or scene.text_excerpt
    path = generate_and_store(prompt, state.story_id)
    return {
        "scenes": [
            scene.model_copy(
                update={
                    "prompt": prompt,
                    # CC-5: the attempt carries the prompt THIS draw used; regeneration corrects
                    # Scene.prompt and would otherwise erase the provenance (ADR-010).
                    "attempts": [*scene.attempts, Attempt(image_ref=path, prompt=prompt, passed=True)],
                    "final_image_ref": path,
                }
            )
        ]
    }

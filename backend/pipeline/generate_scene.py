from google import genai

from app.config import settings
from app.db import get_supabase_client
from contracts.job_state import JobState

BUCKET = "storybook-images"


def call_nano_banana_and_store(prompt: str, job_id: str) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
    )
    # NOTE: parsing shape best-effort against google-genai SDK docs — verify against the
    # installed SDK version if this breaks (flagged in plan Global Constraints).
    image_bytes = response.candidates[0].content.parts[0].inline_data.data

    path = f"{job_id}/scene-1.png"
    supabase = get_supabase_client()
    supabase.storage.from_(BUCKET).upload(
        path, image_bytes, {"content-type": "image/png", "upsert": "true"}
    )
    return path


def generate_scene(state: JobState) -> JobState:
    prompt = state["caption"] or state["input_text"]
    state["image_path"] = call_nano_banana_and_store(prompt, state["job_id"])
    state["stage"] = "generate_scene"
    return state

from google import genai
from google.genai import types

from app.config import settings
from contracts.job_state import JobState, SceneCaption


def call_gemini_for_caption(text: str) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Write one short, kid-friendly caption (max 20 words) for this story: {text}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SceneCaption,
        ),
    )
    parsed = SceneCaption.model_validate_json(response.text)
    return parsed.caption


def analyze(state: JobState) -> JobState:
    state["caption"] = call_gemini_for_caption(state["input_text"])
    state["stage"] = "analyze"
    return state

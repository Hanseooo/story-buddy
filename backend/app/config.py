from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    supabase_db_url: str
    redis_url: str
    openrouter_api_key: str
    fal_key: str
    sentry_dsn_backend: str | None = None
    frontend_origin: str = "http://localhost:3000"

    # Phase-1 dev provenance sentinels (ADR-023 amendment 2026-07-22b). The worker supplies
    # story_id = job_id; these two stand in until `auth-and-classroom` lands. Swapping them for
    # real selection is a value change at one call site — never a contract change.
    dev_classroom_id: str = "dev-classroom"
    dev_profile_id: str = "dev-profile"

    # Model swap is an env-var change; provider swap is providers.py (ADR-001, ADR-002).
    text_model: str = "qwen/qwen3-32b"
    vlm_judge_model: str = "google/gemma-3-27b-it"
    fal_image_model: str = "fal-ai/qwen-image"
    fal_image_edit_model: str = "fal-ai/qwen-image-edit-2511"

    # ADR-022's `cel` preset — "the flagship default kids see first" — authored 2026-07-21 in
    # backend/spikes/phase_05.py. This is ADR-007 as originally written (one fixed style). The
    # three-preset `style_presets` dict, `style_preset_id` resolution and the picker UI stay
    # wholly owned by the `style-presets` spec; `char_bible` only needs *a* fragment to exist.
    default_style_fragment: str = (
        "flat cel-shaded cartoon, thick clean black outlines of even weight, bright solid colour fills, "
        "two flat shadow tones, limited palette, no gradients, no glossy highlights, no airbrushing"
    )

    # The judge moves to a self-hosted vLLM server after Phase 2.5 (ADR-019). vLLM speaks the
    # OpenAI protocol, so the swap is these two vars — no code change.
    judge_base_url: str = "https://openrouter.ai/api/v1"
    judge_api_key: str | None = None  # falls back to openrouter_api_key

    # ADR-011c: CPU-resident primary (HF hub id — downloaded at worker startup by transformers).
    # Model swap is env-var change; provider swap is providers.py.
    moderation_primary_model: str = "Qwen/Qwen3-Guard-Gen-0.6B"
    # ADR-011c: text backstop on OpenRouter.
    moderation_backstop_model: str = "openai/gpt-oss-safeguard-20b"
    # ADR-011c / spec §4b-c: Gemma for image safety rubric (violence, gore, dangerous content).
    # Reuses the same model as vlm_judge_model; separate field so the two can diverge.
    moderation_backstop_image_model: str = "google/gemma-3-27b-it"


settings = Settings()

# ponytail: module-level dict — style presets are not env-driven; BaseSettings adds nothing here.
# Keys mirror the CHECK constraint in supabase/migrations/0002_jobs_style_preset_id.sql.
STYLE_PRESETS: dict[str, str] = {
    "cel": settings.default_style_fragment,
    "comic": "bold comic-book illustration, heavy ink outlines of varied weight, flat spot colours, ben-day halftone dot shading, limited palette, no gradients, no glow",
    "gouache": "flat gouache storybook illustration, thick confident ink outlines, matte paper grain, limited warm palette, flat colour fills, no gradients, no glossy highlights",
}

# Spec `docs/specs/image-generator.md` §4: ADR-025 D4 domain-level breaker.
# IMAGE_BUDGET derives from MAX_SCENES so both share one source of truth.
MAX_SCENES = 15
IMAGE_BUDGET = MAX_SCENES * 2 + 9   # 15 scenes × 2 + 9-image prelude (ADR-029)
# Spec `docs/specs/regeneration-controller.md` §4: LangGraph's graph-level backstop.
# ADR-024's formula — max_scenes × 4 + fixed_prelude. The ×4 is the deepest a single scene
# can go: generate_scene → consistency_check → regenerate → consistency_check. The prelude
# term is 9, the same one IMAGE_BUDGET uses (ADR-025 D4: the two backstops share one number).
# It is generous — today's prelude is 5 — as deliberate headroom for ADR-029's `reveal` node.
RECURSION_LIMIT = MAX_SCENES * 4 + 9

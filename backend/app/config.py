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

    # D-1 resolved (ADR-011c, 2026-07-21): the primary is Qwen3Guard-Gen 0.6B running on the
    # worker CPU — NOT an OpenRouter model id — so this field stays Llama Guard 4 (the demoted
    # fallback) until the Phase-2 `moderation-stack` spec defines the CPU-resident config shape.
    moderation_model: str = "meta-llama/llama-guard-4-12b"

    # D-1 resolved (ADR-011c): backstop is `openai/gpt-oss-safeguard-20b` on OpenRouter (the
    # ADR-011b pair — Qwen3Guard-Gen / Granite Guardian — is not routable there; verified
    # 2026-07-13). Left unset here so the Phase-0.5 probe (`spikes/phase_05.py`) stays opt-in;
    # the Phase-2 `moderation-stack` spec wires the real primary+backstop config shape.
    moderation_backstop_model: str | None = None


settings = Settings()

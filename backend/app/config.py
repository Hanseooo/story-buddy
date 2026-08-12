from pydantic import AliasChoices, Field
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

    langfuse_secret_key: str | None = None
    langfuse_public_key: str | None = None
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        validation_alias=AliasChoices("langfuse_host", "langfuse_base_url", "LANGFUSE_HOST", "LANGFUSE_BASE_URL"),
    )
    langfuse_project_id: str = ""

    # Model swap is an env-var change; provider swap is providers.py (ADR-001, ADR-002).
    # NOT a reasoning model. qwen/qwen3-32b was the default until 2026-08-11 and is proven broken
    # here: OpenRouter routed it to DeepInfra, which spent 1093 of 1497 completion tokens on
    # reasoning and returned JSON violating the strict schema (nested objects where `str` was
    # declared), because grammar-constrained decoding cannot be applied across a thinking block.
    # `provider.require_parameters` selects providers that ACCEPT response_format, not ones that
    # honour it — so the guard is the model choice, not the flag. See prod job af068baf.
    text_model: str = "mistralai/mistral-small-3.2-24b-instruct"
    vlm_judge_model: str = "google/gemma-3-27b-it"
    fal_image_model: str = "fal-ai/qwen-image"
    fal_image_edit_model: str = "fal-ai/qwen-image-edit-2511"

    # ADR-022's `cel` preset — "the flagship default kids see first" — authored 2026-07-21 in
    # backend/spikes/phase_05.py. This is ADR-007 as originally written (one fixed style). The
    # three-preset `style_presets` dict, `style_preset_id` resolution and the picker UI stay
    # wholly owned by the `style-presets` spec; `char_bible` only needs *a* fragment to exist.
    default_style_fragment: str = (
        "flat cel-shaded cartoon, thick clean black outlines of even weight, bright solid colour fills, "
        "two flat shadow tones, limited palette, no gradients, no glossy highlights, no airbrushing, "
        "no speech bubbles, no captions, no lettering"
    )

    # The judge moves to a self-hosted vLLM server after Phase 2.5 (ADR-019). vLLM speaks the
    # OpenAI protocol, so the swap is these two vars — no code change.
    judge_base_url: str = "https://openrouter.ai/api/v1"
    judge_api_key: str | None = None  # falls back to openrouter_api_key

    # ADR-032: Primary text guard on OpenRouter to prevent OOM.
    # Model swap is env-var change; provider swap is providers.py.
    moderation_primary_model: str = "meta-llama/llama-guard-4-12b"
    # ADR-032: Primary image guard on OpenRouter to prevent OOM (replaces Falconsai local model).
    # qwen/qwen3-vl-32b-instruct was the default until 2026-08-11; served by Alibaba Cloud it
    # emitted `is_safe` before `safety_reasoning`, which _assert_field_order rejects (ADR-004
    # reason-then-score) and which hard-failed the job at char_ref_mod. Mistral Small 3.2 is
    # multimodal and returned schema-compliant structured output first try in the same run.
    # Still a different family from the Gemma backstop, so the two-layer check keeps its diversity.
    moderation_primary_image_model: str = "mistralai/mistral-small-3.2-24b-instruct"
    # ADR-011c: text backstop on OpenRouter.
    moderation_backstop_model: str = "openai/gpt-oss-safeguard-20b"
    # ADR-011c / spec §4b-c: Gemma for image safety rubric (violence, gore, dangerous content).
    # Reuses the same model as vlm_judge_model; separate field so the two can diverge.
    moderation_backstop_image_model: str = "google/gemma-3-27b-it"


settings = Settings()

# ponytail: module-level dict — style presets are not env-driven; BaseSettings adds nothing here.
# Keys mirror the CHECK constraint in supabase/migrations/0002_jobs_style_preset_id.sql.
#
# Every fragment ends "no speech bubbles, no captions, no lettering". Prod job d83721d9's s2
# (2026-08-11) drew a speech balloon full of smeared pseudo-lettering: a child's story carries no
# dialogue to letter, so anything the model writes is invented and malformed. `comic` invites it
# hardest — "bold comic-book illustration" brings panels and balloons with the genre — but the
# other two could letter a page just as easily, so all three state it.
#
# ponytail: ADR-035 derives the description filter from these same `no <term>` clauses, so "bubbles"
# now also drops out of a child's character description — a story about a fish blowing bubbles
# loses that word from its draw prompt. Cheaper than the alternative (a second, hand-listed set of
# prohibitions that the model never sees) and it fails safe. If a preset ever needs a forbidden
# word back in descriptions, give `style_prohibitions` an exempt set rather than softening this.
STYLE_PRESETS: dict[str, str] = {
    "cel": settings.default_style_fragment,
    "comic": "bold comic-book illustration, heavy ink outlines of varied weight, flat spot colours, ben-day halftone dot shading, limited palette, no gradients, no glow, no speech bubbles, no captions, no lettering",
    "gouache": "flat gouache storybook illustration, thick confident ink outlines, matte paper grain, limited warm palette, flat colour fills, no gradients, no glossy highlights, no speech bubbles, no captions, no lettering",
}

# Spec `docs/specs/image-generator.md` §4: ADR-025 D4 domain-level breaker.
# IMAGE_BUDGET derives from MAX_SCENES so both share one source of truth.
MAX_SCENES = 15
# Spec `docs/specs/input-gate-hardening.md` §4a: the API-boundary length guard.
MIN_STORY_WORDS = 5     # a book needs at least one scene's worth of text
MAX_STORY_WORDS = 800   # ADR-012 range 500-800, top of range, tunable
IMAGE_BUDGET = MAX_SCENES * 2 + 9   # 15 scenes × 2 + 9-image prelude (ADR-029)
# Spec `docs/specs/regeneration-controller.md` §4: LangGraph's graph-level backstop.
# ADR-024's formula — max_scenes × 4 + fixed_prelude. The ×4 is the deepest a single scene
# can go: generate_scene → consistency_check → regenerate → consistency_check.
# ADR-029 reveal: 6 linear steps (input_gate·analyze·segment·char_bible·char_ref_mod·reveal)
# + 3 retry cycles of 3 super-steps each (char_bible·char_ref_mod·reveal) = 15. This prelude is
# a DIFFERENT unit from IMAGE_BUDGET's — they were only ever coincidentally equal at 9 (spec §4.13).
SUPER_STEP_PRELUDE = 15
RECURSION_LIMIT = MAX_SCENES * 4 + SUPER_STEP_PRELUDE

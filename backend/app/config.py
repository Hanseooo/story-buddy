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
    # "of even weight" dropped 2026-08-13. It is a constraint on the STROKE, and the way a model
    # satisfies it is to stop tapering — so a small feature gets the same stroke width as a torso
    # and fills in solid. Prod cel run: a character's ear came back with its outline doubled and
    # offset, and thin elements smooshed. `comic` asks for outlines "of varied weight" and draws
    # them cleanly, so the weight of the line was never the problem; pinning its uniformity was.
    default_style_fragment: str = (
        "flat cel-shaded cartoon, thick clean black outlines, bright solid colour fills, "
        "two flat shadow tones, limited palette, no gradients, no glossy highlights, no airbrushing"
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
# Every fragment used to end "no speech bubbles, no captions, no lettering", stated on all three
# after prod job d83721d9's s2 (2026-08-11) drew a speech balloon full of smeared pseudo-lettering.
# It did not work: a gouache page lettered again on 2026-08-13, and a cel run drew chat bubbles
# after that. Naming the thing is what summons it — `providers.NEGATIVE_PROMPT`'s comment, and the
# same finding that made `char_bible` stop calling its own output a "reference".
#
# The ban is not weaker, it moved: NEGATIVE_PROMPT carries all three terms plus "comic panels" on
# the channel that subtracts, and applies to every image this project draws rather than to the
# fragments only. `test_config` now asserts the inverse — no fragment may NAME a suppressed term.
#
# ponytail: ADR-035 still derives the description filter from the surviving `no <term>` clauses, so
# ADR-022 keeps sole ownership and a new preset arrives carrying its own. What the strip costs is
# that "bubbles"/"captions"/"lettering" no longer drop out of a child's own description — which the
# note here previously called out as a regretted side effect (the fish that loses its bubbles), so
# it reads as a second small win rather than a hole. A description that says "speech bubble" now
# reaches the prompt; NEGATIVE_PROMPT is the thing standing between it and the canvas.
#
# `gouache` asked for "thick confident ink outlines" from 2026-07-21 until 2026-08-13, and the model
# treated it as optional: the seed-21 picker sample has no keyline anywhere, while a prod gouache run
# came back fully outlined. Both are the same fragment on the same model. That ambiguity is not a
# per-page coin flip, which would merely look inconsistent — `char_bible` mints the canonical
# reference from this fragment and every page inherits it, so the flip happens ONCE and decides all
# twelve pages. The style picker cannot promise a child what it does not control.
#
# Stating the absence resolves it, and it is also the only axis the three presets genuinely differ
# on: strip outline treatment and `gouache` is `cel` with paper grain. `flat colour fills` stays —
# it was in the fragment that produced the sample this was written to reproduce.
#
# `comic`'s halftone was SCOPED to the backgrounds and shadows on 2026-08-14 — it was unscoped from
# 2026-07-21, and `frontend/public/style-presets/comic.png` shows where it went: screened over the
# character's own body and tail. That surface is the identity-bearing one, and two gates landed on
# 2026-08-13 that both read it. `wrong_colour` became GATING (`GATING_REASONS`), and a halftone
# screen tints by dot density — the same fill reads as a different colour at reference scale and at
# page scale, and in that sample the thin limbs came back solid black on a green character while one
# arm stayed outlined green. `text_free` also became gating, and `lettering-suppression.md:216`
# names ben-day halftone dots as the expected judge false positive. `comic` was the only preset
# feeding either.
#
# The halftone is NOT removed, and that is deliberate: ADR-022 makes `comic` the gating primary
# substrate *because* it is "textured enough (halftone) that the no-reference baseline can't fake the
# separation gate" (ADRs.md:1234, pre-registered at PHASE_05_RESULTS.md:512). Deleting the clause
# would make that gate lenient retroactively. Scoping it away from the subject keeps the texture in
# the picture while restoring ADR-022's own resolution — identity in the line, character in the fill.
#
# The outline clause is UNTOUCHED. "of varied weight" is the obvious suspect for the collapsed limbs
# and it is the one thing here that must not be pinned: `cel` lost "of even weight" the day before
# (see `default_style_fragment` above) precisely because pinning uniformity is what smooshes thin
# elements. Same defect, and the fix for it went the other way. If flat-colour scoping does not clear
# the black limbs, the next lever is the ink weight adjective, not its uniformity.
# ⚠️ UNMEASURED. No job has run against this fragment, and `comic.png` — the sample card a child
# picks from — was drawn with the unscoped fragment and now overstates the texture. Regenerating it
# is a paid fal draw and is NOT done here; until it is, the picker promises more screen than the
# pipeline delivers, which is the failure mode the `gouache` note above calls out.
STYLE_PRESETS: dict[str, str] = {
    "cel": settings.default_style_fragment,
    "comic": "bold comic-book illustration, heavy ink outlines of varied weight, flat spot colours, ben-day halftone dot shading in the backgrounds and shadows, the character itself in flat unscreened colour, limited palette, no gradients, no glow",
    "gouache": "flat gouache storybook illustration, no outlines, shapes formed by brushed colour, matte paper grain, limited warm palette, flat colour fills, no gradients, no glossy highlights",
    "cut_paper": "flat cut-paper storybook collage, clean simplified shapes with crisp cut edges, flat layered colour areas, limited warm palette, subtle paper fibre texture, no outlines, no gradients, no glossy highlights, no dimensional shadows",
}
SELECTABLE_STYLE_PRESET_IDS: frozenset[str] = frozenset({"cel", "gouache", "cut_paper"})

# Spec `docs/specs/image-generator.md` §4: ADR-025 D4 domain-level breaker.
# IMAGE_BUDGET derives from MAX_SCENES so both share one source of truth.
MAX_SCENES = 10
# Issue #31. MAX_SCENES was a ceiling with no floor, so `segment` shipped a page whose entire
# excerpt was `"Ana decided to help."` and another that was the story's title line. `build_prompt`
# passes the excerpt through verbatim (invariant 2, correct), so the image model filled the vacuum.
#
# 12 is the top of the safe band, not a midpoint. On the prod story the sentence lengths are
# bimodal — 4, 4 against 12, 15, 16, 17 — so every floor from 5 to 12 collapses the same two pages
# and no others. 13 would start eating that 12-word closing sentence, which was never the problem.
# Raise only against a story where a genuinely thin page survived; the mean sentence there was
# 11 words, and a floor above the mean stops being an outlier guard and becomes the pagination
# policy.
MIN_SCENE_WORDS = 12
# The guard that makes the floor safe to raise. A story of nothing but short sentences — which is
# what a 6-year-old writes — would otherwise merge down to a one-page book. Below this the floor
# is simply not enforced: pages matter more to the child than words per page.
# ponytail: a constant, not `len(timeline)`. The timeline is the story's real beat count and would
# be the better answer, but it is an LLM product that is sometimes empty, and this is the backstop.
MIN_SCENES = 3
# Spec `docs/specs/input-gate-hardening.md` §4a: the API-boundary length guard.
MIN_STORY_WORDS = 5     # a book needs at least one scene's worth of text
MAX_STORY_WORDS = 300   # spend-and-retry-economics spec §4.1 (moved from 800)
# 15-image prelude: 6 (2 refs × 3 draws) + 3 (ADR-029 taps) + 6 (one moderation redraw cycle,
# which re-mints every flagged ref at 3 draws each — `reference-moderation-retry.md` §4.5).
# Was 9 until 2026-08-13. `char_bible` carries NO breaker of its own and deliberately so: the
# prelude is bounded by MAX_MOD_REDRAWS and MAX_RETRY_TAPS, structurally, not by cost.
# 4 paid draws per scene (1 initial + 2 consistency retries + 1 output moderation redraw).
IMAGE_BUDGET = MAX_SCENES * 4 + 15   # 10 scenes × 4 + 15-image prelude = 55
# ADR-037: consistency-checked attempts per scene — the initial draw plus two corrected retries.
# The `* 4` above is this + 1 for output moderation's redraw; the `* 7` below is this × 2 + 1.
# Both formulas keep their spec'd literal shape (spend-and-retry-economics §4.3) rather than
# deriving from this name, so a reader checks the arithmetic against the spec without indirection.
MAX_SCENE_ATTEMPTS = 3


def check_image_budget(image_count: int) -> None:
    """ADR-025 D4: raise before any paid fal call. Every spend site calls this first."""
    if image_count >= IMAGE_BUDGET:
        raise RuntimeError(f"image budget exceeded: {image_count} >= {IMAGE_BUDGET} (ADR-025)")


# Spec `docs/specs/regeneration-controller.md` §4: LangGraph's graph-level backstop.
# ADR-024's formula — max_scenes × 7 + fixed_prelude. The ×7 is the deepest a single scene
# can go: generate_scene → consistency_check → regenerate → consistency_check → regenerate → consistency_check → output_mod.
# Moved from ×5 to ×7 on 2026-08-15 (spend-and-retry-economics spec §4.3).
# ADR-029 reveal: 6 linear steps (input_gate·analyze·segment·char_bible·char_ref_mod·reveal)
# + 3 retry cycles of 3 super-steps each (char_bible·char_ref_mod·reveal) = 15,
# + 2 for `reference-moderation-retry`'s one extra char_bible·char_ref_mod pair = 17.
# This prelude is a DIFFERENT unit from IMAGE_BUDGET's — they were only ever coincidentally
# equal at 9 (spec §4.13), and they are not equal now either. Do not raise one because the
# other moved.
SUPER_STEP_PRELUDE = 17
RECURSION_LIMIT = MAX_SCENES * 7 + SUPER_STEP_PRELUDE

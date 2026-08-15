import logging

from app.config import check_image_budget, settings
from app.db import get_supabase_client
from contracts.story_memory import Attempt, StoryMemory
from pipeline.prompt_optimizer import build_prompt, referenced_characters
from providers import edit_image, get_signed_url, text_to_image

log = logging.getLogger(__name__)

BUCKET = "storybook-images"


def _fal_ref_url(ref_path: str) -> str:
    """Give fal a fresh, short-lived signed URL for a canonical reference."""
    return get_signed_url(ref_path)


def generate_and_store(
    prompt: str, story_id: str, scene_id: str, attempt_n: int, ref_paths: list[str]
) -> tuple[str, bool]:
    """The node's ONE effect boundary (MASTER_SPEC §6). Returns (storage_path, paid).

    CC-10: if the path already exists in Storage, reuse it — a re-executed
    super-step is free. The Attempt is still appended by the caller.

    The path carries `attempt_n` (1-based) because ADR-010's best-of needs two DISTINCT
    objects: at a shared per-scene path the exists-skip above would hand attempt 2 back
    attempt 1's own bytes, and best-of would rank an image against itself. The skip stays
    correct — a re-executed super-step recomputes the same len(attempts) and the same path —
    it is just per-attempt idempotency now instead of per-scene.
    """
    path = f"{story_id}/{scene_id}-{attempt_n}.png"
    supabase = get_supabase_client()

    try:
        supabase.storage.from_(BUCKET).download(path)
        log.info("generate_scene: reusing existing %s (paid=False)", path)
        return path, False
    except Exception:
        pass

    fal_urls = [_fal_ref_url(r) for r in ref_paths]
    if fal_urls:
        image_bytes = edit_image(prompt, fal_urls)
    else:
        # ponytail: text-to-image path — no canonical references for this scene.
        # ADR-007's identity+style mechanism fires only when ref images are present.
        image_bytes = text_to_image(prompt)

    supabase.storage.from_(BUCKET).upload(
        path, image_bytes, {"content-type": "image/png", "upsert": "true"}
    )
    return path, True


def generate_scene(state: StoryMemory) -> dict:
    # ADR-024: loop position is the first scene with no final_image_ref — no cursor field.
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is None:
        return {}

    # ADR-025 D4: breaker before any spend. IMAGE_BUDGET = MAX_SCENES * 4 + 15.
    check_image_budget(state.cost.image_count)

    if not scene.visual_direction:
        raise ValueError(f"generate_scene: scene {scene.scene_id} has no visual_direction")

    # §4.1: `segment` wrote the id; this is the one place it is resolved back to the object.
    # A `location_id` absent from the roster resolves to None and the page simply gets no
    # `Setting:` line — the same posture as every other roster lookup in this pipeline.
    location = next((loc for loc in state.locations if loc.loc_id == scene.location_id), None)

    prompt = build_prompt(
        scene.text_excerpt,
        scene.characters_present,
        state.characters,
        state.style.prompt_fragment,
        location,
        scene.objects_present,
        state.objects,
        scene.visual_direction,
    )

    # Same list `build_prompt` numbered the image roll off, so "Image 2 is X" always names
    # ref_paths[1] (issue #23). build_prompt already logged any char_id missing from the roster.
    ref_paths = [
        c.canonical_ref_image
        for c in referenced_characters(scene.characters_present, state.characters)
    ]

    path, paid = generate_and_store(
        prompt, state.story_id, scene.scene_id, len(scene.attempts) + 1, ref_paths
    )

    log.info(
        "generate_scene: scene_id=%s refs=%d paid=%s prompt_len=%d image_model=%s",
        scene.scene_id,
        len(ref_paths),
        paid,
        len(prompt),
        settings.fal_image_model,
    )

    return {
        "scenes": [
            scene.model_copy(
                update={
                    "prompt": prompt,
                    # CC-5: per-attempt prompt provenance (ADR-010).
                    "attempts": [*scene.attempts, Attempt(image_ref=path, prompt=prompt, passed=False)],
                }
            )
        ],
        # Invariant 6: copy-and-bump, never rebuild from zero (char_bible §4 precedent).
        "cost": state.cost.model_copy(
            update={"image_count": state.cost.image_count + (1 if paid else 0)}
        ),
    }

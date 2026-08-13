"""ADR-010's one corrected retry (spec `docs/specs/regeneration-controller.md`).

The only place ADR-010 exists in code. When the judge fails a scene image, redraw it ONCE with a
prompt corrected from the failure reasons; `consistency_check` then keeps whichever attempt is
better. This node appends exactly one `Attempt` or raises — it never returns `{}`, because `{}`
leaves state unchanged, so `consistency_check` re-judges the same attempt, reaches the same
verdict, and `route_after_check` sends control straight back.

It imports `generate_and_store` rather than restating the effect boundary: the fal upload cache,
the Storage round-trip and the CC-10 exists-skip exist once, in `generate_scene`.
"""
import logging

from app.config import IMAGE_BUDGET
from contracts.story_memory import Attempt, StoryMemory
from pipeline.generate_scene import generate_and_store
from pipeline.prompt_optimizer import correct_prompt, referenced_characters

log = logging.getLogger(__name__)


def regenerate(state: StoryMemory) -> dict:
    # ADR-024: the SAME selection rule generate_scene and consistency_check use — no cursor.
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is None or not scene.attempts:
        # Invariant 1: unreachable given route_after_check's guard, and therefore RAISES rather
        # than returning {} — a silent no-op here is an infinite check ⇄ regenerate loop.
        raise RuntimeError(
            "regenerate: no unfinalized scene with attempts — route_after_check should never "
            "have routed here (ADR-010, invariant 1)"
        )

    last = scene.attempts[-1]
    if last.prompt is None and scene.prompt is None:
        # Unreachable today: generate_scene always sets both. Drawing from correction clauses
        # with no base prompt is a guaranteed-garbage PAID image, so ADR-025 hard-fails instead.
        raise RuntimeError(f"regenerate: scene {scene.scene_id} has no prompt to correct (ADR-025)")

    # ADR-025 D4: breaker before any spend. A retry is not exempt.
    if state.cost.image_count >= IMAGE_BUDGET:
        raise RuntimeError(
            f"image budget exceeded: {state.cost.image_count} >= {IMAGE_BUDGET} (ADR-025)"
        )

    # The retry is conditioned on the same references as the original, or it would be measuring a
    # different thing. `correct_prompt` only appends (invariant 3), so the corrected prompt still
    # carries build_prompt's numbered roll — "Image 2 is X" is asserted against THIS list, which is
    # why it has to be the same list, not a copy of the same rule (issue #23).
    ref_paths = [
        c.canonical_ref_image
        for c in referenced_characters(scene.characters_present, state.characters)
    ]

    # Invariant 5: every reachable path appends at least one clause. The three booleans cover the
    # holes the frozen 7 leave — anatomy and lettering are outside FailureReason entirely (ADR-028),
    # and a same_character failure can arrive with no reason named. A prompt identical to the
    # previous attempt's would be resampling, which ADR-010 rejects.
    #
    # A reason that IS named no longer proves the invariant on its own: `correct_prompt` drops a
    # clause whose axis is empty, so the guarantee now comes from its floor rather than from the
    # reason list being non-empty. Same invariant, enforced one level down.
    v = last.vlm_verdict
    identity_clause = not (v.same_character if v else True) and not last.failure_reasons
    anatomy_clause = not (v.anatomy_intact if v else True)
    text_clause = not (v.text_free if v else True)
    prompt = correct_prompt(
        last.prompt or scene.prompt,
        last.failure_reasons,
        state.characters,
        state.style.prompt_fragment,
        same_character=v.same_character if v else True,
        anatomy_intact=v.anatomy_intact if v else True,
        text_free=v.text_free if v else True,
    )

    attempt_n = len(scene.attempts) + 1
    path, paid = generate_and_store(
        prompt, state.story_id, scene.scene_id, attempt_n, ref_paths
    )

    # CC-5: one line per regeneration. Without the clause flags there is no way to tell a
    # correction that fired from one that silently appended nothing.
    #
    # `identity_clause` reports THIS node's condition — the judge failed identity and named no
    # reason. `correct_prompt` has a second route to the same clause (every named reason turned out
    # unfillable) which this flag deliberately does not try to predict; it logs that route itself,
    # on the line immediately above this one.
    log.info(
        "regenerate: scene_id=%s attempt_n=%d failure_reasons=%s same_character=%s "
        "anatomy_intact=%s text_free=%s identity_clause=%s anatomy_clause=%s text_clause=%s "
        "paid=%s prompt_len=%d",
        scene.scene_id, attempt_n, [r.value for r in last.failure_reasons],
        v and v.same_character, v and v.anatomy_intact, v and v.text_free,
        identity_clause, anatomy_clause, text_clause, paid, len(prompt),
    )

    return {
        "scenes": [
            scene.model_copy(
                update={
                    # Invariants 2, 3, 7: final_image_ref, scenes[].prompt and
                    # regeneration_count are all deliberately absent from this update.
                    "attempts": [*scene.attempts, Attempt(image_ref=path, prompt=prompt, passed=False)],
                }
            )
        ],
        # Invariant 6: image_count is gated on `paid`, regen_count is NOT. On an ADR-025 resume
        # the checkpoint predates this return, so both start from their pre-regenerate values:
        # +0 correctly records the Storage skip meant no re-pay, +1 correctly records the
        # regeneration whose increment the lost checkpoint never persisted.
        "cost": state.cost.model_copy(
            update={
                "image_count": state.cost.image_count + (1 if paid else 0),
                "regen_count": state.cost.regen_count + 1,
            }
        ),
    }

import hashlib
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid5

from app.config import check_image_budget, settings
from app.moderation_policy import TEACHER_MODERATION_CRITERIA
from contracts.story_memory import Attempt, ClassifierEvidence, ReviewContext, StoryMemory
from pipeline.generate_scene import generate_and_store
from pipeline.prompt_optimizer import referenced_characters
from providers import (
    IMAGE_BACKSTOP_INSTRUCTION_VERSION, IMAGE_PRIMARY_INSTRUCTION_VERSION,
    ModerationEvidenceError,
    classify_image_backstop, classify_image_primary, download_book_image, get_signed_url,
)

log = logging.getLogger(__name__)

# The one verdict an operator may override: the backstop refusing what the primary called safe.
# Kept as the literal `_check_image` returns so the two cannot drift apart silently.
BACKSTOP_ALONE = "backstop (primary said safe)"
OVERRIDE_STATUS = "passed_operator_override"


def _check_image(image_url: str, evidence: list[ClassifierEvidence] | None = None) -> str | None:
    """`None` if the image is safe, else a log label naming the classifier that flagged it.

    Posture mirrors `char_ref_mod` (spec §4b, aligned with
    `input_gate` on 2026-08-11): a PRIMARY classifier error degrades to backstop-only, a primary
    flag short-circuits, and a BACKSTOP error propagates — the callers turn that into
    `moderation_error`, which is still correct because the backstop has nothing behind it.

    §4c step 2 always said "same two-classifier check as `char_ref_mod`", but 44489cb aligned
    `input_gate` and `char_ref_mod` and missed this node, which left it hard-failing on ANY
    classifier exception. That made it the strictest gate in the pipeline while screening the
    least risky thing — an image we drew, from text `input_gate` passed, from a reference
    `char_ref_mod` passed — at the point where every scene has already been paid for.

    Prod job f4d0fd74 died exactly there: scene s5, OpenRouter 400 from Venice
    ("Image content is not supported by this model"), five scenes already moderated clean.
    """
    primary_time = datetime.now(timezone.utc)
    primary_model = settings.moderation_primary_image_model
    primary_reasons = []
    try:
        primary_safe = (classify_image_primary(image_url, reasons=primary_reasons)
                        if evidence is not None else classify_image_primary(image_url))
    except ModerationEvidenceError:
        raise
    except Exception as exc:
        log.warning("output_mod: primary classifier failed (%s) — falling back to backstop", exc)
        primary_safe = None  # None = primary errored, not "passed"

    if evidence is not None:
        evidence.append(ClassifierEvidence(
            layer="primary", model_id=primary_model,
            instruction_version=IMAGE_PRIMARY_INSTRUCTION_VERSION,
            outcome="error" if primary_safe is None else "safe" if primary_safe else "flagged",
            checked_at=primary_time,
            reason=primary_reasons[0] if primary_reasons else None,
        ))
    if primary_safe is False:
        # A second opinion cannot change a flag (spec §4a step 3).
        if evidence is not None:
            evidence.append(ClassifierEvidence(
                layer="backstop", model_id=settings.moderation_backstop_image_model,
                instruction_version=IMAGE_BACKSTOP_INSTRUCTION_VERSION, outcome="not_called",
            ))
        return "primary"

    backstop_time = datetime.now(timezone.utc)
    backstop_model = settings.moderation_backstop_image_model
    backstop_reasons = []
    backstop_safe = (classify_image_backstop(image_url, reasons=backstop_reasons)
                     if evidence is not None else classify_image_backstop(image_url))
    if evidence is not None:
        evidence.append(ClassifierEvidence(
            layer="backstop", model_id=backstop_model,
            instruction_version=IMAGE_BACKSTOP_INSTRUCTION_VERSION,
            outcome="safe" if backstop_safe else "flagged", checked_at=backstop_time,
            reason=backstop_reasons[0] if backstop_reasons else None,
        ))
    if backstop_safe:
        return None

    # WHICH classifier flagged, and whether the other was even consulted, is the whole diagnosis
    # when a book dies here (CC-5: "log classifier name, verdict, and latency per call" — this node
    # logged neither name nor verdict). `char_ref_mod:57` already logs both; only this node, which
    # hides the posture behind this helper, threw the answer away.
    #
    # Prod job 4f7698d5 (2026-08-12) is the case: s2 flagged twice while the primary image model
    # was 429ing on OpenRouter's shared free pool, and nothing in the log could say whether that was
    # two classifiers agreeing or gemma-3-27b deciding alone.
    return "backstop (primary said safe)" if primary_safe else "backstop (primary errored)"


def _soften_prompt(prompt: str) -> str:
    # ponytail: stock softening — prepend safety qualifier. Owned here, not by `self-refusal-fallback`
    # (that spec covers the model *refusing*; this is the model complying and the classifier flagging).
    # Upgrade path: if flagged scenes survive this retry in practice, borrow that spec's softener.
    return f"child-safe, gentle, age-appropriate illustration, no violence or inappropriate content: {prompt}"


def output_mod(state: StoryMemory) -> dict:
    updated_scenes = []
    current_image_count = state.cost.image_count

    for scene in state.scenes:
        if scene.moderation_status in {"passed", OVERRIDE_STATUS} or (
            state.moderation_context.mode == "teacher_review_v1" and scene.moderation_status == "teacher_allowed"
        ):
            # Screened on an earlier turn of the loop. This node now runs once per finalized scene
            # rather than once over the finished book (see `route_next_scene`), so without this it
            # would re-pay for a classifier call per already-cleared scene, per scene, per book.
            updated_scenes.append(scene)
            continue

        if scene.final_image_ref is None:
            # Regeneration controller owns unresolved refs (spec §4c edge case).
            updated_scenes.append(scene)
            continue

        signed_url = get_signed_url(scene.final_image_ref)

        evidence = [] if state.moderation_context.mode == "teacher_review_v1" else None
        try:
            flagged_by = _check_image(signed_url, evidence)
        except Exception as exc:
            log.error("output_mod: scene_id=%s classifier error (%s)", scene.scene_id, exc)
            raise RuntimeError("moderation_error") from exc

        if flagged_by is None:
            log.info("output_mod: scene_id=%s passed", scene.scene_id)
            changes = {"moderation_status": "passed"}
            if evidence is not None:
                changes["attempts"] = [
                    a.model_copy(update={"safety_eligibility": "cleared"})
                    if a.image_ref == scene.final_image_ref else a for a in scene.attempts
                ]
            updated_scenes.append(scene.model_copy(update=changes))
            continue

        if evidence is not None:
            subject_version = hashlib.sha256(download_book_image(scene.final_image_ref)).hexdigest()
            review_id = uuid5(
                UUID(state.story_id),
                f"scene_image:{scene.scene_id}:{subject_version}:{state.moderation_context.generation_epoch}",
            )
            review = ReviewContext(
                review_id=review_id, kind="scene_image", subject_id=scene.scene_id,
                subject_version=subject_version, return_node="output_mod", classifier_evidence=evidence,
                criteria=list(TEACHER_MODERATION_CRITERIA),
                replacement=bool(scene.moderation_replacement_count),
            )
            return {
                "scenes": updated_scenes + [scene],
                "moderation_context": state.moderation_context.model_copy(update={"review": review}),
                "cost": state.cost.model_copy(update={"image_count": current_image_count}),
            }

        # ADR-025 D4: breaker before any spend.
        check_image_budget(current_image_count)

        # One soften-and-retry (spec §4c step 4).
        log.info(
            "output_mod: scene_id=%s flagged by %s — softening and retrying",
            scene.scene_id, flagged_by,
        )
        softened = _soften_prompt(scene.prompt or "")

        # `_soften_prompt` prepends, so the softened prompt still carries build_prompt's numbered
        # roll — "Image 2 is X" is asserted against THIS list (issue #23). Same list, not a copy of
        # the same rule.
        ref_paths = [
            c.canonical_ref_image
            for c in referenced_characters(scene.characters_present, state.characters)
        ]

        retry_n = len(scene.attempts) + 1
        retry_path, paid = generate_and_store(softened, state.story_id, scene.scene_id, retry_n, ref_paths)
        if paid:
            current_image_count += 1

        log.info(
            "output_mod: scene_id=%s retry image paid=%s image_count=%d",
            scene.scene_id, paid, current_image_count,
        )

        retry_url = get_signed_url(retry_path)

        try:
            retry_flagged_by = _check_image(retry_url)
        except Exception as exc:
            log.error("output_mod: scene_id=%s retry classifier error (%s)", scene.scene_id, exc)
            raise RuntimeError("moderation_error") from exc

        if retry_flagged_by is None:
            log.info("output_mod: scene_id=%s retry passed", scene.scene_id)
            updated_scenes.append(scene.model_copy(update={
                "final_image_ref": retry_path,
                "moderation_status": "passed",
                # passed=False, not True: `passed` is the CONSISTENCY verdict (it sits beside
                # `vlm_verdict`), and no judge ran on this image — `route_next_scene` sends a
                # moderated scene onward, never back to `consistency_check`. With no verdict
                # either way, `compose.outcome()` reports this page `unchecked`, which is what
                # it is. Whether an unjudged image should ship at all is a routing question and
                # an ADR decision (#78); this line only stops the record from claiming a
                # verdict that was never issued.
                "attempts": [*scene.attempts, Attempt(image_ref=retry_path, prompt=softened, passed=False)],
            }))
        elif (
            retry_flagged_by == BACKSTOP_ALONE
            and f"{state.story_id}:{scene.scene_id}" in settings.scene_moderation_overrides
        ):
            # Only reachable when a human has already looked at this scene and named it. The
            # status is deliberately not "passed": the classifier did refuse, and the bundle has
            # to carry that rather than launder it into a clean verdict.
            log.warning(
                "output_mod: scene_id=%s flagged by %s after retry — accepted on operator override",
                scene.scene_id, retry_flagged_by,
            )
            updated_scenes.append(scene.model_copy(update={
                "final_image_ref": retry_path,
                "moderation_status": OVERRIDE_STATUS,
                "attempts": [*scene.attempts, Attempt(image_ref=retry_path, prompt=softened, passed=False)],
            }))
        else:
            log.error(
                "output_mod: scene_id=%s still flagged by %s after retry — "
                "route_after_output_mod will fail job",
                scene.scene_id, retry_flagged_by,
            )
            updated_scenes.append(scene.model_copy(update={
                # NOT retry_path: `final_image_ref` is the image the book uses, and this one was
                # just flagged. `consistency_check` writes None when no attempt wins; same here.
                # The path is not lost — the flagged attempt is recorded below with passed=False.
                "final_image_ref": None,
                "moderation_status": "failed",
                "attempts": [*scene.attempts, Attempt(image_ref=retry_path, prompt=softened, passed=False)],
            }))

    return {
        "scenes": updated_scenes,
        "cost": state.cost.model_copy(update={"image_count": current_image_count}),
    }

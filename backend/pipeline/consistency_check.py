"""Judges each scene image against the canonical references it was drawn from
(spec `docs/specs/consistency-checker.md`).

This is where ADR-004's control signal fires and where ADR-024's loop invariant — exactly one
scene finalizes per pass — gets its teeth. It never raises: a failing judge or Storage download
means *unchecked*, and the page still ships (ADR-010, ADR-025).
"""
import base64
import logging

from pydantic import BaseModel, Field

from app.db import get_supabase_client
from contracts.story_memory import FailureReason, StoryMemory, VlmVerdict
from providers import judge

log = logging.getLogger(__name__)

BUCKET = "storybook-images"

# Reason-then-score (ADR-004). The prompt asks in exactly the order the schema declares, and
# `providers._assert_field_order` rejects a provider that answers out of order.
JUDGE_PROMPT = """\
The FIRST image is the canonical character reference for {name}. The SECOND image is one page of \
the same picture book, in which {name} should appear drawn to match that reference.

First describe every difference you observe between {name} on the page and the reference. Then \
say whether it is the same character; list which of the reference's attributes are actually \
present on the page; whether the art style matches the reference; and whether the character's \
anatomy is intact, meaning no merged, missing or duplicated body parts. Finally list the failure \
reasons that apply, choosing only from the fixed set."""


class SceneVerdict(BaseModel):
    """Node-local judge boundary schema (ADR-023 D-F). `StoryMemory` stores the verdict and the
    failure reasons as SEPARATE fields, so the combined wire shape is not in the contract.

    Field order mirrors `VlmVerdict` exactly, then appends — mapping to `VlmVerdict` is a
    field-subset copy. `FailureReason` has one home (ADR-028) and is imported, never restated.
    """
    differences_observed: str                    # FIRST — ADR-004 reason-then-score
    same_character: bool
    attributes_present: list[str] = Field(default_factory=list)
    style_match: bool = False
    anatomy_intact: bool = True
    failure_reasons: list[FailureReason] = Field(default_factory=list)   # LAST — the closed 7


def _data_uri(image: bytes) -> str:
    # ponytail: inline base64, same as `char_bible._data_uri`. The judge is shown base64,
    # never a signed URL (CC-4). What is PERSISTED is the path.
    return "data:image/png;base64," + base64.b64encode(image).decode()


def judge_attempt(image_path: str, subjects: list[tuple[str, str]]) -> list[SceneVerdict]:
    """The node's ONE effect boundary (MASTER_SPEC §6). Storage downloads live INSIDE it.

    `(character name, reference path)` → one `SceneVerdict` each, in subject order.

    Returns `[]` for empty subjects AND for any judge/Storage failure — both mean *unchecked*,
    and the node treats them identically, so distinguishing them here would buy nothing.
    """
    if not subjects:
        return []

    try:
        storage = get_supabase_client().storage.from_(BUCKET)
        scene_uri = _data_uri(storage.download(image_path))
        return [
            # One call per character against its OWN reference (ADR-004, invariant 5).
            judge(JUDGE_PROMPT.format(name=name), [_data_uri(storage.download(ref)), scene_uri], SceneVerdict)
            for name, ref in subjects
        ]
    except Exception:
        # ADR-025: the CHECK failed, not the artifact. char_bible's deliberate asymmetry.
        log.warning(
            "consistency_check: judge/Storage failed for %s — attempt stays unchecked", image_path, exc_info=True
        )
        return []


def consistency_check(state: StoryMemory) -> dict:
    """Pure: select, fold, gate, partial-return. Every effect is behind `judge_attempt`.

    Finalizes on EVERY path — pass, fail, or unchecked. With no `regenerate` node, ADR-010's
    best-of degenerates to the single attempt, which is still a real image and still better than
    a placeholder. `regeneration-controller` inserts the branch ahead of finalization.
    """
    # ADR-024: the SAME selection rule generate_scene uses — first scene with no final_image_ref.
    # generate_scene leaves the scene unfinalized, so this node finds the one it just drew.
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is None:
        return {}
    if not scene.attempts:
        # Unreachable in the linear flow (generate_scene either appended one or raised).
        log.warning("consistency_check: scene %s has no attempts — nothing to judge", scene.scene_id)
        return {}

    attempt = scene.attempts[-1]   # Invariant 3: only the last attempt is judged and mutated.

    by_id = {c.char_id: c for c in state.characters}
    subjects: list[tuple[str, str]] = []
    for char_id in scene.characters_present:
        character = by_id.get(char_id)
        if character is None:
            log.warning(
                "consistency_check: char_id %r in characters_present but absent from state.characters, skipped",
                char_id,
            )
        elif character.canonical_ref_image:
            # ADR-028: a failing ref_verdict still ships its reference, so it is still the thing
            # this scene was drawn from and still the thing consistency is measured against.
            subjects.append((character.name, character.canonical_ref_image))

    verdicts = judge_attempt(attempt.image_ref, subjects)

    verdict: VlmVerdict | None = None
    reasons: list[FailureReason] = []
    if verdicts:
        # Worst-wins fold (spec §4). Booleans conjoin; lists union, deduped, order preserved.
        seen = {reason for v in verdicts for reason in v.failure_reasons}
        reasons = [reason for reason in FailureReason if reason in seen]   # declaration order —
        # the order correct_prompt iterates, so any other order silently reorders its clauses.
        verdict = VlmVerdict(
            differences_observed="\n".join(
                f"{name}: {v.differences_observed}" for (name, _), v in zip(subjects, verdicts)
            ),
            same_character=all(v.same_character for v in verdicts),
            attributes_present=list(dict.fromkeys(a for v in verdicts for a in v.attributes_present)),
            style_match=all(v.style_match for v in verdicts),
            anatomy_intact=all(v.anatomy_intact for v in verdicts),
        )

    # The pass rule: the two failures a child notices — wrong character, or three arms. style_match
    # is recorded and available to regeneration-controller's ranking but does NOT gate (ADR-007).
    # Invariant 4: unchecked is never a pass.
    passed = verdict is not None and verdict.same_character and verdict.anatomy_intact

    # CC-5: a wrong character in the finished book traces to a scene, an attempt, and the verdict
    # that let it through.
    log.info(
        "consistency_check: scene_id=%s subjects=%d %s same_character=%s anatomy_intact=%s "
        "style_match=%s failure_reasons=%s passed=%s",
        scene.scene_id, len(subjects), "checked" if verdict else "unchecked",
        verdict and verdict.same_character, verdict and verdict.anatomy_intact,
        verdict and verdict.style_match, [r.value for r in reasons], passed,
    )

    return {
        "scenes": [
            scene.model_copy(
                update={
                    "attempts": [
                        *scene.attempts[:-1],
                        attempt.model_copy(
                            update={"vlm_verdict": verdict, "failure_reasons": reasons, "passed": passed}
                        ),
                    ],
                    # Invariant 2: this node, and only this node, finalizes a scene.
                    "final_image_ref": attempt.image_ref,
                }
            )
        ]
    }

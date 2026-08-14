"""Judges each scene image against the canonical references it was drawn from
(spec `docs/specs/consistency-checker.md`).

This is where ADR-004's control signal fires and where ADR-024's loop invariant — exactly one
scene finalizes per pass — gets its teeth. It never raises: a failing judge or Storage download
means *unchecked*, and the page still ships (ADR-010, ADR-025).
"""
import base64
import logging

from pydantic import BaseModel, Field

from app.config import settings
from app.db import get_supabase_client
from contracts.story_memory import Attempt, FailureReason, StoryMemory, VlmVerdict
from providers import judge

log = logging.getLogger(__name__)

BUCKET = "storybook-images"

# ponytail: a module constant plus the existing log line, NOT a persisted `Attempt` field —
# that would be a third contract change for a problem logs already make traceable. Bump it on
# every wording change; the ADR-028-style hit rate is only comparable within one version, and the
# 2026-08-11 rewording already cost this project a whole discarded series. Upgrade path: if a
# measurement series ever has to be reconstructed from checkpoints rather than logs, promote this
# to an `Attempt` field the way `Character.ref_verdict_prompt_version` was promoted.
# 1 = pre-2026-08-13; 2 = adds the uniqueness question (scene-setting-and-subject-binding §4.4);
# 3 = adds the text question (lettering-suppression §4.1) — v2 and earlier carry no lettering
# signal at all, so the rate series starts at v3.
JUDGE_PROMPT_VERSION = 3

# Reason-then-score (ADR-004). The prompt asks in exactly the order the schema declares, and
# `providers._assert_field_order` rejects a provider that answers out of order.
#
# The style question names what to ignore. Unscoped ("whether the art style matches the reference")
# it read False on 100% of prod job b9506307's 7 scenes, because the two images it compares differ
# by construction: `char_bible.REFERENCE_PROMPT` draws one character on a plain neutral background,
# and a page is a full illustration with scenery and a crop. The judge's own
# `differences_observed` answered about hair-strand detail, freckle rendering and background —
# never about drawing technique — so the field measured "are these two images rendered alike",
# which no scene page can satisfy. Re-judged on that job's own images (issue #24, 2026-08-11,
# 3 runs per cell): unscoped read True 1/6 on a matching comic ref+page pair; scoped reads 3/3.
# Both read 0/3 on a cel reference against the same comic page, so the signal still discriminates
# a real style break — the point of scoping is that it now ONLY discriminates that.
JUDGE_PROMPT = """\
The FIRST image is the canonical character reference for {name}. The SECOND image is one page of \
the same picture book, in which {name} should appear drawn to match that reference.

First describe every difference you observe between {name} on the page and the reference. Then \
say whether it is the same character; list which of the reference's attributes are actually \
present on the page; whether the page is drawn in the same art style as the reference — the same \
linework, shading and colouring technique — ignoring background, composition, pose, crop and \
expression; whether the character's anatomy is intact, meaning no merged, missing or \
duplicated body parts; and whether {name} is drawn exactly once — count only {name} itself, not \
other things of the same kind that the scene simply contains; and whether the picture is free of \
any text — any letters, numbers or writing anywhere in it, including on signs, doors, books and \
clothing. Finally list the failure reasons that apply, choosing only from the fixed set."""


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
    subjects_unique: bool = True                 # §4.4 — asked after anatomy, before the reasons
    text_free: bool = True                       # lettering-suppression §4.1 — asked LAST of the
                                                 # booleans, still before the reasons
    failure_reasons: list[FailureReason] = Field(default_factory=list)   # LAST — the closed 7


SCENE_CONSTRAINT_PROMPT_VERSION = 1

SCENE_CONSTRAINT_PROMPT = """\
The image is one page of a children's picture book. Check it only against the exact scene \
constraints below.

{constraints}

First describe every observed difference from those constraints. Then list each contradiction \
separately. Every contradiction must name the subject and the violated requirement. Check that \
every expected visible character appears exactly once, no unrequested character appears, every \
text-only character matches its frozen profile, each visible object matches its frozen appearance \
and current holder, and the action, movement direction and viewpoint match Visual direction. \
Leave contradictions empty only when every check is clean."""


class SceneConstraintVerdict(BaseModel):
    differences_observed: str
    contradictions: list[str] = Field(default_factory=list)


# The two identity-bearing attribute reasons. Both GATE (2026-08-13); the other five do not.
#
# Prod job 483056e0 shipped `s3` with `['wrong_colour', 'wrong_clothing']` and `s4` with
# `['wrong_colour', 'wrong_body_feature', 'wrong_clothing', 'wrong_style']`, both `passed=True`:
# the judge had already found the dragon off-model and the gate had no term for it, because a
# green dragon is still `same_character=True`. Colour and body features are what a child uses to
# recognise a non-human character across pages — the dragon has no face to fail `different_face`
# on and no clothes to fail `wrong_clothing` on.
#
# `wrong_clothing` and `wrong_style` are deliberately EXCLUDED. Both have a live false-positive
# story: a sash reading differently under gouache lighting, and `style_match` reading False by
# construction (issue #24), and the cost of a false gate is a paid redraw. `wrong_species` and
# `different_face` need no entry — `same_character` already covers both.
#
# Not a contract change: `FailureReason` stays frozen at 7 (ADR-028). This is a subset of the
# existing closed set, read at the gate.
GATING_REASONS = frozenset({FailureReason.wrong_colour, FailureReason.wrong_body_feature})


def _data_uri(image: bytes) -> str:
    # ponytail: inline base64, same as `char_bible._data_uri`. The judge is shown base64,
    # never a signed URL (CC-4). What is PERSISTED is the path.
    return "data:image/png;base64," + base64.b64encode(image).decode()


def judge_attempt(
    image_path: str,
    subjects: list[tuple[str, str]],
    constraint_prompt: str,
) -> tuple[list[SceneVerdict] | None, SceneConstraintVerdict | None]:
    """The node's ONE effect boundary (MASTER_SPEC §6). Storage downloads live INSIDE it.

    `(character name, reference path)` → identity verdicts.
    `constraint_prompt` → composition verdict.
    """
    try:
        storage = get_supabase_client().storage.from_(BUCKET)
        scene_uri = _data_uri(storage.download(image_path))
    except Exception:
        log.warning(
            "consistency_check: scene Storage failed for %s; both checks unavailable",
            image_path,
            exc_info=True,
        )
        return None, None

    identity: list[SceneVerdict] | None = []
    if subjects:
        try:
            identity = [
                judge(
                    JUDGE_PROMPT.format(name=name),
                    [_data_uri(storage.download(ref)), scene_uri],
                    SceneVerdict,
                )
                for name, ref in subjects
            ]
        except Exception:
            log.warning(
                "consistency_check: identity judge/Storage failed for %s",
                image_path,
                exc_info=True,
            )
            identity = None

    try:
        composition = judge(
            SCENE_CONSTRAINT_PROMPT.format(constraints=constraint_prompt),
            [scene_uri],
            SceneConstraintVerdict,
        )
    except Exception:
        log.warning(
            "consistency_check: scene-constraint judge failed for %s",
            image_path,
            exc_info=True,
        )
        composition = None

    return identity, composition


def _rank(a: Attempt) -> tuple[int, int, int, int, int, int, int, int, int]:
    """ADR-028's lexicographic best-of signal, with unchecked sorting below every checked attempt.

    A pass scores (1, 1, 1, …) and beats anything that gated, so `max` needs no special case for
    it. Unchecked scores all zeros: promoting an unjudged image over a judged one would let a
    judge outage silently decide the page, contradicting invariant 4 (unchecked is never a pass).
    """
    verdict = a.vlm_verdict
    contradictions = a.scene_contradictions
    checked = verdict is not None or contradictions is not None
    return (
        checked,
        True if verdict is None else verdict.same_character,
        True if verdict is None else verdict.anatomy_intact,
        True if verdict is None else verdict.text_free,
        not (GATING_REASONS & set(a.failure_reasons)),
        contradictions == [],
        -len(contradictions or []),
        True if verdict is None else verdict.subjects_unique,
        True if verdict is None else verdict.style_match,
    )


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

    identity_verdicts, composition = judge_attempt(
        attempt.image_ref, subjects, attempt.prompt or scene.prompt or ""
    )

    verdict: VlmVerdict | None = None
    reasons: list[FailureReason] = []
    if identity_verdicts:
        # Worst-wins fold (spec §4). Booleans conjoin; lists union, deduped, order preserved.
        seen = {reason for v in identity_verdicts for reason in v.failure_reasons}
        reasons = [reason for reason in FailureReason if reason in seen]   # declaration order —
        # the order correct_prompt iterates, so any other order silently reorders its clauses.
        verdict = VlmVerdict(
            differences_observed="\n".join(
                f"{name}: {v.differences_observed}" for (name, _), v in zip(subjects, identity_verdicts)
            ),
            same_character=all(v.same_character for v in identity_verdicts),
            attributes_present=list(dict.fromkeys(a for v in identity_verdicts for a in v.attributes_present)),
            style_match=all(v.style_match for v in identity_verdicts),
            anatomy_intact=all(v.anatomy_intact for v in identity_verdicts),
            subjects_unique=all(v.subjects_unique for v in identity_verdicts),
            text_free=all(v.text_free for v in identity_verdicts),
        )

    identity_applicable = bool(subjects)
    identity_available = not identity_applicable or identity_verdicts is not None
    identity_clean = not identity_applicable or (
        verdict is not None
        and verdict.same_character
        and verdict.anatomy_intact
        and verdict.text_free
        and not (GATING_REASONS & set(reasons))
    )
    scene_contradictions = None if composition is None else composition.contradictions
    composition_clean = scene_contradictions == []

    passed = identity_available and identity_clean and composition_clean
    concrete_failure = (
        (identity_applicable and verdict is not None and not identity_clean)
        or bool(scene_contradictions)
    )
    finalize = passed or not concrete_failure or len(scene.attempts) >= 2

    updated = [
        *scene.attempts[:-1],
        attempt.model_copy(
            update={
                "vlm_verdict": verdict,
                "failure_reasons": reasons,
                "scene_contradictions": scene_contradictions,
                "passed": passed,
            }
        ),
    ]

    best = max(reversed(range(len(updated))), key=lambda i: _rank(updated[i])) if finalize else None

    ref_prompt_versions = sorted(
        {
            character.ref_verdict_prompt_version
            for character in state.characters
            if character.ref_verdict_prompt_version is not None
        }
    )
    log.info(
        "consistency_check: scene_id=%s attempt=%d/2 roster_ids=%s visible_cast=%s "
        "visible_objects=%s visual_direction=%r identity_available=%s "
        "scene_constraint_available=%s same_character=%s anatomy_intact=%s text_free=%s "
        "subjects_unique=%s style_match=%s failure_reasons=%s scene_contradictions=%s "
        "passed=%s finalize=%s best_of=%s ref_prompt_versions=%s "
        "identity_prompt_version=%d scene_constraint_prompt_version=%d judge_model=%s",
        scene.scene_id,
        len(updated),
        [character.char_id for character in state.characters],
        scene.characters_present,
        scene.objects_present,
        scene.visual_direction,
        identity_available,
        composition is not None,
        verdict and verdict.same_character,
        verdict and verdict.anatomy_intact,
        verdict and verdict.text_free,
        verdict and verdict.subjects_unique,
        verdict and verdict.style_match,
        [reason.value for reason in reasons],
        scene_contradictions,
        passed,
        finalize,
        None if best is None else best + 1,
        ref_prompt_versions,
        JUDGE_PROMPT_VERSION,
        SCENE_CONSTRAINT_PROMPT_VERSION,
        settings.vlm_judge_model,
    )

    return {
        "scenes": [
            scene.model_copy(
                update={
                    "attempts": updated,
                    # Invariant 2: this node, and only this node, finalizes a scene.
                    "final_image_ref": None if best is None else updated[best].image_ref,
                }
            )
        ]
    }

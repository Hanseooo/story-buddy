"""The character reveal (spec `docs/specs/kid-flow-pause-lifecycle.md`, ADR-029).

Performs no effect. Its entire body is a pure projection and one `interrupt()` call — no
provider call, no upload, no write outside its partial return (invariant 9). That property is
the reason it is a dedicated node rather than folded into `char_bible`: LangGraph re-executes a
resumed node from the top, so an `interrupt()` inside `char_bible` would redraw every reference
on each confirm.
"""
import hashlib
from uuid import UUID, uuid5

from langgraph.types import interrupt

from app.config import settings
from app.moderation_policy import TEACHER_MODERATION_CRITERIA
from contracts.story_memory import (
    Character, ClassifierEvidence, PencilChoice, PencilUse, ReferenceChoice, ReferenceRetry, ReviewContext,
    StoryMemory,
)
from pipeline.char_ref_mod import require_reference_clearance
from pipeline.prompt_optimizer import filtered_description, permitted_words

# Character goes per book, shared by "Draw again" and the magic pencil (ADR-082 Decision 5).
MAX_RETRY_TAPS = 3

# ADR-069: finite chip-scope exclusions, never canonical-description normalization.
_VAGUE_CHIPS = {
    "skin tone", "average height", "warm clothing", "casual clothes", "plain clothes",
    "traditional or warm clothes",
}
_VAGUE_HUMAN_CHIPS = {
    "human", "bipedal human", "human face", "human body", "humanoid body",
    "child's humanoid body", "adult's humanoid body", "child's body", "adult's body",
}


def _chips(character: Character, style_fragment: str | None) -> list[str]:
    """Eligible emphasis choices from style-filtered canon, independent of the judge (ADR-069).
    `notes` is free prose, not an attribute, and is never offered. The fallback keeps the list
    nonempty so "try again" remains reachable (invariant 4).
    """
    # ADR-035 surface 5. Under `comic` ("no glow"), a tap on "glowing" spends a draw on a
    # style-forbidden trait. Filtering also lets `_mint_targeted` trust `retry.attribute`.
    description = filtered_description(character.description, style_fragment)
    axes = {
        # `species` is the one axis `filtered_description` deliberately leaves alone (Decision 2),
        # so it is filtered here instead — chip scope only. It was the live leak: a chip becomes
        # `char_bible._mint_targeted`'s explicit emphasis clause, so a species like "glowing orb"
        # would walk straight back into a draw prompt under "no glow" on a fresh job.
        "species": permitted_words(description.species, style_fragment),
        "colours": description.colours,
        "body_features": description.body_features,
        "clothing": description.clothing,
    }
    full_axis_list = [
        v for value in axes.values()
        if value is not None
        for v in ([value] if isinstance(value, str) else value)
        if v
    ]
    human = (character.description.species or "").strip().casefold() == "human"
    seen: set[str] = set()
    chips = []
    for axis in full_axis_list:
        key = axis.strip().casefold()
        # Apostrophe equivalence is suppression-only. Deduplication preserves exact offered text.
        suppression_key = key.replace("‘", "'").replace("’", "'")
        if suppression_key in _VAGUE_CHIPS or (human and suppression_key in _VAGUE_HUMAN_CHIPS):
            continue
        if key not in seen:
            seen.add(key)
            chips.append(axis)
    return chips or ["overall physical appearance"]


def has_versions(state: StoryMemory) -> bool:
    """ADR-082 Decision 6: only a job submitted with the setting on, in teacher-review mode, where
    every flag has a hold (OD-05)."""
    context = state.moderation_context
    return context.mode == "teacher_review_v1" and context.magic_pencil


def _pencil_choice(state: StoryMemory, c: Character) -> dict | None:
    """The pencil result waiting for "Keep this" or "Use the old one": the current picture came from
    a pencil use nobody chose for, and the old picture is still a kept version."""
    use = next((u for u in state.pencil_uses if u.char_id == c.char_id and u.choice is None
                and u.after_path is not None and u.after_path == c.canonical_ref_image), None)
    old = next((v for v in c.versions if use and v.image_path == use.before_path
                and v.ref_moderation_status == "passed"), None)
    return {"use_id": use.use_id, "version_id": old.version_id, "image_path": old.image_path} if old else None


def _pencil_refused(state: StoryMemory, c: Character) -> bool:
    """fal refused the latest edit of this picture, and the picture has not changed since (SH-04)."""
    use = next((u for u in reversed(state.pencil_uses) if u.char_id == c.char_id), None)
    return bool(use and use.reason == "refused" and use.before_path == c.canonical_ref_image)


def _project_reveal(state: StoryMemory) -> dict:
    """Pure — no effect, no mocks needed to test it. The worker writes this dict verbatim to
    `jobs.reveal` (spec §4.2)."""
    style_fragment = state.style.prompt_fragment or settings.default_style_fragment
    characters = [
        {
            "char_id": c.char_id,
            "name": c.name,
            "image_path": c.canonical_ref_image,   # durable path, never a signed URL (ADR-006)
            "chips": _chips(c, style_fragment),
            # ADR-082 Decision 6 (SH-01): absent, not empty, on a job without the feature, so its
            # payload is the one it always was.
            **({"versions": [
                {"version_id": v.version_id, "image_path": v.image_path}
                for v in c.versions if v.ref_moderation_status == "passed"
            ],
                # magic-pencil 05 (SH-02): unchosen draws nobody has opened, by id only. The API
                # moderates them when the child opens "Other versions".
                "unreviewed": [v.version_id for v in c.versions if v.ref_moderation_status is None],
                # ADR-082 Decision 2 (magic-pencil 06).
                "pencil_choice": _pencil_choice(state, c),
                "pencil_refused": _pencil_refused(state, c),
                # Only a classifier-passed picture is kept as a version, so only it can come back (AC-11).
                "pencil_ready": c.ref_moderation_status == "passed",
            } if has_versions(state) else {}),
        }
        for c in state.characters
        if c.canonical_ref_image is not None
    ]
    return {"characters": characters, "taps_left": MAX_RETRY_TAPS - state.cost.ref_retry_count}


def reveal(state: StoryMemory) -> dict:
    """A book with nothing to reveal must not pause (spec §4.1) — otherwise a book from which
    `analyze` extracted no characters parks a child in front of a confirm button that confirms
    nothing, and the job sits in `awaiting_confirm` forever (no client renders that screen).

    An unrecognised resume payload is treated as a confirm, not an error: this node fails toward
    progress. Payload validation is the endpoint's job (spec §4.9) — by the time a resume reaches
    here it has already been checked against the row.
    """
    require_reference_clearance(state)
    payload = _project_reveal(state)
    if not payload["characters"]:
        return {}
    answer = interrupt(payload)
    if isinstance(answer, dict) and answer.get("action") == "try_again":
        return {"reference_retry": ReferenceRetry(char_id=answer["char_id"], attribute=answer["attribute"])}
    if isinstance(answer, dict) and answer.get("action") == "choose_version" and has_versions(state):
        # Not a confirm: the child is still choosing, so `char_bible` swaps and the graph pauses here again.
        return {"reference_choice": ReferenceChoice(
            char_id=answer["char_id"], version_id=answer["version_id"], source=answer["source"],
            cleared=answer.get("cleared") is True)}
    if isinstance(answer, dict) and answer.get("action") == "pencil" and has_versions(state):
        return _pencil_request(state, answer)
    if isinstance(answer, dict) and answer.get("action") == "pencil_choice" and has_versions(state):
        return {"reference_pencil_choice": PencilChoice(
            char_id=answer["char_id"], choice=answer["choice"], source=answer["source"])}
    return {}


def _pencil_request(state: StoryMemory, answer: dict) -> dict:
    """ADR-082 Decision 2. The API already redacted and moderated the text (SH-03, SH-02), so this
    only records the use. Flagged text is held for the teacher with nothing drawn and no go spent
    (SH-05); `moderation_review` then sends it to `char_bible` or back here (OD-08)."""
    use = PencilUse(use_id=f"pencil-{len(state.pencil_uses) + 1}", char_id=answer["char_id"],
                    text=answer["text"], before_path=answer["source"],
                    text_moderation="held" if answer.get("flagged") else "cleared")
    update = {"reference_pencil": use.use_id, "pencil_uses": [*state.pencil_uses, use]}
    if answer.get("flagged"):
        context = state.moderation_context
        version = hashlib.sha256(use.text.encode("utf-8")).hexdigest()
        update["moderation_context"] = context.model_copy(update={"review": ReviewContext(
            review_id=uuid5(UUID(state.story_id),
                            f"character_pencil_text:{use.use_id}:{version}:{context.generation_epoch}"),
            kind="character_pencil_text", subject_id=use.use_id, subject_version=version,
            return_node="char_bible", criteria=list(TEACHER_MODERATION_CRITERIA),
            classifier_evidence=[ClassifierEvidence.model_validate(e) for e in answer.get("evidence", [])],
        )})
    return update

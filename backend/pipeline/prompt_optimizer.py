"""Pure prompt-construction helpers (spec `docs/specs/prompt-optimizer.md`).

Two pure functions, no LLM call: `build_prompt` turns a scene into the text `generate_scene` sends
to the image model; `correct_prompt` turns a failed attempt's `failure_reasons` into emphasis
clauses appended to the prior prompt (ADR-010). Neither writes to `StoryMemory` itself — the
caller stores the return value.
"""
import logging

from app.config import settings
from contracts.story_memory import Character, CharacterDescription, FailureReason

log = logging.getLogger(__name__)


def _describe(description: CharacterDescription, name: str) -> str:
    """The populated CharacterDescription axes as one line — same phrasing char_bible's
    reference_prompt uses, so the canonical reference and every scene prompt describe the same
    character consistently."""
    axes = [
        description.species,
        ", ".join(description.colours),
        ", ".join(description.body_features),
        ", ".join(description.clothing),
        description.notes,
    ]
    populated = [axis for axis in axes if axis]
    return f"{name} - {'; '.join(populated)}" if populated else name


def build_prompt(
    text_excerpt: str,
    characters_present: list[str],
    characters: list[Character],
    style_fragment: str | None,
) -> str:
    """Pure. Always includes the style fragment (invariant 1); never invents detail beyond
    `text_excerpt` and the present characters' populated description axes (invariant 2)."""
    style = style_fragment or settings.default_style_fragment
    by_id = {character.char_id: character for character in characters}

    descriptions = []
    for char_id in characters_present:
        character = by_id.get(char_id)
        if character is None:
            log.warning("build_prompt: char_id %s not found in characters, skipping", char_id)
            continue
        descriptions.append(_describe(character.description, character.name))

    return "\n\n".join([*descriptions, text_excerpt, style])


def _joined(values) -> str:
    return ", ".join(value for value in values if value)


# ADR-004: the 7-value FailureReason set, frozen permanently per ADR-028.
FAILURE_CLAUSES: dict[FailureReason, str] = {
    FailureReason.wrong_colour: "match the reference's exact colours: {colours}",
    FailureReason.wrong_species: "the character is a {species}, not anything else",
    FailureReason.wrong_body_feature: "match these body features exactly: {body_features}",
    FailureReason.wrong_clothing: "match this clothing exactly: {clothing}",
    FailureReason.wrong_style: "{style_fragment}",
    FailureReason.different_face: "match the reference character's face exactly",
    FailureReason.character_absent: "make sure {name} is clearly visible in the scene",
}


def correct_prompt(
    prompt: str,
    failure_reasons: list[FailureReason],
    characters: list[Character],
    style_fragment: str | None,
) -> str:
    """Pure. Never drops content from `prompt` (invariant 3) — only appends emphasis clauses, one
    per `FailureReason` present in `failure_reasons`, in enum-declaration order, no duplicates.

    Attribution ceiling (spec §4): `VlmVerdict`/`Attempt.failure_reasons` carry no per-character
    breakdown, so axis-based clauses fill from EVERY character in `characters`, joining multiple
    values — over-specifying rather than guessing wrong.
    """
    style = style_fragment or settings.default_style_fragment
    values = {
        "colours": _joined(colour for character in characters for colour in character.description.colours),
        "species": _joined(character.description.species for character in characters),
        "body_features": _joined(
            feature for character in characters for feature in character.description.body_features
        ),
        "clothing": _joined(item for character in characters for item in character.description.clothing),
        "name": _joined(character.name for character in characters),
        "style_fragment": style,
    }
    present = set(failure_reasons)
    clauses = [FAILURE_CLAUSES[reason].format(**values) for reason in FailureReason if reason in present]
    return "\n".join([prompt, *clauses]) if clauses else prompt

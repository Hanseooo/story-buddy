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


def referenced_characters(
    characters_present: list[str], characters: list[Character]
) -> list[Character]:
    """The present characters that HAVE a canonical reference, in the order `generate_scene`
    uploads them to fal.

    ONE list feeds both the image roll below and `generate_scene`'s `ref_paths`, so
    "Image 2 is X" cannot drift from `image_urls[1]`. The two used to derive the order
    independently — `generate_scene` filtering on `canonical_ref_image` and `build_prompt` not
    filtering at all — and agreed only because no scene had ever mixed the two kinds.
    """
    by_id = {character.char_id: character for character in characters}
    return [
        character
        for char_id in characters_present
        if (character := by_id.get(char_id)) is not None and character.canonical_ref_image
    ]


# Issue #23: the payload was prose plus ANONYMOUS image_urls. Given two unaddressed references an
# edit model composites them into the canvas as separate elements rather than conditioning identity
# on them — prod job b9506307 duplicated a character on 6 of its 7 two-reference scenes and on
# none of its one-reference scene. Naming each image and stating what it is FOR is the smallest
# change that addresses both branches of #23's discriminator: the duplicated girl (compositing) and
# the duplicated star (the prose says "a star" and one reference IS a star).
REFERENCE_CLAUSE = (
    "Use them only as references for what each character looks like. Draw one new illustration of "
    "the scene described below — do not copy, inset, mirror or repeat the reference images inside it, "
    "and draw each character exactly once."
)


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

    # Omitted entirely on the text-to-image path (`generate_scene:55-57` sends no images), where
    # naming images that were never sent would be a lie the model has to reconcile.
    referenced = referenced_characters(characters_present, characters)
    roll = [
        " ".join(f"Image {n} is {character.name}." for n, character in enumerate(referenced, 1))
        + " "
        + REFERENCE_CLAUSE
    ] if referenced else []

    return "\n\n".join([*roll, *descriptions, text_excerpt, style])


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

# The two corrections that have no FailureReason to hang on (spec `regeneration-controller` §4).
# Fixed strings, no .format — neither has a per-character value to fill: the judge named no
# reason, or the failure is a rendering property rather than an attribute. Driven by a BOOLEAN,
# never an 8th enum value — FailureReason stays frozen at 7 (ADR-028), so the closed set
# Objective 4's F1 is computed over is untouched.
IDENTITY_CLAUSE = "the characters must match the reference images exactly"
# Mirrors consistency_check.JUDGE_PROMPT's phrasing, so the correction restates the thing the
# judge was actually asked about.
ANATOMY_CLAUSE = "anatomy must be correct: no merged, missing or duplicated body parts"


def correct_prompt(
    prompt: str,
    failure_reasons: list[FailureReason],
    characters: list[Character],
    style_fragment: str | None,
    same_character: bool = True,
    anatomy_intact: bool = True,
) -> str:
    """Pure. Never drops content from `prompt` (invariant 3) — only appends emphasis clauses, one
    per `FailureReason` present in `failure_reasons`, in enum-declaration order, no duplicates.

    Attribution ceiling (spec §4): `VlmVerdict`/`Attempt.failure_reasons` carry no per-character
    breakdown, so axis-based clauses fill from EVERY character in `characters`, joining multiple
    values — over-specifying rather than guessing wrong.

    `same_character` / `anatomy_intact` close the two holes where the reason clauses alone
    append NOTHING, which would make the retry a pure resample (ADR-010 rejects resampling).
    Defaulted so the four-positional-arg signature stays call-compatible.
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
    # Guarded on EMPTY failure_reasons so it never duplicates different_face's clause.
    if not same_character and not failure_reasons:
        clauses.append(IDENTITY_CLAUSE)
    if not anatomy_intact:
        clauses.append(ANATOMY_CLAUSE)
    return "\n".join([prompt, *clauses]) if clauses else prompt

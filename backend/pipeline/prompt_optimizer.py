"""Pure prompt-construction helpers (spec `docs/specs/prompt-optimizer.md`).

Two pure functions, no LLM call: `build_prompt` turns a scene into the text `generate_scene` sends
to the image model; `correct_prompt` turns a failed attempt's `failure_reasons` into emphasis
clauses appended to the prior prompt (ADR-010). Neither writes to `StoryMemory` itself — the
caller stores the return value.
"""
import logging

from app.config import settings
from contracts.story_memory import Character, CharacterDescription, FailureReason, Location

log = logging.getLogger(__name__)


# ADR-035. Every preset states its own prohibitions in its own fragment text ("no gradients,
# no glow"), so the forbidden set is DERIVED from the fragment rather than hand-listed: ADR-022
# keeps sole ownership and a new preset arrives carrying its own. This is why the objection that
# killed the species word-list (`char_bible.py:74-77` — "a word list that is wrong the first time
# a child writes something not on it") does not apply here. That list is open-ended; this one is
# closed by the fragment.
_MIN_PREFIX = 4   # so short tokens cannot collide: "glove" must not match "glow"


def style_prohibitions(style_fragment: str | None) -> set[str]:
    """Pure. The words the active fragment forbids, read off its own `no <term>` clauses."""
    fragment = style_fragment or settings.default_style_fragment
    forbidden: set[str] = set()
    for clause in fragment.split(","):
        words = clause.strip().lower().split()
        if words and words[0] == "no":
            forbidden.update(words[1:])
    return forbidden


def _permitted(word: str, forbidden: set[str]) -> bool:
    """Prefix match in BOTH directions — "glowing" against "glow", "gradient" against
    "gradients" — floored at `_MIN_PREFIX` so the match cannot be incidental."""
    stripped = word.strip().lower()
    return not any(
        min(len(stripped), len(term)) >= _MIN_PREFIX
        and (stripped.startswith(term) or term.startswith(stripped))
        for term in forbidden
    )


def _filter_axis(values: list[str], forbidden: set[str]) -> list[str]:
    """Word-level (ADR-035 Decision 3): an entry survives with its permitted words and is
    dropped only if nothing is left, so "glowing eyes" becomes "eyes" instead of taking a real
    subject fact down with the rendering property."""
    kept = []
    for value in values:
        words = [word for word in value.split() if _permitted(word, forbidden)]
        if words:
            kept.append(" ".join(words))
    return kept


def _kept_whole(value: str | None, forbidden: set[str]) -> str | None:
    """All-or-nothing, for the free-prose `notes` axis (ADR-035 limit 6). `_filter_axis`'s
    word-level rule suits short noun phrases; on a sentence it leaves a mangled fragment. Dropping
    is safe here in a way it is not for the other axes — ADR-034 removed `notes` from the judge
    prompt, so nothing dropped here can make acceptance vacuous."""
    if value is None or all(_permitted(word, forbidden) for word in value.split()):
        return value
    return None


def permitted_words(value: str | None, style_fragment: str | None) -> str | None:
    """Pure. `_filter_axis`'s rule over ONE string, for the scalar `species` axis.

    Exists only for `reveal._chips` (ADR-035 amendment). Filtering species is CHIP SCOPE — a chip
    promises that tapping it buys a redraw that could change something, and no redraw clears
    "glowing" under a fragment ending "no glow". Decision 2 still holds everywhere the species is
    *described*: `filtered_description` never touches it, so the draw and judge prompts keep it and
    acceptance cannot go vacuous.
    """
    if value is None:
        return None
    forbidden = style_prohibitions(style_fragment)
    return " ".join(word for word in value.split() if _permitted(word, forbidden))


def filtered_description(
    description: CharacterDescription, style_fragment: str | None
) -> CharacterDescription:
    """Pure, transient (ADR-035 Decision 4) — `StoryMemory` keeps the child's words verbatim and
    only the rendered prompt/chip text drops them, so nothing is destroyed and the filter is
    reversible if the style changes.

    The three LIST axes word-level, plus `notes` all-or-nothing (limit 6 — it reaches the draw and
    scene prompts, and since ADR-034 the judge can no longer see it, so a forbidden term there is
    asserted to the generator and invisible to the gate). `species` is the one axis left alone:
    `analyze.py:22-26` makes it required precisely so an empty description can never make
    acceptance vacuous (limit 4).

    Removes, never invents, so `build_prompt`'s invariant 2 is untouched.
    """
    forbidden = style_prohibitions(style_fragment)
    if not forbidden:
        return description
    return description.model_copy(
        update={
            "colours": _filter_axis(description.colours, forbidden),
            "body_features": _filter_axis(description.body_features, forbidden),
            "clothing": _filter_axis(description.clothing, forbidden),
            "notes": _kept_whole(description.notes, forbidden),
        }
    )


def filtered_location(location: Location | None, style_fragment: str | None) -> Location | None:
    """Pure, transient — ADR-035 surface 5. A location description reaches the draw prompt the way
    a character description does, so `"glowing cave"` under a fragment ending `no glow` puts the
    prompt at war with itself. Word-level, like the list axes.

    The NAME is deliberately never filtered: it is what the child called the place, and when the
    description is null it is the entire `Setting:` line. Removes, never invents, so invariant 2
    is untouched.
    """
    if location is None or location.description is None:
        return location
    forbidden = style_prohibitions(style_fragment)
    if not forbidden:
        return location
    kept = _filter_axis([location.description], forbidden)
    return location.model_copy(update={"description": kept[0] if kept else None})



def _describe(description: CharacterDescription, name: str) -> str:
    """The populated CharacterDescription axes as one line — same phrasing char_bible's
    reference_prompt uses, so the canonical reference and every scene prompt describe the same
    character consistently.

    Issue #32: a species the name already carries renders as `"the star - star"` — a definition,
    not a description, and a SECOND bare assertion of the noun the excerpt is independently
    summoning. Exact token match, so a name that only partly carries the species
    (`"the retriever"` / `"golden retriever"`) keeps it.

    Judge-safe, and this is why it does not touch ADR-035's `species` carve-out: what filtering
    species could make vacuous is the REFERENCE gate, and that prompt is built by char_bible's own
    `_describe` (`char_bible.py:109`). `consistency_check.JUDGE_PROMPT` interpolates `{name}` only,
    and `correct_prompt`'s `wrong_species` clause reads `description.species` off the contract.
    """
    species = description.species
    if species and species.lower() in name.lower().split():
        species = None
    axes = [
        species,
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

    ONE list feeds the image roll below and every `ref_paths` the pipeline builds —
    `generate_scene`, `regenerate` and `output_mod`, the last two because both carry a prompt
    built here forward (`correct_prompt` appends, `_soften_prompt` prepends). So "Image 2 is X"
    cannot drift from `image_urls[1]` on any of the three. They used to derive the order
    independently and agreed only because no scene had ever mixed the two kinds.
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

# Issue #32: the sentences above govern the IMAGES, and a scene's own prose summons the thing
# independently of them. Prod job d83721d9's `s1` sent "Image 2 is the star" AND "found a tiny
# glowing star", and got both — the compositing branch #23 closed was not involved
# (same_character=True, anatomy_intact=True). The sentence below is the only one that binds the
# two mentions together.
#
# Deliberately GENERIC — "one of these characters", not "Ana or the star". The roll immediately
# above supplies the antecedent, so this can never assert a name the roll did not already assert:
# refs are sent for every `characters_present` character, including ones the excerpt never names
# ("Ana decided to help." sent two), and naming an absent character is how #23's floating extra
# appeared. It also binds the NAME, not the noun: "the stars" in "she looked up at the stars"
# names no character and stays drawable.
REFERENCE_CLAUSE = (
    "Use them only as references for what each character looks like. Draw one new illustration of "
    "the scene described below — do not copy, inset, mirror or repeat the reference images inside it, "
    "and draw each character exactly once. When the text below names one of these characters, it is "
    "referring to that character itself, not to a second thing of the same name."
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
        # ADR-035 surface 3. Issue #23's `s1`: this line asserted "glowing" while `style` below
        # forbade it and the reference obeyed `style`, so the edit model saw the scene's noun
        # describing something Image 2 visibly was not, and drew a second one.
        descriptions.append(_describe(filtered_description(character.description, style), character.name))

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
    # ADR-035 surface 4. Issue #24: `wrong_colour` used to answer with "match the reference's
    # exact colours: glowing" — reinforcing, on the retry, the one attribute the style guaranteed
    # the reference would not have. `species` is deliberately unfiltered (Decision 2).
    descriptions = [filtered_description(character.description, style) for character in characters]
    values = {
        "colours": _joined(colour for description in descriptions for colour in description.colours),
        "species": _joined(character.description.species for character in characters),
        "body_features": _joined(
            feature for description in descriptions for feature in description.body_features
        ),
        "clothing": _joined(item for description in descriptions for item in description.clothing),
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

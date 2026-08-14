"""Pure prompt-construction helpers (spec `docs/specs/prompt-optimizer.md`).

Two pure functions, no LLM call: `build_prompt` turns a scene into the text `generate_scene` sends
to the image model; `correct_prompt` turns a failed attempt's `failure_reasons` into emphasis
clauses appended to the prior prompt (ADR-010). Neither writes to `StoryMemory` itself — the
caller stores the return value.
"""
import logging
from string import Formatter

from app.config import settings
from contracts.story_memory import Character, CharacterDescription, FailureReason, Location, StoryObject

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


def filtered_object(
    obj: StoryObject, style_fragment: str | None
) -> StoryObject:
    if obj.description is None:
        return obj
    forbidden = style_prohibitions(style_fragment)
    if not forbidden:
        return obj
    kept = _filter_axis([obj.description], forbidden)
    return obj.model_copy(update={"description": kept[0] if kept else None})


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
    # Plain commas — commit bef9982's finding, ported here because this copy renders far more
    # images than char_bible's does. `"{name} - {a}; {b}"` after a proper noun is a caption shape,
    # and Qwen-Image draws captions: the reference draw returned "Hoe - Star:" lettered on the
    # canvas, and a prod cel page returned the name "Casey" above the character. Commas describe.
    populated = [axis for axis in axes if axis]
    return ", ".join([name, *populated])


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
        # §4.3 D3(a), defensive half. `segment` no longer emits a duplicate, but a checkpoint
        # written before that change can, and `_fal_ref_url`'s cache would hand fal the same URL
        # twice. `dict.fromkeys` is order-preserving, so the survivors keep their relative order
        # and "Image N is X" still names `ref_paths[N-1]` on all three consumers (invariant 4).
        for char_id in dict.fromkeys(characters_present)
        if (character := by_id.get(char_id)) is not None and character.canonical_ref_image
    ]


REFERENCE_CLAUSE = (
    "Use them only as references for what each character looks like. Draw one new illustration of "
    "the scene described below — do not copy, inset, mirror or repeat the reference images inside it, "
    "and draw each character exactly once. When the text below names one of these characters, it is "
    "referring to that character itself, not to a second thing of the same name. "
    "The reference images define appearance, not pose, crop, expression or viewing angle; "
    "the Visual direction controls those scene properties."
)

# §4.2. BOTH clauses below sit OUTSIDE REFERENCE_CLAUSE deliberately: the roll and its clause are
# omitted entirely on the text-to-image path (`generate_scene:55-57` sends no images), and both
# guards must apply there too. Inside, they would be silently inert on every ref-less scene.

# A WHOLE-CANVAS count, structurally different from REFERENCE_CLAUSE's per-character "draw each
# character exactly once": that one constrains each subject, this one constrains the canvas. D3(b)
# residual duplication is compositing, and a canvas-level assertion is the only shape that can
# contradict it.
SUBJECT_COUNT_CLAUSE = "This illustration contains exactly {n} character{plural}: {names}."

# Wording from `char_bible.REFERENCE_PROMPT` (prod job 4cb31620 drew "the star" as a smiling mascot
# with arms and legs), scoped to the scene path and closed with "unless described above".
# UNCONDITIONAL, for the reason char_bible gives: branching on species needs a word list that is
# wrong the first time a child writes something not on it, and this is a no-op for a person.
NON_HUMAN_CLAUSE = (
    "If a character is not a person, draw it as the kind of thing it actually is — give it no "
    "human body and no human face unless described above."
)


def _names(names: list[str]) -> str:
    """"Ana" / "Ana and the star" / "Ana, the star and the bird"."""
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def build_prompt(
    text_excerpt: str,
    characters_present: list[str],
    characters: list[Character],
    style_fragment: str | None,
    location: Location | None = None,
    objects_present: list[str] | None = None,
    objects: list[StoryObject] | None = None,
    visual_direction: str | None = None,
) -> str:
    """Pure. Always includes the style fragment (invariant 1); never invents detail beyond
    `text_excerpt`, the present characters' populated description axes, and the scene's location
    (invariant 2, widened by `scene-setting-and-subject-binding.md` §2).

    `location` is defaulted so the four-positional-arg call stays compatible; the one production
    caller (`generate_scene.py:77`) always passes it.
    """
    style = style_fragment or settings.default_style_fragment
    by_id = {character.char_id: character for character in characters}

    # `dict.fromkeys` mirrors segment's dedup (§4.3) so a checkpoint written before that change
    # cannot reproduce a doubled subject on resume. Order-preserving — invariant 4.
    present: list[Character] = []
    for char_id in dict.fromkeys(characters_present):
        character = by_id.get(char_id)
        if character is None:
            log.warning("build_prompt: char_id %s not found in characters, skipping", char_id)
            continue
        present.append(character)

    # Omitted entirely on the text-to-image path (`generate_scene:55-57` sends no images), where
    # naming images that were never sent would be a lie the model has to reconcile.
    referenced = referenced_characters(characters_present, characters)
    referenced_ids = {character.char_id for character in referenced}

    # §4.2 THE ROLL FOLD — the whole D2 fix. The image and its attributes are ONE sentence, so the
    # model has nothing left to associate. Net token reduction: the separate attribute line for a
    # referenced character is not emitted below. A character with no populated axes yields
    # "Image 1 is Ana." — byte-identical to before the fold.
    roll = [
        " ".join(
            f"Image {n} is "
            f"{_describe(filtered_description(character.description, style), character.name)}."
            for n, character in enumerate(referenced, 1)
        )
        + " "
        + REFERENCE_CLAUSE
    ] if referenced else []

    # ADR-035 surface 3. Issue #23's `s1`: this line asserted "glowing" while `style` below
    # forbade it and the reference obeyed `style`, so the edit model saw the scene's noun
    # describing something Image 2 visibly was not, and drew a second one.
    descriptions = [
        _describe(filtered_description(character.description, style), character.name)
        for character in present
        if character.char_id not in referenced_ids
    ]

    # Emitted only when there is a subject to count — all three clauses would otherwise reference
    # nothing. The count is computed from `present`, i.e. AFTER the missing-char_id filter above,
    # or it asserts a number the prompt does not name.
    guards = ["\n".join([
        SUBJECT_COUNT_CLAUSE.format(
            n=len(present),
            plural="" if len(present) == 1 else "s",
            names=_names([character.name for character in present]),
        ),
        NON_HUMAN_CLAUSE,
    ])] if present else []

    by_object_id = {obj.obj_id: obj for obj in objects or []}
    visible_objects: list[StoryObject] = []
    for obj_id in dict.fromkeys(objects_present or []):
        obj = by_object_id.get(obj_id)
        if obj is None:
            log.warning("build_prompt: obj_id %s not found in objects, skipping", obj_id)
            continue
        visible_objects.append(filtered_object(obj, style))

    object_block = [
        "Visible objects:\n"
        + "\n".join(
            f"{obj.name}, {obj.description}" if obj.description else obj.name
            for obj in visible_objects
        )
    ] if visible_objects else []

    direction = [f"Visual direction: {visual_direction}"] if visual_direction else []

    # Emitted BEFORE the excerpt on purpose: when a location description and the excerpt conflict
    # ("that night" against a sunny description), the excerpt is then the later and more specific
    # assertion. Reduced, not eliminated (§4.5.3).
    place = filtered_location(location, style)
    setting = [
        f"Setting: {place.name} - {place.description}" if place.description
        else f"Setting: {place.name}"
    ] if place else []

    return "\n\n".join(
        [*roll, *descriptions, *guards, *object_block, *direction, *setting, text_excerpt, style]
    )


def _joined(values) -> str:
    return ", ".join(value for value in values if value)


def _fillable(template: str, values: dict[str, str]) -> bool:
    """Whether every `{placeholder}` this clause interpolates has something to say.

    A clause whose only axis is empty renders as `"match the reference's exact colours: "` — a
    dangling instruction that corrects nothing, which makes the retry the resample ADR-010 rejects.
    Reads the placeholders off the template itself rather than a second reason→key dict, so adding
    a clause cannot forget to register its axis. `different_face` parses to no placeholders and is
    therefore always fillable, which is right — it needs no contract value.
    """
    return all(values[key] for _, key, _, _ in Formatter().parse(template) if key)


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
# lettering-suppression §4.4. The wording is the whole trick: it asserts blankness and never says
# text, letters, words, writing, signage, captions or lettering. Those words are what put lettering
# on the canvas the last three times (spec §1), and this clause fires precisely on images that
# already have some. Unlike ANATOMY_CLAUSE it does NOT mirror the judge's phrasing — the judge is
# told exactly what to look for (§4.1), the generator is never told what to avoid.
TEXT_CLAUSE = "every surface in the picture is blank and unmarked"


def correct_prompt(
    prompt: str,
    failure_reasons: list[FailureReason],
    characters: list[Character],
    style_fragment: str | None,
    same_character: bool = True,
    anatomy_intact: bool = True,
    text_free: bool = True,
    scene_contradictions: list[str] | None = None,
) -> str:
    """Pure. Never drops content from `prompt` (invariant 3) — only appends emphasis clauses, one
    per `FailureReason` present in `failure_reasons`, in enum-declaration order, no duplicates.

    Attribution ceiling (spec §4): `VlmVerdict`/`Attempt.failure_reasons` carry no per-character
    breakdown, so axis-based clauses fill from EVERY character in `characters`, joining multiple
    values — over-specifying rather than guessing wrong. A clause whose axes are ALL empty across
    ALL of them is dropped rather than rendered hollow (`_fillable`), and if that empties the whole
    correction, `IDENTITY_CLAUSE` floors it.

    `same_character` / `anatomy_intact` / `text_free` / `scene_contradictions` close the holes where
    the reason clauses alone append NOTHING, which would make the retry a pure resample (ADR-010
    rejects resampling). Defaulted so the four-positional-arg signature stays call-compatible.
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
    clauses: list[str] = []
    dropped: list[str] = []
    for reason in FailureReason:
        if reason not in present:
            continue
        template = FAILURE_CLAUSES[reason]
        if _fillable(template, values):
            clauses.append(template.format(**values))
        else:
            dropped.append(reason.value)
    if dropped:
        log.info("correct_prompt: dropped unfillable clause(s) %s — nothing on that axis", dropped)
    # Guarded on EMPTY failure_reasons so it never duplicates different_face's clause.
    if not same_character and not failure_reasons:
        clauses.append(IDENTITY_CLAUSE)
    if not anatomy_intact:
        clauses.append(ANATOMY_CLAUSE)
    if not text_free:
        clauses.append(TEXT_CLAUSE)
    # LAST, so it fires only when the whole correction would otherwise be empty. The judge named
    # reasons and not one of them could be filled — which is normal, because the judge compares the
    # image to the REFERENCE and the reference carries attributes `analyze` never wrote down.
    # `IDENTITY_CLAUSE` is the right floor for exactly that: it points at the images, which are in
    # the payload and do know the colour. Requires a non-empty `failure_reasons`, so the no-op call
    # (nothing failed) still returns `prompt` untouched.
    if failure_reasons and not clauses:
        clauses.append(IDENTITY_CLAUSE)
    clauses.extend(
        f"Correct this scene contradiction: {contradiction}"
        for contradiction in scene_contradictions or []
    )
    return "\n".join([prompt, *clauses]) if clauses else prompt

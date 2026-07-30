"""The node every other image in the book depends on (spec `docs/specs/character-bible.md`).

Draws one canonical reference per principal character, judges it against the
`CharacterDescription` it came from, re-rolls up to 3 times, and persists the accepted path
plus its verdict. ADR-028 falsified ADR-007's assumption that a reference is correct *because*
it was generated from the description; this node is the gate that makes that failure visible.

It does NOT fix the rate — at the measured draw quality 3 draws still ship an off-spec
reference roughly 42% of the time, now with the verdict persisted instead of silently. The fix
for the rate is swapping `fal_image_model` (ADR-001's named seam), not anything in this file.
"""
import logging

from contracts.story_memory import CharacterDescription, RefVerdict

log = logging.getLogger(__name__)

MAX_DRAWS = 3   # ADR-028. Not ADR-010's 1: a bad scene is one page, a bad reference is every page.

REFERENCE_PROMPT = """\
A single full-body character reference of one character, standing, facing forward, centred on a \
plain neutral background. No other characters, no scenery, no text, no border.

Character: {subject}

Style: {style_fragment}"""


def _describe(description: CharacterDescription, name: str) -> str:
    """The `CharacterDescription` axes as one line. Shared by the draw prompt and the judge
    prompt so they can never drift into describing different characters."""
    axes = [
        description.species,
        ", ".join(description.colours),
        ", ".join(description.body_features),
        ", ".join(description.clothing),
        description.notes,
    ]
    populated = [axis for axis in axes if axis]
    return f"{name} - {'; '.join(populated)}" if populated else name


def reference_prompt(description: CharacterDescription, name: str, style_fragment: str) -> str:
    """Pure. ADR-022: the fragment names a medium and its physical artifacts — it never says
    "beautiful", "8k" or "highly detailed"."""
    return REFERENCE_PROMPT.format(subject=_describe(description, name), style_fragment=style_fragment)


def best_draw(verdicts: list[RefVerdict]) -> int:
    """Pure. Best-of when every draw failed: most attributes present, ties → earliest (ADR-010).

    `char_bible`'s own rule over `RefVerdict`. UNRELATED to `regeneration-controller`'s
    lexicographic scene rule over `VlmVerdict` — different schema, different question. Do not
    unify them.
    """
    return max(range(len(verdicts)), key=lambda i: (len(verdicts[i].attributes_present), -i))


def char_bible(state) -> dict:
    # ponytail: stub — Plan B Task 4 fills this in (select, mint, map, bump cost).
    return {}

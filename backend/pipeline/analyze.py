import logging

from pydantic import BaseModel

from contracts.story_memory import CharacterDescription, StoryMemory, TimelineEvent
from providers import structured_text


class SceneCaption(BaseModel):
    caption: str


def caption_for(text: str) -> str:
    result = structured_text(
        f"Write one short, kid-friendly caption (max 20 words) for this story: {text}",
        SceneCaption,
    )
    return result.caption


# --- LLM boundary (D-F: transient wrapper, so it lives beside its node) ---
# The contract types all carry a REQUIRED id and D-G forbids an id at the boundary, so the
# boundary uses id-less mirrors that the node maps into contract types.


class ExtractedDescription(CharacterDescription):
    """Boundary-strict subclass. The contract's `CharacterDescription` is all-Optional by
    design (ADR-023: mostly-optional container); real per-field validation belongs at the
    LLM boundary (ADR-002). Subclassed rather than mirrored so the axes — deliberately
    aligned to the `FailureReason` taxonomy the judge scores against — stay in one place.

    `species` is required HERE and Optional in the contract. ADR-028's reference-acceptance
    loop judges each draw against `CharacterDescription`; an entirely empty description makes
    `matches_description` vacuously true, so the 3-draw re-roll silently collapses to 1 draw.
    One always-answerable string guarantees the judge has something to check against.
    No visual attribute is required — strict `json_schema` cannot express "at least one of
    three lists is non-empty", so that constraint would have to fire after a paid call.
    """

    species: str


class ExtractedCharacter(BaseModel):
    name: str
    description: ExtractedDescription


class ExtractedLocation(BaseModel):
    name: str
    description: str | None = None


class ExtractedObject(BaseModel):
    name: str
    description: str | None = None


class StoryAnalysis(BaseModel):
    """The transient wrapper — never persisted."""

    characters: list[ExtractedCharacter]   # prominence order, protagonist first
    locations: list[ExtractedLocation]
    objects: list[ExtractedObject]
    timeline: list[TimelineEvent]          # already id-less in contracts/


log = logging.getLogger(__name__)

# `analyze` reads redacted text, and the expected kid story is first-person ("I went to the
# beach with my sister"), so the protagonist is usually unnamed by construction. Asking for a
# short descriptive label rather than a proper noun works identically on redacted and
# un-redacted text, and it is what `char_bible` needs anyway — the canonical reference is drawn
# from `CharacterDescription`, not from the name. Consequence, stated plainly: the child's
# actual name never appears in their storybook. That is correct under CC-2 (spec §4).
EXTRACTION_PROMPT = """Extract the entities from this child's story.

Characters: at most 3, most important first — the first one is the story's protagonist.
Give each a short descriptive label, never a proper noun and never a redaction placeholder
like <PERSON_1>: "the narrator", "the younger sister", "the orange cat". The story is usually
first-person, and the narrator is usually a character. Every character needs a species — one
plain word for what they are: "girl", "dog", "robot". Fill colours, body_features and clothing
only from what the story actually says; leave them empty rather than inventing details.

Locations and objects: whatever the story mentions.

Timeline: the story's events in the order they happen, one short summary each.

Story:
{text}"""


def extract_entities(text: str) -> StoryAnalysis:
    """The node's single effect boundary (MASTER_SPEC §6). One strict-`json_schema` call.

    A provider hard failure raises and the job fails (ADR-025 Decision 1) — the `openai` SDK's
    bounded retry is the entire policy. In Phase 1 a model self-refusal surfaces the same way,
    knowingly blunt; soften-and-retry is `self-refusal-fallback`'s (Phase 2, ADR-011 mech. 4).
    """
    analysis = structured_text(EXTRACTION_PROMPT.format(text=text), StoryAnalysis)
    log.info(
        "analyze: extracted %d characters, %d locations, %d objects, %d timeline events",
        len(analysis.characters),
        len(analysis.locations),
        len(analysis.objects),
        len(analysis.timeline),
    )
    return analysis


def analyze(state: StoryMemory) -> dict:
    # ponytail: stub — the `story-analyzer` spec fills this in (characters, locations, objects,
    # timeline) and mints c/loc/obj ids per §2.1. Deliberately not started: DECISION_BACKLOG.
    # `caption_for` lives here per D-F (transient wrapper beside its node); `segment` calls it.
    return {}

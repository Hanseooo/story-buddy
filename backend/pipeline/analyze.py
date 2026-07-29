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


def analyze(state: StoryMemory) -> dict:
    # ponytail: stub — the `story-analyzer` spec fills this in (characters, locations, objects,
    # timeline) and mints c/loc/obj ids per §2.1. Deliberately not started: DECISION_BACKLOG.
    # `caption_for` lives here per D-F (transient wrapper beside its node); `segment` calls it.
    return {}

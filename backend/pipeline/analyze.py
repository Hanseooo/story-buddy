import logging

from pydantic import BaseModel, field_validator, model_validator

from contracts.story_memory import Character, CharacterDescription, Location, StoryMemory, StoryObject, TimelineEvent
from providers import structured_text


# --- LLM boundary (D-F: transient wrapper, so it lives beside its node) ---
# The contract types all carry a REQUIRED id and D-G forbids an id at the boundary, so the
# boundary uses id-less mirrors that the node maps into contract types.


class ExtractedDescription(CharacterDescription):
    species: str
    is_humanoid: bool

    @model_validator(mode="after")
    def complete_visual_profile(self) -> "ExtractedDescription":
        axes = (self.colours, self.body_features, self.clothing)
        if sum(len(axis) for axis in axes) < 3 or sum(bool(axis) for axis in axes) < 2:
            raise ValueError("character needs at least three visual discriminators across two axes")
        if self.is_humanoid and not self.clothing:
            raise ValueError("humanoid character needs a clothing description")
        return self


class ExtractedCharacter(BaseModel):
    name: str
    description: ExtractedDescription


class ExtractedLocation(BaseModel):
    name: str
    description: str

    @field_validator("description", mode="after")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description cannot be blank")
        return v


class ExtractedObject(BaseModel):
    name: str
    description: str
    owner_name: str | None = None


class StoryAnalysis(BaseModel):
    """The transient wrapper — never persisted."""

    characters: list[ExtractedCharacter]   # prominence order, protagonist first
    locations: list[ExtractedLocation]
    objects: list[ExtractedObject]
    timeline: list[TimelineEvent]          # already id-less in contracts/

    @model_validator(mode="after")
    def entity_rosters_do_not_overlap(self) -> "StoryAnalysis":
        character_names = {character.name.casefold() for character in self.characters}
        overlap = character_names & {obj.name.casefold() for obj in self.objects}
        if overlap:
            raise ValueError(f"entity appears as both character and object: {sorted(overlap)}")
        return self


log = logging.getLogger(__name__)

# `analyze` reads REDACTED text, so any name reaching this prompt is already a pseudonym from
# `providers._PSEUDONYM_POOL` — a story about "Jun" arrives as a story about "Ana". Using that
# name is the entire point of pseudonymizing rather than hard-redacting ("so the story survives
# with a protagonist an illustrator can draw"). Until 2026-08-11 this prompt forbade proper nouns
# outright, so it discarded the pseudonym and every protagonist the pipeline ever produced was
# called "the narrator" — two mechanisms, the second negating the first.
#
# Stated plainly: the child's real name still never appears in their storybook, because CC-2 is
# `redact_pii`'s job upstream and not this prompt's. What was given up is a SECOND layer — the
# old label rule also neutralised a spaCy NER miss, and `en_core_web_sm` is not reliable on
# Filipino names ("Kuya Jun", "Ate Mimi"). That residue is accepted, not overlooked.
#
# The descriptive-label fallback stays for the common first-person case ("I went to the beach"),
# where there is no name to use and `char_bible` still needs something to put in the prompt.
EXTRACTION_PROMPT = """Extract the entities from this child's story.

Characters: at most 3, most important first — the first one is the story's protagonist.
Use the name the story gives the character. If the story never names them, use a short
descriptive label instead: "the narrator", "the younger sister", "the orange cat". Never emit a
redaction placeholder like <PERSON_1>. The story is usually first-person, and the narrator is
usually a character.
Classify by agency: a character speaks, decides, moves intentionally, or performs an action. An inert prop belongs only in objects. A personified object belongs only in characters, never both.
Species is the physical kind, never a job title or role: a human wizard is physically human.
Copy every visual fact the story states without alteration. Fill only missing visual axes once with neutral, child-safe, non-stereotyped details that distinguish this character from the rest of the roster.
Return at least three stable visual discriminators across at least two of colours, body_features, and clothing. Set is_humanoid accurately; every humanoid needs a non-empty clothing description.

Locations and objects: whatever the story mentions. Describe each location by what is permanently there — not the weather, the time of day, or what happens there. Copy every stated permanent fact without alteration. Fill missing detail once with neutral, child-safe features that make the place visually recognizable. For each object, provide a stable physical description and set owner_name to the character's name if owned by a character, or null if unowned.

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
    """One extraction call, one roster. Every downstream node works from `characters[]`
    instead of re-reading the child's prose (spec `docs/specs/story-analyzer.md`).

    This body does no I/O — it truncates, mints, re-indexes, and partial-returns (ADR-024).
    `caption_for` above lives here per D-F but belongs to `segment`; it is not called here.
    """
    analysis = extract_entities(state.input.redacted_text or state.input.raw_text)

    # The 3-character cap IS the pre-scene cost ceiling (CC-3): at most 9 reference draws
    # (3 characters x ADR-028's 3-draw cap) before a single scene is generated. The prompt
    # asks for <=3 too, but a prompt is not enforceable — this slice is the control.
    characters = [
        Character(
            char_id=f"c{i}",
            name=extracted.name,
            # the strict subclass is a boundary concern; what is persisted is the contract type
            description=CharacterDescription(**extracted.description.model_dump(exclude={"is_humanoid"})),
        )
        for i, extracted in enumerate(analysis.characters[:3])
    ]
    # locations/objects are deliberately uncapped — neither costs an image, so neither is a
    # CC-3 lever. Cap them only if a measured checkpoint problem appears (spec §4).
    locations = [
        Location(loc_id=f"loc{i}", name=extracted.name, description=extracted.description)
        for i, extracted in enumerate(analysis.locations)
    ]
    name_to_char_id: dict[str, str] = {}
    for character in characters:
        name_to_char_id.setdefault(character.name, character.char_id)

    # §4.2 makes an UNKNOWN owner a boundary error. A owner the model did extract but that the
    # 3-character cap dropped is not unknown — it is known and uncapped, and raising on it would
    # turn a routine over-extraction (the cap exists precisely because the prompt is not
    # enforceable) into a dead job before any image is drawn.
    extracted_names = {extracted.name for extracted in analysis.characters}

    objects = []
    for i, extracted in enumerate(analysis.objects):
        owner_char_id = None
        if extracted.owner_name is not None:
            owner_char_id = name_to_char_id.get(extracted.owner_name)
            if owner_char_id is None:
                if extracted.owner_name not in extracted_names:
                    raise ValueError(f"analyze: unknown owner {extracted.owner_name!r}")
                log.warning(
                    "analyze: owner %r capped out of the roster; object %r kept unowned",
                    extracted.owner_name,
                    extracted.name,
                )
        objects.append(
            StoryObject(
                obj_id=f"obj{i}",
                name=extracted.name,
                description=extracted.description,
                owner_char_id=owner_char_id,
            )
        )
    # `order` is re-assigned from list position, never trusted from the model: a returned
    # `1, 2, 5` or a duplicate validates fine against Pydantic and would silently corrupt the
    # only ordering `segment` receives.
    timeline = [
        TimelineEvent(order=i, summary=event.summary) for i, event in enumerate(analysis.timeline)
    ]

    log.info(
        "analyze: minted %s",
        [c.char_id for c in characters]
        + [loc.loc_id for loc in locations]
        + [o.obj_id for o in objects],
    )
    return {
        "characters": characters,
        "locations": locations,
        "objects": objects,
        "timeline": timeline,
    }

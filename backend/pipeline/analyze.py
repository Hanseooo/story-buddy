import logging
import re

from pydantic import BaseModel, field_validator, model_validator

from contracts.story_memory import (
    Character,
    CharacterDescription,
    Location,
    StoryMemory,
    StoryObject,
    TimelineEvent,
    _DESCRIPTION_PLACEHOLDERS,
    _is_description_placeholder,
)
from providers import structured_text


# --- LLM boundary (D-F: transient wrapper, so it lives beside its node) ---
# The contract types all carry a REQUIRED id and D-G forbids an id at the boundary, so the
# boundary uses id-less mirrors that the node maps into contract types.


class ExtractedDescription(CharacterDescription):
    species: str
    body_plan: str
    face_or_interface: str
    is_humanoid: bool

    @field_validator("body_plan", "face_or_interface", mode="before")
    @classmethod
    def morphology_is_concrete(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("morphology must be text")
        value = value.strip()
        if not value or value.casefold() in _DESCRIPTION_PLACEHOLDERS:
            raise ValueError("morphology must not be blank or a placeholder")
        if "\n" in value or "\r" in value:
            raise ValueError("morphology must be single-line")
        if len(value) > 120:
            raise ValueError("morphology must be at most 120 characters")
        return value

    @model_validator(mode="after")
    def complete_visual_profile(self) -> "ExtractedDescription":
        self.body_features = list(dict.fromkeys([
            self.body_plan,
            self.face_or_interface,
            *self.body_features,
        ]))
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


_AXIS_STOPWORDS = frozenset({
    "a", "an", "and", "the", "of", "with", "in", "on", "at", "to", "it", "its",
    "is", "was", "were", "be", "been", "by", "for", "into", "that", "this", "then", "later",
})


def _stem(word: str) -> str:
    """Crude suffix strip — `painted`/`paint`, `flowers`/`flower`, `dusty`/`dust`. The drop rule
    below was measured with exactly this, over all 66 axis entries the four probe arms produced;
    a real stemmer is a dependency the measurement does not ask for."""
    for suffix in ("ing", "ed", "es", "s", "y"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _stems(text: str | None) -> set[str]:
    return {
        _stem(word)
        for word in re.findall(r"[a-z0-9]+", (text or "").lower())
        if word not in _AXIS_STOPWORDS
    }


def _permanent_atoms(entries: list[str], changed: set[str]) -> list[str]:
    """ADR-053 D3. Split, clean, bound, then drop what the object's own `changes_during_story`
    already says. The model emits `'bamboo, paint'` as ONE entry, so an axis is atomised on commas
    before anything is judged.

    Self-consistency, not a list of English words: the model states the change itself, so the leak
    is removable by comparing the axis against that statement. Two shared stemmed content words,
    never one — over the probe's 66 entries a threshold of two drops exactly the two leaked entries
    and a threshold of one also destroys `tail that spins`, a genuine permanent feature of the
    weathervane whose tail is what changes.
    """
    kept: list[str] = []
    for entry in entries:
        for atom in entry.split(","):
            atom = atom.strip()
            if _is_description_placeholder(atom):
                continue
            if "\n" in atom or "\r" in atom or len(atom) > 120:
                continue
            if len(_stems(atom) & changed) >= 2:
                continue
            kept.append(atom)
    return kept


class ExtractedObject(BaseModel):
    name: str
    # ADR-053 D1/D2: axes, not prose. Three arms over the same stories moved clean visual fields
    # from 4/14 (one `description: str`) to 15/16 (these three, no prose slot).
    materials: list[str]
    colours: list[str]
    form_features: list[str]
    # Boundary-only (D2). Removing the prose slot left one residue — the axes still leaked on the
    # object that genuinely changes — and this is where the model puts the change instead. It is
    # NOT persisted to `StoryObject` and never reaches a prompt; `segment` remains the sole author
    # of per-scene state (ADR-052 D3). Its only other job is to be what the axes are checked
    # against below.
    changes_during_story: str | None = None
    owner_name: str | None = None

    @field_validator("owner_name", mode="before")
    @classmethod
    def normalize_owner_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped or v_stripped.casefold() in {"null", "none", "nil", "unowned", "n/a"}:
                return None
            return v_stripped
        return v

    @model_validator(mode="after")
    def axes_hold_only_permanent_appearance(self) -> "ExtractedObject":
        """ADR-053 D3 — a NORMALIZING validator, never a rejecting one.

        `providers.py:300-315` grants exactly one blind re-ask on a `ValidationError`: the same
        prompt, at `temperature=0`, with no feedback about what failed. At the measured 34-in-41
        violation rate that is a corpus-wide quarantine, not a fix. So every rule here drops the
        offending atom and returns; nothing raises.

        The single-line, 120-code-point bound is the one `morphology_is_concrete` already imposes
        on the character axes, applied per atom.
        """
        changed = _stems(self.changes_during_story)
        self.materials = _permanent_atoms(self.materials, changed)
        self.colours = _permanent_atoms(self.colours, changed)
        self.form_features = _permanent_atoms(self.form_features, changed)
        return self


_EXPLICIT_ALIAS = re.compile(r"\(([^()]*)\)\s*$")


class StoryAnalysis(BaseModel):
    """The transient wrapper — never persisted."""

    characters: list[ExtractedCharacter]   # prominence order, protagonist first
    locations: list[ExtractedLocation]
    objects: list[ExtractedObject]
    timeline: list[TimelineEvent]          # already id-less in contracts/

    @model_validator(mode="after")
    def entity_rosters_do_not_overlap(self) -> "StoryAnalysis":
        character_names = {character.name.casefold() for character in self.characters}
        objects: list[ExtractedObject] = []
        for obj in self.objects:
            if obj.name.casefold() in character_names:
                continue
            match = _EXPLICIT_ALIAS.search(obj.name)
            if match and match.group(1).strip().casefold() in character_names:
                continue
            objects.append(obj)
        self.objects = objects
        return self


log = logging.getLogger(__name__)

EXTRACTION_PROMPT_VERSION = 6   # v6: ADR-053 D1/D2 — an object is described on axes, not in prose

# `analyze` reads REDACTED text, and this prompt is allowed to use the names in it. Until
# 2026-08-11 it forbade proper nouns outright, so every protagonist the pipeline ever produced was
# called "the narrator" — the prompt was discarding the one thing upstream redaction had worked to
# preserve.
#
# ADR-045 (2026-09-01) changed what "redacted" means here: names arriving in this prompt are now
# the child's OWN words, not pool pseudonyms, because person pseudonymization is off by default.
# The prompt is unchanged — it wanted a usable name and it still gets one — but the privacy claim
# that used to sit here does not survive, and is not restated. CC-2 now covers structured
# identifiers only; a first name reaching this prompt reaches the storybook. That is ADR-045's
# accepted cost, argued there and in `docs/capstone/ethics_and_safety.md` §1, not a gap here.
#
# The descriptive-label fallback stays for the common first-person case ("I went to the beach"),
# where there is no name to use and `char_bible` still needs something to put in the prompt.
#
# v2 (2026-08-27): selection moved above description, because the agency rule was two lines in a
# prompt whose other ~28 are about appearance and the model weighted the bulk — a corpus probe of
# 30 stories put "the hill", "the river" and "the jar of pickles" in `characters[]`. Two rules were
# added with it: do not pad the roster to 3 (27 of those 30 padded to exactly 3), and only a
# first-person story gets a narrator character (the old line asserted first-person unconditionally
# and minted "the narrator" for third-person text).
#
# v3 (2026-08-27): the faceless wording was ungated. It said how to phrase facelessness but never
# when it applied, so "robot" alone triggered it and the prompt's own example phrase was copied
# onto syn-001's tin rooster ("smooth unbroken front surface with no visible face"). `char_bible`
# drew the species-appropriate rooster the neighbouring sentence demands, so the reference
# contradicted its own spec and all 7 scenes failed `different_face`/`wrong_body_feature` to the
# retry ceiling -- 25 image calls for 9 assets, and a bundle the consistency judge never passed.
# v4 (2026-08-27): the prompt asked for the value it bans. "neutral" was both the instructed
# design choice ("choose one neutral ... design", "fill missing detail once with neutral ...
# features") and a banned placeholder two lines later, and `contracts.story_memory`
# `_DESCRIPTION_PLACEHOLDERS` enforces the ban -- a model that obeyed the instruction emitted
# body_plan="neutral", failed validation, spent the single re-ask and hard-failed the story after
# two billed text calls. The two INSTRUCTIONAL uses now say "plain"; both bans are unchanged.
EXTRACTION_PROMPT = """Extract the entities from this child's story.

Decide the cast before describing it. Classify by agency: a character speaks, decides, or moves
on its own intent. An inert prop belongs only in objects, however much the story dwells on it; a
place belongs only in locations; a group present only as scenery ("the crowd", "the other bats")
is not a character. A personified object that acts on its own intent belongs only in characters,
never both. An object name such as "the robot (Leo)" is an alias for character Leo and must not
appear in objects.
Characters: at most 3, most important first — the first one is the story's protagonist. Return
fewer than 3 whenever fewer than 3 entities act; never pad the roster to reach 3.
Use the name the story gives the character. If the story never names them, use a short
descriptive label instead: "the narrator", "the younger sister", "the orange cat". Never emit a
redaction placeholder like <PERSON_1>. When the story is told in the first person its teller is a
character; when it is told in the third person, do not add a narrator character.
Species is the physical kind, never a job title or role: a human wizard is physically human.
Treat every character name as an identifier only. Do not infer age, gender, ethnicity, body,
face, clothing, or temperament from a name. Do not treat pronouns, speech, dialogue, jobs,
actions, or emotions as permanent appearance; "smiled" describes an expression in that moment,
not a human mouth or human face. Copy every stated permanent physical fact without alteration.
When the story is silent, choose one plain, child-safe, drawable design once. Keep animals,
robots, vehicles, objects, and other non-people species-appropriate unless the story explicitly
anthropomorphizes them. A named kind keeps that kind's face: a tin rooster still has a beak and a
comb, a robot dog still has a dog's muzzle. Only when the story establishes that the character has
no face, prefer positive visible morphology over a bare prohibition: use a positive faceless
surface/interface such as "smooth unbroken front surface" rather than only "no face".
face_or_interface names a face or a faceless surface, never both in one value.
Choose body_plan for the stable whole-subject silhouette and construction, and
face_or_interface for the stable visible head, face, sensory interface, or positive faceless
surface. Both are permanent facts, not pose, expression, damage, lighting, weather, style, or
story action. Derive is_humanoid from the resolved body plan; speech, walking, or emotion are
insufficient; a name or a pronoun alone never makes it true. Preserve explicit human-faced robots and explicit
anthropomorphic animals. If two characters are not stated to be identical, use distinct missing
visual details where possible; never invent a difference for stated twins.
Return both body_plan and face_or_interface as trimmed, single-line, concrete values under
120 Unicode code points. Never use none, neutral, unknown, or unspecified for them.
Fill only missing visual axes once with concrete, directly drawable, child-safe, non-stereotyped details that distinguish this character from the rest of the roster. Never use placeholder values such as neutral, none, unknown, or unspecified.
Return at least three stable visual discriminators across at least two of colours, body_features, and clothing. Set is_humanoid accurately; every humanoid needs a non-empty clothing description.

Locations and objects: whatever the story mentions. Describe each location by what is permanently there — not the weather, the lighting, the time of day, any damage, or what happens there. Copy every stated permanent fact without alteration. Fill missing detail once with plain, child-safe features that make the place visually recognizable. Describe each object on three axes instead of in prose: materials is what it is made of, colours is its colours, form_features is its shape and its permanent visible parts. Every axis entry is one short phrase that is true of the object in EVERY picture of the story, never a sentence and never several phrases joined by commas. Copy every stated permanent physical fact without alteration. Put anything that happens to the object during the story — painted, broken, eaten, opened, dirtied, mended — in changes_during_story instead, and leave it out of the axes; set changes_during_story to null when nothing about the object changes. Set owner_name to the character's name if owned by a character, or null if unowned.

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
        "analyze: extraction_prompt_version=%d; extracted %d characters, %d locations, %d objects, %d timeline events",
        EXTRACTION_PROMPT_VERSION,
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
            description=CharacterDescription(
                **extracted.description.model_dump(
                    exclude={"body_plan", "face_or_interface"}
                )
            ),
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
                materials=extracted.materials,
                colours=extracted.colours,
                form_features=extracted.form_features,
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

import logging
import re

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.config import MAX_SCENES, MIN_SCENE_WORDS, MIN_SCENES
from contracts.story_memory import Character, Location, Scene, StoryMemory, StoryObject, TimelineEvent
from providers import structured_text

log = logging.getLogger(__name__)


def split_sentences(text: str) -> list[str]:
    units = re.split(r'(?<=[.!?…])\s+|\n+', text)
    return [u.strip() for u in units if u.strip()]


# --- LLM boundary (D-F: transient wrapper, lives beside its node) ---

class ExtractedObjectEvent(BaseModel):
    object_name: str
    action: Literal["acquire", "release"]
    holder_name: str


class ExtractedScene(BaseModel):
    start: int                        # inclusive index into the numbered units
    end: int                          # inclusive
    characters_present: list[str]     # Character.name values — node maps to char_ids
    location_name: str | None = None  # Location.name value — node maps to a loc_id, null → inherit
    objects_present: list[str] = Field(default_factory=list)
    object_events: list[ExtractedObjectEvent] = Field(default_factory=list)
    visual_direction: str

    @field_validator("visual_direction")
    @classmethod
    def direction_is_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("visual_direction must not be blank")
        return value


class SceneSegmentation(BaseModel):
    scenes: list[ExtractedScene]


SEGMENTATION_PROMPT = """\
Split this story into picture-book pages (scenes). Return index ranges — do not copy or \
paraphrase any sentence.

Numbered story sentences:
{numbered}

Characters in the story: {roster}

Locations in the story: {locations}

Objects in the story: {objects}

Story plot points:
{plot}

Rules:
- At most 15 scenes.
- Each scene captures a distinct moment or plot point.
- start and end are inclusive sentence indices.
- characters_present lists character names exactly as given above.
- List a character in characters_present only when they are intended to be visible in this scene frame. List them even when the sentences refer to them only as he, she, it or they.
- location_name is where the scene happens, named exactly as given above. Leave it null if the \
story does not say.
- objects_present lists object names exactly as given above.
- object_events lists ordered acquire or release events for objects in the scene.
- visual_direction is a short literal visual direction containing subject, action, target or movement direction when applicable, and viewpoint.
- Together the scenes must cover every sentence."""


def segment_scenes(
    units: list[str],
    characters: list[Character],
    timeline: list[TimelineEvent],
    locations: list[Location],
    objects: list[StoryObject],
) -> SceneSegmentation:
    numbered = "\n".join(f"{i}: {u}" for i, u in enumerate(units))
    roster = ", ".join(c.name for c in characters) if characters else "(none)"
    places = ", ".join(loc.name for loc in locations) if locations else "(none)"
    things = ", ".join(obj.name for obj in objects) if objects else "(none)"
    plot = "\n".join(f"{e.order}. {e.summary}" for e in timeline) if timeline else "(none)"
    result = structured_text(
        SEGMENTATION_PROMPT.format(
            numbered=numbered, roster=roster, locations=places, objects=things, plot=plot
        ),
        SceneSegmentation,
    )
    log.info("segment: %d units → %d raw scenes", len(units), len(result.scenes))
    return result


def _merge_extracted(a: ExtractedScene, b: ExtractedScene) -> ExtractedScene:
    return ExtractedScene(
        start=a.start,
        end=b.end,
        characters_present=list(dict.fromkeys(a.characters_present + b.characters_present)),
        location_name=a.location_name or b.location_name,
        objects_present=list(dict.fromkeys(a.objects_present + b.objects_present)),
        object_events=[*a.object_events, *b.object_events],
        visual_direction=" ".join([a.visual_direction, b.visual_direction]),
    )


def repair(scenes: list[ExtractedScene], n: int) -> list[ExtractedScene]:
    if n == 0:
        return []

    # Clamp into [0, n-1]; drop ranges where start > end after clamping
    clamped = []
    for s in scenes:
        start = max(0, min(s.start, n - 1))
        end = max(0, min(s.end, n - 1))
        if start <= end:
            clamped.append(s.model_copy(update={"start": start, "end": end}))
    if len(clamped) != len(scenes):
        log.info("segment/repair: clamp dropped %d of %d ranges", len(scenes) - len(clamped), len(scenes))

    # Sort by start
    clamped.sort(key=lambda s: s.start)

    # De-overlap — earlier scene wins
    deoverlapped: list[ExtractedScene] = []
    prev_end = -1
    for s in clamped:
        new_start = max(s.start, prev_end + 1)
        if new_start <= s.end:
            deoverlapped.append(s.model_copy(update={"start": new_start, "end": s.end}))
            prev_end = s.end
    if len(deoverlapped) != len(clamped):
        log.info("segment/repair: de-overlap dropped %d ranges", len(clamped) - len(deoverlapped))

    if not deoverlapped:
        # Reached only when clamp + de-overlap emptied every range — a malformed index set, not a
        # missing visual direction (`ExtractedScene` already requires a non-blank one). The old
        # whole-story floor cannot be rebuilt here: it minted a scene with no direction, which
        # `generate_scene` would now have to draw blind.
        raise ValueError("segment: no usable scene range survived clamp and de-overlap")

    # Close gaps (leading, interior, trailing)
    gaps_closed = 0
    first = deoverlapped[0]
    if first.start > 0:
        deoverlapped[0] = first.model_copy(update={"start": 0, "end": first.end})
        gaps_closed += 1
    for i in range(len(deoverlapped) - 1):
        curr = deoverlapped[i]
        nxt = deoverlapped[i + 1]
        if curr.end + 1 < nxt.start:
            deoverlapped[i] = curr.model_copy(update={"start": curr.start, "end": nxt.start - 1})
            gaps_closed += 1
    last = deoverlapped[-1]
    if last.end < n - 1:
        deoverlapped[-1] = last.model_copy(update={"start": last.start, "end": n - 1})
        gaps_closed += 1
    if gaps_closed:
        log.info("segment/repair: gap-fill closed %d gap(s)", gaps_closed)

    # Merge to ≤MAX_SCENES — smallest combined unit count, ties → earliest
    if len(deoverlapped) > MAX_SCENES:
        log.info("segment/repair: merging %d scenes → %d", len(deoverlapped), MAX_SCENES)
    while len(deoverlapped) > MAX_SCENES:
        best_idx = 0
        best_size = (deoverlapped[0].end - deoverlapped[0].start + 1) + (deoverlapped[1].end - deoverlapped[1].start + 1)
        for i in range(1, len(deoverlapped) - 1):
            size = (deoverlapped[i].end - deoverlapped[i].start + 1) + (deoverlapped[i + 1].end - deoverlapped[i + 1].start + 1)
            if size < best_size:
                best_size = size
                best_idx = i
        a, b = deoverlapped[best_idx], deoverlapped[best_idx + 1]
        deoverlapped = (
            deoverlapped[:best_idx]
            + [_merge_extracted(a, b)]
            + deoverlapped[best_idx + 2:]
        )

    return deoverlapped


def merge_thin(scenes: list[ExtractedScene], units: list[str]) -> list[ExtractedScene]:
    """Fold pages too thin to draw into a neighbour (issue #31).

    Runs after `repair`, so it inherits total coverage and the MAX_SCENES cap and can only ever
    reduce the count further. Deliberately deterministic and not a prompt rule: SEGMENTATION_PROMPT
    already carries the timeline as plot points and already says "each scene captures a distinct
    moment or plot point", and prod job d83721d9 got 6 scenes out of 3 plot points anyway.

    ponytail: word count is a proxy for "is there a picture in this sentence". It catches fragments
    that cannot name a subject, a setting and an action, and misses a wordy sentence that depicts
    nothing. The real test needs another LLM call, which is the thing this avoids.
    """
    def words(scene: ExtractedScene) -> int:
        return sum(len(units[i].split()) for i in range(scene.start, scene.end + 1))

    merged = list(scenes)
    while len(merged) > MIN_SCENES:
        thin = next((i for i, s in enumerate(merged) if words(s) < MIN_SCENE_WORDS), None)
        if thin is None:
            break
        # Index of the LEFT half of the pair to fuse. Interior thin scenes go to the smaller
        # neighbour — the same policy the MAX_SCENES merge below already uses — so pages stay even;
        # at either end there is only one direction to go.
        if thin == len(merged) - 1:
            left = thin - 1
        elif thin > 0 and words(merged[thin - 1]) < words(merged[thin + 1]):
            left = thin - 1
        else:
            left = thin
        a, b = merged[left], merged[left + 1]
        merged[left : left + 2] = [_merge_extracted(a, b)]
    return merged


# visual-continuity §4.3 REVERSED this regex's job. It used to be the omitted-character backstop,
# recovering a roster name from the excerpt and appending it to `characters_present`; that
# unconditional recovery is now removed, because a name appearing in an excerpt does not prove the
# character should be VISIBLE (the motivating job drew characters who were only mentioned). The
# structured `characters_present` decision is the sole authority on the visible cast.
#
# What the match is used for now is the opposite check: `visual_direction` must not name a roster
# character outside that cast, which fails the job before any fal image is purchased (§4.8).
#
# Leading article stripped so a roster "the dragon" matches "a huge red dragon"; word boundaries so
# "the star" does not match "stars", which names no character (`prompt_optimizer.REFERENCE_CLAUSE`
# carves out the same case). Blind to pronouns, which is acceptable here: a direction that says only
# "he flees" names no one outside the cast and correctly does not trip the check.
_ARTICLE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)


def _names_character(text: str, name: str) -> bool:
    stem = _ARTICLE.sub("", name).strip()
    return bool(stem) and re.search(
        rf"\b{re.escape(stem)}\b", text, re.IGNORECASE
    ) is not None


def segment(state: StoryMemory) -> dict:
    text = state.input.redacted_text or state.input.raw_text
    units = split_sentences(text)
    if not units:
        return {"scenes": []}

    raw = segment_scenes(units, state.characters, state.timeline, state.locations, state.objects)
    repaired = merge_thin(repair(raw.scenes, len(units)), units)
    if len(repaired) != len(raw.scenes):
        log.info("segment: repair changed scene count %d → %d", len(raw.scenes), len(repaired))

    # §4.3 path 2: `analyze` never checks for a name collision, so a list-valued map sent ONE
    # named character's mention out as TWO references. First-seen wins — the roster is already in
    # prominence order, so the first id is the more important character.
    name_to_id: dict[str, str] = {}
    for c in state.characters:
        name_to_id.setdefault(c.name, c.char_id)

    name_to_loc = {loc.name: loc.loc_id for loc in state.locations}
    # Carry-forward seed (§4.1): s0 with no location takes locations[0], so a story that names a
    # place once still gets one setting for the whole book rather than none.
    prev_loc: str | None = state.locations[0].loc_id if state.locations else None

    object_by_name = {obj.name: obj for obj in state.objects}
    object_by_id = {obj.obj_id: obj for obj in state.objects}
    character_by_id = {character.char_id: character for character in state.characters}
    holder_by_obj = {obj.obj_id: obj.owner_char_id for obj in state.objects}
    active_objects: list[str] = []

    scenes = []
    for i, r in enumerate(repaired):
        excerpt = " ".join(units[r.start : r.end + 1])
        char_ids: list[str] = []
        for name in r.characters_present:
            char_id = name_to_id.get(name)
            if char_id is None:
                raise ValueError(f"segment: unknown character {name!r}")
            char_ids.append(char_id)
        char_ids = list(dict.fromkeys(char_ids))

        outside_cast = [
            name
            for name, char_id in name_to_id.items()
            if char_id not in char_ids and _names_character(r.visual_direction, name)
        ]
        if outside_cast:
            raise ValueError(f"segment: visual_direction names character outside visible cast: {outside_cast}")

        visible_objects: list[str] = []
        for name in r.objects_present:
            obj = object_by_name.get(name)
            if obj is None:
                raise ValueError(f"segment: unknown object {name!r}")
            if obj.obj_id not in active_objects:
                active_objects.append(obj.obj_id)
            visible_objects.append(obj.obj_id)

        visible_objects.extend(
            obj_id
            for obj_id in active_objects
            if holder_by_obj.get(obj_id) in char_ids
        )

        for event in r.object_events:
            obj = object_by_name.get(event.object_name)
            holder_id = name_to_id.get(event.holder_name)
            if obj is None:
                raise ValueError(f"segment: unknown object {event.object_name!r}")
            if holder_id is None:
                raise ValueError(f"segment: unknown holder {event.holder_name!r}")
            if obj.obj_id not in active_objects:
                active_objects.append(obj.obj_id)
            if event.action == "acquire":
                holder_by_obj[obj.obj_id] = holder_id
                if holder_id in char_ids:
                    visible_objects.append(obj.obj_id)
            else:
                visible_objects.append(obj.obj_id)
                if holder_by_obj.get(obj.obj_id) == holder_id:
                    holder_by_obj[obj.obj_id] = None

        visible_objects = list(dict.fromkeys(visible_objects))
        relations = [
            f"{object_by_id[obj_id].name} is held by {character_by_id[holder_id].name}."
            for obj_id in visible_objects
            if (holder_id := holder_by_obj.get(obj_id)) is not None
        ]
        visual_direction = " ".join([r.visual_direction, *relations])

        loc_id = name_to_loc.get(r.location_name) if r.location_name else None
        if r.location_name and loc_id is None:
            log.warning("segment: location %r not in roster, dropped", r.location_name)
        if loc_id is None:
            loc_id = prev_loc          # carry-forward, over the FINAL scene list in order
        prev_loc = loc_id

        scenes.append(Scene(
            scene_id=f"s{i}",
            text_excerpt=excerpt,
            caption=excerpt,
            characters_present=char_ids,
            location_id=loc_id,
            objects_present=visible_objects,
            visual_direction=visual_direction,
        ))
        log.info(
            "segment: s%d chars=%s objs=%s direction=%r",
            i,
            char_ids,
            visible_objects,
            visual_direction,
        )

    log.info("segment: minted %s", [s.scene_id for s in scenes])
    return {"scenes": scenes}


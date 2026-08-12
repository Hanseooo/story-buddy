import logging
import re

from pydantic import BaseModel

from app.config import MAX_SCENES, MIN_SCENE_WORDS, MIN_SCENES
from contracts.story_memory import Character, Location, Scene, StoryMemory, TimelineEvent
from providers import structured_text

log = logging.getLogger(__name__)


def split_sentences(text: str) -> list[str]:
    units = re.split(r'(?<=[.!?…])\s+|\n+', text)
    return [u.strip() for u in units if u.strip()]


# --- LLM boundary (D-F: transient wrapper, lives beside its node) ---

class ExtractedScene(BaseModel):
    start: int                        # inclusive index into the numbered units
    end: int                          # inclusive
    characters_present: list[str]     # Character.name values — node maps to char_ids
    location_name: str | None = None  # Location.name value — node maps to a loc_id, null → inherit


class SceneSegmentation(BaseModel):
    scenes: list[ExtractedScene]


SEGMENTATION_PROMPT = """\
Split this story into picture-book pages (scenes). Return index ranges — do not copy or \
paraphrase any sentence.

Numbered story sentences:
{numbered}

Characters in the story: {roster}

Locations in the story: {locations}

Story plot points:
{plot}

Rules:
- At most 15 scenes.
- Each scene captures a distinct moment or plot point.
- start and end are inclusive sentence indices.
- characters_present lists character names exactly as given above.
- location_name is where the scene happens, named exactly as given above. Leave it null if the \
story does not say.
- Together the scenes must cover every sentence."""


def segment_scenes(
    units: list[str],
    characters: list[Character],
    timeline: list[TimelineEvent],
    locations: list[Location],
) -> SceneSegmentation:
    numbered = "\n".join(f"{i}: {u}" for i, u in enumerate(units))
    roster = ", ".join(c.name for c in characters) if characters else "(none)"
    places = ", ".join(loc.name for loc in locations) if locations else "(none)"
    plot = "\n".join(f"{e.order}. {e.summary}" for e in timeline) if timeline else "(none)"
    result = structured_text(
        SEGMENTATION_PROMPT.format(numbered=numbered, roster=roster, locations=places, plot=plot),
        SceneSegmentation,
    )
    log.info("segment: %d units → %d raw scenes", len(units), len(result.scenes))
    return result



def repair(scenes: list[ExtractedScene], n: int) -> list[ExtractedScene]:
    if n == 0:
        return []

    # Clamp into [0, n-1]; drop ranges where start > end after clamping
    clamped = []
    for s in scenes:
        start = max(0, min(s.start, n - 1))
        end = max(0, min(s.end, n - 1))
        if start <= end:
            clamped.append(ExtractedScene(
                start=start, end=end,
                characters_present=s.characters_present, location_name=s.location_name,
            ))
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
            deoverlapped.append(ExtractedScene(
                start=new_start, end=s.end,
                characters_present=s.characters_present, location_name=s.location_name,
            ))
            prev_end = s.end
    if len(deoverlapped) != len(clamped):
        log.info("segment/repair: de-overlap dropped %d ranges", len(clamped) - len(deoverlapped))

    # Floor: if nothing survived clamp + de-overlap, emit one whole-story range
    if not deoverlapped:
        log.info("segment/repair: floor fired — emitting whole-story range")
        return [ExtractedScene(start=0, end=n - 1, characters_present=[])]

    # Close gaps (leading, interior, trailing)
    gaps_closed = 0
    first = deoverlapped[0]
    if first.start > 0:
        deoverlapped[0] = ExtractedScene(
            start=0, end=first.end,
            characters_present=first.characters_present, location_name=first.location_name,
        )
        gaps_closed += 1
    for i in range(len(deoverlapped) - 1):
        curr = deoverlapped[i]
        nxt = deoverlapped[i + 1]
        if curr.end + 1 < nxt.start:
            deoverlapped[i] = ExtractedScene(
                start=curr.start, end=nxt.start - 1,
                characters_present=curr.characters_present, location_name=curr.location_name,
            )
            gaps_closed += 1
    last = deoverlapped[-1]
    if last.end < n - 1:
        deoverlapped[-1] = ExtractedScene(
            start=last.start, end=n - 1,
            characters_present=last.characters_present, location_name=last.location_name,
        )
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
        merged_chars = list(dict.fromkeys(a.characters_present + b.characters_present))
        deoverlapped = (
            deoverlapped[:best_idx]
            + [ExtractedScene(
                start=a.start, end=b.end,
                characters_present=merged_chars,
                location_name=a.location_name or b.location_name,
            )]
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
        merged[left : left + 2] = [ExtractedScene(
            start=a.start,
            end=b.end,
            characters_present=list(dict.fromkeys(a.characters_present + b.characters_present)),
            location_name=a.location_name or b.location_name,
        )]
    return merged



def segment(state: StoryMemory) -> dict:
    text = state.input.redacted_text or state.input.raw_text
    units = split_sentences(text)
    if not units:
        return {"scenes": []}

    raw = segment_scenes(units, state.characters, state.timeline, state.locations)
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

    scenes = []
    for i, r in enumerate(repaired):
        excerpt = " ".join(units[r.start : r.end + 1])
        char_ids: list[str] = []
        for name in r.characters_present:
            if name in name_to_id:
                char_ids.append(name_to_id[name])
            else:
                log.warning("segment: name %r not in roster, dropped", name)

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
            # §4.3 path 1. `dict.fromkeys` preserves first-seen order, so removing a duplicate
            # cannot reorder the survivors (invariant 4).
            characters_present=list(dict.fromkeys(char_ids)),
            location_id=loc_id,
        ))


    log.info("segment: minted %s", [s.scene_id for s in scenes])
    return {"scenes": scenes}


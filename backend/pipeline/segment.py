import logging
import re

from pydantic import BaseModel

from app.config import MAX_SCENES
from contracts.story_memory import Character, Scene, StoryMemory, TimelineEvent
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


class SceneSegmentation(BaseModel):
    scenes: list[ExtractedScene]


SEGMENTATION_PROMPT = """\
Split this story into picture-book pages (scenes). Return index ranges — do not copy or \
paraphrase any sentence.

Numbered story sentences:
{numbered}

Characters in the story: {roster}

Story plot points:
{plot}

Rules:
- At most 15 scenes.
- Each scene captures a distinct moment or plot point.
- start and end are inclusive sentence indices.
- characters_present lists character names exactly as given above.
- Together the scenes must cover every sentence."""


def segment_scenes(
    units: list[str],
    characters: list[Character],
    timeline: list[TimelineEvent],
) -> SceneSegmentation:
    numbered = "\n".join(f"{i}: {u}" for i, u in enumerate(units))
    roster = ", ".join(c.name for c in characters) if characters else "(none)"
    plot = "\n".join(f"{e.order}. {e.summary}" for e in timeline) if timeline else "(none)"
    result = structured_text(
        SEGMENTATION_PROMPT.format(numbered=numbered, roster=roster, plot=plot),
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
            clamped.append(ExtractedScene(start=start, end=end, characters_present=s.characters_present))
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
            deoverlapped.append(ExtractedScene(start=new_start, end=s.end, characters_present=s.characters_present))
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
        deoverlapped[0] = ExtractedScene(start=0, end=first.end, characters_present=first.characters_present)
        gaps_closed += 1
    for i in range(len(deoverlapped) - 1):
        curr = deoverlapped[i]
        nxt = deoverlapped[i + 1]
        if curr.end + 1 < nxt.start:
            deoverlapped[i] = ExtractedScene(start=curr.start, end=nxt.start - 1, characters_present=curr.characters_present)
            gaps_closed += 1
    last = deoverlapped[-1]
    if last.end < n - 1:
        deoverlapped[-1] = ExtractedScene(start=last.start, end=n - 1, characters_present=last.characters_present)
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
            + [ExtractedScene(start=a.start, end=b.end, characters_present=merged_chars)]
            + deoverlapped[best_idx + 2:]
        )

    return deoverlapped


def segment(state: StoryMemory) -> dict:
    text = state.input.redacted_text or state.input.raw_text
    units = split_sentences(text)
    if not units:
        return {"scenes": []}

    raw = segment_scenes(units, state.characters, state.timeline)
    repaired = repair(raw.scenes, len(units))
    if len(repaired) != len(raw.scenes):
        log.info("segment: repair changed scene count %d → %d", len(raw.scenes), len(repaired))

    name_to_ids: dict[str, list[str]] = {}
    for c in state.characters:
        name_to_ids.setdefault(c.name, []).append(c.char_id)

    scenes = []
    for i, r in enumerate(repaired):
        excerpt = " ".join(units[r.start : r.end + 1])
        char_ids: list[str] = []
        for name in r.characters_present:
            if name in name_to_ids:
                char_ids.extend(name_to_ids[name])
            else:
                log.warning("segment: name %r not in roster, dropped", name)
        scenes.append(Scene(scene_id=f"s{i}", text_excerpt=excerpt, caption=excerpt, characters_present=char_ids))

    log.info("segment: minted %s", [s.scene_id for s in scenes])
    return {"scenes": scenes}

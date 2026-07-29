import logging
import re

from pydantic import BaseModel

from contracts.story_memory import Character, Scene, StoryMemory, TimelineEvent
from pipeline.analyze import caption_for
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

    # Step 1: Clamp into [0, n-1]; drop ranges where start > end after clamping
    clamped = []
    for s in scenes:
        start = max(0, min(s.start, n - 1))
        end = max(0, min(s.end, n - 1))
        if start <= end:
            clamped.append(ExtractedScene(start=start, end=end, characters_present=s.characters_present))

    # Step 2: Sort by start
    clamped.sort(key=lambda s: s.start)

    # Step 3: De-overlap — earlier scene wins
    deoverlapped: list[ExtractedScene] = []
    prev_end = -1
    for s in clamped:
        new_start = max(s.start, prev_end + 1)
        if new_start <= s.end:
            deoverlapped.append(ExtractedScene(start=new_start, end=s.end, characters_present=s.characters_present))
            prev_end = s.end

    # Step 5 (floor): if nothing survived steps 1-3, one whole-story range
    if not deoverlapped:
        return [ExtractedScene(start=0, end=n - 1, characters_present=[])]

    # Step 4: Close gaps
    # Leading gap
    first = deoverlapped[0]
    if first.start > 0:
        deoverlapped[0] = ExtractedScene(start=0, end=first.end, characters_present=first.characters_present)
    # Interior gaps: uncovered run attaches to preceding scene
    for i in range(len(deoverlapped) - 1):
        curr = deoverlapped[i]
        nxt = deoverlapped[i + 1]
        if curr.end + 1 < nxt.start:
            deoverlapped[i] = ExtractedScene(start=curr.start, end=nxt.start - 1, characters_present=curr.characters_present)
    # Trailing gap
    last = deoverlapped[-1]
    if last.end < n - 1:
        deoverlapped[-1] = ExtractedScene(start=last.start, end=n - 1, characters_present=last.characters_present)

    # Step 6: Merge to ≤15 — smallest combined unit count, ties → earliest
    while len(deoverlapped) > 15:
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
    # ponytail: one scene per story. The real segmenter splits into pages and mints s0..sN;
    # this mints s0 only. scene_id convention: §2.1.
    text = state.input.redacted_text or state.input.raw_text
    return {"scenes": [Scene(scene_id="s0", text_excerpt=text, caption=caption_for(text))]}

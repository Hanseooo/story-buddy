"""Pure length guard (spec `docs/specs/input-gate-hardening.md` §4a). No I/O, no exceptions —
the minimum-length rejection is `app.main`'s job, this module only clamps."""
import re

from app.config import MAX_STORY_WORDS

_WORD = re.compile(r"\S+")


def word_count(text: str) -> int:
    return len(_WORD.findall(text))


def clamp_story(text: str) -> tuple[str, bool]:
    """Returns (final_text, truncated). Never raises; the floor is main.py's job."""
    text = text.replace("\r\n", "\n")
    spans = list(_WORD.finditer(text))
    if len(spans) <= MAX_STORY_WORDS:
        return text, False

    head = text[: spans[MAX_STORY_WORDS - 1].end()]   # slice the ORIGINAL string
    floor = MAX_STORY_WORDS // 2
    for cut in (_last_paragraph(head), _last_sentence(head)):
        if cut is not None and len(_WORD.findall(cut)) >= floor:
            return cut.rstrip(), True
    # ponytail: collapse any \n\n that survived into the hard cut — the paragraph rule
    # already ran and rejected it (floor guard), so destroying it here is correct.
    return re.sub(r"\n{2,}", " ", head).rstrip(), True


def _last_paragraph(text: str) -> str | None:
    matches = list(re.finditer(r"\n\s*\n", text))
    if not matches:
        return None
    return text[: matches[-1].start()]


def _last_sentence(text: str) -> str | None:
    matches = list(re.finditer(r"[.!?](?=\s|$)", text))
    if not matches:
        return None
    return text[: matches[-1].end()]

"""The node every other image in the book depends on (spec `docs/specs/character-bible.md`).

Draws one canonical reference per principal character, judges it against the
`CharacterDescription` it came from, re-rolls up to 3 times, and persists the accepted path
plus its verdict. ADR-028 falsified ADR-007's assumption that a reference is correct *because*
it was generated from the description; this node is the gate that makes that failure visible.

It does NOT fix the rate — at the measured draw quality 3 draws still ship an off-spec
reference roughly 42% of the time, now with the verdict persisted instead of silently. The fix
for the rate is swapping `fal_image_model` (ADR-001's named seam), not anything in this file.
"""
import base64
import logging

from app.db import get_supabase_client
from contracts.story_memory import CharacterDescription, RefVerdict
from providers import judge, text_to_image

log = logging.getLogger(__name__)

MAX_DRAWS = 3   # ADR-028. Not ADR-010's 1: a bad scene is one page, a bad reference is every page.

BUCKET = "storybook-images"

# Reason-then-score (ADR-004) applies to EVERY judge call. `RefVerdict` already declares
# `differences_observed` before `matches_description`, and `providers._assert_field_order`
# enforces the ordering on the wire — this prompt only has to ask in the same order.
JUDGE_PROMPT = """\
This image is meant to be a character reference drawn from the description below.

Description: {subject}

First describe every difference you observe between the image and the description. Then say \
whether the image matches the description, and list which of the described attributes are \
actually present in the image."""

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


def _data_uri(image: bytes) -> str:
    """The judge is shown base64, never a signed URL (CC-4). What is PERSISTED is the path.

    ponytail: inline base64. Risk recorded in spec §8 — a 1024^2 PNG is ~1.9 MB encoded and
    `providers._run_fal` hardcodes png. If OpenRouter rejects the body on the first real call,
    the fix is a signed-URL helper in `app/db.py` — a deliberate change, not a hotfix.
    """
    return "data:image/png;base64," + base64.b64encode(image).decode()


def _upload(image: bytes, story_id: str, char_id: str) -> str:
    path = f"{story_id}/ref-{char_id}.png"
    get_supabase_client().storage.from_(BUCKET).upload(
        path, image, {"content-type": "image/png", "upsert": "true"}
    )
    return path


def mint_reference(
    description: CharacterDescription,
    name: str,
    style_fragment: str,
    story_id: str,
    char_id: str,
) -> tuple[str, RefVerdict | None, int]:
    """The node's ONE effect boundary (MASTER_SPEC §6): draw, judge, re-roll, upload.

    Returns `(storage_path, verdict, draws_made)`. The draw count is reported rather than
    inferred because the loop lives in here and the node needs it for CC-3 (invariant 4).

    The loop is node-internal and adds no graph edge and no super-step (ADR-028 Decision 3),
    so ADR-003 and ADR-024 are unamended by it.
    """
    prompt = reference_prompt(description, name, style_fragment)
    judge_prompt = JUDGE_PROMPT.format(subject=_describe(description, name))
    candidates: list[tuple[bytes, RefVerdict]] = []
    draws = 0

    for _ in range(MAX_DRAWS):
        # No seed: a fixed one makes every draw identical and the re-roll a no-op (§4).
        # A hard failure raises → job `failed` with an ADR-025 `failure_reason`. No artifact
        # exists, so there is nothing to ship and no node-level retry.
        image = text_to_image(prompt)
        draws += 1
        try:
            verdict = judge(judge_prompt, [_data_uri(image)], RefVerdict)
        except Exception:
            # DIFFERENT policy from text_to_image above, deliberately (§4). The artifact exists
            # and is paid for; only the CHECK failed. `None` stays honest and is distinguishable
            # from a FAILED verdict (matches_description=False). Do not "fix" this asymmetry.
            log.warning(
                "char_bible: %s judge failed on draw %d — accepting unchecked, ref_verdict=None",
                char_id, draws, exc_info=True,
            )
            return _upload(image, story_id, char_id), None, draws

        # CC-5: a wrong character downstream traces back to a specific reference and draw.
        log.info(
            "char_bible: %s draw %d/%d matches=%s attributes=%s",
            char_id, draws, MAX_DRAWS, verdict.matches_description, verdict.attributes_present,
        )
        if verdict.matches_description:
            log.info("char_bible: %s accepted draw %d", char_id, draws)
            return _upload(image, story_id, char_id), verdict, draws
        candidates.append((image, verdict))

    winner = best_draw([v for _, v in candidates])
    log.warning(
        "char_bible: %s all %d draws failed — best-of picked draw %d, FAILING verdict persisted",
        char_id, draws, winner + 1,
    )
    image, verdict = candidates[winner]
    return _upload(image, story_id, char_id), verdict, draws


def char_bible(state) -> dict:
    # ponytail: stub — Plan B Task 4 fills this in (select, mint, map, bump cost).
    return {}

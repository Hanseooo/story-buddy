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

from app.config import settings
from app.db import get_supabase_client
from contracts.story_memory import CharacterDescription, RefVerdict, StoryMemory
from providers import judge, text_to_image

log = logging.getLogger(__name__)

MAX_DRAWS = 3   # ADR-028. Not ADR-010's 1: a bad scene is one page, a bad reference is every page.

BUCKET = "storybook-images"

# Reason-then-score (ADR-004) applies to EVERY judge call. `RefVerdict` already declares
# `differences_observed` before `matches_description`, and `providers._assert_field_order`
# enforces the ordering on the wire — this prompt only has to ask in the same order.
#
# The question is CONTRADICTION, not difference. Asking for "every difference" made a thin
# description unpassable: prod job 4cb31620 (2026-08-11) rendered c0 as "the narrator - girl;
# the protagonist", and the judge failed all 3 draws because the image showed hair and clothing
# the description never mentioned. Absence is not a defect — a text-to-image model must draw
# *some* hair, so unlisted details are unavoidable and would fail every draw at every draw
# count. ADR-028 targets off-spec on a *stated* feature; spec §4's "species-only" row is
# amended to match (it predicted near-vacuously TRUE and got the opposite).
#
# BUMP THIS whenever the wording above changes what a FALSE verdict means. It is persisted as
# `Character.ref_verdict_prompt_version`, and it is the only thing that makes the ADR-028 hit
# rate comparable across prompt revisions — v1 measured the judge's tolerance for sparse
# descriptions, v2 measures the generator. Unversioned, the 2026-08-11 change silently
# invalidated every verdict before it and the series had to restart.
JUDGE_PROMPT_VERSION = 2

JUDGE_PROMPT = """\
This image is meant to be a character reference drawn from the description below.

Description: {subject}

The description lists only what the story stated. The image will necessarily show details it \
does not mention — hair, clothing, background — and those are NOT differences.

First describe any way the image CONTRADICTS a stated attribute. Then say whether the image \
matches the description, and list which of the described attributes are actually present in \
the image."""

# `analyze`'s EXTRACTION_PROMPT deliberately says "leave them empty rather than inventing
# details", so a character routinely arrives with nothing drawable — prod job 4cb31620
# (2026-08-11) drew c0 from "the narrator - girl; the protagonist". Every page of the book
# inherits that one reference, so the generator gets a neutral floor rather than a role noun.
#
# Deliberately vague: it must not assert anything the story could contradict. Keyed on the
# VISUAL axes, not on how many fields are populated — species and notes are identity, not
# appearance, and c0 had both while specifying nothing to draw.
THIN_DESCRIPTION_FILLER = ", a friendly children's picture-book character"

# Two clauses here exist to stop the generator anthropomorphising a non-human subject. Prod job
# 4cb31620 (2026-08-11) drew c1 — "the star" — as a smiling mascot with arms and legs; the judge
# caught it, so it is a TRUE negative and not a judging bug.
#
# 1. The pose ask used to read "full-body ... standing". That is a human anatomy instruction, and
#    a model told to draw a star standing has to invent legs to comply — we authored half of that
#    failure. "shown in full" asks for the same framing without asserting a body.
# 2. The explicit guard below. Deliberately UNCONDITIONAL rather than branching on species:
#    deciding that "star" and "jeepney" are non-humanoid while "girl" is not needs a word list
#    that is wrong the first time a child writes something not on it, and the clause is a no-op
#    for a person anyway. Unlike THIN_DESCRIPTION_FILLER there is no structural signal to key on.
#
# Draw-prompt only, like the filler — the judge must keep measuring the generator against the
# STORY, not against our instructions to the generator.
REFERENCE_PROMPT = """\
A single character reference of one character, shown in full, facing forward, centred on a \
plain neutral background. No other characters, no scenery, no text, no border.

Character: {subject}

If the character is not a person, draw it as the kind of thing it actually is — give it no human \
body and no human face unless the description above says so.

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
    "beautiful", "8k" or "highly detailed".

    The enrichment below is the ONE sanctioned divergence from `_describe`'s shared output, and
    it is one-directional: the draw prompt gets it, the judge prompt never does. If the judge saw
    it, it would become a *stated* attribute and draws would start failing over our filler
    instead of over the story — ADR-028 measures the generator against the STORY.
    """
    subject = _describe(description, name)
    if not (description.colours or description.body_features or description.clothing):
        subject += THIN_DESCRIPTION_FILLER
    return REFERENCE_PROMPT.format(subject=subject, style_fragment=style_fragment)


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


def _upload(image: bytes, story_id: str, char_id: str, n: int) -> str:
    path = f"{story_id}/ref-{char_id}-{n}.png"
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
            return _upload(image, story_id, char_id, 1), None, draws

        # CC-5: a wrong character downstream traces back to a specific reference and draw.
        log.info(
            "char_bible: %s draw %d/%d matches=%s attributes=%s",
            char_id, draws, MAX_DRAWS, verdict.matches_description, verdict.attributes_present,
        )
        if verdict.matches_description:
            log.info("char_bible: %s accepted draw %d", char_id, draws)
            return _upload(image, story_id, char_id, 1), verdict, draws
        candidates.append((image, verdict))

    winner = best_draw([v for _, v in candidates])
    log.warning(
        "char_bible: %s all %d draws failed — best-of picked draw %d, FAILING verdict persisted",
        char_id, draws, winner + 1,
    )
    image, verdict = candidates[winner]
    return _upload(image, story_id, char_id, 1), verdict, draws


def _mint_targeted(state: StoryMemory) -> dict:
    """ADR-029 §2: one draw, one judge call, unconditional overwrite. `n` is a uniqueness
    suffix, not a per-character draw count — `ref_retry_count` is per BOOK (spec §4.6), so a
    second tap on a different character still advances `n`. A per-character counter would be a
    second source of truth for something that only needs to be unique.
    """
    retry = state.reference_retry
    character = next(c for c in state.characters if c.char_id == retry.char_id)
    style_fragment = state.style.prompt_fragment or settings.default_style_fragment
    description = character.description.model_copy(update={"notes": retry.attribute})
    prompt = reference_prompt(description, character.name, style_fragment)
    if retry.attribute not in prompt:
        prompt = f"{prompt}\n\nBe sure to include: {retry.attribute}."
    judge_prompt = JUDGE_PROMPT.format(subject=_describe(description, character.name))

    image = text_to_image(prompt)
    verdict = judge(judge_prompt, [_data_uri(image)], RefVerdict)
    n = state.cost.ref_retry_count + 2  # post-bump: rc is incremented below; +2 = +1(initial) +1(this tap)
    path = _upload(image, state.story_id, character.char_id, n)

    characters = [
        c.model_copy(update={
            "canonical_ref_image": path,
            "ref_verdict": verdict,
            "ref_verdict_prompt_version": JUDGE_PROMPT_VERSION,
            "ref_moderation_status": None,
        })
        if c.char_id == character.char_id
        else c
        for c in state.characters
    ]
    cost = state.cost.model_copy(
        update={"image_count": state.cost.image_count + 1, "ref_retry_count": state.cost.ref_retry_count + 1}
    )
    log.info(
        "char_bible: targeted redraw for %s, attribute=%r, ref_retry_count=%d",
        character.char_id, retry.attribute, cost.ref_retry_count,
    )
    return {"characters": characters, "cost": cost, "reference_retry": None}


def char_bible(state: StoryMemory) -> dict:
    """Pure: select, map, bump, partial-return. Every effect is behind `mint_reference` (or,
    on a retry, `_mint_targeted`).
    """
    if state.reference_retry is not None:
        return _mint_targeted(state)

    # Cap FIRST (invariant 1, ADR-004), THEN filter (invariant 6). The order is load-bearing:
    # filtering first slides the 2-slot window onto c2 when c0 is already referenced, producing
    # three canonical references and breaking the cap.
    selected = [c for c in state.characters[:2] if c.canonical_ref_image is None]
    if not selected:
        return {}

    # Nothing writes `style` today, so this fallback is the normal Phase-1 path, not an error
    # path. The three-preset dict and `style_preset_id` resolution belong to `style-presets`.
    style_fragment = state.style.prompt_fragment or settings.default_style_fragment

    minted: dict[str, tuple[str, RefVerdict | None]] = {}
    draws_made = 0
    for character in selected:
        path, verdict, draws = mint_reference(
            character.description, character.name, style_fragment, state.story_id, character.char_id
        )
        minted[character.char_id] = (path, verdict)
        draws_made += draws

    # Invariant 2: `characters` has NO reducer, so a partial return REPLACES the list —
    # returning only the modified entries would silently delete every other character.
    characters = [
        c.model_copy(update={
            "canonical_ref_image": minted[c.char_id][0],
            "ref_verdict": minted[c.char_id][1],
            # Stamped even when the verdict is None (degraded judge): it records which prompt
            # this reference was checked against, which is true whether or not a verdict came back.
            "ref_verdict_prompt_version": JUDGE_PROMPT_VERSION,
        })
        if c.char_id in minted
        else c
        for c in state.characters
    ]
    # Invariant 4: `cost` has no reducer either — copy and bump, never rebuild from zero.
    # CC-3: this node's prelude bound is 6 (2 references x 3 draws). `image-generator` owns the
    # scene-image half of `image_count`; the breaker cannot trip until it writes its share.
    cost = state.cost.model_copy(update={"image_count": state.cost.image_count + draws_made})

    log.info("char_bible: minted %s in %d draws", sorted(minted), draws_made)
    return {"characters": characters, "cost": cost}

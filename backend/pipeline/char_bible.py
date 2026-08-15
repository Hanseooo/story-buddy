"""The node every other image in the book depends on (spec `docs/specs/character-bible.md`).

Draws one canonical reference per principal character, judges it against the
`CharacterDescription` it came from, re-rolls up to 3 times, and persists the accepted path
plus its verdict. ADR-028 falsified ADR-007's assumption that a reference is correct *because*
it was generated from the description; this node is the gate that makes that failure visible.

It does NOT fix the rate — 3 draws still ship an off-spec reference often, now with the verdict
persisted instead of silently. The fix for the rate is swapping `fal_image_model` (ADR-001's
named seam), not anything in this file.

ADR-028's "roughly 42%" is deliberately not quoted here any more: it was measured against a gate
that accepted whatever the judge's boolean said, and prod job b9506307 showed that boolean going
TRUE on a verdict whose own prose read "This is a contradiction". Every draw the old gate passed
is unmeasured, so 42% is a floor, not an estimate. ADR-034 re-derives acceptance from a list; the
series restarts at JUDGE_PROMPT_VERSION 3.
"""
import base64
import logging

from app.config import settings
from app.db import get_supabase_client
from contracts.story_memory import CharacterDescription, RefVerdict, StoryMemory
from pipeline.prompt_optimizer import filtered_description
from providers import judge, text_to_image

log = logging.getLogger(__name__)

MAX_DRAWS = 3   # ADR-028. Not ADR-010's 1: a bad scene is one page, a bad reference is every page.

BUCKET = "storybook-images"

# Reason-then-score (ADR-004) applies to EVERY judge call. `RefVerdict` already declares
# `differences_observed` before `matches_description`, and `providers._assert_field_order`
# enforces the ordering on the wire — this prompt only has to ask in the same order.
#
# v3 (ADR-034): the acceptance question is asked as a LIST, not as a boolean. v2 asked for prose
# and then for a verdict, and prod job b9506307 answered "This is a contradiction" followed by
# matches_description=true — ordering made the model reason first, it did not make the score
# follow the reasoning. The prompt below therefore asks for one list entry per contradicted
# attribute and the code derives acceptance from the list's length. The boolean is still asked
# for, and still recorded, purely so the disagreement rate stays measurable.
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
# 4 (lettering-suppression §4.1): adds the text question. v3 verdicts carry no `text_free` signal
# at all — they default True — so the lettering rate is only measurable from v4 forward.
# 5 (visual-continuity §4.9): makes the walk explicit. Job 3cc05c4b's judge wrote that the
# reference read young and cheerful where the description said dark and imposing, and STILL
# returned `contradictions=[]` — the prose found the defect and the list did not carry it, so
# ADR-034's derived gate accepted the draw. v4 asked for the list without ever saying the two had
# to agree. v5 says it, and says to take the stated attributes one at a time so a skim cannot
# clear an axis it never looked at. v4 verdicts are not comparable: an empty v4 list may mean
# "clean" or "skimmed", and only from v5 do the two stop sharing a value.
JUDGE_PROMPT_VERSION = 5

JUDGE_PROMPT = """\
This image is meant to be a character reference drawn from the description below.

Description: {subject}

The description lists only what the story stated. The image will necessarily show details it \
does not mention — hair, clothing, background — and those are NOT differences.

Take the stated attributes one at a time and check each one against the image; do not skip any. \
First describe any way the image CONTRADICTS a stated attribute. Then list the contradictions: \
one entry for each stated attribute the image contradicts, naming the attribute and what the \
image shows instead. Everything you described as contradicted must appear in that list. If the \
image contradicts nothing that was stated, leave that list empty. \
Then say whether the image matches the description, list which of the described attributes \
are actually present in the image, and finally say whether the picture is free of any text — any \
letters, numbers or writing anywhere in it, including on signs, doors, books and clothing."""

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
# Everything a reference must NOT accrete, on the channel that actually subtracts (`providers.
# NEGATIVE_PROMPT`'s comment: a `no <term>` clause in the positive prompt competes with what
# Qwen-Image is best at and loses). The old prompt tail said "No other characters, no scenery, no
# text, no border" and the 2026-08-13 draws came back with a wall/floor horizon and a cast shadow
# behind both non-human subjects anyway — a half-drawn room, which is how furniture from the
# child's own story ends up standing behind a character who is supposed to be on nothing.
#
# Passed per call rather than folded into NEGATIVE_PROMPT: `text_to_image` is also
# `generate_scene`'s no-reference fallback (`generate_scene.py:57`), and a scene needs the exact
# scenery this suppresses. Terms are generic — "furniture", not "bed" — because the noun is
# whatever the child wrote.
# The framing terms are here for the same reason as the scenery ones. "shown in full" and then
# "drawn in full with nothing cropped" were BOTH measured being ignored for human subjects on
# 2026-08-13 — a "girl" came back cropped at the chest, then at the waist, while the monster and
# the robot came back whole. Portrait bias is strong enough on a human that only the negative
# channel moves it, and a reference cropped at the waist cannot anchor `clothing` — one of the
# four judged axes — for any scene that inherits it.
REFERENCE_NEGATIVE = (
    "background scenery, room, interior, furniture, floor, wall, horizon line, ground, landscape, "
    "cast shadow, second character, other characters, crowd, "
    "close-up, bust shot, head and shoulders, waist-up, cropped at the waist, cropped limbs, "
    "back view, seen from behind, "
    "letterbox, black bars, "
    "model sheet, turnaround, multiple views, colour swatches, name plate, border, frame"
)

# The opening clause describes the PICTURE and never names the document. It used to read "A single
# character reference of one character", and on 2026-08-13 a draw for "the monster - monster;
# purple; tiny, lost" returned the word **"Reference;"** lettered across the top in the style's own
# font. NEGATIVE_PROMPT already listed "text, letters, words, labels, captions" and did not stop it:
# a negative prompt subtracts a tendency, it cannot outvote a word sitting in the positive prompt.
# "character reference" also carries the model-sheet prior — in training data that phrase means a
# sheet WITH a name plate — so we were asking for the artifact whose defining feature is the label
# we then asked not to have.
#
# The framing clause replaces "shown in full", measured being ignored in the same batch (a "girl"
# came back as a head-and-shoulders crop). "full shot" is a framing term, not an anatomy one — the
# note below on "standing" applies to any phrasing that implies a body, so "head to toe" is out.
# REFERENCE_NEGATIVE carries the other half; the positive clause alone did not hold on a human.
#
# "facing forward" became "seen from a slight angle rather than straight on" (2026-08-13). Head-on
# is the WORST view of a snouted or long-bodied subject: foreshortening hides the snout, the neck,
# the tail and the wing profile — the whole identifying silhouette — so the reference anchored least
# of the character it matters most for. Prod job 483056e0's dragon came back head-on and every page
# inherited it. The turn is a framing term, not an anatomy one, so the 2026-08-11 "standing" lesson
# is respected; and dropping the word "facing" is what makes it a no-op for a subject with no face
# at all, where "facing forward" was arguably part of what induced the mascot.
#
# UNCONDITIONAL, on the same reasoning as the non-human clause below. A "has a snout" test is the
# species word list that comment already rejects, and it would be wrong on "the star" first.
#
# NOT "three-quarter view": that is model-sheet vocabulary, and REFERENCE_NEGATIVE spends four terms
# suppressing the model-sheet prior. The negative carries the overshoot half — a slight turn that
# runs to a back view anchors nothing — on the channel that moves framing.
REFERENCE_PROMPT = """\
One character alone, a full shot showing the whole of it, seen from a slight angle rather than \
straight on, centred against a flat empty background of one single colour.

The character is {subject}.

If the character is not a person, draw it as the kind of thing it actually is — give it no human \
body and no human face unless the description above says so.

Style: {style_fragment}"""


def _describe(description: CharacterDescription, name: str, notes: bool = True) -> str:
    """The `CharacterDescription` axes as one line. Shared by the draw prompt and the judge
    prompt so they can never drift into describing different characters.

    `notes=False` excludes free-prose narrative metadata from both the normal draw and judge
    prompts. A role such as "builds and names the robot" is not visual identity and can make the
    canonical portrait draw the robot. Targeted redraws retain their tapped attribute through the
    explicit `Be sure to include:` fallback in `_mint_targeted`.
    """
    axes = [
        description.species,
        ", ".join(description.colours),
        ", ".join(description.body_features),
        ", ".join(description.clothing),
        description.notes if notes else None,
    ]
    # Plain commas, no " - " and no ";". Those two separators made the line read as a caption, and
    # Qwen-Image drew it: a 2026-08-13 draw of `the star - star; tiny` came back with **"Hoe -
    # Star:"** lettered across the top — a mangled render of this very string, dash and all. It is
    # the same defect as the old prompt's "Reference;", one layer in, and it is the "name above the
    # character" a reader sees. Commas describe; dashes and colons label.
    populated = [axis for axis in axes if axis]
    return ", ".join([name, *populated])


def reference_prompt(description: CharacterDescription, name: str, style_fragment: str) -> str:
    """Pure. ADR-022: the fragment names a medium and its physical artifacts — it never says
    "beautiful", "8k" or "highly detailed".

    The enrichment below is the ONE sanctioned divergence from `_describe`'s shared output, and
    it is one-directional: the draw prompt gets it, the judge prompt never does. If the judge saw
    it, it would become a *stated* attribute and draws would start failing over our filler
    instead of over the story — ADR-028 measures the generator against the STORY.
    """
    subject = _describe(description, name, notes=False)
    if not (description.colours or description.body_features or description.clothing):
        subject += THIN_DESCRIPTION_FILLER
    return REFERENCE_PROMPT.format(subject=subject, style_fragment=style_fragment)


def best_draw(verdicts: list[RefVerdict]) -> int:
    """Pure. Best-of when every draw failed: fewest contradictions, then most attributes present,
    ties → earliest (ADR-010, ADR-034).

    `attributes_present` was the sole key until ADR-034 and it is noisy — prod job b9506307 listed
    "glowing" for a flat teal image and "secondary character", which is a `notes` value and not a
    visual attribute at all. It is demoted to a tiebreak behind a count of actual defects rather
    than dropped: between two draws that contradict the description equally, "showed more of what
    was asked for" is still the better of the two signals available.

    `text_free` (lettering-suppression §4.2) sits BEHIND contradictions and AHEAD of
    attributes_present: a draw that contradicts the child's own description is worse than one
    with a sign in it, and `attributes_present` is documented noise (ADR-034).

    `char_bible`'s own rule over `RefVerdict`. UNRELATED to `regeneration-controller`'s
    lexicographic scene rule over `VlmVerdict` — different schema, different question. Do not
    unify them.
    """
    return max(
        range(len(verdicts)),
        key=lambda i: (
            -len(verdicts[i].contradictions),
            verdicts[i].text_free,
            len(verdicts[i].attributes_present),
            -i,
        ),
    )


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
    n: int = 1,
) -> tuple[str, RefVerdict | None, int]:
    """The node's ONE effect boundary (MASTER_SPEC §6): draw, judge, re-roll, upload.

    Returns `(storage_path, verdict, draws_made)`. The draw count is reported rather than
    inferred because the loop lives in here and the node needs it for CC-3 (invariant 4).

    `n` is the uniqueness suffix on the single monotonic per-book sequence both minting paths
    share (spec §4.4) — NOT a per-character draw count. It defaults to 1 for the initial mint;
    a moderation redraw passes a higher one so the flagged image survives as evidence.

    The loop is node-internal and adds no graph edge and no super-step (ADR-028 Decision 3),
    so ADR-003 and ADR-024 are unamended by it.
    """
    # ADR-035 surfaces 1 and 2. Prod job b9506307 asked for `star; glowing; tiny` under a fragment
    # ending "no glow": the draw could not satisfy it, and post-ADR-034 the judge can legitimately
    # contradict it on all 3 draws, burning the budget on every job. Unlike the two one-directional
    # divergences in `_describe`, this is filtered for BOTH prompts — the defect is asking at all.
    description = filtered_description(description, style_fragment)
    prompt = reference_prompt(description, name, style_fragment)
    judge_prompt = JUDGE_PROMPT.format(subject=_describe(description, name, notes=False))
    candidates: list[tuple[bytes, RefVerdict]] = []
    draws = 0

    for _ in range(MAX_DRAWS):
        # No seed: a fixed one makes every draw identical and the re-roll a no-op (§4).
        # A hard failure raises → job `failed` with an ADR-025 `failure_reason`. No artifact
        # exists, so there is nothing to ship and no node-level retry.
        image = text_to_image(prompt, negative_extra=REFERENCE_NEGATIVE)
        draws += 1
        try:
            verdict = judge(judge_prompt, [_data_uri(image)], RefVerdict)
        except Exception:
            # DIFFERENT policy from text_to_image above, deliberately (§4). The artifact exists
            # and is paid for; only the CHECK failed. `None` stays honest and is distinguishable
            # from a FAILED verdict (a non-empty `contradictions`). Do not "fix" this asymmetry.
            log.warning(
                "char_bible: %s judge failed on draw %d — accepting unchecked, ref_verdict=None",
                char_id, draws, exc_info=True,
            )
            return _upload(image, story_id, char_id, n), None, draws

        # CC-5: a wrong character downstream traces back to a specific reference and draw.
        # `matches` is logged beside the list it no longer controls: the two disagreeing is the
        # ADR-034 failure, and this line is where it becomes visible in production.
        log.info(
            "char_bible: %s draw %d/%d contradictions=%s matches=%s attributes=%s text_free=%s",
            char_id, draws, MAX_DRAWS,
            verdict.contradictions, verdict.matches_description, verdict.attributes_present,
            verdict.text_free,
        )
        # lettering-suppression §4.2. ANDed with the ADR-034 list, never folded into it: a
        # contradiction is the wrong character, text is the right character in a marked room.
        if not verdict.contradictions and verdict.text_free:
            log.info("char_bible: %s accepted draw %d", char_id, draws)
            return _upload(image, story_id, char_id, n), verdict, draws
        candidates.append((image, verdict))

    winner = best_draw([v for _, v in candidates])
    log.warning(
        "char_bible: %s all %d draws failed — best-of picked draw %d, FAILING verdict persisted",
        char_id, draws, winner + 1,
    )
    image, verdict = candidates[winner]
    return _upload(image, story_id, char_id, n), verdict, draws


def _mint_targeted(state: StoryMemory) -> dict:
    """ADR-029 §2: one draw, one judge call, unconditional overwrite. `n` is a uniqueness
    suffix, not a per-character draw count — `ref_retry_count` is per BOOK (spec §4.6), so a
    second tap on a different character still advances `n`. A per-character counter would be a
    second source of truth for something that only needs to be unique.
    """
    retry = state.reference_retry
    character = next(c for c in state.characters if c.char_id == retry.char_id)
    style_fragment = state.style.prompt_fragment or settings.default_style_fragment
    # ADR-035, same two surfaces. `notes` is set AFTER filtering, so `_kept_whole` never sees the
    # tapped attribute — it does not need to: the attribute comes from `reveal._chips`, which is
    # filtered at source, so it can never be a forbidden term.
    #
    # That "filtered at source" claim is load-bearing and it was FALSE until the amendment:
    # `_chips` offered the species axis raw, so a species like "glowing orb" came back through
    # `notes` under "no glow". It holds now only because `_chips` filters species in chip scope.
    # Anything that relaxes that puts a forbidden term into this prompt — see
    # `test_char_bible_targeted_mode_never_appends_the_re_injection_clause` for the second half.
    description = filtered_description(character.description, style_fragment).model_copy(
        update={"notes": retry.attribute}
    )
    prompt = reference_prompt(description, character.name, style_fragment)
    if retry.attribute not in prompt:
        prompt = f"{prompt}\n\nBe sure to include: {retry.attribute}."
    judge_prompt = JUDGE_PROMPT.format(subject=_describe(description, character.name, notes=False))

    image = text_to_image(prompt, negative_extra=REFERENCE_NEGATIVE)
    verdict = judge(judge_prompt, [_data_uri(image)], RefVerdict)
    # PRE-bump on BOTH counters — rc is incremented below, mrc is not touched by this path.
    # +2 = +1(initial mint) +1(this tap). Spec §4.4.
    n = state.cost.ref_retry_count + state.cost.ref_mod_retry_count + 2
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

    # CC-3 accounting, computed BEFORE the loop because §4.4's suffix is derived from it. A
    # post-loop bump would hand mint_reference n=1 on a redraw and upsert over the flagged image.
    # Once per CYCLE, not once per character: char_ref_mod screens the whole roster in one node
    # run, so a book where both c0 and c1 flag spends one redraw, not two (spec §2).
    was_flagged = any(c.ref_moderation_status == "flagged" for c in selected)
    mrc = state.cost.ref_mod_retry_count + (1 if was_flagged else 0)
    n = state.cost.ref_retry_count + mrc + 1

    minted: dict[str, tuple[str, RefVerdict | None]] = {}
    draws_made = 0
    for character in selected:
        path, verdict, draws = mint_reference(
            character.description, character.name, style_fragment, state.story_id,
            character.char_id, n=n,
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
            # A status describes the image that was in `canonical_ref_image` when it was written.
            # This path now overwrites that image on a moderation redraw, so the status has to go
            # with it (`moderation-stack.md` §4b) — `_mint_targeted` has always done the same.
            "ref_moderation_status": None,
        })
        if c.char_id in minted
        else c
        for c in state.characters
    ]
    # Invariant 4: `cost` has no reducer either — copy and bump, never rebuild from zero.
    # CC-3: this node's prelude bound is 6 (2 references x 3 draws), doubled to 12 by one
    # moderation redraw cycle. `image-generator` owns the scene-image half of `image_count`.
    cost = state.cost.model_copy(update={
        "image_count": state.cost.image_count + draws_made,
        "ref_mod_retry_count": mrc,
    })

    log.info("char_bible: minted %s in %d draws, n=%d, ref_mod_retry_count=%d",
             sorted(minted), draws_made, n, mrc)
    return {"characters": characters, "cost": cost}

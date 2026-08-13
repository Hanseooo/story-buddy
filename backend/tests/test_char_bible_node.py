import re
from unittest.mock import MagicMock, patch

import pytest

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Character, CharacterDescription, Cost, Input, RefVerdict, StoryMemory, Style
from app.config import STYLE_PRESETS
from pipeline.char_bible import REFERENCE_NEGATIVE, best_draw, char_bible, mint_reference, reference_prompt

FRAG = "flat cel-shaded cartoon, thick clean black outlines"
DRAWS = [b"draw-1-bytes", b"draw-2-bytes", b"draw-3-bytes"]


def _verdict(matches: bool, attributes: list[str] | None = None) -> RefVerdict:
    """A SELF-CONSISTENT judge: the list and the boolean agree. Post-ADR-034 only the list is
    read, so `matches` alone would no longer decide anything — the tests below say "a failing
    draw" and must keep meaning it. The verdict where the two DISAGREE is the production bug,
    and it is constructed explicitly in its own test rather than reachable from this helper."""
    return RefVerdict(
        differences_observed="the scarf is blue, not red",
        contradictions=[] if matches else ["the scarf is blue, the description says red"],
        matches_description=matches,
        attributes_present=attributes or [],
    )


def _contradicting(attributes: list[str], contradictions: list[str]) -> RefVerdict:
    """A failing verdict whose two lists vary independently — the only way to see which one
    `best_draw` actually ranks on."""
    return RefVerdict(
        differences_observed="the scarf is blue, not red",
        contradictions=contradictions,
        matches_description=False,
        attributes_present=attributes,
    )


def _lettered(contradictions: list[str], attributes: list[str] | None = None) -> RefVerdict:
    """A draw whose only new defect is text on the canvas. `contradictions` varies independently
    so the KEY ORDER is what the tests below observe, not a coincidence of two aligned axes."""
    return RefVerdict(
        differences_observed="a word is lettered across the burrow door",
        contradictions=contradictions,
        matches_description=not contradictions,
        attributes_present=attributes or [],
        text_free=False,
    )


# --- best_draw (pure) ---

def test_best_draw_ranks_on_contradiction_count_first():
    """ADR-034: fewest contradictions wins even when it shows the FEWEST attributes.

    Index 1 contradicts once and shows one attribute; index 0 contradicts three times and shows
    three. Under the pre-ADR-034 key (attributes only) index 0 won — best-of shipped the draw
    that got more things wrong because it also got more things listed.
    """
    verdicts = [
        _contradicting(["a", "b", "c"], ["c1", "c2", "c3"]),
        _contradicting(["a"], ["c1"]),
        _contradicting(["a", "b"], ["c1", "c2"]),
    ]
    assert best_draw(verdicts) == 1


def test_best_draw_prefers_the_text_free_draw_when_contradiction_counts_tie():
    """lettering-suppression §4.2: text_free sits behind contradictions and AHEAD of
    attributes_present. Index 1 letters and shows three attributes; index 0 is clean and shows
    one. attributes_present is documented as noisy (ADR-034), so the clean draw must win."""
    verdicts = [
        _contradicting(["a"], ["c1"]),
        _lettered(["c1"], ["a", "b", "c"]),
    ]
    assert best_draw(verdicts) == 0


def test_best_draw_still_prefers_fewer_contradictions_over_text_free():
    """§6 test 7 — the key order is load-bearing. A draw that contradicts the child's own
    description is worse than one with a sign in it: the first is the wrong character, the second
    is the right character in a marked room."""
    verdicts = [
        _contradicting(["a", "b"], ["c1", "c2"]),   # clean of text, contradicts twice
        _lettered(["c1"], ["a", "b"]),              # letters, contradicts once
    ]
    assert best_draw(verdicts) == 1


def test_best_draw_breaks_equal_contradictions_on_attributes_present_length():
    """Spec §4, demoted to a tiebreak by ADR-034: equal contradiction counts, attribute lengths
    1, 3, 2 → index 1."""
    verdicts = [
        _verdict(False, ["a"]),
        _verdict(False, ["a", "b", "c"]),
        _verdict(False, ["a", "b"]),
    ]
    assert best_draw(verdicts) == 1


def test_best_draw_breaks_ties_toward_the_earliest_draw():
    """Spec §4: ties → earliest draw. Lengths 2, 2, 2 → index 0."""
    verdicts = [_verdict(False, ["a", "b"]) for _ in range(3)]
    assert best_draw(verdicts) == 0


def test_best_draw_returns_zero_when_every_verdict_is_empty():
    """Spec §4 edge case: all attributes_present empty → 0. Deterministic, never arbitrary."""
    verdicts = [_verdict(False), _verdict(False), _verdict(False)]
    assert best_draw(verdicts) == 0


# --- reference_prompt (pure) ---

def test_reference_prompt_contains_every_populated_description_axis():
    description = CharacterDescription(
        species="dog",
        colours=["orange"],
        body_features=["three eyes"],
        clothing=["a red scarf"],
        notes="always smiling",
    )
    prompt = reference_prompt(description, "the orange dog", FRAG)
    for axis in ["dog", "orange", "three eyes", "a red scarf", "always smiling"]:
        assert axis in prompt


def test_reference_prompt_floors_to_the_character_name_on_an_empty_description():
    """Spec §4: CharacterDescription is all-Optional, so a fully empty one is contract-legal
    (a resumed pre-story-analyzer checkpoint could carry one). The prompt floors to the name."""
    prompt = reference_prompt(CharacterDescription(), "the orange dog", FRAG)
    assert "The character is the orange dog," in prompt


# --- visually-thin descriptions (2026-08-11) ---

def test_reference_prompt_enriches_a_description_with_no_visual_axis():
    """`analyze`'s EXTRACTION_PROMPT says "leave them empty rather than inventing details", so
    colours/body_features/clothing are routinely all empty — prod job 4cb31620 (2026-08-11) drew
    c0 from "the narrator, girl, the protagonist". Every page of the book inherits that
    reference, so the generator needs *something* to draw beyond a role noun.

    Triggered on the visual axes, NOT on len(populated): c0 had two populated axes (species and
    notes) and still specified nothing drawable. `species` and `notes` are identity, not
    appearance.
    """
    prompt = reference_prompt(CharacterDescription(species="girl", notes="the protagonist"), "the narrator", FRAG)

    assert "the narrator, girl, the protagonist" in prompt
    assert "friendly children's picture-book character" in prompt


@pytest.mark.parametrize("description", [
    CharacterDescription(species="dog", colours=["orange"]),
    CharacterDescription(species="dog", body_features=["three eyes"]),
    CharacterDescription(species="dog", clothing=["a red scarf"]),
])
def test_reference_prompt_leaves_a_description_with_any_visual_axis_alone(description):
    """One drawable attribute is enough. Enriching on top of it would dilute the story's own
    detail, which is the thing the reference exists to preserve."""
    assert "friendly children's picture-book character" not in reference_prompt(description, "the dog", FRAG)


def test_enrichment_reaches_the_draw_prompt_but_never_the_judge_prompt():
    """THE load-bearing property of this whole approach. `_describe` is deliberately shared so
    the two prompts cannot drift into describing different characters; this is the one sanctioned
    exception, and it is one-directional.

    If the enrichment reached the judge it would become a *stated* attribute, and the judge
    (which checks contradiction of stated attributes) would start failing draws over invented
    detail — reintroducing the exact bug the 2026-08-11 rewording fixed, from the other end.
    ADR-028 must keep measuring the generator against the STORY, never against our filler.
    """
    thin = CharacterDescription(species="girl", notes="the protagonist")
    _, t2i_mock, judge_mock, _ = _mint([_verdict(True)], description=thin, name="the narrator")

    draw_prompt = t2i_mock.call_args.args[0]
    judge_prompt = judge_mock.call_args.args[0]

    assert "friendly children's picture-book character" in draw_prompt
    assert "friendly children's picture-book character" not in judge_prompt
    # `notes` is the OTHER one-directional divergence (ADR-034 follow-on), so the judge sees the
    # visual axes only — here that floors the subject to the bare name.
    assert "the narrator, girl, the protagonist" in draw_prompt
    assert "the narrator, girl" in judge_prompt
    assert "the protagonist" not in judge_prompt


# --- non-humanoid subjects (2026-08-11) ---

def test_reference_prompt_does_not_order_a_humanoid_pose():
    """"standing, facing forward" is a HUMAN pose instruction, and this prompt sent it for every
    character including the ones with no legs. Prod job 4cb31620 (2026-08-11) drew c1 — "the
    star" — as a smiling mascot with arms and legs, and the judge correctly failed it.

    The pose ask is the half of that failure we authored: a text-to-image model told to draw a
    star "standing" has to invent legs to comply. "shown in full" asks for the same framing (the
    thing the reference actually needs) without asserting an anatomy.
    """
    assert "standing" not in reference_prompt(CharacterDescription(species="star"), "the star", FRAG)


def test_reference_prompt_guards_against_anthropomorphising_a_non_human_subject():
    """The direct counter to c1, and it deliberately does NOT branch on species.

    Classifying "star", "cloud", "jeepney", "kalabaw" as non-humanoid needs a word list that is
    wrong the first time a child writes something not on it — and unlike the thin-description
    filler there is no cheap structural signal to key on. An unconditional clause is a no-op for
    a girl or a dog, which is what makes the branchless version the correct lazy one.
    """
    for species in ["star", "girl", "dog"]:
        prompt = reference_prompt(CharacterDescription(species=species), f"the {species}", FRAG)
        assert "not a person" in prompt


def test_notes_reaches_the_draw_prompt_but_never_the_judge_prompt():
    """ADR-034 follow-on, measured 2026-08-11: `notes` is free prose, not a visual attribute, and
    the gate now re-rolls on whatever the judge lists as contradicted.

    Re-judging prod job b9506307's `ref-c1-1.png` under v3 returned
    `"secondary character - The image does not provide cues as to this character's role."` as a
    contradiction. No redraw can ever clear that, so the character would burn all 3 draws on every
    job, forever. The generator still gets `notes` — "secondary character" is useful framing for a
    drawing — but the judge measures VISUAL axes only, the same line `reveal._chips` already draws
    ("free prose, not an attribute, and not a thing a child can tap").
    """
    described = CharacterDescription(species="star", body_features=["tiny"], notes="secondary character")
    _, t2i_mock, judge_mock, _ = _mint([_verdict(True)], description=described, name="the star")

    assert "secondary character" in t2i_mock.call_args.args[0]
    assert "secondary character" not in judge_mock.call_args.args[0]
    # The visual axes still reach the judge — this narrows the subject, it does not gut it.
    assert "the star, star, tiny" in judge_mock.call_args.args[0]


# --- lettering and scenery (2026-08-13) ---

def test_the_positive_prompt_never_utters_a_word_the_negative_prompt_suppresses():
    """The general form of the "Reference;" bug, and the reason it is a test rather than a note:
    it recurred DURING the fix. A draft of the clause above read "the whole of it inside the
    frame", and the very next draw of a rabbit came back sitting inside a drawn border — with
    "frame" already sitting in REFERENCE_NEGATIVE, two lines away.

    Qwen-Image renders what the positive prompt says. A term in both channels is not belt and
    braces, it is a contradiction the positive side wins, so the negative list doubles as a list of
    words this prompt may not use. Word-boundary matched, or "ground" would fire on "background".
    """
    prompt = reference_prompt(CharacterDescription(species="dog", colours=["orange"]), "the dog", FRAG)
    said = [
        term for term in REFERENCE_NEGATIVE.split(", ")
        if re.search(rf"\b{re.escape(term)}\b", prompt, re.IGNORECASE)
    ]
    assert said == []


def test_reference_prompt_never_names_the_artifact_it_is_asking_for():
    """Measured 2026-08-13: the draw for "the monster - monster; purple; tiny, lost" came back
    with the word **"Reference;"** lettered across the top in the style's own font.

    Nothing hallucinated it. `REFERENCE_PROMPT` opened "A single character reference of one
    character", and Qwen-Image renders text *by design* — hand it a noun that names a kind of
    document and it draws the document, title and all. `providers.NEGATIVE_PROMPT` already lists
    "text, letters, words, labels, captions" and did not stop it, because a negative prompt
    subtracts a tendency and cannot outvote a word sitting in the positive prompt.

    "character reference" also carries the model-sheet prior: in training data that phrase means
    a sheet with a name plate, a turnaround and colour swatches. We were asking for the artifact
    whose defining feature is the label we then asked not to have.

    So the prompt describes the PICTURE and never names the document. Asserted case-insensitively
    on the whole prompt, subject included — a child's character can be called anything, but our
    own framing must never contribute the word.
    """
    prompt = reference_prompt(CharacterDescription(species="monster", colours=["purple"]), "the monster", FRAG)
    assert "reference" not in prompt.lower()


def test_reference_prompt_states_its_background_positively_instead_of_negating():
    """The same 2026-08-13 draws put a wall/floor horizon and a cast shadow behind the monster and
    behind Bolt, under a prompt whose tail read "No other characters, no scenery, no text, no
    border". `providers.py`'s NEGATIVE_PROMPT comment already recorded this lesson for the style
    presets: a `no <term>` clause in a positive prompt competes with the thing the model is best
    at, and loses. It was still being written here.

    A room half-drawn behind a character reference is how a bed ends up behind a girl whose story
    happens at bedtime — and every scene inherits this image, so it is a per-book defect, not a
    per-page one. The prohibitions move to REFERENCE_NEGATIVE, which rides the channel that works.
    """
    prompt = reference_prompt(CharacterDescription(species="dog"), "the dog", FRAG)
    assert "no scenery" not in prompt
    assert "No other characters" not in prompt
    # The clause that ISN'T a background prohibition stays — it guards anatomy, not the backdrop,
    # and there is no negative-prompt phrasing for "no human body *unless* the story said so".
    assert "not a person" in prompt


def test_reference_prompt_asks_for_a_full_shot_without_asserting_an_anatomy():
    """Two framing phrasings were measured being ignored for human subjects on 2026-08-13 —
    "shown in full" cropped a girl at the chest, "drawn in full with nothing cropped" cropped her
    at the waist — while the monster and the robot came back whole both times. `clothing` is one of
    the four judged axes and every scene inherits this image, so a waist-up reference silently
    drops the story's own detail from the whole book.

    The escalation is a framing term plus the matching REFERENCE_NEGATIVE entries, NOT "full body"
    or "head to toe": the 2026-08-11 lesson that killed "standing" applies to any phrasing that
    hands a star a pair of legs to comply with.
    """
    prompt = reference_prompt(CharacterDescription(species="star"), "the star", FRAG)
    assert "full shot" in prompt
    for anatomical in ["full body", "full-body", "head to toe", "standing"]:
        assert anatomical not in prompt.lower()
    assert "cropped limbs" in REFERENCE_NEGATIVE


def test_the_reference_draw_suppresses_scenery_through_the_negative_prompt():
    """The positive prompt says what the picture IS; REFERENCE_NEGATIVE says what a reference must
    never accrete. It is passed per call rather than added to `providers.NEGATIVE_PROMPT` because
    `text_to_image` is also `generate_scene`'s no-reference fallback (`generate_scene.py:57`), and
    a scene needs the scenery this suppresses.
    """
    _, t2i_mock, _, _ = _mint([_verdict(True)])
    assert t2i_mock.call_args.kwargs["negative_extra"] == REFERENCE_NEGATIVE


def test_the_non_humanoid_guard_never_reaches_the_judge_prompt():
    """Same one-directional rule the thin-description filler follows, for the same reason.

    Structural today — the clause lives in REFERENCE_PROMPT and the judge is built from
    JUDGE_PROMPT — but asserted anyway, because "obviously separate" is exactly what the shared
    `_describe` helper was before it started leaking.
    """
    _, t2i_mock, judge_mock, _ = _mint(
        [_verdict(True)], description=CharacterDescription(species="star"), name="the star"
    )
    assert "not a person" in t2i_mock.call_args.args[0]
    assert "not a person" not in judge_mock.call_args.args[0]


def test_reference_prompt_always_contains_the_style_fragment():
    """ADR-022: style rides the reference, so the fragment is never optional in this prompt."""
    assert FRAG in reference_prompt(CharacterDescription(), "the orange dog", FRAG)
    assert FRAG in reference_prompt(CharacterDescription(species="dog"), "the orange dog", FRAG)


# --- mint_reference (effect boundary) ---

def _mint(judge_side_effect, images=None, description=None, name="the orange dog", style_fragment=FRAG):
    """Runs mint_reference with all three effects patched.

    Returns (result, text_to_image_mock, judge_mock, fake_supabase).
    """
    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", side_effect=list(images or DRAWS)) as t2i, \
         patch("pipeline.char_bible.judge", side_effect=judge_side_effect) as judge_mock, \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        result = mint_reference(
            description or CharacterDescription(species="dog", colours=["orange"]),
            name,
            style_fragment,
            "story-1",
            "c0",
        )
    return result, t2i, judge_mock, fake_supabase


def _uploaded_bytes(fake_supabase) -> bytes:
    return fake_supabase.storage.from_.return_value.upload.call_args.args[1]


def _uploaded_path(fake_supabase) -> str:
    return fake_supabase.storage.from_.return_value.upload.call_args.args[0]


def test_mint_reference_accepts_a_passing_first_draw():
    """Spec §6: one text_to_image call, one judge call, verdict returned unchanged."""
    passing = _verdict(True, ["dog", "orange"])
    (path, verdict, draws), t2i, judge_mock, supabase = _mint([passing])

    assert t2i.call_count == 1
    assert judge_mock.call_count == 1
    assert verdict is passing
    assert draws == 1


def test_mint_reference_rejects_a_lettered_draw_and_redraws():
    """§6 test 4 / §4.2. The reference is the higher-value catch: char_bible mints ONE canonical
    image per character and every page inherits it, so a lettered reference letters the book.
    No contradictions at all here — text alone must be enough to burn a draw."""
    (_, verdict, draws), t2i, _, supabase = _mint([_lettered([]), _verdict(True, ["dog"])])

    assert t2i.call_count == 2
    assert draws == 2
    assert verdict.text_free is True
    assert _uploaded_bytes(supabase) == b"draw-2-bytes"


def test_mint_reference_accepts_a_clean_text_free_first_draw_on_the_spot():
    """§6 test 5: the unchanged path, asserted so the new gate cannot silently swallow it.
    `_verdict` defaults text_free to True, which is the same default a v3 checkpoint carries."""
    passing = _verdict(True, ["dog"])
    (path, verdict, draws), t2i, judge_mock, supabase = _mint([passing])

    assert (t2i.call_count, judge_mock.call_count, draws) == (1, 1, 1)
    assert verdict is passing
    assert draws == 1
    assert _uploaded_bytes(supabase) == b"draw-1-bytes"
    assert path == "story-1/ref-c0-1.png"


def test_mint_reference_rejects_a_draw_whose_verdict_declares_a_contradiction():
    """ADR-034: acceptance is derived from `contradictions`, never asked for as a boolean.

    The verbatim shape from prod job b9506307 (2026-08-11), character c1 "the star": the judge
    wrote "This is a contradiction" and set the boolean to TRUE. ADR-004's ordering worked — the
    reason WAS emitted first — and the gate accepted it anyway, because ordering makes the model
    reason before it scores, not score in line with its reasoning. Every scene then carried a
    description its own reference contradicts (#23's star branch).
    """
    inconsistent = RefVerdict(
        differences_observed=(
            "The description states the star is 'tiny', but the image depicts the star as a "
            "significant size relative to the image frame. This is a contradiction."
        ),
        contradictions=["the image draws the star large; the description states it is tiny"],
        matches_description=True,
        attributes_present=["star", "glowing"],
    )
    (_, verdict, draws), t2i, _, supabase = _mint([inconsistent, _verdict(True, ["star"])])

    assert t2i.call_count == 2          # the boolean did NOT end the loop
    assert draws == 2
    assert verdict.contradictions == []
    assert _uploaded_bytes(supabase) == b"draw-2-bytes"


def test_mint_reference_rerolls_until_a_draw_passes():
    """Spec §6: fail → fail → pass yields 3 draws, and the THIRD image's bytes are uploaded."""
    (_, verdict, draws), t2i, _, supabase = _mint(
        [_verdict(False), _verdict(False), _verdict(True, ["dog"])]
    )

    assert t2i.call_count == 3
    assert draws == 3
    assert verdict.matches_description is True
    assert _uploaded_bytes(supabase) == b"draw-3-bytes"


def test_mint_reference_best_of_uploads_the_draw_with_most_attributes_present():
    """Spec §6 exhaustion best-of: attributes_present lengths 1, 3, 2 → the SECOND draw wins.
    Guards the ranking key."""
    (_, verdict, draws), _, _, supabase = _mint([
        _verdict(False, ["a"]),
        _verdict(False, ["a", "b", "c"]),
        _verdict(False, ["a", "b"]),
    ])

    assert _uploaded_bytes(supabase) == b"draw-2-bytes"
    assert draws == 3
    # A FAILING verdict is persisted — loud, never a placeholder, never a failed job (ADR-010).
    assert verdict.matches_description is False


def test_mint_reference_best_of_ties_go_to_the_earliest_draw():
    """Spec §6: lengths 2, 2, 2 → the FIRST draw's bytes are uploaded."""
    (_, _, _), _, _, supabase = _mint([
        _verdict(False, ["a", "b"]),
        _verdict(False, ["c", "d"]),
        _verdict(False, ["e", "f"]),
    ])

    assert _uploaded_bytes(supabase) == b"draw-1-bytes"


def test_mint_reference_never_draws_more_than_three_times():
    """Spec §6 cap (ADR-028): never more than 3 text_to_image calls, however many verdicts fail."""
    (_, _, draws), t2i, _, _ = _mint([_verdict(False) for _ in range(3)])

    assert t2i.call_count == 3
    assert draws == 3


def test_mint_reference_degrades_to_a_null_verdict_when_the_judge_fails():
    """Spec §4 two-policies table: the artifact exists and is paid for, only the CHECK failed.
    Accept the draw, return None, and STOP re-rolling — exactly one text_to_image call."""
    (path, verdict, draws), t2i, _, supabase = _mint(RuntimeError("openrouter 500"))

    assert verdict is None
    assert draws == 1
    assert t2i.call_count == 1
    assert path == "story-1/ref-c0-1.png"
    assert _uploaded_bytes(supabase) == b"draw-1-bytes"


def test_mint_reference_propagates_a_text_to_image_failure():
    """Spec §6 (guards ADR-025 Decision 1): no artifact exists, so there is nothing to ship.
    The exception propagates and the job fails. No node-level retry."""
    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", side_effect=RuntimeError("fal 503")), \
         patch("pipeline.char_bible.judge") as judge_mock, \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        with pytest.raises(RuntimeError, match="fal 503"):
            mint_reference(CharacterDescription(species="dog"), "the dog", FRAG, "story-1", "c0")

    judge_mock.assert_not_called()
    fake_supabase.storage.from_.return_value.upload.assert_not_called()


def test_mint_reference_uploads_to_the_exact_reference_path():
    """Spec §6 upload target: `{story_id}/ref-{char_id}.png`, in the storybook-images bucket."""
    (path, _, _), _, _, supabase = _mint([_verdict(True)])

    assert path == "story-1/ref-c0-1.png"
    assert _uploaded_path(supabase) == "story-1/ref-c0-1.png"
    supabase.storage.from_.assert_called_with("storybook-images")


def test_mint_reference_shows_the_judge_a_data_uri_never_a_url():
    """Spec §6 (guards invariant 5 and the CC-4 posture): the judge sees base64, never a signed
    URL, and what is PERSISTED is the path, never the data URI."""
    (path, _, _), _, judge_mock, _ = _mint([_verdict(True)])

    image_urls = judge_mock.call_args.args[1]
    assert len(image_urls) == 1
    assert image_urls[0].startswith("data:image/png;base64,")
    assert not image_urls[0].startswith("http")
    assert not path.startswith("data:")
    assert not path.startswith("http")


def test_judge_prompt_scopes_the_question_to_contradiction_not_to_any_difference():
    """Regression, prod job 4cb31620 (2026-08-11): c0's description rendered to
    "the narrator, girl, the protagonist" and all 3 draws returned matches_description=False.
    The judge's own reasoning was the proof — "the description is incredibly brief... the image
    offers a lot of details *not* present in the description" — and it went on to list hair and
    clothing. Neither contradicts "a girl who is the protagonist"; a text-to-image model cannot
    draw a girl with no hair and no clothes, so unlisted details are unavoidable, and under the
    old "describe every difference" wording a thin description could never pass at ANY draw
    count. Spec §4 predicted the opposite failure (near-vacuously TRUE, loop collapses to 1
    draw); production falsified it and charged 3 draws instead.

    ADR-028 targets *off-spec on a stated feature*, so the question must be contradiction of a
    stated attribute, never mere absence from the description.
    """
    _, _, judge_mock, _ = _mint([_verdict(True)])
    prompt = judge_mock.call_args.args[0]

    assert "CONTRADICTS" in prompt
    assert "are NOT differences" in prompt
    # ADR-004 reason-then-score survives the rewording: reason is still asked for first.
    assert prompt.index("First describe") < prompt.index("Then say whether")
    # The description still reaches the judge — _describe and the prompt must not drift apart.
    assert "the orange dog, dog, orange" in prompt


def test_the_judge_is_asked_about_text_last_and_the_version_is_bumped():
    """§6 test 8. ADR-004: `providers._assert_field_order` rejects a provider that answers out of
    schema order, so the prompt must ask in schema order — `RefVerdict.text_free` is declared
    LAST, so the question comes after the attributes question.

    Naming signs and doors here is safe and is the point: this prompt goes to the VLM JUDGE,
    never to the image model. The rule that naming summons applies to the generator's prompt;
    the judge has to be told what to look at, and the door is exactly where it landed.

    The version bump is asserted in the same test because it is the same edit: an unversioned
    reword silently invalidates every verdict before it, which already cost one series (v3).
    """
    from pipeline.char_bible import JUDGE_PROMPT, JUDGE_PROMPT_VERSION

    assert JUDGE_PROMPT_VERSION == 4

    prompt = JUDGE_PROMPT.format(subject="the orange dog, dog, orange")
    assert "free of any text" in prompt
    assert prompt.index("attributes are actually present") < prompt.index("free of any text")


def test_mint_reference_reports_a_draw_count_equal_to_the_provider_calls():
    """Spec §6: the count the helper reports equals the number of text_to_image calls.
    Invariant 4 rides on this — the node cannot compute it, the loop is in here."""
    for side_effect, expected in [
        ([_verdict(True)], 1),
        ([_verdict(False), _verdict(True)], 2),
        ([_verdict(False), _verdict(False), _verdict(False)], 3),
    ]:
        (_, _, draws), t2i, _, _ = _mint(side_effect)
        assert draws == t2i.call_count == expected


def test_mint_reference_passes_no_seed_to_the_image_model():
    """Spec §4 "No seed, by necessity": a fixed seed makes all three draws identical and the
    re-roll a no-op. CC-7 is unsatisfied here as a consequence of the mechanism (§5)."""
    _, t2i, _, _ = _mint([_verdict(False), _verdict(False), _verdict(False)])

    for call in t2i.call_args_list:
        assert call.kwargs.get("seed") is None
        assert len(call.args) == 1   # prompt only — no positional seed


# --- char_bible node (mint_reference mocked) ---

def _char(char_id: str, name: str, ref: str | None = None) -> Character:
    return Character(
        char_id=char_id,
        name=name,
        description=CharacterDescription(species="dog"),
        canonical_ref_image=ref,
    )


def _state(characters: list[Character], style: Style | None = None, cost: Cost | None = None) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="story-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="The dog ran.", redacted_text="The dog ran."),
        characters=characters,
        style=style or Style(),
        cost=cost or Cost(),
    )


def _minted(path: str = "story-1/ref.png", draws: int = 1):
    """A mint_reference stand-in: same 3-tuple shape, one accepted draw."""
    return (path, _verdict(True, ["dog"]), draws)


def test_char_bible_resets_ref_moderation_status_on_a_re_mint():
    """Spec §4.3 change 1. A moderation redraw arrives with the character still reading
    "flagged" (char_ref_mod cleared the image, not the status). Without this reset the router
    either raises on a brand-new image or spins on the same flag forever.

    It is also the precondition for char_ref_mod's skip-if-passed guard:
    `moderation-stack.md:144-148` — a status describes the image that was in
    `canonical_ref_image` when it was written, so overwriting the image without clearing the
    status would route an UNMODERATED image straight to a child.
    """
    flagged = _char("c0", "the dog")
    flagged = flagged.model_copy(update={"ref_moderation_status": "flagged"})
    state = _state([flagged])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    assert result["characters"][0].ref_moderation_status is None
    assert result["characters"][0].canonical_ref_image == "story-1/ref.png"



def test_char_bible_references_at_most_two_characters():
    """Invariant 1 (ADR-004: max 2 canonical refs, v1): a 3-character roster calls the helper
    exactly twice, for c0 and c1."""
    state = _state([_char("c0", "the dog"), _char("c1", "the cat"), _char("c2", "the bird")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(state)

    assert mint.call_count == 2
    assert [call.args[4] for call in mint.call_args_list] == ["c0", "c1"]


def test_char_bible_returns_the_complete_character_list():
    """Invariant 2 — THE REDUCER TRAP. `characters` has no reducer, so a partial return
    REPLACES the list. Returning only the two modified entries deletes c2 silently."""
    c2 = _char("c2", "the bird")
    state = _state([_char("c0", "the dog"), _char("c1", "the cat"), c2])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    assert len(result["characters"]) == 3
    assert result["characters"][2] == c2          # byte-identical to input
    assert result["characters"][2].canonical_ref_image is None
    assert [c.char_id for c in result["characters"]] == ["c0", "c1", "c2"]


def test_char_bible_writes_the_path_and_verdict_onto_the_referenced_characters():
    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted("story-1/ref-c0-1.png")):
        result = char_bible(state)

    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0-1.png"
    assert result["characters"][0].ref_verdict.matches_description is True


def test_char_bible_stamps_the_judge_prompt_version_next_to_the_verdict():
    """`matches_description` is both a product gate and the capstone's ADR-028 hit rate, and the
    prompt that produces it is under active development — it changed on 2026-08-11 (every
    difference → contradiction only) and that silently invalidated every verdict measured before
    it. Spec §7 warned this could happen; nothing recorded which prompt a verdict came from, so
    the only honest response was to reset the series.

    Stamping the version makes the next change segment the series instead of resetting it. It
    lives on `Character`, NOT on `RefVerdict`: `RefVerdict` is handed to `providers.judge` as
    `response_format`, so a field there becomes a required model output under strict json_schema
    and the judge would be asked to invent its own prompt version.
    """
    from pipeline.char_bible import JUDGE_PROMPT_VERSION

    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    assert result["characters"][0].ref_verdict_prompt_version == JUDGE_PROMPT_VERSION
    # A bare int is only comparable if it moves when the prompt moves.
    assert JUDGE_PROMPT_VERSION >= 2, "bump this when JUDGE_PROMPT changes meaning"


def test_char_bible_persists_a_failing_verdict_rather_than_failing_the_job():
    """ADR-010/ADR-028: a failed acceptance loop is loud, never a failed job, never a placeholder."""
    failing = ("story-1/ref-c0-1.png", _verdict(False, ["dog"]), 3)
    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=failing):
        result = char_bible(state)

    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0-1.png"
    assert result["characters"][0].ref_verdict.matches_description is False


def test_char_bible_accepts_a_null_verdict_from_a_degraded_judge():
    """Spec §4: ref_verdict=None is honest and distinguishable from a FAILED verdict."""
    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=("story-1/ref-c0-1.png", None, 1)):
        result = char_bible(state)

    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0-1.png"
    assert result["characters"][0].ref_verdict is None


def test_char_bible_bumps_image_count_by_the_draws_made_and_preserves_the_rest_of_cost():
    """Invariant 4: cost has no reducer, so it is COPIED and bumped — never rebuilt from zero,
    which would erase any field a future node has written."""
    state = _state(
        [_char("c0", "the dog"), _char("c1", "the cat")],
        cost=Cost(image_count=4, regen_count=2, usd_estimate=1.25),
    )

    with patch("pipeline.char_bible.mint_reference", side_effect=[_minted(draws=3), _minted(draws=2)]):
        result = char_bible(state)

    assert result["cost"].image_count == 4 + 3 + 2
    assert result["cost"].regen_count == 2
    assert result["cost"].usd_estimate == 1.25


def test_char_bible_on_an_empty_roster_returns_without_calling_the_helper():
    """Spec §4 edge case: zero characters → no refs, no cost change, and the node does NOT raise.
    Scenes generate unreferenced — a book with drifting art beats no book (ADR-010)."""
    with patch("pipeline.char_bible.mint_reference") as mint:
        result = char_bible(_state([]))

    mint.assert_not_called()
    assert result == {}


def test_char_bible_on_a_single_character_mints_exactly_one_reference():
    """Spec §4: the cap is a ceiling, not a quota."""
    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        result = char_bible(_state([_char("c0", "the dog")]))

    assert mint.call_count == 1
    assert len(result["characters"]) == 1


def test_char_bible_skips_a_character_that_already_has_a_reference():
    """Invariant 6 / CC-10: idempotent re-entry — zero draws, zero cost for an existing ref."""
    state = _state([_char("c0", "the dog", ref="story-1/ref-c0-1.png"), _char("c1", "the cat")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted(draws=1)) as mint:
        result = char_bible(state)

    assert mint.call_count == 1
    assert mint.call_args.args[4] == "c1"
    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0-1.png"


def test_char_bible_makes_zero_helper_calls_when_both_references_already_exist():
    """Invariant 6: full re-entry after success costs nothing."""
    state = _state([
        _char("c0", "the dog", ref="story-1/ref-c0-1.png"),
        _char("c1", "the cat", ref="story-1/ref-c1-1.png"),
    ])

    with patch("pipeline.char_bible.mint_reference") as mint:
        result = char_bible(state)

    mint.assert_not_called()
    assert result == {}


def test_char_bible_caps_before_it_filters():
    """Spec §4's trap. A 3-character roster where c0 is already referenced calls the helper
    ONCE, for c1 only — never for c2. Filtering before capping slides the 2-slot window onto c2
    and mints a THIRD canonical reference against ADR-004."""
    state = _state([
        _char("c0", "the dog", ref="story-1/ref-c0-1.png"),
        _char("c1", "the cat"),
        _char("c2", "the bird"),
    ])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        result = char_bible(state)

    assert mint.call_count == 1
    assert mint.call_args.args[4] == "c1"
    assert result["characters"][2].canonical_ref_image is None


def test_char_bible_leaves_ref_moderation_status_untouched():
    """Contract slice: ref_moderation_status is owned by the Phase-2 char-ref moderation node.
    CC-1 is NOT closed by this node completing (spec §5)."""
    state = _state([_char("c0", "the dog"), _char("c1", "the cat"), _char("c2", "the bird")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    for character in result["characters"]:
        assert character.ref_moderation_status is None


def test_char_bible_partial_returns_exactly_characters_and_cost_without_mutating_state():
    """ADR-024: partial-return, never mutate."""
    state = _state([_char("c0", "the dog")])
    before = state.model_dump()

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    assert set(result) == {"characters", "cost"}
    assert state.model_dump() == before


def test_char_bible_falls_back_to_the_default_style_fragment():
    """Spec §4: nothing writes `style` today, so the fallback is the NORMAL Phase-1 path."""
    from app.config import settings

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(_state([_char("c0", "the dog")], style=Style(prompt_fragment=None)))

    assert mint.call_args.args[2] == settings.default_style_fragment


def test_char_bible_prefers_the_state_style_fragment_when_set():
    """ADR-022: the style is frozen before the reference is drawn, and state wins over the default."""
    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(_state([_char("c0", "the dog")], style=Style(prompt_fragment="flat gouache storybook")))

    assert mint.call_args.args[2] == "flat gouache storybook"


# --- targeted mode (ADR-029, spec §4.5-4.7) ---

def _targeted_state(char_id: str = "c0", attribute: str = "orange sock", ref_retry_count: int = 0,
                    style: Style | None = None) -> StoryMemory:
    from contracts.story_memory import ReferenceRetry

    c0 = _char("c0", "the dog", ref="story-1/ref-c0-1.png")
    c0.ref_verdict = _verdict(True, ["dog"])
    c0.ref_moderation_status = "passed"
    return _state(
        [c0, _char("c1", "the cat", ref="story-1/ref-c1-1.png")],
        style=style,
        cost=Cost(image_count=2, ref_retry_count=ref_retry_count),
    ).model_copy(update={"reference_retry": ReferenceRetry(char_id=char_id, attribute=attribute)})


def test_char_bible_targeted_mode_makes_exactly_one_draw_and_one_judge_call():
    state = _targeted_state()
    with patch("pipeline.char_bible.text_to_image", return_value=b"redraw-bytes") as t2i, \
         patch("pipeline.char_bible.judge", return_value=_verdict(True, ["dog"])) as judge_mock, \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        result = char_bible(state)

    assert t2i.call_count == 1
    assert judge_mock.call_count == 1
    assert result["characters"][0].char_id == "c0"


def test_char_bible_targeted_mode_restates_the_tapped_attribute_in_the_prompt():
    state = _targeted_state(attribute="orange sock")
    with patch("pipeline.char_bible.text_to_image", return_value=b"x") as t2i, \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        char_bible(state)

    assert "orange sock" in t2i.call_args.args[0]


def test_char_bible_targeted_mode_suppresses_scenery_like_the_first_draw():
    """A targeted redraw replaces the canonical reference outright, so a room drawn behind THIS
    draw reaches every page exactly the same way. Two call sites, one policy."""
    state = _targeted_state()
    with patch("pipeline.char_bible.text_to_image", return_value=b"x") as t2i, \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        char_bible(state)

    assert t2i.call_args.kwargs["negative_extra"] == REFERENCE_NEGATIVE


def test_char_bible_targeted_mode_never_appends_the_re_injection_clause():
    """`_mint_targeted`'s `if retry.attribute not in prompt` branch is UNREACHABLE, and has been
    since the commit that introduced it: the line above writes the attribute into `notes`, and
    `_describe(notes=True)` always renders `notes`, so the attribute is a substring of the prompt
    by construction.

    Pinned rather than deleted because the branch is a trap. It is dead only while `notes` and
    `retry.attribute` are both unfiltered — anything that starts filtering either one reanimates
    it, and it would then re-append the exact term the filter had just removed, rebuilding the
    ADR-035 defect on the retry path. If this test ever fails, delete the branch; do not repair it.
    """
    for attribute in ("orange sock", "glowing"):
        state = _targeted_state(attribute=attribute, style=Style(prompt_fragment=STYLE_PRESETS["comic"]))
        with patch("pipeline.char_bible.text_to_image", return_value=b"x") as t2i, \
             patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
             patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
            char_bible(state)

        prompt = t2i.call_args.args[0]
        assert attribute in prompt
        assert "Be sure to include" not in prompt


def test_char_bible_still_describes_a_species_the_style_forbids():
    """The counterpart to the reveal test: filtering the species is CHIP SCOPE ONLY. ADR-035
    Decision 2 stands where it was reasoned about — `analyze` makes species required so the judge
    always has something to check, and stripping it here would make acceptance vacuous."""
    orb = Character(
        char_id="c0", name="the orb",
        description=CharacterDescription(species="glowing orb", colours=["blue"]),
    )
    comic = STYLE_PRESETS["comic"]
    with patch("pipeline.char_bible.text_to_image", return_value=b"x") as t2i, \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)) as judge_mock, \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        char_bible(_state([orb], style=Style(prompt_fragment=comic)))

    assert "glowing orb" in t2i.call_args.args[0]
    assert "glowing orb" in judge_mock.call_args.args[0]


def test_char_bible_targeted_mode_only_mutates_the_flagged_character():
    state = _targeted_state()
    c1_before = next(c for c in state.characters if c.char_id == "c1")
    with patch("pipeline.char_bible.text_to_image", return_value=b"x"), \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        result = char_bible(state)

    c1_after = next(c for c in result["characters"] if c.char_id == "c1")
    assert c1_after == c1_before


def test_char_bible_targeted_mode_bumps_image_count_and_ref_retry_count_and_clears_retry():
    state = _targeted_state(ref_retry_count=1)
    with patch("pipeline.char_bible.text_to_image", return_value=b"x"), \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        result = char_bible(state)

    assert result["cost"].image_count == 3
    assert result["cost"].ref_retry_count == 2
    assert result["reference_retry"] is None


def test_char_bible_targeted_mode_overwrites_unconditionally():
    """ADR-029 §2: best-of over old-versus-new would risk showing the child the same picture
    back, the worst answer to "try again". The overwrite never compares to the prior verdict."""
    state = _targeted_state()
    with patch("pipeline.char_bible.text_to_image", return_value=b"x"), \
         patch("pipeline.char_bible.judge", return_value=_verdict(False, ["dog"])), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        result = char_bible(state)

    c0 = next(c for c in result["characters"] if c.char_id == "c0")
    assert c0.ref_verdict.matches_description is False   # overwritten even though it "got worse"


def test_char_bible_targeted_mode_uploads_to_a_new_path_and_clears_moderation_status():
    """Invariant 6 (spec §4.6-4.7): first tap (ref_retry_count=0) must write ref-c0-2.png, not
    ref-c0-1.png (the initial mint's path). Uses the realistic first-tap state so the Storage-path
    collision the spec warns against is directly covered."""
    state = _targeted_state()   # ref_retry_count=0: the first tap
    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", return_value=b"x"), \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        result = char_bible(state)

    c0 = next(c for c in result["characters"] if c.char_id == "c0")
    assert c0.canonical_ref_image == "story-1/ref-c0-2.png"
    assert c0.ref_moderation_status is None
    assert _uploaded_path(fake_supabase) == "story-1/ref-c0-2.png"


def test_char_bible_targeted_mode_also_stamps_the_judge_prompt_version():
    """The targeted redraw judges with the same JUDGE_PROMPT, so its verdict is part of the same
    series and must carry the same stamp — otherwise the ADR-029 retries are the unlabelled
    subset that makes the ADR-028 series unsegmentable again."""
    from pipeline.char_bible import JUDGE_PROMPT_VERSION

    state = _targeted_state()
    with patch("pipeline.char_bible.text_to_image", return_value=b"x"), \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        result = char_bible(state)

    c0 = next(c for c in result["characters"] if c.char_id == "c0")
    assert c0.ref_verdict_prompt_version == JUDGE_PROMPT_VERSION


def test_char_bible_ignores_invariant_six_skip_when_reference_retry_targets_an_existing_ref():
    """The targeted overwrite applies even though c0 already has canonical_ref_image set —
    invariant 6's skip is for the first-pass path only (spec §3)."""
    state = _targeted_state()
    with patch("pipeline.char_bible.text_to_image", return_value=b"x") as t2i, \
         patch("pipeline.char_bible.judge", return_value=_verdict(True)), \
         patch("pipeline.char_bible.get_supabase_client", return_value=MagicMock()):
        char_bible(state)

    assert t2i.call_count == 1


# --- ADR-035: the style fragment's prohibitions filter the description ---

COMIC = STYLE_PRESETS["comic"]   # "...no gradients, no glow"


def test_a_style_forbidden_attribute_reaches_neither_the_draw_prompt_nor_the_judge_prompt():
    """ADR-035 surfaces 1 and 2, from prod job b9506307. `reference_prompt` used to ask for
    `star; glowing; tiny` in the same payload whose style clause ended "no glow", so the draw
    could not satisfy it and — post-ADR-034 — the judge could legitimately contradict it on all
    three draws, burning the whole budget on every job for that character.

    Unlike the two `notes`/filler divergences this is NOT one-directional: an unsatisfiable
    attribute must reach neither prompt, because the defect is in asking for it at all.
    """
    star = CharacterDescription(species="star", colours=["glowing"], body_features=["tiny"])
    _, t2i_mock, judge_mock, _ = _mint(
        [_verdict(True)], description=star, name="the star", style_fragment=COMIC
    )

    assert "glowing" not in t2i_mock.call_args.args[0]
    assert "glowing" not in judge_mock.call_args.args[0]
    # Narrowed, not gutted: species and the permitted axes still describe the character.
    assert "the star, star, tiny" in judge_mock.call_args.args[0]


def test_an_attribute_the_active_fragment_never_forbids_still_reaches_both_prompts():
    """ADR-035 is per-preset, not a blanket ban: `cel` never says "no glow"."""
    star = CharacterDescription(species="star", colours=["glowing"])
    _, t2i_mock, judge_mock, _ = _mint(
        [_verdict(True)], description=star, name="the star", style_fragment=STYLE_PRESETS["cel"]
    )

    assert "glowing" in t2i_mock.call_args.args[0]
    assert "glowing" in judge_mock.call_args.args[0]


def test_mint_reference_uploads_to_the_suffix_it_is_given():
    """Spec §4.4. Both minting paths join ONE monotonic per-book sequence; the flagged image at
    suffix 1 is preserved as evidence (`providers.py:625` marks the backstop rubric UNMEASURED),
    so a redraw must not land back on suffix 1 and upsert over it."""
    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", side_effect=list(DRAWS)), \
         patch("pipeline.char_bible.judge", side_effect=[_verdict(True)]), \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        path, _, _ = mint_reference(
            CharacterDescription(species="dog"), "the dog", FRAG, "story-1", "c0", n=2,
        )

    assert path == "story-1/ref-c0-2.png"
    assert _uploaded_path(fake_supabase) == "story-1/ref-c0-2.png"


def test_mint_reference_defaults_to_suffix_one():
    """The default keeps every pre-existing caller and fixture on the path they already assert."""
    (path, _, _), _, _, supabase = _mint([_verdict(True)])

    assert path == "story-1/ref-c0-1.png"
    assert _uploaded_path(supabase) == "story-1/ref-c0-1.png"


def test_mint_targeted_after_a_moderation_redraw_picks_a_suffix_that_collides_with_nothing():
    """§6 test 15 / §4.4. rc=0, mrc=1 (both PRE-bump here) → 0 + 1 + 2 = 3. Suffix 1 is the
    flagged original and suffix 2 is the moderation redraw; a tap must land clear of both."""
    from contracts.story_memory import Cost, ReferenceRetry

    state = _state(
        [_char("c0", "the dog", ref="story-1/ref-c0-2.png")],
        cost=Cost(ref_retry_count=0, ref_mod_retry_count=1),
    )
    state.reference_retry = ReferenceRetry(char_id="c0", attribute="a red hat")

    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", return_value=b"img"), \
         patch("pipeline.char_bible.judge", return_value=_verdict(True, ["dog"])), \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        result = char_bible(state)

    assert result["characters"][0].canonical_ref_image == "story-1/ref-c0-3.png"


def test_ref_mod_retry_count_bumps_by_exactly_one_when_two_characters_arrive_flagged():
    """§6 test 12 / §2. The counter is per BOOK — it measures loop iterations, not characters.
    One cycle re-mints both, so a book where c0 and c1 both flag spends 1, not 2."""
    from contracts.story_memory import Cost

    flagged = [
        _char("c0", "the dog").model_copy(update={"ref_moderation_status": "flagged"}),
        _char("c1", "the cat").model_copy(update={"ref_moderation_status": "flagged"}),
    ]
    state = _state(flagged, cost=Cost(ref_mod_retry_count=0))

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        result = char_bible(state)

    assert mint.call_count == 2
    assert result["cost"].ref_mod_retry_count == 1


def test_ref_mod_retry_count_does_not_bump_on_a_first_unflagged_mint():
    """§6 test 13. The ordinary path must not spend budget it never used."""
    state = _state([_char("c0", "the dog"), _char("c1", "the cat")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()):
        result = char_bible(state)

    assert result["cost"].ref_mod_retry_count == 0


def test_the_re_mint_uploads_to_suffix_two_and_leaves_the_flagged_image_alone():
    """§6 test 14 / §4.4. The bump happens BEFORE the loop so `n` reads the post-bump counter:
    rc=0, mrc=1 → 0 + 1 + 1 = 2. A pre-bump read would give 1 and upsert over the evidence."""
    from contracts.story_memory import Cost

    flagged = _char("c0", "the dog").model_copy(update={"ref_moderation_status": "flagged"})
    state = _state([flagged], cost=Cost(ref_mod_retry_count=0))

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(state)

    assert mint.call_args.kwargs["n"] == 2


def test_the_initial_mint_asks_for_suffix_one():
    """The other half of the arithmetic: rc=0, mrc=0 (no flag, no bump) → 0 + 0 + 1 = 1."""
    state = _state([_char("c0", "the dog")])

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        char_bible(state)

    assert mint.call_args.kwargs["n"] == 1


def test_a_flag_on_one_character_bumps_the_counter_even_when_another_is_a_fresh_mint():
    """§4.6 row 3, on the cost side. c0 arrives flagged-and-cleared, c1 never had a reference.
    Both are in `selected`, one cycle is spent, and both land on the same suffix — which is safe
    because char_id is in the path."""
    from contracts.story_memory import Cost

    flagged = _char("c0", "the dog").model_copy(update={"ref_moderation_status": "flagged"})
    state = _state([flagged, _char("c1", "the cat")], cost=Cost(ref_mod_retry_count=0))

    with patch("pipeline.char_bible.mint_reference", return_value=_minted()) as mint:
        result = char_bible(state)

    assert result["cost"].ref_mod_retry_count == 1
    assert {call.kwargs["n"] for call in mint.call_args_list} == {2}



"""Deterministic tests for `consistency_check` (spec `docs/specs/consistency-checker.md` §6).

Two seams (MASTER_SPEC §6): `judge_attempt` with `providers.judge` + Supabase mocked, and the
node with `judge_attempt` patched. The router is pure and needs no mocks at all.
"""
import base64
from unittest.mock import MagicMock, patch

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Attempt,
    Character,
    CharacterDescription,
    Cost,
    FailureReason,
    Input,
    RefVerdict,
    Scene,
    StoryMemory,
    VlmVerdict,
)
from pipeline.consistency_check import SceneVerdict, _rank, consistency_check, judge_attempt
from pipeline.graph import route_after_check, route_next_scene


def _uri(path: str) -> str:
    """What `judge_attempt` should build for a download that returns `path.encode()`."""
    return "data:image/png;base64," + base64.b64encode(path.encode()).decode()


def _verdict(
    same: bool = True,
    *,
    anatomy: bool = True,
    style: bool = True,
    unique: bool = True,
    text_free: bool = True,
    attributes: list[str] | None = None,
    reasons: list[FailureReason] | None = None,
    differences: str = "none",
) -> SceneVerdict:
    return SceneVerdict(
        differences_observed=differences,
        same_character=same,
        attributes_present=attributes or [],
        style_match=style,
        anatomy_intact=anatomy,
        subjects_unique=unique,
        text_free=text_free,
        failure_reasons=reasons or [],
    )



def _supabase_returning_path_bytes() -> MagicMock:
    """Storage mock whose download echoes the path, so each image is identifiable."""
    fake = MagicMock()
    fake.storage.from_.return_value.download.side_effect = lambda path: path.encode()
    return fake


# --- judge_attempt (providers.judge + Supabase mocked) ---

def test_judge_attempt_makes_one_call_per_subject_with_its_own_reference_first():
    """Spec §6 + invariant 5: one call per character, `[reference, scene]` in that order."""
    fake = _supabase_returning_path_bytes()

    with patch("pipeline.consistency_check.get_supabase_client", return_value=fake), \
         patch("pipeline.consistency_check.judge", return_value=_verdict()) as judge_mock:
        verdicts = judge_attempt(
            "job-1/s0.png",
            [("the dog", "job-1/ref-c0.png"), ("the cat", "job-1/ref-c1.png")],
        )

    assert len(verdicts) == 2
    assert judge_mock.call_count == 2
    assert judge_mock.call_args_list[0].args[1] == [_uri("job-1/ref-c0.png"), _uri("job-1/s0.png")]
    assert judge_mock.call_args_list[1].args[1] == [_uri("job-1/ref-c1.png"), _uri("job-1/s0.png")]


def test_judge_attempt_shows_the_judge_base64_never_a_url():
    """CC-4 posture, inherited from char_bible: base64 in, durable paths persisted."""
    fake = _supabase_returning_path_bytes()

    with patch("pipeline.consistency_check.get_supabase_client", return_value=fake), \
         patch("pipeline.consistency_check.judge", return_value=_verdict()) as judge_mock:
        judge_attempt("job-1/s0.png", [("the dog", "job-1/ref-c0.png")])

    for url in judge_mock.call_args.args[1]:
        assert url.startswith("data:image/png;base64,")
        assert not url.startswith("http")


def test_judge_attempt_returns_empty_for_no_subjects_without_touching_storage_or_judge():
    """Spec §6: the `text_to_image` branch of a scene — nothing to judge identity against."""
    fake = _supabase_returning_path_bytes()

    with patch("pipeline.consistency_check.get_supabase_client", return_value=fake), \
         patch("pipeline.consistency_check.judge") as judge_mock:
        verdicts = judge_attempt("job-1/s0.png", [])

    assert verdicts == []
    judge_mock.assert_not_called()
    fake.storage.from_.return_value.download.assert_not_called()


def test_judge_attempt_swallows_a_raising_judge():
    """Spec §4: the artifact exists and is paid for; only the CHECK failed. Never a job failure."""
    fake = _supabase_returning_path_bytes()

    with patch("pipeline.consistency_check.get_supabase_client", return_value=fake), \
         patch("pipeline.consistency_check.judge", side_effect=RuntimeError("openrouter 500")):
        verdicts = judge_attempt("job-1/s0.png", [("the dog", "job-1/ref-c0.png")])

    assert verdicts == []


def test_judge_attempt_swallows_a_raising_storage_download():
    """Spec §4: failing the job over a check would violate ADR-010's shippable-page rule."""
    fake = MagicMock()
    fake.storage.from_.return_value.download.side_effect = Exception("404 not found")

    with patch("pipeline.consistency_check.get_supabase_client", return_value=fake), \
         patch("pipeline.consistency_check.judge") as judge_mock:
        verdicts = judge_attempt("job-1/s0.png", [("the dog", "job-1/ref-c0.png")])

    assert verdicts == []
    judge_mock.assert_not_called()


def test_scene_verdict_declares_differences_first_and_failure_reasons_last():
    """ADR-004 reason-then-score. `providers._assert_field_order` enforces this on the wire,
    but only if the schema declares it — this test is what pins the declaration."""
    names = list(SceneVerdict.model_fields)
    assert names[0] == "differences_observed"
    assert names[-1] == "failure_reasons"
    assert names == [
        "differences_observed",
        "same_character",
        "attributes_present",
        "style_match",
        "anatomy_intact",
        "subjects_unique",
        "text_free",
        "failure_reasons",
    ]


# --- §4.4 D3(b): uniqueness, measured not gated ---

def test_scene_verdict_declares_subjects_unique_between_anatomy_and_the_reasons():
    """ADR-004: the wire order must match the schema, and `providers._assert_field_order` rejects
    a provider that answers out of order. The prompt asks in exactly this order."""
    names = list(SceneVerdict.model_fields)
    assert names.index("anatomy_intact") < names.index("subjects_unique") < names.index("failure_reasons")


def test_the_judge_prompt_asks_the_uniqueness_question_after_anatomy_and_before_the_reasons():
    from pipeline.consistency_check import JUDGE_PROMPT

    assert JUDGE_PROMPT.index("anatomy is intact") < JUDGE_PROMPT.index("drawn exactly once")
    assert JUDGE_PROMPT.index("drawn exactly once") < JUDGE_PROMPT.index("failure reasons")


def test_the_uniqueness_question_scopes_to_the_character_not_the_noun():
    """§4.4: `REFERENCE_CLAUSE` already draws this distinction — "the stars" in "she looked up at
    the stars" names no character and stays drawable. A question phrased "is there more than one
    star" fails a legitimate night sky."""
    from pipeline.consistency_check import JUDGE_PROMPT

    question = JUDGE_PROMPT.format(name="the star")
    assert "the star is drawn exactly once" in question
    assert "not other things of the same kind" in question


def test_scene_verdict_subjects_unique_defaults_to_true():
    """A provider that omits the field must not read as a duplicate — same default as the
    contract field, for the same CC-10 reason."""
    verdict = SceneVerdict(differences_observed="d", same_character=True)
    assert verdict.subjects_unique is True


def test_the_scene_judge_asks_about_text_in_schema_order_and_the_version_is_bumped():
    """§6 test 14. `providers._assert_field_order` rejects a provider that answers out of schema
    order, so the prompt asks in `SceneVerdict`'s declaration order: uniqueness, then text, then
    the failure reasons. Naming doors and clothing is safe here — this string goes to the VLM
    JUDGE and never to the image model (§4.1).
    """
    from pipeline.consistency_check import JUDGE_PROMPT, JUDGE_PROMPT_VERSION

    assert JUDGE_PROMPT_VERSION == 3

    prompt = JUDGE_PROMPT.format(name="the dog")
    assert "free of any text" in prompt
    assert prompt.index("drawn exactly once") < prompt.index("free of any text")
    assert prompt.index("free of any text") < prompt.index("failure reasons")


def test_one_duplicated_subject_folds_the_whole_verdict_to_not_unique():
    """§6 test 18: worst-wins, like every other folded boolean."""
    state = _state(
        [_scene_with_attempt(characters_present=["c0", "c1"])],
        [_char("c0", "the dog", "job-1/ref-c0.png"), _char("c1", "the cat", "job-1/ref-c1.png")],
    )

    result = _run(state, [_verdict(True, unique=True), _verdict(True, unique=False)])

    assert result["scenes"][0].attempts[-1].vlm_verdict.subjects_unique is False


def test_all_unique_verdicts_fold_to_unique():
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])

    result = _run(state, [_verdict(True, unique=True)])

    assert result["scenes"][0].attempts[-1].vlm_verdict.subjects_unique is True


def test_a_duplicated_subject_alone_does_not_flip_passed():
    """§6 test 19 / §4.4: `passed` is unchanged — `same_character and anatomy_intact`. Gating
    means more regenerations, and issue #26 is open and already critical: prod job f4d0fd74 burned
    500s of a 900s timeout on a 7-scene book. Cost is not the constraint; latency is."""
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])

    result = _run(state, [_verdict(True, anatomy=True, unique=False)])

    attempt = result["scenes"][0].attempts[-1]
    assert attempt.vlm_verdict.subjects_unique is False
    assert attempt.passed is True
    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"    # and it finalized


def test_a_duplicated_subject_alone_does_not_buy_a_regeneration():
    """The consequence of not gating, pinned separately: `route_after_check` must still send this
    scene onward, not back to `regenerate`."""
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])

    result = _run(state, [_verdict(True, unique=False)])
    merged = _state([result["scenes"][0]], [_char("c0", "the dog")])

    assert route_after_check(merged) != "regenerate"


def test_an_unchecked_attempt_writes_no_verdict_and_therefore_no_uniqueness_signal():
    """A judge or Storage outage means *unchecked*, not *unique* — the verdict stays None."""
    state = _state([_scene_with_attempt(characters_present=[])])

    result = _run(state, [])

    assert result["scenes"][0].attempts[-1].vlm_verdict is None


def test_a_lettered_verdict_from_any_character_folds_the_page_to_not_text_free():
    """§6 test 9 / §4.3: worst-wins, like every other boolean in this fold. Two subjects, one
    judge call each; one comes back lettered and the page is lettered."""
    scene = _scene_with_attempt(characters_present=["c0", "c1"])
    state = _state([scene], [_char("c0", "the dog"), _char("c1", "the star")])

    result = _run(state, [_verdict(True, text_free=True), _verdict(True, text_free=False)])

    assert result["scenes"][0].attempts[-1].vlm_verdict.text_free is False


def test_lettering_alone_flips_passed_to_false():
    """§6 test 10 / §4.3 — the gate. Everything else on this verdict is clean: same character,
    anatomy intact, unique subjects, matching style. Only the door has a word on it.

    This is deliberately UNLIKE subjects_unique (which records and ranks but does not gate):
    that decision was blocked on an unmeasured duplicate rate, whereas at least 3 of the 6
    burrow-door draws in the 2026-08-13 probe came back lettered, and a word on a page in a book
    for a six-year-old is not a judgement call (CC-6).
    """
    scene = _scene_with_attempt(characters_present=["c0"])
    state = _state([scene], [_char("c0", "the dog")])

    result = _run(state, [_verdict(True, anatomy=True, unique=True, style=True, text_free=False)])

    attempt = result["scenes"][0].attempts[-1]
    assert attempt.vlm_verdict.same_character is True
    assert attempt.vlm_verdict.anatomy_intact is True
    assert attempt.passed is False


def test_a_lettered_page_is_not_finalized_and_buys_the_one_retry():
    """§4.3 + ADR-010: a real verdict saying *fail* buys the retry, and only the first time.
    An unfinalized scene is what routes control to `regenerate`."""
    scene = _scene_with_attempt(characters_present=["c0"])
    state = _state([scene], [_char("c0", "the dog")])

    result = _run(state, [_verdict(True, text_free=False)])

    assert result["scenes"][0].final_image_ref is None


def test_text_free_is_declared_after_subjects_unique_and_before_the_failure_reasons():
    """ADR-004: `providers._assert_field_order` enforces schema order on the wire, and
    `failure_reasons` must stay LAST — it is what `correct_prompt` iterates."""
    fields = list(SceneVerdict.model_fields)
    assert fields[-1] == "failure_reasons"
    assert fields.index("subjects_unique") < fields.index("text_free") < fields.index("failure_reasons")





# --- consistency_check node (judge_attempt patched — the node seam) ---

def _char(char_id: str, name: str, ref: str | None = "job-1/ref.png", verdict: RefVerdict | None = None) -> Character:
    return Character(
        char_id=char_id,
        name=name,
        description=CharacterDescription(species="dog"),
        canonical_ref_image=ref,
        ref_verdict=verdict,
    )


def _state(scenes: list[Scene], characters: list[Character] | None = None, cost: Cost | None = None) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        characters=characters or [],
        scenes=scenes,
        cost=cost or Cost(),
    )


def _scene_with_attempt(scene_id: str = "s0", image_ref: str = "job-1/s0-1.png", **kwargs) -> Scene:
    return Scene(
        scene_id=scene_id,
        text_excerpt="The dog ran.",
        attempts=[Attempt(image_ref=image_ref, prompt="p", passed=False)],
        **kwargs,
    )


def _run(state: StoryMemory, verdicts: list[SceneVerdict]) -> dict:
    with patch("pipeline.consistency_check.judge_attempt", return_value=verdicts):
        return consistency_check(state)


def test_node_folds_two_verdicts_worst_wins():
    """Spec §6: one failing subject drags every folded boolean to False; lists union and dedupe;
    differences_observed names both characters."""
    state = _state(
        [_scene_with_attempt(characters_present=["c0", "c1"])],
        [_char("c0", "the dog", "job-1/ref-c0.png"), _char("c1", "the cat", "job-1/ref-c1.png")],
    )
    result = _run(state, [
        _verdict(True, anatomy=True, style=True, attributes=["orange", "scarf"],
                 reasons=[FailureReason.wrong_colour], differences="tail is shorter"),
        _verdict(False, anatomy=False, style=False, attributes=["scarf", "whiskers"],
                 reasons=[FailureReason.wrong_colour, FailureReason.different_face],
                 differences="entirely different animal"),
    ])

    attempt = result["scenes"][0].attempts[-1]
    assert attempt.vlm_verdict.same_character is False
    assert attempt.vlm_verdict.anatomy_intact is False
    assert attempt.vlm_verdict.style_match is False
    assert attempt.vlm_verdict.attributes_present == ["orange", "scarf", "whiskers"]
    assert attempt.failure_reasons == [FailureReason.wrong_colour, FailureReason.different_face]
    assert "the dog: tail is shorter" in attempt.vlm_verdict.differences_observed
    assert "the cat: entirely different animal" in attempt.vlm_verdict.differences_observed


def test_node_emits_failure_reasons_in_enum_declaration_order():
    """Spec §6: declaration order regardless of subject order — it is the order `correct_prompt`
    iterates, so a different order silently reorders the correction clauses."""
    state = _state(
        [_scene_with_attempt(characters_present=["c0", "c1"])],
        [_char("c0", "the dog", "job-1/ref-c0.png"), _char("c1", "the cat", "job-1/ref-c1.png")],
    )
    result = _run(state, [
        _verdict(False, reasons=[FailureReason.character_absent, FailureReason.wrong_style]),
        _verdict(False, reasons=[FailureReason.wrong_species]),
    ])

    assert result["scenes"][0].attempts[-1].failure_reasons == [
        FailureReason.wrong_species,
        FailureReason.wrong_style,
        FailureReason.character_absent,
    ]


def test_node_passes_when_same_character_and_anatomy_intact_even_if_style_fails():
    """Spec §4 the pass rule: `style_match` is recorded and folded but does NOT gate.
    Consequence, stated rather than hidden: a genuinely off-style page can ship."""
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])
    result = _run(state, [_verdict(True, anatomy=True, style=False)])

    attempt = result["scenes"][0].attempts[-1]
    assert attempt.passed is True
    assert attempt.vlm_verdict.style_match is False


def test_node_fails_the_gate_on_anatomy_alone():
    """Spec §4 ⚠️: an anatomy-only failure gates the attempt and produces NO failure_reasons —
    ADR-028 excluded anatomy from the closed 7. Recorded, handed to regeneration-controller.
    Do not 'fix' this by adding an 8th enum value."""
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])
    result = _run(state, [_verdict(True, anatomy=False)])

    attempt = result["scenes"][0].attempts[-1]
    assert attempt.passed is False
    assert attempt.failure_reasons == []


def test_node_finalizes_unchecked_when_the_helper_returns_nothing():
    """Spec §6 + invariant 4: vlm_verdict None means UNCHECKED, never checked-and-clean.
    The page still ships (ADR-010) — final_image_ref is still set."""
    state = _state([_scene_with_attempt(characters_present=[])])
    result = _run(state, [])

    scene = result["scenes"][0]
    attempt = scene.attempts[-1]
    assert attempt.vlm_verdict is None
    assert attempt.failure_reasons == []
    assert attempt.passed is False
    assert scene.final_image_ref == "job-1/s0-1.png"


def test_node_sets_final_image_ref_to_the_last_attempts_image():
    """Invariant 2: final_image_ref is written by THIS node only."""
    state = _state([_scene_with_attempt(image_ref="job-1/scene-abc.png", characters_present=["c0"])],
                   [_char("c0", "the dog")])
    result = _run(state, [_verdict(True)])

    scene = result["scenes"][0]
    assert scene.final_image_ref == scene.attempts[-1].image_ref == "job-1/scene-abc.png"


def test_node_mutates_only_the_last_attempt():
    """Invariant 3: earlier attempts are never rewritten — byte-identical in, byte-identical out."""
    earlier = Attempt(image_ref="job-1/s0-a.png", prompt="first", passed=False)
    scene = Scene(
        scene_id="s0",
        text_excerpt="x",
        characters_present=["c0"],
        attempts=[earlier, Attempt(image_ref="job-1/s0-b.png", prompt="second", passed=False)],
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(True)])

    returned = result["scenes"][0]
    assert returned.attempts[0] == earlier
    assert returned.attempts[1].passed is True
    assert returned.final_image_ref == "job-1/s0-b.png"


def test_node_selects_the_first_unfinalized_scene():
    """ADR-024: same selection rule as generate_scene — no cursor, no second rule."""
    state = _state(
        [
            Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-1/s0-1.png"),
            _scene_with_attempt("s1", "job-1/s1-1.png"),
        ]
    )
    result = _run(state, [])

    scene, = result["scenes"]
    assert scene.scene_id == "s1"


def test_node_returns_empty_when_every_scene_is_finalized():
    """Invariant 1: exactly one scene finalizes per invocation, or nothing is left to do."""
    state = _state([Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-1/s0-1.png")])

    with patch("pipeline.consistency_check.judge_attempt") as helper:
        result = consistency_check(state)

    assert result == {}
    helper.assert_not_called()


def test_node_returns_empty_when_the_selected_scene_has_no_attempts():
    """Spec §4 step 2: unreachable in the linear flow, so this is a guard, not a path."""
    state = _state([Scene(scene_id="s0", text_excerpt="0")])

    with patch("pipeline.consistency_check.judge_attempt") as helper:
        result = consistency_check(state)

    assert result == {}
    helper.assert_not_called()


def test_node_skips_a_char_id_absent_from_the_roster():
    """Spec §4: this node may not extend the roster. Same posture as generate_scene."""
    state = _state(
        [_scene_with_attempt(characters_present=["c0", "ghost-id"])],
        [_char("c0", "the dog", "job-1/ref-c0.png")],
    )

    with patch("pipeline.consistency_check.judge_attempt", return_value=[_verdict(True)]) as helper:
        consistency_check(state)

    helper.assert_called_once_with("job-1/s0-1.png", [("the dog", "job-1/ref-c0.png")])


def test_node_skips_a_character_carrying_no_reference():
    """Spec §4: no reference means no identity to judge against — not a subject."""
    state = _state(
        [_scene_with_attempt(characters_present=["c0", "c1"])],
        [_char("c0", "the dog", "job-1/ref-c0.png"), _char("c1", "the cat", ref=None)],
    )

    with patch("pipeline.consistency_check.judge_attempt", return_value=[_verdict(True)]) as helper:
        consistency_check(state)

    helper.assert_called_once_with("job-1/s0-1.png", [("the dog", "job-1/ref-c0.png")])


def test_node_judges_against_a_reference_whose_ref_verdict_failed():
    """Spec §4: ADR-028 ships the best-of reference and generate_scene conditions on it.
    Judging against anything else would fail every scene of a book for the reference's fault."""
    off_spec = RefVerdict(differences_observed="the scarf is blue", matches_description=False)
    state = _state(
        [_scene_with_attempt(characters_present=["c0"])],
        [_char("c0", "the dog", "job-1/ref-c0.png", verdict=off_spec)],
    )

    with patch("pipeline.consistency_check.judge_attempt", return_value=[_verdict(True)]) as helper:
        consistency_check(state)

    helper.assert_called_once_with("job-1/s0-1.png", [("the dog", "job-1/ref-c0.png")])


def test_node_returns_only_scenes_and_never_touches_cost_or_state():
    """Invariant 6: Cost counts images and this node buys none. ADR-024: partial return, never mutate."""
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")],
                   cost=Cost(image_count=7, regen_count=1, usd_estimate=2.5))
    before = state.model_dump()

    result = _run(state, [_verdict(True)])

    assert set(result) == {"scenes"}
    assert state.model_dump() == before


# --- ADR-010 best-of and the three-term finalize rule (regeneration-controller §4) ---

def _attempt(
    image_ref: str,
    *,
    same: bool | None = None,
    anatomy: bool = True,
    style: bool = True,
    unique: bool = True,
    text: bool = True,
) -> Attempt:
    """An already-judged attempt. same=None means UNCHECKED (vlm_verdict is None)."""
    if same is None:
        return Attempt(image_ref=image_ref, prompt="p", passed=False)
    return Attempt(
        image_ref=image_ref,
        prompt="p",
        vlm_verdict=VlmVerdict(
            differences_observed="d",
            same_character=same,
            style_match=style,
            anatomy_intact=anatomy,
            subjects_unique=unique,
            text_free=text,
        ),
        passed=same and anatomy and text,
    )


def test_rank_prefers_the_unique_attempt_when_the_higher_keys_tie():
    """§6 test 20 / §4.4: the free improvement. When a retry fires for some OTHER reason, best-of
    now prefers the non-duplicated attempt at no extra draw."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, unique=False, style=True),
        _attempt("job-1/s0-2.png", same=False, anatomy=True, unique=True, style=True),
    )

    result = _run(
        _state([scene], [_char("c0", "the dog")]),
        [_verdict(False, anatomy=True, unique=True, style=True)],
    )

    assert result["scenes"][0].final_image_ref == "job-1/s0-2.png"


def test_rank_puts_uniqueness_above_style_match():
    """The declared order is (same_character, anatomy_intact, subjects_unique, style_match), so a
    unique-but-off-style attempt beats a duplicated-but-on-style one."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, unique=True, style=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=True, unique=False, style=True),
    )

    result = _run(
        _state([scene], [_char("c0", "the dog")]),
        [_verdict(False, anatomy=True, unique=False, style=True)],
    )

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_rank_puts_uniqueness_below_anatomy():
    """Anatomy GATES and uniqueness does not, so anatomy must outrank it."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, unique=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=False, unique=True),
    )

    result = _run(
        _state([scene], [_char("c0", "the dog")]),
        [_verdict(False, anatomy=False, unique=True)],
    )

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_rank_sorts_a_lettered_attempt_below_a_clean_one_and_above_an_anatomy_failure():
    """§6 test 11 / §4.3 ordering rationale: text_free sits AFTER anatomy_intact, because a
    merged limb is a worse picture than a lettered door."""
    clean = _attempt("job-1/s0-1.png", same=True, anatomy=True, text=True)
    lettered = _attempt("job-1/s0-2.png", same=True, anatomy=True, text=False)
    broken = _attempt("job-1/s0-3.png", same=True, anatomy=False, text=True)

    assert _rank(clean) > _rank(lettered) > _rank(broken)


def test_rank_prefers_a_text_free_attempt_over_a_unique_subject_one():
    """§6 test 12 / §4.3: text_free sits AHEAD of subjects_unique and style_match, because those
    two deliberately do not gate and this one does."""
    text_free_but_duplicated = _attempt(
        "job-1/s0-1.png", same=True, anatomy=True, text=True, unique=False, style=False
    )
    lettered_but_unique = _attempt(
        "job-1/s0-2.png", same=True, anatomy=True, text=False, unique=True, style=True
    )

    assert _rank(text_free_but_duplicated) > _rank(lettered_but_unique)


def test_the_unchecked_rank_tuple_widened_to_six_zeros():
    """§6 test 13: unchecked still sorts below EVERY checked attempt (invariant 4). The tuple
    widened, so the zeros have to widen with it or the comparison raises on length."""
    unchecked = Attempt(image_ref="job-1/s0-1.png", prompt="p", passed=False)
    assert _rank(unchecked) == (0, 0, 0, 0, 0, 0)

    worst_checked = _attempt(
        "job-1/s0-2.png", same=False, anatomy=False, text=False, unique=False, style=False
    )
    assert _rank(worst_checked) > _rank(unchecked)


def test_the_checked_rank_tuple_is_six_terms_in_the_declared_order():
    ranked = _rank(
        _attempt("job-1/s0-1.png", same=True, anatomy=False, text=True, unique=False, style=True)
    )
    assert ranked == (1, True, False, True, False, True)


def test_the_worst_possible_checked_attempt_still_outranks_an_unchecked_one():
    """§6 test 21, the behavioural half. Promoting an unjudged image over a judged one would let
    a judge outage silently decide the page (invariant 4)."""
    worst = _attempt("job-1/s0-1.png", same=False, anatomy=False, unique=False, style=False)
    unchecked = _attempt("job-1/s0-2.png", same=None)

    assert _rank(worst) > _rank(unchecked)



def _two_attempt_scene(first: Attempt, second: Attempt) -> Scene:
    return Scene(scene_id="s0", text_excerpt="x", characters_present=["c0"], attempts=[first, second])


def test_node_defers_finalization_when_a_single_attempt_fails_the_gate():
    """The whole point of the change: a checked FAILURE with one attempt is left unfinalized so
    route_after_check can send it to regenerate."""
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])
    result = _run(state, [_verdict(False)])

    assert result["scenes"][0].final_image_ref is None


def test_node_finalizes_a_single_unchecked_attempt_rather_than_retrying():
    """The `verdict is None` term is load-bearing. A judge or Storage outage must not buy a
    second paid draw with no signal to correct on — that redraw would be a pure resample."""
    state = _state([_scene_with_attempt(characters_present=[])])
    result = _run(state, [])

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_node_finalizes_a_single_passing_attempt():
    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])
    result = _run(state, [_verdict(True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_best_of_prefers_the_attempt_that_wins_on_same_character():
    """Lexicographic: same_character is the first term and outranks everything below it."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=True, anatomy=False, style=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=True, style=True),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(False, anatomy=True, style=True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_best_of_prefers_the_attempt_that_wins_on_anatomy_when_identity_ties():
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, style=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=False, style=True),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(False, anatomy=False, style=True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_best_of_prefers_the_attempt_that_wins_on_style_when_the_first_two_terms_tie():
    """style_match does not GATE, but it is the third term of the ranking (ADR-028)."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, style=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=True, style=True),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(False, anatomy=True, style=True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-2.png"


def test_best_of_breaks_a_genuine_tie_in_favour_of_attempt_two():
    """Pinned explicitly: max returns the FIRST maximal element, so this only holds because the
    ranking iterates in reverse. On a tie the corrected prompt is the better prior — ADR-010
    calls attempt 2 refinement, not resampling."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=True, style=True),
        _attempt("job-1/s0-2.png", same=False, anatomy=True, style=True),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(False, anatomy=True, style=True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-2.png"


def test_best_of_ranks_a_checked_failure_above_an_unchecked_attempt():
    """Unchecked sorts last (0,0,0,0). Promoting an unjudged image over a judged one would let
    a judge outage silently decide the page — invariant 4 says unchecked is never a pass."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=False, style=False),
        _attempt("job-1/s0-2.png", same=None),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [])

    assert result["scenes"][0].final_image_ref == "job-1/s0-1.png"


def test_two_attempts_always_finalize_even_when_both_fail():
    """ADR-010: at most one regeneration per scene, and never a broken page. A real image ships."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=False),
        _attempt("job-1/s0-2.png", same=False, anatomy=False),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(False, anatomy=False)])

    finalized = result["scenes"][0]
    assert finalized.final_image_ref is not None
    assert all(a.passed is False for a in finalized.attempts)


def test_best_of_uses_the_verdict_written_this_pass_not_the_stale_one():
    """Ranking runs over `updated`, not scene.attempts. If it ranked the pre-fold list, attempt 2
    would carry no verdict, sort last, and attempt 1 would win every retry."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False, anatomy=False, style=False),
        Attempt(image_ref="job-1/s0-2.png", prompt="corrected", passed=False),   # unjudged going in
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(True, anatomy=True)])

    assert result["scenes"][0].final_image_ref == "job-1/s0-2.png"


def test_the_second_pass_never_rewrites_attempt_ones_verdict():
    """consistency-checker invariant 3: only the last attempt is judged and mutated."""
    first = _attempt("job-1/s0-1.png", same=False, anatomy=False, style=False)
    scene = _two_attempt_scene(first, Attempt(image_ref="job-1/s0-2.png", prompt="corrected"))
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(True)])

    assert result["scenes"][0].attempts[0] == first


def test_the_returned_attempt_list_replaces_rather_than_appends():
    """len(updated) == len(scene.attempts). Appending here would let a scene reach three attempts
    and break ADR-010's at-most-one-regeneration rule."""
    scene = _two_attempt_scene(
        _attempt("job-1/s0-1.png", same=False),
        Attempt(image_ref="job-1/s0-2.png", prompt="corrected"),
    )
    result = _run(_state([scene], [_char("c0", "the dog")]), [_verdict(True)])

    assert len(result["scenes"][0].attempts) == 2


# --- route_next_scene (pure — no mocks) ---

def test_router_moderates_a_just_finalized_scene_before_drawing_the_next():
    """Spec §4c granularity (resolved 2026-08-13): the gate runs INSIDE the loop, so a book that
    is going to fail moderation fails two images in rather than eleven. s0 is drawn and unscreened
    while s1 is not drawn at all — screening s0 comes first."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-1/s0-1.png"),
        Scene(scene_id="s1", text_excerpt="1"),
    ])
    assert route_next_scene(state) == "output_mod"


def test_router_sends_an_unfinalized_scene_back_to_generate_scene_once_the_drawn_one_is_screened():
    """The other half of the pair above: nothing is owed to output_mod, so the loop continues.
    Without the `moderation_status is None` term this returns "output_mod" forever."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-1/s0-1.png", moderation_status="passed"),
        Scene(scene_id="s1", text_excerpt="1"),
    ])
    assert route_next_scene(state) == "generate_scene"


def test_router_sends_a_fully_finalized_book_to_output_mod():
    state = _state([Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-1/s0-1.png")])
    assert route_next_scene(state) == "output_mod"


def test_router_sends_a_fully_screened_book_to_compose():
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-1/s0-1.png", moderation_status="passed"),
    ])
    assert route_next_scene(state) == "compose"


def test_router_sends_an_empty_scene_list_to_compose():
    """ADR-024: segment produced no scenes. The loop head must not enter a loop with no work.

    Destination moved from "output_mod" to "compose" when moderation moved into the loop: there is
    nothing for output_mod to screen, and compose raises "no scenes" either way — one hop earlier.
    """
    assert route_next_scene(_state([])) == "compose"


# --- route_after_check (pure — no mocks) ---

def test_route_after_check_sends_a_checked_failing_scene_to_regenerate():
    state = _state([_scene_with_attempt(characters_present=["c0"])])
    assert route_after_check(state) == "regenerate"


def test_route_after_check_sends_a_scene_with_no_attempts_to_generate_scene():
    """The ping-pong guard. Without the `scene.attempts` term this returns "regenerate", which
    raises, or — if it returned {} instead — loops until recursion_limit. A scene with no
    attempts belongs to generate_scene, and route_next_scene says so."""
    state = _state([Scene(scene_id="s0", text_excerpt="0")])
    assert route_after_check(state) == "generate_scene"


def test_route_after_check_sends_a_fully_finalized_book_to_output_mod():
    state = _state([Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-1/s0-1.png")])
    assert route_after_check(state) == "output_mod"


def test_route_after_check_sends_an_empty_scene_list_to_compose():
    assert route_after_check(_state([])) == "compose"


def test_route_after_check_skips_finalized_scenes_when_selecting():
    """Same selection rule as every other node in the loop — the FIRST unfinalized scene."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-1/s0-1.png"),
        _scene_with_attempt("s1", "job-1/s1-1.png"),
    ])
    assert route_after_check(state) == "regenerate"


def test_the_per_scene_log_line_carries_uniqueness_and_the_prompt_version(caplog):
    """CC-5: a duplicated page in the finished book traces to a scene, an attempt, the verdict
    that let it through, AND the prompt version that produced the verdict."""
    import logging

    from pipeline.consistency_check import JUDGE_PROMPT_VERSION

    state = _state([_scene_with_attempt(characters_present=["c0"])], [_char("c0", "the dog")])
    with caplog.at_level(logging.INFO):
        _run(state, [_verdict(True, unique=False)])

    assert "subjects_unique=False" in caplog.text
    assert f"judge_prompt_version={JUDGE_PROMPT_VERSION}" in caplog.text


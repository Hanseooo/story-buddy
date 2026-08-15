"""Deterministic tests for `regenerate` (spec `docs/specs/regeneration-controller.md` §6).

One seam (MASTER_SPEC §6): the node with `generate_and_store` patched. Everything else in this
node is pure — `correct_prompt` has no model call, and the selection rule is a list scan.
"""
import pytest
from unittest.mock import patch

from app.config import IMAGE_BUDGET
from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Attempt,
    Character,
    CharacterDescription,
    Cost,
    FailureReason,
    Input,
    Scene,
    StoryMemory,
    StoryObject,
    Style,
    VlmVerdict,
)
from pipeline.prompt_optimizer import ANATOMY_CLAUSE, IDENTITY_CLAUSE, TEXT_CLAUSE, build_prompt
from pipeline.regenerate import regenerate


def _char(char_id: str = "c0", name: str = "the dog", ref: str | None = "job-1/ref-c0.png") -> Character:
    return Character(
        char_id=char_id,
        name=name,
        description=CharacterDescription(species="dog", colours=["orange"]),
        canonical_ref_image=ref,
    )


def _verdict(*, same: bool = False, anatomy: bool = True, style: bool = True, text: bool = True) -> VlmVerdict:
    return VlmVerdict(
        differences_observed="the face is wrong",
        same_character=same,
        style_match=style,
        anatomy_intact=anatomy,
        text_free=text,
    )


def _failed_attempt(
    *,
    verdict: VlmVerdict | None = None,
    reasons: list[FailureReason] | None = None,
    prompt: str | None = "the original prompt",
) -> Attempt:
    return Attempt(
        image_ref="job-1/s0-1.png",
        prompt=prompt,
        vlm_verdict=verdict if verdict is not None else _verdict(),
        failure_reasons=reasons or [],
        passed=False,
    )


def _state(
    scenes: list[Scene],
    characters: list[Character] | None = None,
    cost: Cost | None = None,
) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        characters=characters if characters is not None else [_char()],
        style=Style(prompt_fragment="flat cel-shaded cartoon"),
        scenes=scenes,
        cost=cost or Cost(),
    )


def _scene(attempts: list[Attempt] | None = None, **kwargs) -> Scene:
    kwargs.setdefault("visual_direction", "The dog runs.")
    return Scene(
        scene_id="s0",
        text_excerpt="The dog ran.",
        characters_present=["c0"],
        prompt="the original prompt",
        attempts=attempts if attempts is not None else [_failed_attempt()],
        **kwargs,
    )


def _run(state: StoryMemory, *, paid: bool = True):
    with patch(
        "pipeline.regenerate.generate_and_store", return_value=("job-1/s0-2.png", paid)
    ) as store:
        return regenerate(state), store


# --- the partial return (invariant 1) ---

def test_appends_exactly_one_attempt_and_returns_both_keys():
    result, _ = _run(_state([_scene()]))

    assert set(result) == {"scenes", "cost"}
    scene, = result["scenes"]
    assert len(scene.attempts) == 2
    assert scene.attempts[-1].image_ref == "job-1/s0-2.png"
    assert scene.attempts[-1].passed is False


def test_returns_the_pre_existing_attempt_byte_identical():
    """Only consistency_check judges and mutates attempts. This node appends and nothing else."""
    first = _failed_attempt()
    result, _ = _run(_state([_scene([first])]))

    assert result["scenes"][0].attempts[0] == first


def test_never_returns_an_empty_dict_on_any_reachable_path():
    """Invariant 1: `{}` leaves state unchanged, so consistency_check re-judges the same attempt,
    reaches the same verdict, and route_after_check sends control straight back — an infinite
    loop bounded only by recursion_limit."""
    result, _ = _run(_state([_scene()]))

    assert result != {}


# --- attempt_n (the per-attempt Storage path) ---

def test_passes_attempt_n_of_len_attempts_plus_one():
    _, store = _run(_state([_scene()]))

    assert store.call_args.args[3] == 2


def test_attempt_n_tracks_the_attempt_list_rather_than_a_stored_counter():
    """ADR-024 rejected a loop cursor for the same reason: derived beats stored."""
    scene = _scene([_failed_attempt(), Attempt(image_ref="job-1/s0-2.png", prompt="second")])
    _, store = _run(_state([scene]))

    assert store.call_args.args[3] == 3


# --- cost (invariant 6) ---

def test_bumps_image_count_and_regen_count_when_paid():
    result, _ = _run(_state([_scene()], cost=Cost(image_count=4, regen_count=1)), paid=True)

    assert result["cost"].image_count == 5
    assert result["cost"].regen_count == 2


def test_bumps_regen_count_but_not_image_count_when_the_asset_was_reused():
    """Resume mid-retry: the checkpoint predates this return, so both counters start from their
    pre-regenerate values. image_count + 0 records that the Storage skip meant no re-pay;
    regen_count + 1 records the regeneration the lost checkpoint never persisted. Gating
    regen_count on `paid` would count it as zero."""
    result, _ = _run(_state([_scene()], cost=Cost(image_count=4, regen_count=1)), paid=False)

    assert result["cost"].image_count == 4
    assert result["cost"].regen_count == 2


# --- what this node must NOT write (invariants 2, 3, 7) ---

def test_never_writes_final_image_ref():
    """Invariant 2: consistency_check remains its only writer."""
    result, _ = _run(_state([_scene()]))

    assert result["scenes"][0].final_image_ref is None


def test_never_writes_the_scene_prompt():
    """Invariant 3: scenes[].prompt holds the ORIGINAL build_prompt output. Per-attempt
    provenance is Attempt.prompt, which is what that field exists for (CC-5 tracing)."""
    result, _ = _run(_state([_scene()]))

    assert result["scenes"][0].prompt == "the original prompt"


def test_never_writes_regeneration_count():
    """Invariant 7: it equals len(attempts) - 1. A stored copy of a derived fact is a second
    source of truth that a resume can desynchronise."""
    result, _ = _run(_state([_scene()]))

    assert result["scenes"][0].regeneration_count == 0


def test_does_not_mutate_the_state_it_was_handed():
    state = _state([_scene()])
    before = state.model_dump()

    _run(state)

    assert state.model_dump() == before


# --- ref_paths (the shared list, not a copy of the rule) ---

def test_ref_paths_agree_with_the_image_roll_the_corrected_prompt_carries():
    """Issue #23's invariant on this node. `correct_prompt` only appends, so the retry still
    asserts build_prompt's roll — "Image 2 is the star" against a list this node passes to fal.
    A second copy of the selection rule would satisfy the ref_paths tests below and still let the
    roll lie the first time the two rules diverge."""
    characters = [
        _char(),
        _char("c1", "the cat", ref=None),
        _char("c2", "the star", ref="job-1/ref-c2.png"),
    ]
    present = ["c0", "c1", "c2"]
    prompt = build_prompt("The dog ran.", present, characters, "flat cel-shaded cartoon")
    scene = _scene(attempts=[_failed_attempt(prompt=prompt)]).model_copy(
        update={"characters_present": present, "prompt": prompt}
    )
    _, store = _run(_state([scene], characters=characters))

    assert "Image 1 is the dog, orange." in store.call_args.args[0]
    assert "Image 2 is the star, dog, orange." in store.call_args.args[0]
    assert store.call_args.args[4] == ["job-1/ref-c0.png", "job-1/ref-c2.png"]


# --- ref_paths (identical to generate_scene's loop) ---

def test_collects_refs_only_for_present_characters_carrying_a_canonical_image():
    cat = _char("c1", "the cat", ref=None)
    scene = _scene()
    scene = scene.model_copy(update={"characters_present": ["c0", "c1"]})
    _, store = _run(_state([scene], characters=[_char(), cat]))

    assert store.call_args.args[4] == ["job-1/ref-c0.png"]


def test_skips_an_unresolvable_char_id_without_raising():
    """This node may not extend the roster — identical posture to generate_scene."""
    scene = _scene().model_copy(update={"characters_present": ["c0", "ghost-id"]})
    _, store = _run(_state([scene], characters=[_char()]))

    assert store.call_args.args[4] == ["job-1/ref-c0.png"]


def test_falls_back_to_text_to_image_refs_when_the_scene_has_none():
    """ref_paths == [] → the same text_to_image branch generate_scene takes. The corrected
    prompt still applies."""
    scene = _scene().model_copy(update={"characters_present": []})
    _, store = _run(_state([scene]))

    assert store.call_args.args[4] == []


# --- invariant 5: the prompt is ALWAYS corrected, never resampled ---

def test_corrected_prompt_differs_from_the_previous_attempts_prompt_on_reasons():
    scene = _scene([_failed_attempt(reasons=[FailureReason.different_face])])
    _, store = _run(_state([scene]))

    sent = store.call_args.args[0]
    assert sent != "the original prompt"
    assert sent.startswith("the original prompt")
    assert "match the reference character's face exactly" in sent


def test_corrected_prompt_differs_on_an_anatomy_only_failure():
    """ADR-028 froze anatomy out of FailureReason, so without the boolean this retry would send
    a byte-identical prompt — a pure resample."""
    scene = _scene([_failed_attempt(verdict=_verdict(same=True, anatomy=False), reasons=[])])
    _, store = _run(_state([scene]))

    sent = store.call_args.args[0]
    assert sent != "the original prompt"
    assert ANATOMY_CLAUSE in sent


def test_corrected_prompt_differs_on_same_character_false_with_no_reasons():
    """The judge named the failure but gave no reason for it."""
    scene = _scene([_failed_attempt(verdict=_verdict(same=False), reasons=[])])
    _, store = _run(_state([scene]))

    sent = store.call_args.args[0]
    assert sent != "the original prompt"
    assert IDENTITY_CLAUSE in sent


def test_the_identity_clause_is_suppressed_when_the_judge_gave_a_reason():
    """No duplication with different_face."""
    scene = _scene([_failed_attempt(verdict=_verdict(same=False), reasons=[FailureReason.different_face])])
    _, store = _run(_state([scene]))

    assert IDENTITY_CLAUSE not in store.call_args.args[0]


def test_invariant_5_survives_a_gating_reason_whose_axis_is_empty():
    """The path fix B opened. `wrong_colour` gates `passed` now, so it can be the ONLY reason on a
    page — and the judge compares against the reference image, so it can flag a colour `analyze`
    never recorded. `correct_prompt` then drops the hollow clause, and without its floor this
    retry would send a byte-identical prompt: the resample ADR-010 rejects, paid for."""
    colourless = Character(
        char_id="c0",
        name="the dog",
        description=CharacterDescription(species="dog", colours=[]),
        canonical_ref_image="job-1/ref-c0.png",
    )
    scene = _scene([_failed_attempt(verdict=_verdict(same=True), reasons=[FailureReason.wrong_colour])])
    _, store = _run(_state([scene], characters=[colourless]))

    sent = store.call_args.args[0]
    assert sent != "the original prompt"
    assert "match the reference's exact colours" not in sent
    assert IDENTITY_CLAUSE in sent


def test_the_new_attempt_records_the_corrected_prompt_not_the_original():
    """CC-5: per-attempt provenance is the whole reason Attempt.prompt exists."""
    scene = _scene([_failed_attempt(reasons=[FailureReason.different_face])])
    result, store = _run(_state([scene]))

    assert result["scenes"][0].attempts[-1].prompt == store.call_args.args[0]


def test_corrects_from_the_scene_prompt_when_the_attempt_carries_none():
    scene = _scene([_failed_attempt(prompt=None, reasons=[FailureReason.different_face])])
    _, store = _run(_state([scene]))

    assert store.call_args.args[0].startswith("the original prompt")


def test_treats_a_missing_verdict_as_no_boolean_correction():
    """`v.same_character if v else True` — an attempt with no verdict cannot have failed on
    identity or anatomy, so neither boolean clause fires."""
    scene = _scene([_failed_attempt(verdict=None, reasons=[FailureReason.wrong_colour])])
    _, store = _run(_state([scene]))

    sent = store.call_args.args[0]
    assert IDENTITY_CLAUSE not in sent
    assert ANATOMY_CLAUSE not in sent


def test_a_lettered_verdict_reaches_correct_prompt_as_the_text_free_keyword():
    """§6 test 18 / §4.4. Mirrors anatomy_intact exactly: a boolean, not an 8th FailureReason
    (ADR-028). `regenerate` passes no seed, so the retry also resamples for free — the clause is
    what makes it a CORRECTION rather than the pure re-roll ADR-010 rejects."""
    state = _state([_scene([_failed_attempt(verdict=_verdict(same=True, text=False))])])

    with patch("pipeline.regenerate.correct_prompt", return_value="corrected") as corrected:
        with patch("pipeline.regenerate.generate_and_store", return_value=("job-1/s0-2.png", True)):
            regenerate(state)

    assert corrected.call_args.kwargs["text_free"] is False


def test_the_text_clause_is_appended_to_the_retry_prompt():
    """End to end through the real `correct_prompt`: the prompt the retry actually draws from
    carries the clause, and still carries everything the first attempt had (invariant 3)."""
    state = _state([_scene([_failed_attempt(verdict=_verdict(same=True, text=False))])])

    with patch("pipeline.regenerate.generate_and_store", return_value=("job-1/s0-2.png", True)) as gas:
        regenerate(state)

    prompt = gas.call_args.args[0]
    assert TEXT_CLAUSE in prompt
    assert prompt.startswith("the original prompt")


def test_the_log_line_reports_whether_the_text_clause_fired(caplog):
    """§6 test 19 / CC-5: a correction that fired must be distinguishable from one that silently
    appended nothing (invariant 5)."""
    import logging

    def _log(verdict) -> str:
        caplog.clear()
        state = _state([_scene([_failed_attempt(verdict=verdict)])])
        with caplog.at_level(logging.INFO, logger="pipeline.regenerate"):
            with patch("pipeline.regenerate.generate_and_store", return_value=("job-1/s0-2.png", True)):
                regenerate(state)
        return caplog.text

    # Both directions: asserting only the True case would pass against a hardcoded literal, which
    # is exactly the silent-append confusion the line exists to remove.
    assert "text_clause=True" in _log(_verdict(same=True, text=False))
    assert "text_clause=False" in _log(_verdict(same=False, text=True))


# --- the guards that raise (invariant 1, ADR-025 D4) ---

def test_raises_when_no_scene_is_unfinalized():
    state = _state([_scene(final_image_ref="job-1/s0-1.png")])

    with patch("pipeline.regenerate.generate_and_store") as store, pytest.raises(RuntimeError):
        regenerate(state)

    store.assert_not_called()


def test_raises_when_the_selected_scene_has_no_attempts():
    """A scene with no attempts belongs to generate_scene, and route_after_check says so.
    Returning {} here instead would ping-pong forever."""
    state = _state([_scene([])])

    with patch("pipeline.regenerate.generate_and_store") as store, pytest.raises(RuntimeError):
        regenerate(state)

    store.assert_not_called()


def test_raises_before_any_spend_when_the_image_budget_is_reached():
    """ADR-025 D4. A retry is not exempt from the breaker — same posture as generate_scene."""
    state = _state([_scene()], cost=Cost(image_count=IMAGE_BUDGET))

    with patch("pipeline.regenerate.generate_and_store") as store, pytest.raises(RuntimeError):
        regenerate(state)

    store.assert_not_called()


def test_raises_when_neither_the_attempt_nor_the_scene_carries_a_prompt():
    """Unreachable today. The alternative — drawing from correction clauses with no base prompt —
    is a guaranteed-garbage PAID image, so an ADR-025 hard failure is the honest outcome."""
    scene = _scene([_failed_attempt(prompt=None)]).model_copy(update={"prompt": None})
    state = _state([scene])

    with patch("pipeline.regenerate.generate_and_store") as store, pytest.raises(RuntimeError):
        regenerate(state)

    store.assert_not_called()


def test_regenerate_preserves_visual_direction_and_objects_in_rebuilt_prompt():
    ana = Character(char_id="c0", name="Ana", description=CharacterDescription(species="girl"))
    sword = StoryObject(obj_id="obj0", name="wooden sword", description="a wooden sword")
    prompt = build_prompt(
        "Ana ran.",
        ["c0"],
        [ana],
        None,
        None,
        ["obj0"],
        [sword],
        "Ana runs right holding the wooden sword.",
    )
    scene = Scene(
        scene_id="s0",
        text_excerpt="Ana ran.",
        characters_present=["c0"],
        objects_present=["obj0"],
        visual_direction="Ana runs right holding the wooden sword.",
        prompt=prompt,
        attempts=[Attempt(image_ref="job-1/s0-1.png", prompt=prompt, failure_reasons=[FailureReason.wrong_colour], passed=False)],
    )
    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        characters=[ana],
        objects=[sword],
        style=Style(),
        scenes=[scene],
    )
    with patch("pipeline.regenerate.correct_prompt", return_value="corrected prompt") as mock_correct, \
         patch("pipeline.regenerate.generate_and_store", return_value=("job-1/s0-2.png", True)):
        regenerate(state)

    mock_correct.assert_called_once()
    assert "Visible objects:\nwooden sword, a wooden sword" in mock_correct.call_args.args[0]
    assert "Visual direction: Ana runs right holding the wooden sword." in mock_correct.call_args.args[0]


def test_regenerate_rejects_scene_with_empty_visual_direction():
    scene = Scene(
        scene_id="s0",
        text_excerpt="Ana ran.",
        characters_present=["c0"],
        visual_direction="",
        attempts=[_failed_attempt()],
    )
    state = _state([scene])
    with patch("pipeline.regenerate.generate_and_store"):
        with pytest.raises(ValueError, match="has no visual_direction"):
            regenerate(state)


def test_regenerate_passes_stored_scene_contradictions_and_preserves_refs():
    attempt = _failed_attempt(
        reasons=[FailureReason.wrong_colour],
    ).model_copy(
        update={"scene_contradictions": ["The wooden sword is missing."]}
    )
    state = _state([_scene(attempts=[attempt])])
    with patch("pipeline.regenerate.correct_prompt", return_value="corrected") as correct, patch(
        "pipeline.regenerate.generate_and_store",
        return_value=("story/s0-2.png", True),
    ) as store:
        regenerate(state)

    assert correct.call_args.kwargs["scene_contradictions"] == [
        "The wooden sword is missing."
    ]
    assert store.call_args.args[4] == ["job-1/ref-c0.png"]


# --- attempt 3 (spend-and-retry-economics §6.10, invariant 4) ---

def test_attempt_3_accumulates_both_correction_rounds_and_uses_the_dash_3_path():
    """spend-and-retry-economics §6.10 + invariant 4: "Attempt 3 corrects from attempt 2's
    prompt, preserving the first correction and appending the newest one."

    Round 1 corrected an identity failure, so attempt 2's prompt already carries
    IDENTITY_CLAUSE. Round 2 corrects an anatomy failure. Because `regenerate` bases the
    correction on `last.prompt`, attempt 3 must carry BOTH clauses — that accumulation is the
    whole mechanism, and nothing else in the suite pins it.
    """
    round_1 = _failed_attempt(verdict=_verdict(same=False))
    round_2 = Attempt(
        image_ref="job-1/s0-2.png",
        prompt=f"the original prompt. {IDENTITY_CLAUSE}",
        vlm_verdict=_verdict(same=True, anatomy=False),
        failure_reasons=[],
        passed=False,
    )
    state = _state([_scene([round_1, round_2])])

    with patch(
        "pipeline.regenerate.generate_and_store", return_value=("job-1/s0-3.png", True)
    ) as store:
        result = regenerate(state)

    third = result["scenes"][0].attempts[-1]
    assert IDENTITY_CLAUSE in third.prompt, "round 1's correction was dropped"
    assert ANATOMY_CLAUSE in third.prompt, "round 2's correction was not appended"

    # The per-attempt Storage path is derived from the attempt count (CC-10), so attempt 3
    # lands on `-3.png` and re-pays nothing on resume.
    assert store.call_args.args[3] == 3
    assert third.image_ref == "job-1/s0-3.png"

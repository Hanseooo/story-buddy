"""Integration regression test for LangGraph pipeline ordering and retry semantics.

Proves the unchanged graph shape, node/edge execution order, moderation order,
and three-attempt retry economics using deterministic fakes for non-scene nodes
and real `generate_scene` / `regenerate` execution.
"""
from unittest.mock import patch
from langgraph.checkpoint.memory import MemorySaver

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Cost,
    FailureReason,
    Input,
    ModerationResult,
    Scene,
    StoryMemory,
    Style,
    VlmVerdict,
)
from pipeline.generate_scene import generate_scene
from pipeline.prompt_optimizer import ANATOMY_CLAUSE
from pipeline.regenerate import regenerate
import pipeline.graph as graph_module


def test_three_attempt_graph_ordering_and_clean_base_retries():
    events: list[str] = []
    generated_prompts: list[str] = []

    def fake_input_gate(state: StoryMemory) -> dict:
        events.append("input_gate")
        return {
            "input": state.input.model_copy(
                update={"moderation": ModerationResult(passed=True, categories=[])}
            )
        }

    def fake_analyze(state: StoryMemory) -> dict:
        events.append("analyze")
        char = Character(
            char_id="c0",
            name="Leo",
            description=CharacterDescription(
                species="human",
                colours=["orange shirt"],
                body_features=["curly hair"],
                clothing=["blue jeans"],
            ),
        )
        return {"characters": [char]}

    def fake_segment(state: StoryMemory) -> dict:
        events.append("segment")
        scene = Scene(
            scene_id="s0",
            text_excerpt="Leo ran across the field.",
            characters_present=["c0"],
            visual_direction="Leo runs right across a field. Viewpoint: eye-level. Framing: wide shot.",
            attempts=[],
        )
        return {"scenes": [scene]}

    def fake_char_bible(state: StoryMemory) -> dict:
        events.append("char_bible")
        updated_chars = [
            c.model_copy(update={"canonical_ref_image": "story/ref-c0.png"})
            for c in state.characters
        ]
        return {"characters": updated_chars}

    def fake_char_ref_mod(state: StoryMemory) -> dict:
        events.append("char_ref_mod")
        updated_chars = [
            c.model_copy(update={"ref_moderation_status": "passed"})
            for c in state.characters
        ]
        return {"characters": updated_chars}

    def fake_reveal(state: StoryMemory) -> dict:
        events.append("reveal")
        return {}

    def wrapped_generate_scene(state: StoryMemory) -> dict:
        events.append("generate_scene")
        return generate_scene(state)

    def wrapped_regenerate(state: StoryMemory) -> dict:
        events.append("regenerate")
        return regenerate(state)

    def fake_consistency_check(state: StoryMemory) -> dict:
        events.append("consistency_check")
        scene = next(s for s in state.scenes if s.final_image_ref is None)
        attempt_n = len(scene.attempts)
        if attempt_n == 1:
            updated_attempts = [
                scene.attempts[0].model_copy(
                    update={
                        "vlm_verdict": VlmVerdict(differences_observed="diff 1", same_character=False),
                        "failure_reasons": [FailureReason.wrong_colour],
                        "passed": False,
                    }
                )
            ]
            return {"scenes": [scene.model_copy(update={"attempts": updated_attempts})]}
        elif attempt_n == 2:
            updated_attempts = [
                scene.attempts[0],
                scene.attempts[1].model_copy(
                    update={
                        "vlm_verdict": VlmVerdict(
                            differences_observed="diff 2",
                            same_character=True,
                            anatomy_intact=False,
                        ),
                        "failure_reasons": [FailureReason.wrong_clothing],
                        "passed": False,
                    }
                ),
            ]
            return {"scenes": [scene.model_copy(update={"attempts": updated_attempts})]}
        else:
            updated_attempts = [
                scene.attempts[0],
                scene.attempts[1],
                scene.attempts[2].model_copy(
                    update={
                        "vlm_verdict": VlmVerdict(
                            differences_observed="",
                            same_character=True,
                            anatomy_intact=True,
                        ),
                        "failure_reasons": [],
                        "passed": True,
                    }
                ),
            ]
            return {
                "scenes": [
                    scene.model_copy(
                        update={
                            "attempts": updated_attempts,
                            "final_image_ref": scene.attempts[2].image_ref,
                        }
                    )
                ]
            }

    def fake_output_mod(state: StoryMemory) -> dict:
        events.append("output_mod")
        updated_scenes = [
            s.model_copy(update={"moderation_status": "passed"})
            for s in state.scenes
        ]
        return {"scenes": updated_scenes}

    def fake_compose(state: StoryMemory) -> dict:
        events.append("compose")
        return {}

    def fake_generate_and_store(prompt, story_id, scene_id, attempt_n, ref_paths):
        generated_prompts.append(prompt)
        return f"story/s0-{attempt_n}.png", True

    initial_state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="test-story-1",
        classroom_id="test-classroom",
        profile_id="test-profile",
        input=Input(raw_text="Leo ran across the field.", redacted_text="Leo ran across the field."),
        style=Style(prompt_fragment="flat cel-shaded cartoon"),
        cost=Cost(),
    )

    with patch.object(graph_module, "input_gate", fake_input_gate), \
         patch.object(graph_module, "analyze", fake_analyze), \
         patch.object(graph_module, "segment", fake_segment), \
         patch.object(graph_module, "char_bible", fake_char_bible), \
         patch.object(graph_module, "char_ref_mod", fake_char_ref_mod), \
         patch.object(graph_module, "reveal", fake_reveal), \
         patch.object(graph_module, "generate_scene", wrapped_generate_scene), \
         patch.object(graph_module, "regenerate", wrapped_regenerate), \
         patch.object(graph_module, "consistency_check", fake_consistency_check), \
         patch.object(graph_module, "output_mod", fake_output_mod), \
         patch.object(graph_module, "compose", fake_compose), \
         patch("pipeline.generate_scene.generate_and_store", side_effect=fake_generate_and_store), \
         patch("pipeline.regenerate.generate_and_store", side_effect=fake_generate_and_store):

        app = graph_module.build_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-thread-1"}}
        final_state_dict = app.invoke(initial_state, config=config)

    expected_events = [
        "input_gate",
        "analyze",
        "segment",
        "char_bible",
        "char_ref_mod",
        "reveal",
        "generate_scene",
        "consistency_check",
        "regenerate",
        "consistency_check",
        "regenerate",
        "consistency_check",
        "output_mod",
        "compose",
    ]
    assert events == expected_events

    scene = final_state_dict["scenes"][0]
    assert len(scene.attempts) == 3
    assert final_state_dict["cost"].image_count == 3
    assert final_state_dict["cost"].regen_count == 2
    assert scene.final_image_ref == "story/s0-3.png"
    assert scene.moderation_status == "passed"

    # Verify clean base and latest verdict only
    clean_base = scene.prompt
    assert clean_base is not None
    assert scene.attempts[0].prompt == clean_base
    assert generated_prompts[0] == clean_base

    # Attempt 2 corrected for wrong_colour from attempt 1
    assert "match the reference's exact colours: orange shirt" in generated_prompts[1]
    assert generated_prompts[1] == scene.attempts[1].prompt

    # Attempt 3 corrected for wrong_clothing and anatomy from attempt 2 only, deriving from clean_base
    assert "match this clothing exactly: blue jeans" in generated_prompts[2]
    assert ANATOMY_CLAUSE in generated_prompts[2]
    assert "match the reference's exact colours" not in generated_prompts[2]
    assert generated_prompts[2] == scene.attempts[2].prompt

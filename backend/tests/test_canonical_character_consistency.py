from unittest.mock import MagicMock, patch

from app.config import STYLE_PRESETS
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, RefVerdict, StoryMemory
from pipeline.analyze import StoryAnalysis, analyze
from pipeline.char_bible import mint_reference
import pipeline.graph as graph_module
from pipeline.prompt_optimizer import build_prompt
from pipeline.reveal import _project_reveal


def _robot_analysis() -> StoryAnalysis:
    return StoryAnalysis.model_validate({
        "characters": [{
            "name": "Leo",
            "description": {
                "species": "robot",
                "body_plan": "small box-shaped metal body with short hinged limbs and a blue chest button",
                "face_or_interface": "rounded metal head with two circular blue LED lenses",
                "is_humanoid": False,
                "colours": ["silver"],
                "body_features": ["blue chest button", "short hinged limbs"],
                "clothing": [],
            },
        }],
        "locations": [{
            "name": "the room",
            "description": "a small room with a wooden floor",
        }],
        "objects": [],
        "timeline": [{
            "order": 0,
            "summary": "Leo rolls across the room.",
        }],
    })


def _state(
    raw_text: str = "Andres met a small robot named Leo. Leo rolled across the room.",
    redacted_text: str = "Andres met a small robot named Leo. Leo rolled across the room.",
) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="t1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text=raw_text, redacted_text=redacted_text),
    )


def test_redacted_name_stays_in_text_identity_but_not_fresh_reference_prompts():
    state = _state(
        raw_text="Andres met a small robot named Leo. Leo rolled across the room.",
        redacted_text="Andres met a small robot named Leo. Leo rolled across the room.",
    )
    analysis = _robot_analysis()

    with patch("pipeline.analyze.structured_text", return_value=analysis) as structured:
        analyzed = analyze(state)

    character = analyzed["characters"][0]
    assert structured.call_count == 1
    assert "Leo" in structured.call_args.args[0]
    assert character.name == "Leo"
    assert character.char_id == "c0"
    assert character.description.body_features[:2] == [
        "small box-shaped metal body with short hinged limbs and a blue chest button",
        "rounded metal head with two circular blue LED lenses",
    ]

    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", return_value=b"reference-bytes") as draw, \
         patch("pipeline.char_bible.judge", return_value=RefVerdict(
             differences_observed="",
             contradictions=[],
             matches_description=True,
             attributes_present=[
                 "robot",
                 "silver",
                 "small box-shaped metal body with short hinged limbs and a blue chest button",
                 "rounded metal head with two circular blue LED lenses",
             ],
         )) as judge, \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        path, _, draws = mint_reference(
            character.description,
            character.name,
            STYLE_PRESETS["gouache"],
            state.story_id,
            character.char_id,
        )

    draw_prompt = draw.call_args.args[0]
    judge_prompt = judge.call_args.args[0]
    assert draws == 1
    assert draw.call_count == 1
    assert judge.call_count == 1
    assert "Leo" not in draw_prompt
    assert "Leo" not in judge_prompt
    for value in character.description.body_features[:2]:
        assert value in draw_prompt
        assert value in judge_prompt

    referenced = character.model_copy(update={"canonical_ref_image": path})
    reveal_state = state.model_copy(update={"characters": [referenced]})
    reveal_payload = _project_reveal(reveal_state)
    assert reveal_payload["characters"][0]["char_id"] == "c0"
    assert reveal_payload["characters"][0]["name"] == "Leo"
    assert reveal_payload["characters"][0]["image_path"] == path

    scene_prompt = build_prompt(
        ["c0"],
        [referenced],
        STYLE_PRESETS["gouache"],
        visual_direction="Leo rolls across the room.",
    )
    assert "Leo" in scene_prompt


def test_canonical_consistency_does_not_add_a_graph_node():
    compiled = graph_module.build_graph()
    runtime_nodes = set(compiled.get_graph().nodes) - {"__start__", "__end__"}

    assert runtime_nodes == {
        "input_gate",
        "analyze",
        "segment",
        "char_bible",
        "char_ref_mod",
        "reveal",
        "generate_scene",
        "consistency_check",
        "regenerate",
        "output_mod",
        "compose",
    }

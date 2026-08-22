"""Test-side ground truth manifest for the 17 visual pilot fixture pairs.

Invariants (Ticket 01, spec docs/specs/judge-finetune.md §4, ADR-028):
1. This manifest is strictly test-side and must never leak into DB columns,
   storage paths, or frontend API payloads.
2. All failure reasons must strictly belong to the frozen 7-item taxonomy.
"""

from typing import Any

# Frozen 7-item taxonomy from ADR-028 / judge-finetune.md
TAXONOMY = [
    "wrong_colour",
    "wrong_species",
    "wrong_body_feature",
    "wrong_clothing",
    "wrong_style",
    "different_face",
    "character_absent",
]

EXPECTED_PILOT_LABELS: dict[str, dict[str, Any]] = {
    "case_01_puppy_pose": {
        "same_character": True,
        "failure_reasons": [],
        "anatomy_intact": True,
        "text_free": True,
        "description": "PASS: Golden puppy with red collar; pose/angle variation across park scenery.",
    },
    "case_02_robot_lighting": {
        "same_character": True,
        "failure_reasons": [],
        "anatomy_intact": True,
        "text_free": True,
        "description": "PASS: Blue cyclops robot; lighting and lab background variation.",
    },
    "case_03_dragon_action": {
        "same_character": True,
        "failure_reasons": [],
        "anatomy_intact": True,
        "text_free": True,
        "description": "PASS: Emerald dragon kid with purple scales; sitting eating apple action.",
    },
    "case_04_fox_color": {
        "same_character": False,
        "failure_reasons": ["wrong_colour"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (wrong_colour): Orange fox rendered with neon purple coat in scene.",
    },
    "case_05_bird_color": {
        "same_character": False,
        "failure_reasons": ["wrong_colour"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (wrong_colour): Red cardinal bird rendered with bright emerald feathers.",
    },
    "case_06_bear_clothing": {
        "same_character": False,
        "failure_reasons": ["wrong_clothing"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (wrong_clothing): Brown bear in blue sailor suit rendered in astronaut suit.",
    },
    "case_07_duck_clothing": {
        "same_character": False,
        "failure_reasons": ["wrong_clothing"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (wrong_clothing): Yellow duck in yellow raincoat rendered in royal red cape.",
    },
    "case_08_alien_body_feature": {
        "same_character": False,
        "failure_reasons": ["wrong_body_feature"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (wrong_body_feature): 2-eyed purple alien rendered with 4 eyes.",
    },
    "case_09_bunny_body_feature": {
        "same_character": False,
        "failure_reasons": ["wrong_body_feature"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (wrong_body_feature): Long-eared white rabbit rendered with missing ears.",
    },
    "case_10_cat_face": {
        "same_character": False,
        "failure_reasons": ["different_face"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (different_face): Cute round anime kitten face rendered as grumpy wrinkled old cat.",
    },
    "case_11_boy_face": {
        "same_character": False,
        "failure_reasons": ["different_face"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (different_face): Freckled boy face rendered with sharp angular jaw and narrow eyes.",
    },
    "case_12_dog_to_bear_species": {
        "same_character": False,
        "failure_reasons": ["wrong_species"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (wrong_species): Golden retriever dog wearing bandana rendered as grizzly bear.",
    },
    "case_13_girl_absent": {
        "same_character": False,
        "failure_reasons": ["character_absent"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (character_absent): Little girl on playroom beanbag chair missing completely from scene.",
    },
    "case_14_lion_vector_to_pixel_style": {
        "same_character": False,
        "failure_reasons": ["wrong_style"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (wrong_style): Smooth vector lion rendered as coarse 8-bit pixel art sprite.",
    },
    "case_15_turtle_sketch_style": {
        "same_character": False,
        "failure_reasons": ["wrong_style"],
        "anatomy_intact": True,
        "text_free": True,
        "description": "FAIL (wrong_style): Pastel watercolor turtle rendered as neon inverted chalkboard sketch.",
    },
    "case_16_penguin_shadow_ambiguous": {
        "same_character": True,
        "failure_reasons": [],
        "anatomy_intact": True,
        "text_free": True,
        "description": "PASS / Ambiguous: Penguin with red scarf in dramatic nighttime torchlight shadow.",
    },
    "case_17_squirrel_accessory_ambiguous": {
        "same_character": True,
        "failure_reasons": [],
        "anatomy_intact": True,
        "text_free": True,
        "description": "PASS / Ambiguous: Squirrel holding acorn/pinecone with minor backpack accessory variance.",
    },
}

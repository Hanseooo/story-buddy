# ADR-043 — Preventing Hybrid Characters via `is_humanoid` Contract Signal and Conditional Negative Prompting

**Status:** Accepted (2026-08-17; owner approved) · **amends ADR-041's deferred `is_person` persistence** · **amends ADR-028's reference generation** · **amends ADR-035/040's prompt construction** · preserves ADR-011, ADR-023 single-int versioning

**Context:** 

When children create stories with non-human characters (e.g., Bolt the robot, animals, celestial bodies, vehicles), the image generator (Qwen-Image via fal.ai) frequently hallucinates human child faces, heads, hair, and flesh onto the non-human bodies. 

In a reproduction with the story of Bolt the robot:
- ADR-041 successfully removed character names (`Leo`/`Bolt`) and supplied structured morphology (`smooth unbroken front surface`).
- Commit `19b83f1` removed the anti-pattern `"give it no human body and no human face"` from positive prompts in `char_bible.py`.
- Despite these changes, all 3 canonical reference draws for Bolt in production testing produced a robot body with a literal child's head / human face.

Investigation revealed three compounding root causes:
1. **Positive Prompt Keyword Priming:** `REFERENCE_PROMPT` in `char_bible.py` unconditionally contained `"If the character is not a person, draw it as the kind of thing it actually is. For a human or humanoid character, show age-appropriate clothing covering the torso."` Text encoders in diffusion models lack boolean counterfactual logic and attend heavily to keywords like `person`, `human`, `humanoid`, `clothing`, and `torso`, biasing the generation toward human children.
2. **Missing Negative Suppression Channel:** `REFERENCE_NEGATIVE` suppressed background and framing, but had zero tokens suppressing human features (`human face, human body, human skin, flesh, person`).
3. **Discarded Structural Signal:** `analyze.py` already extracted `is_humanoid: bool` in its transient boundary schema, but discarded it when instantiating `CharacterDescription` because the Pydantic contract in `contracts/story_memory.py` had no `is_humanoid` field. Consequently, `char_bible.py` and downstream nodes could not branch on character humanity.
4. **Scene Prompt Token Contamination:** `prompt_optimizer.py` still retained `NON_HUMAN_CLAUSE` containing `"give it no human body and no human face"`, uttering the forbidden tokens in positive scene prompts.

ADR-041 previously deferred persisting `is_person` or morphology flags until the transient approach measurably failed. The empirical failure is now verified with clear photographic evidence (`Screenshot 2026-08-17 202504.png`).

**Decision:**

1. **Add `is_humanoid: bool = True` to `CharacterDescription` in `backend/contracts/story_memory.py`.**
   - Defaulting to `True` preserves backward compatibility so that existing serialized checkpoints in Postgres deserialize cleanly without migration errors or schema version bumps.
   - `CharacterDescription.without_placeholders()` and `filtered_description()` preserve `is_humanoid` across projections.

2. **Preserve `is_humanoid` across the Analyzer Seam.**
   - In `backend/pipeline/analyze.py`, `ExtractedDescription` retains `is_humanoid: bool` as a required LLM extraction field.
   - `analyze()` removes `"is_humanoid"` from its `model_dump(exclude=...)` set, persisting the value directly into `CharacterDescription`.

3. **Branch Positive and Negative Prompts in Canonical Reference Generation (`char_bible.py`).**
   - **Positive Prompt:** If `description.is_humanoid` is `False`, omit the torso clothing clause (`"Show age-appropriate clothing covering the torso."`) and omit any mention of "person" or "humanoid" from `reference_prompt()`.
   - **Negative Prompt:** Define `NON_HUMAN_NEGATIVE`:
     `"human, human face, human body, person, human head, human skin, flesh, child face, boy, girl, human hands, human fingers"`
     When `not description.is_humanoid`, append `NON_HUMAN_NEGATIVE` to `negative_extra` in `mint_reference()` and `_mint_targeted()`.
   - Positive and negative prompts are kept orthogonal: negative tokens never include animal or object traits, clothing, or eyes/mouth/face.

4. **Clean Positive Scene Prompts and Maintain Mixed-Scene Safety (`prompt_optimizer.py` & `generate_scene.py`).**
   - Delete `NON_HUMAN_CLAUSE` from `build_prompt()`. Scene identity is fully anchored by the reference image roll (`Image 1 is ...`) and populated visual axes.
   - Do **NOT** inject `NON_HUMAN_NEGATIVE` into mixed-character scenes containing any human character (`is_humanoid == True`), as global negative prompts would distort the human subjects. Consistency for non-humans in mixed scenes relies on their clean canonical reference via `edit_image`.

5. **No Second Prompt-Writing LLM.**
   - `analyze` remains the sole authority over character morphology. No dynamic LLM prompt generation is inserted into the scene loop (preserving ADR-041 and Ponytail simplicity).

**Consequences:**

- Non-human characters (robots, animals, inanimate objects, vehicles) are shielded from human facial and anatomical hallucinations during canonical reference creation through both positive prompt decluttering and active negative prompt suppression.
- Once a clean non-human reference image is minted and vetted, `qwen-image-edit` preserves its non-human morphology in downstream scene generation without needing risky scene-wide human bans in mixed scenes.
- Backwards compatibility is 100% maintained: old checkpoint blobs deserialize with `is_humanoid=True`, avoiding runtime breaks on resume.
- Zero added API calls, zero added latency, and zero new infrastructure dependencies.

**Alternatives:**

- **Dynamic LLM scene prompt writer.** Rejected (violates ADR-041, adds latency and per-scene token cost, introduces lexical drift across pages).
- **Scene-wide negative human ban for all scenes with any non-human.** Rejected because negative prompts operate on the whole canvas and would mutilate human characters (e.g. Jamie) in mixed scenes.
- **Rely only on positive prompt instructions.** Rejected because diffusion models lack counterfactual boolean parsing and empirically failed across all 3 draws.

**Escape hatch:** If specific fantasy creature classifications (e.g. centaurs or mermaids) show unexpected rendering artifacts, classification rules in `analyze.py`'s extraction prompt can be calibrated without altering the underlying contract or pipeline topology.

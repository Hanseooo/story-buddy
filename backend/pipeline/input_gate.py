from contracts.story_memory import Input, ModerationResult, StoryMemory


def input_gate(state: StoryMemory) -> dict:
    # ponytail: stub — Phase 2 moderation-stack replaces with real Qwen3Guard-Gen + Presidio.
    # It exists now so the graph shape is already correct: Phase 2 is a single-file swap,
    # not a topology change (spec §9).
    return {
        "input": Input(
            raw_text=state.input.raw_text,
            redacted_text=state.input.raw_text,
            moderation=ModerationResult(passed=True),
        )
    }

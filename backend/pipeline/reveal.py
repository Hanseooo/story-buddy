"""The character reveal (spec `docs/specs/kid-flow-pause-lifecycle.md`, ADR-029).

Performs no effect. Its entire body is a pure projection and one `interrupt()` call — no
provider call, no upload, no write outside its partial return (invariant 9). That property is
the reason it is a dedicated node rather than folded into `char_bible`: LangGraph re-executes a
resumed node from the top, so an `interrupt()` inside `char_bible` would redraw every reference
on each confirm.
"""
from langgraph.types import interrupt

from app.config import settings
from contracts.story_memory import Character, ReferenceRetry, StoryMemory
from pipeline.prompt_optimizer import filtered_description, permitted_words

MAX_RETRY_TAPS = 3


def _chips(character: Character, style_fragment: str | None) -> list[str]:
    """Described attributes minus what the judge already found (spec §4.3). `notes` is free
    prose, not an attribute, and is never offered as a chip. Never empty (two fallbacks below) —
    an empty chip list would dead-end the "try again" button (invariant 4)."""
    verdict = character.ref_verdict
    # ADR-035 surface 5. A chip promises that tapping it buys a redraw that could plausibly fix
    # the attribute. Under `comic` ("no glow") a tap on "glowing" spends one of three ADR-029 taps
    # and one paid draw on something the style guarantees will not change. Filtering here is also
    # what lets `char_bible._mint_targeted` trust `retry.attribute`.
    description = filtered_description(character.description, style_fragment)
    axes = {
        # `species` is the one axis `filtered_description` deliberately leaves alone (Decision 2),
        # so it is filtered here instead — chip scope only. It was the live leak: a chip becomes
        # `char_bible._mint_targeted`'s explicit emphasis clause, so a species like "glowing orb"
        # would walk straight back into a draw prompt under "no glow" on a fresh job.
        "species": permitted_words(description.species, style_fragment),
        "colours": description.colours,
        "body_features": description.body_features,
        "clothing": description.clothing,
    }
    full_axis_list = [
        v for value in axes.values()
        if value is not None
        for v in ([value] if isinstance(value, str) else value)
        if v
    ]
    if not full_axis_list:
        return ["overall physical appearance"]
    # ADR-034: the same acceptance predicate `char_bible` gates on, for the same reason. This
    # branch means "the reference passed" — if it read `matches_description` while the gate read
    # `contradictions`, a reference accepted by one and rejected by the other would offer the
    # child the wrong chips. Keep the two in lockstep.
    if verdict is None or not verdict.contradictions:
        return full_axis_list
    present = {a.lower() for a in verdict.attributes_present}
    missing = [axis for axis in full_axis_list if axis.lower() not in present]
    return missing or full_axis_list


def _project_reveal(state: StoryMemory) -> dict:
    """Pure — no effect, no mocks needed to test it. The worker writes this dict verbatim to
    `jobs.reveal` (spec §4.2)."""
    style_fragment = state.style.prompt_fragment or settings.default_style_fragment
    characters = [
        {
            "char_id": c.char_id,
            "name": c.name,
            "image_path": c.canonical_ref_image,   # durable path, never a signed URL (ADR-006)
            "chips": _chips(c, style_fragment),
        }
        for c in state.characters
        if c.canonical_ref_image is not None
    ]
    return {"characters": characters, "taps_left": MAX_RETRY_TAPS - state.cost.ref_retry_count}


def reveal(state: StoryMemory) -> dict:
    """A book with nothing to reveal must not pause (spec §4.1) — otherwise a book from which
    `analyze` extracted no characters parks a child in front of a confirm button that confirms
    nothing, and the job sits in `awaiting_confirm` forever (no client renders that screen).

    An unrecognised resume payload is treated as a confirm, not an error: this node fails toward
    progress. Payload validation is the endpoint's job (spec §4.9) — by the time a resume reaches
    here it has already been checked against the row.
    """
    payload = _project_reveal(state)
    if not payload["characters"]:
        return {}
    answer = interrupt(payload)
    if isinstance(answer, dict) and answer.get("action") == "try_again":
        return {"reference_retry": ReferenceRetry(char_id=answer["char_id"], attribute=answer["attribute"])}
    return {}

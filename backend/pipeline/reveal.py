"""The character reveal (spec `docs/specs/kid-flow-pause-lifecycle.md`, ADR-029).

Performs no effect. Its entire body is a pure projection and one `interrupt()` call — no
provider call, no upload, no write outside its partial return (invariant 9). That property is
the reason it is a dedicated node rather than folded into `char_bible`: LangGraph re-executes a
resumed node from the top, so an `interrupt()` inside `char_bible` would redraw every reference
on each confirm.
"""
from langgraph.types import interrupt

from contracts.story_memory import Character, ReferenceRetry, StoryMemory

MAX_RETRY_TAPS = 3


def _chips(character: Character) -> list[str]:
    """Described attributes minus what the judge already found (spec §4.3). `notes` is free
    prose, not an attribute, and is never offered as a chip. Never empty (two fallbacks below) —
    an empty chip list would dead-end the "try again" button (invariant 4)."""
    verdict = character.ref_verdict
    description = character.description
    axes = {
        "species": description.species,
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
        return [character.name]
    if verdict is None or verdict.matches_description:
        return full_axis_list
    present = {a.lower() for a in verdict.attributes_present}
    missing = [axis for axis in full_axis_list if axis.lower() not in present]
    return missing or full_axis_list


def _project_reveal(state: StoryMemory) -> dict:
    """Pure — no effect, no mocks needed to test it. The worker writes this dict verbatim to
    `jobs.reveal` (spec §4.2)."""
    characters = [
        {
            "char_id": c.char_id,
            "name": c.name,
            "image_path": c.canonical_ref_image,   # durable path, never a signed URL (ADR-006)
            "chips": _chips(c),
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

"""Shared guard for the one state-write rule that has no enforcement in the graph itself.

Only `scenes` has a reducer (ADR-024). Every other `StoryMemory` field is replaced outright by
a node's partial return, so a node that returns a whole sub-model must carry forward every
field it is not deliberately changing — otherwise the pydantic defaults on that model silently
overwrite live data, with no error anywhere.

This is not hypothetical. `input_gate` rebuilt `Input(...)` from scratch in all four of its
return paths, resetting `word_count` to 0 and `truncated` to False on every job that has ever
run; prod job 4cb31620 (2026-08-11) reported `word_count=0` for a 79-word story. `char_bible`
carries three separate comments warning about this exact hazard ("`characters` has NO reducer,
so a partial return REPLACES the list", "`cost` has no reducer either — copy and bump, never
rebuild from zero"). Comments are precisely what failed here, which is why this is a callable.

Use it in any node test where the node returns a whole sub-model rather than a scalar.
"""
from pydantic import BaseModel

# `0`/`False`/`""`/`[]` are what pydantic defaults look like, so they are what a dropped field
# looks like. A node that deliberately sets a field to one of these is indistinguishable from a
# node that dropped it — accepted: the false negative is silent, the false positive is not, and
# only the false positive would train someone to ignore this assert.
_DEFAULTISH = (None, 0, False, "", [], {})


def assert_no_fields_dropped(before, patch: dict) -> None:
    """`before` is the state the node was called with, `patch` is the dict it returned."""
    for key, new in patch.items():
        old = getattr(before, key, None)
        if not (isinstance(old, BaseModel) and isinstance(new, BaseModel)):
            continue  # scalars and lists: nothing to carry forward
        dropped = [
            name for name, value in old.model_dump().items()
            if value not in _DEFAULTISH and getattr(new, name, None) in _DEFAULTISH
        ]
        assert not dropped, (
            f"node dropped {dropped} from `{key}`. `{key}` has no reducer, so returning it "
            f"REPLACES the whole model and the defaults win. Build the return with "
            f"`state.{key}.model_copy(update=...)`, never `{type(new).__name__}(...)`."
        )

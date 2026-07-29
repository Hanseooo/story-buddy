"""Phase 0 provisional subset of the Story Memory contract (MASTER_SPEC §3).
Full field-level schema is frozen in the Phase 1 `story-memory-contract` spec — do not extend
this file with Phase 1 fields; add them there instead.
"""
from typing import Optional, TypedDict


class JobState(TypedDict):
    job_id: str
    input_text: str
    caption: Optional[str]
    image_path: Optional[str]
    stage: str

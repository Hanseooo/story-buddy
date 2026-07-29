"""The frozen Story Memory contract (spec `docs/specs/story-memory-contract.md`, ADR-023).

Simultaneously (a) the inter-module data contract, (b) the LangGraph runtime state, and
(c) the Postgres checkpoint blob. Everything is Optional / default_factory unless a value
exists at job creation — this is a mostly-optional container, NOT a mid-run completeness
validator. Real per-field validation lives in each node's structured-output sub-schema at
its LLM boundary (ADR-002).

Read ADR-023 and ADR-028 before changing anything here.
"""
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field

CURRENT_SCHEMA_VERSION = 1


# --- Closed taxonomy: ONE home, imported by judge schema, regen-controller, finetune tooling ---
class FailureReason(str, Enum):
    wrong_colour       = "wrong_colour"
    wrong_species      = "wrong_species"
    wrong_body_feature = "wrong_body_feature"
    wrong_clothing     = "wrong_clothing"
    wrong_style        = "wrong_style"
    different_face     = "different_face"
    character_absent   = "character_absent"


# --- Analysis products (analyze / char_bible) ---
class CharacterDescription(BaseModel):
    # minimal, aligned to the failure-reason axes; refined by `character-bible` (§8, additive)
    species: Optional[str] = None
    colours: list[str] = Field(default_factory=list)
    body_features: list[str] = Field(default_factory=list)
    clothing: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


# --- Reference acceptance verdict (ADR-028 Decision 3). Reason-then-score, like every judge call. ---
class RefVerdict(BaseModel):
    differences_observed: str          # MUST be declared before matches_description (ADR-004)
    matches_description: bool
    attributes_present: list[str] = Field(default_factory=list)   # best-of key when all draws fail


class Character(BaseModel):
    char_id: str
    name: str
    description: CharacterDescription = Field(default_factory=CharacterDescription)
    canonical_ref_image: Optional[str] = None       # durable Storage PATH, never a signed URL
    ref_moderation_status: Optional[str] = None
    ref_verdict: Optional[RefVerdict] = None        # ADR-028: the reference is checked, not assumed


class Location(BaseModel):     # minimal; refined by `story-analyzer` (§8, additive)
    loc_id: str
    name: str
    description: Optional[str] = None


class StoryObject(BaseModel):  # minimal; refined by `story-analyzer` (§8, additive)
    obj_id: str
    name: str
    description: Optional[str] = None


class TimelineEvent(BaseModel):  # minimal; refined by `story-analyzer` (§8, additive)
    order: int
    summary: str


# --- Input gate ---
class ModerationResult(BaseModel):  # minimal; refined by `moderation-stack` Phase 2 (§8, additive)
    passed: bool = False
    categories: list[str] = Field(default_factory=list)


class Input(BaseModel):
    raw_text: str
    redacted_text: Optional[str] = None   # CC-2: redacted_text is what downstream nodes consume
    word_count: int = 0
    truncated: bool = False
    moderation: Optional[ModerationResult] = None


# --- Style (ADR-007, ADR-022) ---
class Style(BaseModel):
    style_preset_id: Optional[str] = None
    prompt_fragment: Optional[str] = None


# --- Consistency verdict (ADR-004). FIELD ORDER IS LOAD-BEARING. ---
class VlmVerdict(BaseModel):
    differences_observed: str          # MUST be declared before same_character (ADR-004 amendment)
    same_character: bool
    attributes_present: list[str] = Field(default_factory=list)
    style_match: bool = False
    anatomy_intact: bool = True        # ADR-028: merged, missing or duplicated body parts. Declared
                                       # LAST so the ADR-004 ordering above is untouched. Additive →
                                       # no schema_version bump. Best-of (ADR-010) ranks
                                       # lexicographically: same_character → anatomy_intact → style_match.
                                       # ponytail: bool, not a score — widen only if a measured tie forces it.


class Attempt(BaseModel):
    image_ref: str                     # durable Storage PATH
    prompt: Optional[str] = None       # the prompt THIS attempt used; regeneration corrects it (ADR-010),
                                       # so Scene.prompt alone loses per-attempt provenance (CC-5 tracing)
    vlm_verdict: Optional[VlmVerdict] = None
    failure_reasons: list[FailureReason] = Field(default_factory=list)  # closed set; extras rejected
    passed: bool = False


class Scene(BaseModel):
    scene_id: str
    text_excerpt: str
    caption: Optional[str] = None
    characters_present: list[str] = Field(default_factory=list)  # char_ids
    prompt: Optional[str] = None
    attempts: list[Attempt] = Field(default_factory=list)        # no reducer — appended by the owning node (ADR-024, §8)
    final_image_ref: Optional[str] = None                        # best-of (ADR-010); durable path
    regeneration_count: int = 0
    moderation_status: Optional[str] = None


# --- LangGraph reducer (ADR-024): upsert-by-scene_id, replace-matching, keep-others ---
# SCENE LIST ORDER IS THE CONTRACT: dict semantics keep an upserted scene in its original
# slot and append new ones, so order == segmentation order and survives the JSON round-trip.
# The ADR-024 loop ("first Scene whose final_image_ref is None") and page sequence both rely
# on this. There is deliberately no Scene.order field — it would be a second source of truth.
def upsert_scenes(current: list["Scene"], update: list["Scene"]) -> list["Scene"]:
    by_id = {s.scene_id: s for s in current}
    for s in update:
        by_id[s.scene_id] = s      # replace-by-id; the node already built the full scene
    return list(by_id.values())  # insertion order preserved — Python 3.7+ dict guarantee


# --- Accessory blocks ---
class NarrationEntry(BaseModel):
    scene_id: str
    audio_ref: Optional[str] = None    # durable path


class Sharing(BaseModel):
    teacher_approved: bool = False
    in_gallery: bool = False


class Cost(BaseModel):                 # CC-3
    image_count: int = 0
    regen_count: int = 0
    usd_estimate: float = 0.0


class Eval(BaseModel):                 # CC-7
    seed: Optional[int] = None


# --- Root ---
class StoryMemory(BaseModel):
    schema_version: int                # REQUIRED, no default — see spec §3
    # durable provenance (ADR-023 Decision 3 — NO mutable job/status block; that lives in the DB job row)
    story_id: str
    classroom_id: str
    profile_id: str
    input: Input
    characters: list[Character] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    objects: list[StoryObject] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    style: Style = Field(default_factory=Style)
    scenes: Annotated[list[Scene], upsert_scenes] = Field(default_factory=list)  # upsert-by-scene_id reducer (ADR-024, §8)
    narration: list[NarrationEntry] = Field(default_factory=list)
    sharing: Sharing = Field(default_factory=Sharing)
    cost: Cost = Field(default_factory=Cost)
    eval: Eval = Field(default_factory=Eval)

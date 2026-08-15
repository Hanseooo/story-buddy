# Feature Spec — story-analyzer

**Status:** built (2026-07-29, commits e8906e9–8a5a1ed) · **Phase:** 1 · **Owner node:** `backend/pipeline/analyze.py`
**Derived from:** MASTER_SPEC §2 (system map), §3 (frozen contract), §6 (test seam) · **Rationale:** ADR-002, ADR-023 (D-F, D-G), ADR-024, ADR-025, ADR-028, PRD §8

> One extraction call, one roster. Every downstream node works from `characters[]` instead of
> re-reading the child's prose. This spec adds **no** contract fields and bumps **no**
> `schema_version` — it closes `story-memory-contract` §8's open refinement item by deciding the
> minimal shapes are sufficient.

## 1. Purpose

Extract the story's entities — characters, locations, objects, and a coarse timeline — once, from
the redacted input text, so `char_bible` has a stable roster to draw canonical references from and
`segment` has an ordering to split against.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `input.redacted_text` (falls back to `input.raw_text` when redaction has not run —
  the same fallback `segment` already uses)
- **Writes:** `characters[]`, `locations[]`, `objects[]`, `timeline[]`
- **Does not write:** `scenes[]`. Scenes do not exist yet — `segment` runs after this node. The
  `caption_for` and `SceneCaption` have been **deleted** from this file — they were orphans created by ADR-013 and removed by the `scene-segmentation` spec (2026-07-29).

**Invariants** (each guarded by a test in §6):

1. `len(characters) <= 3`, prominence-ordered — index `0` is the protagonist.
2. Ids are `c{i}` / `loc{i}` / `obj{i}`, zero-based, **minted node-side by list position** after
   parsing (`story-memory-contract` §2.1, D-G). The LLM schema carries no id field.
3. `Character.name` is **the name the story gives**, falling back to a short descriptive label when
   the story names nobody. Never a redaction placeholder.
4. `timeline[].order` is **re-assigned by the node** from list index: zero-based and dense. It is
   not trusted from the model. A model that returns `1, 2, 5` or a duplicate `order` validates
   fine against Pydantic and would silently corrupt the only ordering `segment` receives.
5. Every emitted `Character` has a complete visual profile: at least three discriminators across at least two of `colours`, `body_features`, and `clothing`. Humanoids carry a required `clothing` description. Enforced by transient `is_humanoid` validator at the LLM boundary; `is_humanoid` is not persisted in the contract.
6. `characters[]` and `objects[]` are mutually exclusive by agency: actors perform actions and decide; inert items belong in `objects[]`. An entity appearing in both rosters fails boundary validation.
7. Every `ExtractedObject` requires a stable physical `description`. `owner_name` is mapped to `owner_char_id` after character capping; an unknown owner fails boundary validation.

## 3. Position in the system map

```
input_gate ──► analyze ──► segment ──► char_bible ──► ...
```

Linear. **No conditional edge** — ADR-003's branch points are moderation pass/fail, consistency
pass/fail, and the reveal confirm/try-again (ADR-029, Phase 2); this node is none of them.

**Test seam (MASTER_SPEC §6):** one module-level helper, `extract_entities(text) -> StoryAnalysis`,
is the effect boundary. The node body only maps, truncates, and mints. Node and graph tests patch
`pipeline.analyze.extract_entities`; the helper's own tests patch
`pipeline.analyze.structured_text`.

## 4. Behavior & edge cases

### The extraction schema (D-F: transient wrapper, so it lives beside its node)

The contract types `Character` / `Location` / `StoryObject` all carry a **required** id, and D-G
forbids an id at the LLM boundary. The boundary therefore uses id-less mirrors in
`backend/pipeline/analyze.py`, which the node maps into contract types:

```python
class ExtractedDescription(CharacterDescription):
    """Boundary-strict subclass. Enforces complete visual canon at the extraction boundary."""
    species: str
    is_humanoid: bool

    @model_validator(mode="after")
    def complete_visual_profile(self) -> "ExtractedDescription":
        axes = (self.colours, self.body_features, self.clothing)
        if sum(len(axis) for axis in axes) < 3 or sum(bool(axis) for axis in axes) < 2:
            raise ValueError("character needs at least three visual discriminators across two axes")
        if self.is_humanoid and not self.clothing:
            raise ValueError("humanoid character needs a clothing description")
        return self

class ExtractedCharacter(BaseModel):
    name: str
    description: ExtractedDescription

class ExtractedLocation(BaseModel):
    name: str
    description: str   # Enforced strictly at the transient boundary, no longer nullable

class ExtractedObject(BaseModel):
    name: str
    description: str
    owner_name: str | None = None

class StoryAnalysis(BaseModel):         # the transient wrapper; never persisted
    characters: list[ExtractedCharacter]   # prominence order, protagonist first
    locations: list[ExtractedLocation]
    objects: list[ExtractedObject]
    timeline: list[TimelineEvent]          # already id-less in contracts/

    @model_validator(mode="after")
    def entity_rosters_do_not_overlap(self) -> "StoryAnalysis":
        character_names = {character.name.casefold() for character in self.characters}
        overlap = character_names & {obj.name.casefold() for obj in self.objects}
        if overlap:
            raise ValueError(f"entity appears as both character and object: {sorted(overlap)}")
        return self
```

`CharacterDescription` is subclassed rather than mirrored: it has no id, and its axes
(`species`, `colours`, `body_features`, `clothing`) are deliberately aligned to the `FailureReason`
taxonomy the judge scores against. Re-deriving them here would create a second source of truth.

`is_humanoid` is a node-local transient flag used only to enforce required clothing on humanoid figures. It is stripped via `exclude={"is_humanoid"}` when converting to `CharacterDescription` so it does not leak into the persisted contract.

The prompt requires filling missing visual axes with concrete, directly drawable, child-safe,
non-stereotyped details that distinguish the character across the roster. It explicitly forbids the
placeholder values `neutral`, `none`, `unknown`, and `unspecified`; this is prompt guidance only,
not a new semantic Pydantic validator or terminal failure path.

Locations require a strict permanent description. The prompt instructs the model to preserve stated permanent facts and fill missing detail neutrally, excluding temporary conditions.

Objects require a stable physical description and an optional `owner_name`. Initial ownership is mapped after the three-character cap: `owner_name` maps to `owner_char_id`. If an `owner_name` cannot be resolved against the capped character roster, node execution raises `ValueError`.

### Edge cases

| Case | Behavior |
|---|---|
| **Zero characters extracted** | Valid, not a failure. Return an empty `characters[]` and still write the other three collections. `char_bible` mints no references and scenes generate unreferenced — a book with drifting art beats no book (ADR-010's "always a shippable page"). |
| **More than 3 characters** | Node truncates to the first 3. The prompt also asks for ≤3, so the truncation is belt-and-braces; the node is the control, because the prompt is not enforceable. |
| **Same character named twice** ("my sister", "Ate") | **Documented ceiling, not guarded.** Two `char_id`s, two reference images, two of the three budget slots. Consistent with `story-memory-contract` §2.1 — entities are minted once and never merged or re-indexed within a run. A dedup pass would be a new node, and nothing in Phase 1 justifies one. |
| **Unbounded `locations[]` / `objects[]`** | **Deliberately uncapped.** Neither costs an image, so neither is a CC-3 lever; the only cost is checkpoint size, which is bounded in practice by a ≤800-word story (ADR-012). Cap them only if a measured checkpoint problem appears — not preemptively. |
| **Character vs object ambiguity** ("my teddy bear") | Guided by agency in the extraction prompt (actors decide/act; inert items are objects). `StoryAnalysis` model_validator explicitly rejects any entity listed in both rosters with `ValueError`. |
| **Character with sparse or incomplete description** | **Cannot happen** — `complete_visual_profile` requires at least 3 discriminators across 2 axes (and clothing if humanoid) at the LLM boundary, raising `ValidationError` if incomplete. |
| **Unknown object owner** | **Fails boundary** — mapping `owner_name` to `owner_char_id` raises `ValueError` if `owner_name` is not in the capped character roster. |
| **Empty `timeline[]`** | Valid. `segment` falls back to text order. |
| **Very short input** ("I like dogs") | Valid. Extraction yields whatever it yields; a minimum-length gate is `length-guard`'s job (Phase 2), not this node's. |
| **Input was truncated** (ADR-012) | No special handling. `analyze` sees the kept portion, which is correct — the book illustrates what was kept, and ADR-012 forbids summarizing the tail back in. |
| **Model self-refusal** on a mild-peril story | In Phase 1 a refusal surfaces as `message.parsed is None` → **hard failure** per ADR-025 → job `failed`. This is knowingly blunt. ADR-025 explicitly classes content-refusal as *not* a resilience concern and hands soften-and-retry to `self-refusal-fallback` (Phase 2, ADR-011 mech. 4). |
| **Provider hard failure** | Raises. Job → `failed` with an ADR-025 `failure_reason`; never a partial roster. No node-level retry — the `openai` SDK's bounded retry is the entire policy (ADR-025 Decision 1). |
| **Resume mid-job** | LangGraph checkpoints after every node, so a resumed job reuses the persisted roster and never re-mints ids (`story-memory-contract` §2.1). |
| **Prompt injection in the story text** | The child's text enters an LLM prompt, but `input_gate` moderates it **first** — CC-1's ordering is the mitigation, and it is a graph edge, not something this node re-implements. Strict `json_schema` further constrains the *shape* of what comes back; it does not constrain content, so this is defence-in-depth, not a guarantee. |

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-2 PII redaction** — reads `redacted_text`, and no `<PERSON_1>` placeholder reaches a
  prompt, a caption, or the exported book.
  ~~⚠️ **Not satisfied end-to-end today.** `input_gate` is a pass-through stub that copies
  `raw_text` into `redacted_text`, and Presidio is not a dependency anywhere in `backend/`.~~
  **Resolved 2026-08-11.** `input_gate` is no longer a stub: it calls `providers.redact_pii`
  (Presidio + spaCy `en_core_web_sm` + `ph_recognizers`) on every job. The tick is now real.
  ⚠️ **But this node stopped being a second layer on the same date** — see §4 *Naming*. It relies
  entirely on upstream redaction, so CC-2 here is exactly as strong as Presidio's recall.
- [x] **CC-3 Cost control** — the 3-character cap is the roster ceiling, but **not** the pre-scene
  image ceiling. ~~at most 9 reference draws (3 characters × ADR-028's 3-draw cap)~~ — corrected
  2026-07-30 by `character-bible` §8: ADR-004 caps canonical references at **2** per book, so the real
  pre-scene ceiling is **6 draws** (2 references × ADR-028's 3-draw cap). The character cap and the
  reference cap are different numbers; a third character simply gets no reference. This
  node writes no `cost` fields; its own text-token spend is untracked in `cost.usd_estimate`
  (noise against image cost — ADR-001).
- [x] **CC-5 Observability** — the helper logs extracted counts and the minted ids, so a wrong
  reference downstream traces back to a specific roster entry.
- [x] **CC-9 Failure states** — an empty roster is **not** a failure and must never fail the job;
  only a provider failure does, through the ADR-025 `failure_reason` enum.
- [x] **CC-10 Checkpointing** — one call, one partial-return, no partial writes. Safe to resume.
- [ ] **CC-7 Reproducibility** — **not satisfied, recorded as a limitation.**
  `providers.structured_text` accepts no seed, so extraction is not reproducible run-to-run: two
  runs of the same story can produce different rosters and therefore different `char_id`
  assignments. `story-memory-contract` §2.1 requires only within-run/resume id stability, which
  checkpointing provides, so nothing breaks — but a seeded re-run is not byte-identical. Same
  family as MASTER_SPEC §8's un-run image-seed probe; recorded here, not closed here.
- [ ] CC-1, CC-4, CC-6, CC-8 — N/A. Moderation ordering is a graph edge (see §4); this node writes
  no assets, renders no UI.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Every model call mocked. **No assertion touches extraction quality** — that is Tier B by
definition.

**Provider seam** — patch `pipeline.analyze.structured_text`:
- `extract_entities` passes the story text and the `StoryAnalysis` schema to the provider
- returns the parsed wrapper unchanged

**Node, helper mocked** — patch `pipeline.analyze.extract_entities`:
- **Id minting:** 2 characters → `c0`, `c1`; locations → `loc0`, `loc1`; objects → `obj0`
- **Character cap:** 5 extracted → 3 returned, and they are the **first** 3 (prominence survives
  the cut)
- **Timeline re-indexing:** input `order` values of `1, 2, 5` (or duplicates) come back as
  `0, 1, 2` in list order — guards invariant 4
- **Empty roster:** zero characters returns `{"characters": [], …}` and does **not** raise
- **CC-2 source:** prefers `redacted_text`; falls back to `raw_text` when it is `None`
- **Partial-return (ADR-024):** result keys are exactly the four; `state` is unmutated afterwards
- **D-G guard:** no extraction model declares an id field —
  `"char_id" not in ExtractedCharacter.model_fields`, and likewise for `loc_id` / `obj_id`
- **Persisted type is the contract type:** an emitted `Character.description` is a
  `CharacterDescription`, not the strict subclass (`type(c.description) is CharacterDescription`)

**Boundary strictness** — schema-level, no provider needed:
- `ExtractedDescription` **requires** `species`: validating `{"colours": ["red"]}` raises
  `ValidationError` (guards invariant 5 and ADR-028's re-roll)
- the contract is **unchanged**: `CharacterDescription()` with no arguments still validates, and
  `Character(char_id="c0", name="x")` still gets its `default_factory` description
- `ExtractedDescription` inherits every axis — `set(CharacterDescription.model_fields) <=
  set(ExtractedDescription.model_fields)` — so the axes have one source of truth
- no visual attribute is required: `ExtractedDescription(species="dog")` validates (guards against
  someone later "tightening" this into an after-the-call failure — see §4)

**Graph** — patch the single helper and assert the roster survives `input_gate → analyze → segment`
(one patch point per node, per MASTER_SPEC §6 rule 1).

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

**Roster fidelity** — does `analyze` find the characters a human reads in the story, and does it
rank the protagonist first? Measured offline on the story corpus with real models, never in CI.

It feeds **Objective 3** (expert validation: narrative coherence, story faithfulness). Per
MASTER_SPEC §6 this is a *pipeline behaviour exercised inside that leg*, **not** an evaluation leg
of its own — do not construct a separate instrument for it.

## 8. Linked decisions & open questions

**Depends on:** ADR-002 (strict `json_schema` + `require_parameters`) · ADR-023 amendment, D-F
(schema home) and D-G (id minting) · ADR-024 (partial-return, no mutation) · ADR-025 (failure
taxonomy, refusal deferred) · ADR-028 (the 3-draw reference cap this spec's character cap
multiplies against) · MASTER_SPEC §2 node-I/O table, §6 test seam.

**Closes:** `story-memory-contract` §8's item *"`Location` / `StoryObject` / `TimelineEvent` —
refined by the `story-analyzer` spec"*. **The answer is no refinement.** The minimal shapes are
sufficient for every Phase-1 consumer. No contract change, no `schema_version` bump.

**Hands off — named here, owned elsewhere:**
- **`Scene.characters_present`** → **`scene-segmentation`**. Nothing mints it today, and `analyze`
  cannot: it runs before scenes exist. `segment` creates scenes and already reads the analysis, so
  the mapping belongs there. The join key is `Character.name`. **Landed 2026-07-29**: `segment` maps `Character.name → char_id` using the join key named here.
- **Description *richness*** → **`character-bible`**. Closed at `analyze`: complete visual canon (at least 3 discriminators across 2 axes) is required at the LLM boundary (§4), so ADR-028's re-roll can no longer receive sparse descriptions. `char_bible` receives complete descriptions for canonical reference generation.
- **Character dedup** → **unowned**, documented ceiling (§4).

**Open:**
- **CC-7 seed reproducibility for text extraction** — recorded in §5, not closed. Needs a seed
  parameter on `providers.structured_text`, which is a `providers.py` change and therefore its own
  decision.
- ⚠️ **Filipino / Taglish extraction quality is unmeasured.** `mistralai/mistral-small-3.2-24b-instruct`
  (the `text_model` since 2026-08-11 — ADR-002 amendment; ~~`qwen/qwen3-32b`~~ before that) has no
  published Filipino entity-extraction performance, and the respondents are Filipino children (ADR-017). A
  Taglish story may also yield descriptive labels in Filipino, which then flow into an
  English-prompted image model. This is the same measurement gap ADR-011 carries for the text
  moderation gate (Phase 0.5 probe 4, un-run). **Not a Phase-1 blocker; flag it before Phase 2
  hardening.**

## 9. Definition of done

Per AGENTS.md *Definition of Done*. This module is done when **all** of the following hold:

1. `backend/pipeline/analyze.py` implements §4 — `StoryAnalysis` + mirrors, the
   `extract_entities` helper, and a node that truncates, mints, re-indexes, and partial-returns.
   The `# ponytail: stub` comment and its `DECISION_BACKLOG` pointer are removed.
2. Every §6 assertion exists and passes. `tests/test_analyze_node.py`'s
   `test_analyze_is_a_pass_through_stub` is **deleted** — it asserts the behaviour this spec
   replaces.
3. Backend verify is green and its output is shown, not claimed:
   `uv run ruff check . && uv run pytest` from `backend/`.
4. **Status line above flips to `built`** with the commit range, per the spec lifecycle
   (MASTER_SPEC §7).
5. **The finding-change grep is run** (AGENTS.md *Definition of Done*) and every hit fixed in the
   same change. Known surface as of 2026-07-29:
   - `docs/product/DECISION_BACKLOG.md` — tick the `story-analyzer` line, **and** replace the
     stale *"Recommended next session"* block, which still names the completed `job_state.py`
     migration.
   - `docs/WORKFLOW.md` §"Right now" — currently names writing this spec as the next action.
   - `AGENTS.md` *Validation Notes* — drop `story-analyzer` from the remaining-Phase-1 list; and
     *Project Context*, which lists `analyze` among the pass-through stubs.
   - `docs/specs/story-memory-contract.md` §8 — mark the `Location` / `StoryObject` /
     `TimelineEvent` refinement item resolved (no refinement), citing this spec.
   - `docs/MASTER_SPEC.md` §2 — no edit expected; confirm the `analyze` row still reads true.
6. **No new file is added to the status surface** (AGENTS.md's nine-file table). This spec points
   at `PHASE_05_RESULTS.md` and asserts no probe numbers of its own.

**Not done** if: any §6 test is skipped, the roster caps are enforced only by prompt text,
`species` is relaxed to Optional at the boundary, `backend/contracts/` is modified, or a handoff in
§8 is silently absorbed into this node instead of being left to its owner.

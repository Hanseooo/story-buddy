# Feature Spec — scene-segmentation

**Status:** built (2026-07-29, commits 6f53f29..c879680) · **Phase:** 1 · **Owner node:** `backend/pipeline/segment.py`
**Derived from:** MASTER_SPEC §2 (system map), §3 (frozen contract), §6 (test seam) · **Rationale:** ADR-003, ADR-010, ADR-012, ADR-013, ADR-023 (D-F, D-G), ADR-024, ADR-025, PRD §8/§11.6, methodology §2

> The model chooses *where* the cuts go; the node builds the text. Every `text_excerpt` is sliced
> from the child's own sentences, so no scene can contain a word the child did not write. This spec
> adds **no** contract fields and bumps **no** `schema_version`.

## 1. Purpose

Split the story into the pages of the picture book: an ordered, gap-free sequence of scenes, each
carrying a verbatim excerpt of the child's text, its caption, and the `char_id`s present in it.

It also **retires `caption_for`**. ADR-013 decided captions are the child's verbatim text, not
LLM-rewritten; the stub's caption call predates that and contradicts it (§4).

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `input.redacted_text` (falls back to `input.raw_text` when redaction has not run — the
  same fallback `analyze` uses), `characters[]`, `timeline[]`
- **Writes:** `scenes[]` — `scene_id`, `text_excerpt`, `caption`, `characters_present`
- **Does not write:** `scenes[].prompt`, `attempts[]`, `final_image_ref`, `moderation_status`,
  `regeneration_count`. Those belong to `prompt-optimizer`, `image-generator`,
  `regeneration-controller`, and the output-moderation node.

**Invariants** (each guarded by a test in §6):

1. `scene_id` is `s{i}`, zero-based, minted node-side by list position
   (`story-memory-contract` §2.1, D-G). The LLM schema carries no id field.
2. **Total coverage.** Every sentence unit of the source text appears in exactly one scene — no
   gaps, no overlaps, no reordering. The child's words are neither dropped nor duplicated.
3. **Verbatim.** `text_excerpt` is a join of source units, never model-authored prose.
4. `caption == text_excerpt` (ADR-013).
5. `1 <= len(scenes) <= 15` for any non-empty input; `len(scenes) == 0` only for empty input.
6. `characters_present` contains only `char_id`s that exist in `state.characters`.

## 3. Position in the system map

```
input_gate ──► analyze ──► segment ──► char_bible ──► ...
```

Linear. **No conditional edge** — ADR-003's branch points are moderation pass/fail, consistency
pass/fail, and the reveal confirm/try-again (ADR-029, Phase 2); this node is none of them.

**Test seam (MASTER_SPEC §6):** one module-level helper, `segment_scenes`, is the node's entire
effect boundary. `split_sentences` and `repair` are **pure** and tested directly, with no patching.
Node and graph tests patch `pipeline.segment.segment_scenes`; the helper's own tests patch
`pipeline.segment.structured_text`.

## 4. Behavior & edge cases

### Why the model returns indices, not text

The model is given the story's sentences, numbered, and returns index *ranges*. The node slices the
units itself. This is what makes invariants 2 and 3 structural rather than hopeful: a model that
returns excerpt strings can reword, paraphrase, or silently drop a clause, and the only defence is
a substring check that then has nowhere to go on a miss. Returning ranges also costs output tokens
proportional to the number of scenes rather than to the length of the story.

The cost of the choice is that a malformed range set is now possible in a way a string echo is not.
That is what `repair` is for, and it is deterministic and total (below).

### Captions are not generated (ADR-013)

ADR-013 is Accepted and explicit: *"Captions are the **child's verbatim text excerpt**
(post-PII-redaction), not rewritten,"* with LLM-polished captions rejected for MVP on fidelity and
moderation-surface grounds. The `segment` stub calls `caption_for`, an LLM caption writer living in
`analyze.py` per D-F. It predates the ADR and contradicts it.

Therefore `caption = text_excerpt`, and `caption_for` + `SceneCaption` are **deleted** from
`backend/pipeline/analyze.py`. They are orphans this spec's decision creates, which AGENTS.md
*Surgical Changes* puts in scope; nothing else in `analyze.py` is touched. This is not an ADR
change — ADR-013 already decided it.

**Grepped, because the blast radius is wider than one import** (`grep -rn "caption_for\|SceneCaption"`):

| Site | Action |
|---|---|
| `pipeline/segment.py:2,9` | The import and the call — replaced by this spec. |
| `tests/test_segment_node.py:19,31` | Both tests patch `caption_for`; replaced by §6. |
| `tests/test_graph_stub.py:46` | Patches `pipeline.segment.caption_for`; repoint to `segment_scenes`. |
| `tests/test_analyze_node.py:20–57` | Four `SceneCaption` / `caption_for` tests; **delete** — they test a helper that no longer exists. |
| `docs/MASTER_SPEC.md:302` | Uses `pipeline.analyze.caption_for` as the worked example of the helper seam. Swap the example to `pipeline.segment.segment_scenes`. |
| `docs/MASTER_SPEC.md:76`, `docs/product/adr/ADR-023-story-memory-is-the-langgraph-state-single-int.md` (**Amendment (2026-07-22)**, the "D-F — where structured-output sub-schemas live" bullet) | Use `SceneCaption` as D-F's worked example of a transient wrapper. Swap to `SceneSegmentation`, which is the same shape and is not going away. |
| `docs/specs/story-analyzer.md:23` | Says `caption_for` "lives in this file per D-F but belongs to `segment`". Update. |
| `docs/specs/plans/2026-07-29-story-memory-contract.md` | Historical, already-executed plan. **Do not edit** — git keeps the record of what was built. |

**D-F is not violated.** `SceneCaption` was D-F's *illustration*, not its subject; the rule is
"transient wrapper lives beside its node", and `SceneSegmentation` obeys it. No ADR change.

### The LLM boundary schema (D-F: transient wrapper, so it lives beside its node)

```python
class ExtractedObjectEvent(BaseModel):
    object_name: str
    action: Literal["acquire", "release"]
    holder_name: str

class ExtractedScene(BaseModel):
    start: int                      # inclusive index into the numbered units
    end: int                        # inclusive
    characters_present: list[str]   # Character.name values — the node maps them to char_ids
    location_name: str | None = None  # Location.name value — node maps to a loc_id, null → inherit
    objects_present: list[str] = Field(default_factory=list)
    object_events: list[ExtractedObjectEvent] = Field(default_factory=list)
    visual_direction: str           # Required non-blank direction string

class SceneSegmentation(BaseModel):
    scenes: list[ExtractedScene]
```

No id field, per D-G. `characters_present` represents intended-visible cast only. All five planning fields (`characters_present`, `location_name`, `objects_present`, `object_events`, `visual_direction`) are preserved through `repair` and `merge_thin`.

### Happy path

1. `text = state.input.redacted_text or state.input.raw_text`
2. `units = split_sentences(text)` — pure. If `units` is empty, return `{"scenes": []}` **without
   calling the provider**; there is nothing to pay for.
3. `segment_scenes(units, state.characters, state.timeline, state.locations, state.objects)` — one `providers.structured_text` call,
   strict `json_schema` → `SceneSegmentation` (ADR-002). The prompt gets the numbered units, roster names,
   location names, object roster, and `timeline[]` as context.
4. `repair(...)` — clamp, sort, de-overlap, close gaps, raise if empty, merge to ≤15. `_merge_extracted` combines payload fields deterministically.
5. Single-pass visible cast validation and object lifecycle resolution:
   - `characters_present` is strict visible cast authority; unknown character raises `ValueError`.
   - `visual_direction` naming a roster character outside `characters_present` raises `ValueError`.
   - Object lifecycle pass tracks active objects and holders, formatting holder relationships into `visual_direction`.
   - Unknown object or holder raises `ValueError`; unknown location logs warning and carries forward.
6. Mint `s{i}`, join units into `text_excerpt`, copy it into `caption`, map names → `char_id`s.
7. Partial-return `{"scenes": [...]}` (ADR-024 — never mutate `state`).

### Sentence splitting

`re.split` on sentence-final punctuation (`. ! ? …`) and line breaks, with empty units dropped.
Stdlib only — no new dependency, so no AGENTS.md §2 decision gate. This is adequate for ≤800-word
kid prose (ADR-012), and a wrong boundary costs a slightly-off page break, not a broken book.

### `repair(scenes, n)` — deterministic, total, pure

1. **Clamp** each range into `[0, n-1]`; drop any where `start > end` afterwards (via `model_copy`).
2. **Sort** by `start`.
3. **De-overlap** — walking in order, force `start = max(start, prev_end + 1)`; drop the range if
   that empties it. Overlaps resolve in favour of the earlier scene.
4. **Close gaps** — an uncovered run attaches to the preceding scene (extend its `end`); a leading
   run extends the first scene's `start` to `0`; a trailing run extends the last scene's `end` to
   `n-1`.
5. **No empty floor** — if nothing survived clamp + de-overlap, raise
   `ValueError("segment: no usable scene range survived clamp and de-overlap")`. The former
   whole-story floor cannot be rebuilt: it minted a scene with no `visual_direction`, which
   `generate_scene` would now have to draw blind.
6. **Merge to ≤15** — while there are more than 15, merge the adjacent pair with the smallest
   combined unit count using `_merge_extracted(a, b)` (union characters/objects, concatenate events and visual directions).

### Visible Cast Authority & Object Lifecycle Pass

- **Visible Cast Authority:** `characters_present` is the single authoritative visible cast. Regex recovery is removed. If `characters_present` contains an unknown character name, or if `visual_direction` names a roster character not in `characters_present`, `segment` raises `ValueError`.
- **Object Lifecycle Pass:** `holder_by_obj` is seeded with `owner_char_id`, but `active_objects` starts empty. An object activates upon explicit appearance in `objects_present` or an `acquire` event. In each beat, active objects whose current holder is visible in `characters_present` are included in `objects_present` and formatted into `visual_direction` (`"<object> is held by <holder>."`). Transfers apply `release` then `acquire` in narrative order. An unknown object name or holder raises `ValueError`.

### Edge cases

| Case | Behavior |
|---|---|
| **Empty `timeline[]`** | Valid. The prompt loses its plot-point context and the model segments from the text alone. |
| **Input was truncated** (ADR-012) | Segments the kept portion only. Correct — the book illustrates what was kept. |
| **Provider hard failure** | Raises. Job → `failed` with an ADR-025 `failure_reason`; never a partial `scenes[]`. No node-level retry — the `openai` SDK's bounded retry is the entire policy (ADR-025 Decision 1). |
| **Model self-refusal** | `message.parsed is None` → hard failure, same as above. Knowingly blunt in Phase 1; soften-and-retry belongs to `self-refusal-fallback` (Phase 2, ADR-011 mech. 4). |
| **Resume mid-job** | LangGraph checkpoints after every node, so a resumed job reuses the persisted scenes and never re-mints `scene_id`s (`story-memory-contract` §2.1). |
| **Prompt injection in the story text** | `input_gate` moderates **first** — CC-1's ordering is the mitigation, a graph edge, not something this node re-implements. Strict `json_schema` further constrains the shape of what comes back, and because the node only reads *integers* from the response, a hostile response cannot inject text into the book. |

### Setting (`scene-setting-and-subject-binding.md` §4.1)

`SEGMENTATION_PROMPT` carries a location roster and `ExtractedScene.location_name`, mapped to
`scenes[].location_id` by the same pattern as the character path (unknown name → warn + treated as
null). Carry-forward runs last, over the final scene list in order: a null inherits the previous
scene's `location_id`; a null `s0` takes `locations[0].loc_id` if the story named any, else `None`.
A story that names no location leaves every `location_id` as `None` — identical to before.

Every repair and merge path now rebuilds scenes with `model_copy(update=...)` rather than a fresh
`ExtractedScene(...)`, so `location_name` — and `visual-continuity`'s `objects_present`,
`object_events` and `visual_direction` — propagate by construction instead of by being restated at
eight call sites. `_merge_extracted` is the one place that combines them: `a.location_name or
b.location_name`, union the object lists, concatenate the events and the directions.

### Invariant: no duplicate `char_id` (`scene-setting-and-subject-binding.md` §4.3)

`characters_present` contains no repeated `char_id`. Two paths produced one: the model naming a
character twice, and `analyze` minting two characters with the same name. The name → id map is
first-seen-wins and the id list is deduplicated with `dict.fromkeys`, which preserves first-seen
order — so removing a duplicate cannot reorder the survivors that `build_prompt`'s image roll and
`generate_scene`'s `ref_paths` are both indexed against.


### Name recovery — removed by `visual-continuity` §4.3 (2026-08-14)

**This backstop no longer exists.** From 2026-08-13 to 2026-08-14, every roster name the excerpt
mentioned and that the model had omitted from `characters_present` was appended to `char_ids` by a
word-boundary regex. `visual-continuity` §4.3 deleted it: *"a name appearing in an excerpt does not
prove that the character should be visible. The structured `characters_present` decision is the
authority."* The motivating job drew characters the story only *mentioned*, which is precisely what
over-recovery buys.

The regex itself survives as `_names_character`, doing the opposite job: a `visual_direction` that
names a roster character **outside** the visible cast raises `ValueError` before any fal image is
purchased. Recovery appended; this rejects.

**What the removal gives back to the model, and the residual risk.** The compounding failure the
backstop was built for is real and is not fixed by deleting it: an omitted character means
`generate_scene` finds no reference and falls through to `text_to_image`, and `consistency_check`
then finds no subject on the identity leg. What changed is that the page is no longer *unchecked* —
`visual-continuity` §4.6's scene-constraint judge runs on every attempt including reference-free
ones, so an omitted or unrequested character is now caught by a judge that can read the picture
rather than by a regex that can only read the text.

`SEGMENTATION_PROMPT` keeps its pronoun rule, now the only text-side layer:

> `- List a character in characters_present only when they are intended to be visible in this scene frame. List them even when the sentences refer to them only as he, she, it or they.`

**Deliberately not built:** a cast carry-forward mirroring §4.1's location seed — an empty cast is
either a pronoun beat *or* a genuine scenery page, and inheriting the previous page's cast draws a
character into the scenery one. Revisit if the logs show beats still landing at `refs=0`.

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-2 PII redaction** — reads `redacted_text`.
  ⚠️ **Not satisfied end-to-end today**, same as `story-analyzer` §5: `input_gate` is a pass-through
  stub and Presidio is not a dependency anywhere in `backend/`. This node is correct *by
  construction*; the redaction it depends on lands with `moderation-stack` (Phase 2).
- [x] **CC-3 Cost control** — the **15-scene cap is the image ceiling**: ≤15 scenes × ADR-010's ~2
  attempts ≈ ≤30 images per book, which is what makes PRD §15's ~$0.30–0.65 estimate structural
  rather than hopeful. This node writes no `cost` fields; its own text-token spend is noise against
  image cost (ADR-001).
- [x] **CC-5 Observability** — the helper logs the unit count and the returned scene count; the node
  logs the minted `scene_id`s **and which repair steps changed the tiling** (clamp / de-overlap /
  gap-fill / floor / merge), so an odd page break traces to a specific repair rather than to "the
  model did something".
- [x] **CC-9 Failure states = success states** — no content-shaped input fails the job. Empty input,
  a one-sentence story, zero scenes, and a garbage tiling all produce a valid result. Only a
  provider failure fails the job, through the ADR-025 `failure_reason` enum.
- [x] **CC-10 Checkpointing** — one call, one partial-return, no partial writes. Safe to resume.
- [ ] **CC-7 Reproducibility** — **not satisfied, recorded as a limitation.**
  `providers.structured_text` accepts no seed, so two runs of the same story can tile it differently
  and produce different page breaks. `story-memory-contract` §2.1 requires only within-run/resume id
  stability, which checkpointing provides. This is the **same** open item `story-analyzer` §8
  records — one `providers.py` seed parameter closes both. Not duplicated into the backlog.
- [ ] CC-1, CC-4, CC-6, CC-8 — N/A. Moderation ordering is a graph edge (§4); this node writes no
  assets and renders no UI.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Every model call mocked. **No assertion touches segmentation quality** — that is Tier B by
definition.

**Pure — `split_sentences`, no mocks:**
- splits on `.`, `!`, `?`, `…` and on line breaks
- drops empty and whitespace-only units
- `""` → `[]`

**Pure — `repair`, no mocks.** The invariant-bearing tests:
- out-of-order ranges come back sorted
- overlapping ranges resolve in favour of the earlier scene
- an interior gap attaches to the preceding scene
- a leading gap extends the first scene to index `0`; a trailing gap extends the last to `n-1`
- **total coverage:** for a spread of inputs, every index in `range(n)` appears in **exactly one**
  output range — guards invariant 2 directly
- empty input → one whole-story range (the floor)
- out-of-bounds indices clamp into `[0, n-1]`
- 18 ranges → 15, still dense and ordered, with `characters_present` **unioned** across each merge

**Provider seam** — patch `pipeline.segment.structured_text`:
- `segment_scenes` passes the numbered units and the `SceneSegmentation` schema to the provider
- returns the parsed wrapper unchanged

**Node, helper mocked** — patch `pipeline.segment.segment_scenes`:
- **Id minting:** 3 ranges → `s0`, `s1`, `s2`
- **Verbatim:** each `text_excerpt` is the join of exactly its own units, and concatenating all
  excerpts in order reproduces the source units in order
- **ADR-013:** `caption == text_excerpt` for every scene
- **`characters_present`:** roster names map to `char_id`s; a name absent from the roster **raises**
  (`visual-continuity` §4.8 — fail before any image draw)
- **Empty roster:** every scene gets `[]` and the node does not raise
- **Visible cast authority:** a merely mentioned off-screen character is absent from
  `characters_present`; no regex re-adds it
- **Direction cast check:** a `visual_direction` naming a roster character outside the visible cast
  raises; `"the star"` does **not** match `"stars"` (word boundary); matching is case-insensitive
- **Pronoun layer:** the prompt carries the pronoun rule, which is now the only text-side defence
  against an omitted character — a direction saying only `"He flees."` names no one and correctly
  does not trip the cast check
- **CC-2 source:** prefers `redacted_text`; falls back to `raw_text` when it is `None`
- **Empty text:** returns `{"scenes": []}` and `segment_scenes` is **never called**
- **Partial-return (ADR-024):** the result keys are exactly `{"scenes"}`; `state` is unmutated
- **D-G guard:** `"scene_id" not in ExtractedScene.model_fields`

**Regression guard for §4's retirement:**
- `caption_for` and `SceneCaption` no longer exist in `pipeline.analyze` —
  `not hasattr(pipeline.analyze, "caption_for")`. Cheap, and it stops the LLM caption path being
  reintroduced by reflex against ADR-013.

**Graph** — patch the single helper per node and assert the scenes survive
`input_gate → analyze → segment` (one patch point per node, per MASTER_SPEC §6 rule 1).

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

**Scene-selection completeness** — do the cuts land on the story's distinct major plot points, and
does a short story get a proportionately short book without padding? Measured offline on the story
corpus with real models, never in CI.

It feeds **Objective 3** (expert validation: narrative coherence, story faithfulness). Per
MASTER_SPEC §6 and PRD §10 this is a *pipeline behaviour exercised inside that leg*, **not** an
evaluation leg of its own — the former RQ1 was deliberately demoted (ADR-008, rev. 2026-07-25). Do
not construct a separate instrument for it.

## 8. Linked decisions & open questions

**Depends on:** ADR-002 (strict `json_schema`) · ADR-003 (no new conditional edge) · ADR-010
(always a shippable page; ~2 attempts/scene) · ADR-012 (truncation belongs to the input gate) ·
**ADR-013 (captions are verbatim)** · ADR-023 amendment, D-F (schema home) and D-G (id minting) ·
ADR-024 (partial-return, no mutation) · ADR-025 (failure taxonomy, refusal deferred) ·
MASTER_SPEC §2 node-I/O table, §6 test seam · PRD §8, §10, §11.6, §15 · methodology §2.

**Closes:** `story-analyzer` §8's hand-off of **`Scene.characters_present`**, joined on
`Character.name` as that spec specified.

**Hands off — named here, owned elsewhere:**
- **`scenes[].prompt`** → `prompt-optimizer`. This node writes the text and the roster join; it
  builds no image prompt.
- **PII placeholders in printed captions** → `moderation-stack`. See below.

**Open:**
- ⚠️ **A redaction placeholder can appear in the printed book.** ADR-013 makes the caption the
  child's *post-redaction* verbatim text, so a story naming a real person yields a page reading
  `[PERSON_1] and I went to the beach`. That is ADR-013 working as specified, but it is
  product-visible in the exported PDF and the slideshow. **Not resolvable here** — this node has no
  basis to rewrite text ADR-013 forbids it to rewrite, and the placeholder *format* is
  `moderation-stack`'s (Phase 2), which is also when redaction first actually runs. Recorded as that
  spec's problem, deliberately **not** a `DECISION_BACKLOG` row, because it is a display decision
  inside an owned spec rather than an open architectural decision.
- **CC-7 seed reproducibility** — recorded in §5. **The same open item as `story-analyzer` §8**, not
  a second one: one seed parameter on `providers.structured_text` closes both, and that is a
  `providers.py` change and therefore its own decision.
- ⚠️ **Filipino / Taglish sentence splitting is unmeasured**, as is the model's plot-point reasoning
  in Taglish. Same family as `story-analyzer` §8's extraction-quality gap and ADR-011's text-gate
  gap (Phase 0.5 probe 4, un-run). **Not a Phase-1 blocker; flag it before Phase 2 hardening.**

## 9. Definition of done

Per AGENTS.md *Definition of Done*. This module is done when **all** of the following hold:

1. `backend/pipeline/segment.py` implements §4 — `ExtractedScene` / `SceneSegmentation`, the pure
   `split_sentences` and `repair`, the `segment_scenes` helper, and a node that slices, mints, joins,
   and partial-returns. The `# ponytail: one scene per story` comment is removed.
2. `caption_for` and `SceneCaption` are **deleted** from `backend/pipeline/analyze.py`, with no
   other change to that file.
3. Every §6 assertion exists and passes, and every `caption_for` / `SceneCaption` site in §4's
   blast-radius table is closed — `tests/test_segment_node.py` replaced, `tests/test_graph_stub.py`
   repointed, and the four `SceneCaption` / `caption_for` tests in `tests/test_analyze_node.py`
   deleted.
4. Backend verify is green and its output is shown, not claimed:
   `uv run ruff check . && uv run pytest` from `backend/`.
5. **Status line above flips to `built`** with the commit range, per the spec lifecycle
   (MASTER_SPEC §7).
6. **The finding-change grep is run** (AGENTS.md *Definition of Done*) and every hit fixed in the
   same change. Known surface as of 2026-07-29:
   - `docs/product/DECISION_BACKLOG.md` — tick the `scene-segmentation` line and replace the
     *"Recommended next session"* block, which currently names writing this spec.
   - `docs/WORKFLOW.md` §"Right now".
   - `AGENTS.md` *Validation Notes* (drop `scene-segmentation` from the remaining-Phase-1 list) and
     *Project Context* (which lists `segment` among the pass-through stubs).
   - `docs/specs/story-analyzer.md` §8 — mark the `Scene.characters_present` hand-off landed, citing
     this spec.
   - `docs/MASTER_SPEC.md` §2 — the `segment` row's Writes column reads
     `scenes[].text_excerpt, caption`; extend it with `characters_present`.
   - `docs/MASTER_SPEC.md` §6 (`:302`) and `:76`, and
     `docs/product/adr/ADR-023-story-memory-is-the-langgraph-state-single-int.md`
     (**Amendment (2026-07-22)**, the D-F bullet) — the
     `caption_for` / `SceneCaption` worked examples, per §4's table. Swapping an *example* is not
     an ADR change; D-F's rule is unaltered.
   - `docs/specs/story-analyzer.md` §2 — the line stating `caption_for` lives in `analyze.py`.
   - `docs/specs/plans/2026-07-29-story-memory-contract.md` — **do not edit.** Executed plan; git
     is the record.

**Not done** if: any §6 test is skipped, the 15-scene cap is enforced only by prompt text, the cap
is implemented as truncation instead of merging, `text_excerpt` is taken from model-authored strings
instead of sliced from source units, `caption` is generated by a model, `backend/contracts/` is
modified, or a hand-off in §8 is silently absorbed into this node instead of being left to its owner.

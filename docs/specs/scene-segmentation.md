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
| `docs/MASTER_SPEC.md:76`, `docs/product/ADRs.md:1353` | Use `SceneCaption` as D-F's worked example of a transient wrapper. Swap to `SceneSegmentation`, which is the same shape and is not going away. |
| `docs/specs/story-analyzer.md:23` | Says `caption_for` "lives in this file per D-F but belongs to `segment`". Update. |
| `docs/specs/plans/2026-07-29-story-memory-contract.md` | Historical, already-executed plan. **Do not edit** — git keeps the record of what was built. |

**D-F is not violated.** `SceneCaption` was D-F's *illustration*, not its subject; the rule is
"transient wrapper lives beside its node", and `SceneSegmentation` obeys it. No ADR change.

### The LLM boundary schema (D-F: transient wrapper, so it lives beside its node)

```python
class ExtractedScene(BaseModel):
    start: int                      # inclusive index into the numbered units
    end: int                        # inclusive
    characters_present: list[str]   # Character.name values — the node maps them to char_ids

class SceneSegmentation(BaseModel):
    scenes: list[ExtractedScene]
```

No id field, per D-G. `characters_present` crosses the boundary as **names**, which is the join key
`story-analyzer` §8 named when it handed this field over; the node maps names to `char_id`s.

### Happy path

1. `text = state.input.redacted_text or state.input.raw_text`
2. `units = split_sentences(text)` — pure. If `units` is empty, return `{"scenes": []}` **without
   calling the provider**; there is nothing to pay for.
3. `segment_scenes(units, state.characters, state.timeline)` — one `providers.structured_text` call,
   strict `json_schema` → `SceneSegmentation` (ADR-002). The prompt gets the numbered units, the
   roster names, and `timeline[]` as the plot-point context, and asks for at most 15 scenes that
   track the story's distinct major plot points.
4. `repair(...)` — clamp, sort, de-overlap, close gaps, floor, merge to ≤15 (below)
5. Mint `s{i}`, join units into `text_excerpt`, copy it into `caption`, map names → `char_id`s
6. Partial-return `{"scenes": [...]}` (ADR-024 — never mutate `state`)

### Sentence splitting

`re.split` on sentence-final punctuation (`. ! ? …`) and line breaks, with empty units dropped.
Stdlib only — no new dependency, so no AGENTS.md §2 decision gate. This is adequate for ≤800-word
kid prose (ADR-012), and a wrong boundary costs a slightly-off page break, not a broken book.

**Documented ceiling:** abbreviations, ellipsis-heavy prose, and Filipino/Taglish punctuation habits
are unmeasured. This is the same measurement gap `story-analyzer` §8 already carries, not a new one.
A run-on story with no terminal punctuation yields one unit and therefore one scene; a word-chunk
fallback for that case was considered and **not** taken, because it adds a second code path and a
threshold constant to defend for an input that `length-guard` (Phase 2) is better placed to catch.

### `repair(scenes, n)` — deterministic, total, pure

1. **Clamp** each range into `[0, n-1]`; drop any where `start > end` afterwards.
2. **Sort** by `start`.
3. **De-overlap** — walking in order, force `start = max(start, prev_end + 1)`; drop the range if
   that empties it. Overlaps resolve in favour of the earlier scene.
4. **Close gaps** — an uncovered run attaches to the preceding scene (extend its `end`); a leading
   run extends the first scene's `start` to `0`; a trailing run extends the last scene's `end` to
   `n-1`. After this step every unit is in exactly one scene.
5. **Floor** — if nothing survived, emit one range `(0, n-1)`. The whole-story fallback is the floor
   of the repair, not a separate code path.
6. **Merge to ≤15** — while there are more than 15, merge the adjacent pair with the smallest
   combined unit count (ties → earliest), unioning their `characters_present`.

**Step order is load-bearing.** Merging runs last so the cap applies to an already-dense tiling and
can never reintroduce a gap.

**Why repair rather than fail.** ADR-025 reserves hard failure for *provider* failures; a
well-formed response the node dislikes is not one. ADR-010's "always a shippable page" points the
same way: a child should not lose their whole book to an off-by-one index.

### The 15-scene cap

The prompt asks for ≤15 and the **node is the control** — the same belt-and-braces pattern as
`analyze`'s 3-character cap, because a prompt is not enforceable. The cap is enforced by *merging*,
not truncating: ADR-012 confines content-losing truncation to the input gate, and a second one here
would silently delete the tail of the child's story from a book that ADR-012 promised would contain
their actual words.

There is **no floor.** Methodology §2 (module 3) and PRD §11.6 target ≥3 scenes *where the arc supports it* and
state that never-invent overrides the floor. A three-sentence story gets a short book.

### Edge cases

| Case | Behavior |
|---|---|
| **Empty / whitespace-only text** | Zero units → `{"scenes": []}`, **no LLM call**. A minimum-length gate is `length-guard`'s job (Phase 2), not this node's. |
| **One sentence** | One scene, `s0`. No floor is enforced — see above. |
| **Model returns zero scenes** | Repair step 5 → one whole-story scene. Never an empty book from a non-empty story. |
| **Model returns more than 15** | Merged down to 15. No child sentence is dropped. |
| **Out-of-order / overlapping / gapped ranges** | Repaired (steps 1–4). Logged, per CC-5, so an odd page break is traceable. |
| **Out-of-bounds indices** | Clamped. A model that hallucinates index 900 on a 12-sentence story gets index 11. |
| **Unpunctuated run-on story** | One unit → one scene. Documented ceiling. |
| **`characters_present` name not in the roster** | Dropped and logged. This node may not extend the roster — `analyze` owns it, and inventing a `char_id` here would produce a character with no canonical reference. |
| **Duplicate names in the roster** (`analyze`'s documented dedup ceiling) | Maps to **every** matching `char_id`. Over-conditioning is safer than dropping, and ADR-001's 1–3 reference cap bounds the consequence downstream. |
| **Empty roster** (`analyze` found zero characters) | Every scene gets `characters_present: []`. Valid — `generate_scene` runs unreferenced, per ADR-010's "always a shippable page". |
| **Empty `timeline[]`** | Valid. The prompt loses its plot-point context and the model segments from the text alone. |
| **Input was truncated** (ADR-012) | Segments the kept portion only. Correct — the book illustrates what was kept. |
| **Provider hard failure** | Raises. Job → `failed` with an ADR-025 `failure_reason`; never a partial `scenes[]`. No node-level retry — the `openai` SDK's bounded retry is the entire policy (ADR-025 Decision 1). |
| **Model self-refusal** | `message.parsed is None` → hard failure, same as above. Knowingly blunt in Phase 1; soften-and-retry belongs to `self-refusal-fallback` (Phase 2, ADR-011 mech. 4). |
| **Resume mid-job** | LangGraph checkpoints after every node, so a resumed job reuses the persisted scenes and never re-mints `scene_id`s (`story-memory-contract` §2.1). |
| **Prompt injection in the story text** | `input_gate` moderates **first** — CC-1's ordering is the mitigation, a graph edge, not something this node re-implements. Strict `json_schema` further constrains the shape of what comes back, and because the node only reads *integers* from the response, a hostile response cannot inject text into the book. |

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
- **`characters_present`:** roster names map to `char_id`s; a name absent from the roster is dropped
- **Empty roster:** every scene gets `[]` and the node does not raise
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
   - `docs/MASTER_SPEC.md` §6 (`:302`) and `:76`, and `docs/product/ADRs.md:1353` — the
     `caption_for` / `SceneCaption` worked examples, per §4's table. Swapping an *example* is not
     an ADR change; D-F's rule is unaltered.
   - `docs/specs/story-analyzer.md` §2 — the line stating `caption_for` lives in `analyze.py`.
   - `docs/specs/plans/2026-07-29-story-memory-contract.md` — **do not edit.** Executed plan; git
     is the record.

**Not done** if: any §6 test is skipped, the 15-scene cap is enforced only by prompt text, the cap
is implemented as truncation instead of merging, `text_excerpt` is taken from model-authored strings
instead of sliced from source units, `caption` is generated by a model, `backend/contracts/` is
modified, or a hand-off in §8 is silently absorbed into this node instead of being left to its owner.

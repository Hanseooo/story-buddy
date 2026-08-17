# Feature Spec — canonical-character consistency hardening

**Status:** built (2026-08-17) · owner-approved (ADR-041 accepted 2026-08-17) · **Phase:** 2 · **Owner surfaces:**
`backend/pipeline/analyze.py`, `backend/pipeline/char_bible.py`, `backend/pipeline/reveal.py`
**Derived from:** MASTER_SPEC §§2, 3, 5, 6 · `character-bible.md` · `story-analyzer.md`
**Rationale:** ADR-004, ADR-011, ADR-023, ADR-028, ADR-034, ADR-035, ADR-039, ADR-040,
ADR-041 · production Jamie/Bolt reproduction (2026-08-17)

> **Declared deviation from “one spec = one module.”** This feature owns one artifact crossing one
> existing seam: `analyze` materializes the stable character canon and `char_bible` consumes that
> canon to draw and judge a reference. Splitting the design would permit either richer morphology
> that is still contaminated by a semantic name, or a name-free prompt with insufficient anatomy.

---

## 1. Purpose and evidence

Make every newly analyzed character carry enough explicit, permanent morphology for the canonical
reference generator and reference judge to agree on what body and face/interface should be visible.
Prevent a Presidio pseudonym from acting as physical evidence in canonical-reference model calls.

The motivating story names a small robot `Bolt`. Presidio classifies that token as `PERSON` and,
under the current mandatory privacy policy, deterministically pseudonymizes it to `Leo`. The analyzer
correctly persists `species="robot"`, but its remaining appearance facts can be as weak as `small`
and `metal construction`. `char_bible` then sends `Leo` beside that sparse description. The image
model has produced a robot with a human face and, on another run, a lion-like face.

The failure exposes three distinct structural contributors:

1. a semantic pseudonym enters a visual prompt even though a name is not physical appearance;
2. the persisted canon does not always state a body plan and face/interface design;
3. the reference judge treats unlisted anatomy as a permissible extra detail, so a malformed face
   may not become a contradiction.

This spec removes the first prompt source and makes the missing morphology explicit before persistence. It
does not claim deterministic image quality. The Tier-B check in §7 decides whether the remaining
probabilistic generator and judge behavior is acceptable.

### 1.1 Success criteria

For every fresh analyzer result:

- the existing analyzer LLM remains the single authority allowed to fill missing permanent visual
  detail;
- every character has one concrete `body_plan` and one concrete `face_or_interface` at the
  structured-output boundary;
- both values are folded once into the existing `CharacterDescription.body_features` list;
- names, pronouns, dialogue, jobs, actions, and emotions are not treated as appearance evidence;
- normal and targeted canonical-reference draw and judge prompts do not directly concatenate
  `Character.name`, and the motivating pseudonym `Leo` is absent from both projections;
- draw and judge receive the same persisted physical identity axes;
- Presidio, captions, reveal display names, character IDs, Storage paths, graph shape, provider
  choice, draw caps, and moderation order do not change;
- no second prompt-writing or canon-rewriting LLM call is added.

### 1.2 Out of scope

- Disabling, bypassing, delaying, or context-gating Presidio. ADR-011 remains mandatory.
- Preserving a fictional name exactly in captions or exports.
- Removing names from scene generation, scene correction, or scene-judge prompts. D-P owns that
  broader model-facing alias decision if Tier-B evidence requires it.
- Changing the reference judge model, fine-tune, frozen Objective-4 taxonomy, or pre-registration.
- Changing `MAX_DRAWS`, image budgets, the reveal tap cap, best-of ranking, or the behavior after a
  judge exception or three rejected references. D-Q owns fail-open versus fail-closed policy.
- Adding `body_plan`, `face_or_interface`, `is_person`, or `is_humanoid` to Story Memory.
- A new node, graph edge, provider, model, dependency, persisted field, database migration, or
  schema-version bump.
- Multiple permanent forms, shapeshifters, or a character whose body permanently transforms during
  the story. One frozen canonical reference cannot represent those states.
- ADR-042's Gouache/Comic/Cut-paper policy. Its implementation and validation remain separate.

---

## 2. Contract and transient boundary

### 2.1 Story Memory contract

- **Reads:** `input.redacted_text`; existing `characters[].name`, `characters[].description`,
  `style.prompt_fragment`, `reference_retry`, `story_id`, and `cost`.
- **Writes:** the existing `characters[]` and `cost` outputs owned by `analyze` and `char_bible`.
- **Does not add or change:** a `StoryMemory` field, reducer, enum, ID convention, schema version,
  checkpoint shape, or database column.

`Character.name` remains authoritative for text/UI identity and character-to-scene binding.
`Character.char_id` remains authoritative for internal identity, reference paths, checkpoint resume,
and targeted redraw selection. Neither is deleted or rewritten by this feature.

### 2.2 Analyzer-only structured fields

`ExtractedDescription` gains two required trimmed, non-placeholder, single-line fields, each capped
at 120 Unicode code points so the same value remains usable as a reveal chip. They exist only in the
strict structured-output schema used by `analyze`:

- **`body_plan`** — the stable whole-subject silhouette and construction: torso or central mass,
  limbs/supports, proportions, and material arrangement. It must describe the kind of body the
  character actually has.
- **`face_or_interface`** — the stable visible head, face, sensory interface, or positively worded
  faceless surface. Examples include `round metal head with two blue LED eyes`, `short muzzle with
  triangular ears`, and `smooth unbroken front surface with no separate face`.

Both values are permanent physical facts, not current pose, expression, damage, lighting, weather,
style/rendering effects, or story action. Structural geometry and components belong here; colour
belongs in `colours`, while clothing remains in `clothing`. Keeping each morphology phrase atomic
reduces the chance that ADR-035 drops an entire body/face definition because one bundled adjective
is forbidden by the selected style. The fields are required for people, animals, robots, fantasy
creatures, vehicles, and personified objects alike.

Before the existing discriminator-floor check, `analyze` constructs a candidate persisted
`body_features` in this order:

1. `body_plan`;
2. `face_or_interface`;
3. existing additional `body_features` in model-return order;
4. exact duplicate strings removed in first-seen order.

The existing three-discriminator/two-axis validator evaluates the folded candidate, so the two
morphology values count as `body_features` while a second populated axis is still required. After
validation, the transient fields and existing `is_humanoid` are discarded.

For this feature, `is_humanoid` is derived from the resolved canonical body plan, whether copied
from the story or safely filled once. A human or humanlike torso/body plan sets it true and therefore
keeps the existing clothing requirement. Mere speech, walking, or emotion is insufficient; an
ordinary animal or non-human-shaped machine remains false. The flag does not decide whether a face
is human.

### 2.3 Invariants

1. Every fresh structured character has trimmed, single-line `species`, `body_plan`, and
   `face_or_interface` values that are neither blank nor one of the existing description
   placeholders (`none`, `neutral`, `unknown`, `unspecified`). `body_plan` and
   `face_or_interface` are each at most 120 Unicode code points.
2. The existing floor of at least three visual discriminators across at least two of `colours`,
   `body_features`, and `clothing` remains.
3. A humanoid still has nonempty clothing under the existing safety rule.
4. A spoken line, smile, emotion, occupation, or proper name does not establish permanent anatomy.
5. Explicit story morphology wins. An explicitly human-faced robot or upright clothed animal keeps
   that stated design.
6. Missing permanent morphology is invented once by `analyze`, then persisted. `char_bible` never
   invents a second body or face design.
7. The folded morphology reaches normal draw, targeted draw, and reference judge prompts through
   the existing `body_features` axis.
8. Fresh valid descriptions never need a name as a visual fallback.

---

## 3. Position and data flow

```text
redacted story
  → analyze: one strict structured call
      → required body_plan + face_or_interface
      → fold into CharacterDescription.body_features
  → segment: unchanged; names map scenes to char_ids
  → char_bible
      → name-free physical description → Fal reference draw
      → same name-free physical description → reference judge
      → existing contradiction/text-free acceptance loop
  → moderation → reveal: display name unchanged; empty-chip fallback becomes name-free
  → scene loop: unchanged
```

The deep seam remains `CharacterDescription`: downstream modules learn no new interface. The extra
structure exists only where missing visual facts are already authorized to be created.

---

## 4. Behavior and edge cases

### 4.1 Analyzer rules

The extraction instruction must state all of the following:

- treat a character name as an identifier only;
- do not infer age, gender, ethnicity, body, face, clothing, or temperament from a name;
- do not treat speech, pronouns, jobs, actions, or emotions as permanent appearance;
- `smiled` requests an expression in that moment, not a human mouth or human face;
- copy every stated permanent physical fact without alteration;
- when the story is silent, choose one neutral, child-safe, drawable design once;
- keep nonpeople species-appropriate unless the story explicitly anthropomorphizes them;
- prefer positive visible morphology over a bare prohibition.

The story may establish physical kind through explicit personhood, kinship, species, construction,
or other narrative context. When it does not, `analyze` may choose one neutral child-safe kind as
part of its existing fill-once authority. A name or pronoun alone cannot supply that choice.

Thus a faceless subject should use `smooth unbroken front surface` rather than only `no face`, while
a robot may use `single camera lens` or `simple LED display` rather than an unspecified “robot face.”

### 4.2 Canonical-reference projection

For fresh valid descriptions, both the normal reference path and ADR-029 targeted redraw path render
only:

- `species`;
- `colours`;
- `body_features`, including folded body/face morphology;
- `clothing`;
- the existing reference framing and non-human guards;
- the selected style fragment;
- the targeted `ReferenceRetry.attribute`, on a targeted redraw only.

The prompt assembler does not directly concatenate `Character.name`; `CharacterDescription.notes`
is also absent. No deterministic string filter removes a name echoed inside a physical field:
character names such as `Blue`, `Tiny`, `Star`, and `Bolt` can also be legitimate appearance words,
and explicit story morphology must win. Analyzer guidance discourages identifier-shaped echoes;
the exact Jamie/Bolt Tier-B gate catches `Leo` leakage. The child-facing reveal still displays the
redacted name, but it is not physical evidence.

The existing unconditional non-human generator guard remains defense in depth. It does not become a
new judge-only rule. Instead, the positive persisted `body_plan` and `face_or_interface` make visible
human/lion anatomy an explicit contradiction when it conflicts with canon.

Changing the judge's assessed subject requires `JUDGE_PROMPT_VERSION` to change from 5 to 6. Historical
verdict counts from earlier versions must not pool with the new series.

For the motivating character, the intended shape is equivalent to:

```text
robot, small box-shaped metal body with short hinged limbs and a blue chest button,
rounded metal head with two circular blue LED lenses
```

`Leo` is absent. Exact punctuation remains an implementation detail; the required projection and
attribute parity do not.

### 4.3 Legacy checkpoints

Existing minted references are not redrawn. `char_bible` keeps its idempotent skip.

A contract-legal legacy character takes the name fallback only when its name-free projection of
`species`, `colours`, `body_features`, and `clothing` is empty after placeholder removal and the
existing ADR-035 reference filtering. A legacy `species="robot"` therefore does not need `Leo`.
This exception avoids a new terminal failure and does not apply to fresh validated analysis. Logs
record only `char_id` and a fallback boolean, never the name, story, or full prompt.

Reveal chips have a different fallback. If placeholder/style filtering removes every offered axis,
`reveal` offers the fixed chip `overall physical appearance`, not `Character.name`. A targeted redraw
therefore cannot reintroduce a fresh pseudonym through `ReferenceRetry.attribute`. This narrowly
amends ADR-029's chip fallback without changing reveal payload shape, tap count, pause behavior, or
the displayed character name.

### 4.4 Character classes

| Case | Required result |
|---|---|
| Small robot named `Leo` | `Leo` is absent from reference model calls; mechanical body and interface are explicit. |
| Robot that “smiles” | Expression does not imply a human face; the chosen mechanical interface remains permanent. |
| Explicit human-faced robot | Preserve the stated human-like face; do not apply the ordinary non-human default against it. |
| Ordinary talking animal | Speech does not imply an upright body, clothes, hands, or a human face. |
| Explicit anthropomorphic animal | Preserve stated upright posture, clothing, hands, or other human-like features. |
| Faceless star/cloud/vehicle | Persist a positive surface/interface design; do not invent mascot limbs or a face. |
| Human with sparse description | Fill neutral permanent body/face details once; existing clothing rule remains. |
| Two same-species characters | Analyzer guidance asks for distinct missing details unless the story says they are identical; no semantic uniqueness guarantee is added. |
| Identical twins/robots | Preserve stated identity; do not force artificial visual difference. |
| Permanent transformation | Unsupported by one frozen canon; requires a separate per-scene appearance-state design. |
| Old checkpoint with sparse canon | Resume unchanged; legacy fallback may still expose the pseudonym to model calls. |

### 4.5 Provider and validation failures

- Invalid analyzer structure uses `providers.structured_text`'s existing single schema re-ask.
- A valid but semantically poor morphology remains a Tier-B quality failure; CI cannot judge it.
- Image-generation failure, judge exception, three-draw fallback, moderation, and reveal pause/tap
  behavior remain as frozen; only the empty-chip value changes under ADR-041.
- No second text model is called when extraction is weak. Evidence must first identify whether the
  miss belongs to analyzer canon, Fal adherence, reference judging, or later scene editing.

---

## 5. Cross-cutting checklist

- [x] **CC-2 PII redaction** — Presidio is not bypassed based on fictional status; `analyze` and
  canonical-reference calls consume redacted identity. This feature does not repair the inherited
  gap that raw text is stored in `jobs.input_text` before Presidio or that input moderation
  classifiers receive the original text.
- [x] **CC-3 Cost control** — no successful-path model/image call, retry, or budget term is added.
  The existing schema re-ask remains the only invalid-output retry.
- [x] **CC-5 Observability** — add log-only `EXTRACTION_PROMPT_VERSION = 1` (the first recorded
  series; older runs remain unversioned) and record it with the existing analyzer completion log;
  persist reference judge prompt version as today; log only
  `char_id` plus a boolean when legacy name fallback fires. Never log the full story, full prompt,
  name, signed URL, or image.
- [x] **CC-10 Checkpointing/resumability** — Story Memory is unchanged; existing references skip;
  old sparse descriptions remain readable.
- [ ] **CC-1 Moderation ordering** — unchanged.
- [ ] **CC-4 Security** — no new asset, URL, table, or policy.
- [ ] **CC-6 Accessibility** — captions/narration unchanged.
- [ ] **CC-7 Reproducibility** — still unsatisfied because Fal remains unseeded. Tier-B records
  prompt versions and every attempt without claiming deterministic causality.
- [x] **CC-8 Kid vs teacher design** — the reveal display name remains, folded morphology becomes
  child-facing retry chips, and the empty list uses the short fixed `overall physical appearance`
  chip. The 120-code-point field cap and standalone-chip tests protect the new payload values; no
  payload shape or screen changes.
- [ ] **CC-9 Failure states** — current fail-open reference policy remains pending D-Q.

---

## 6. Deterministic tests — Tier A

All provider/model/image calls are mocked. Tests assert contracts and prompt projections, never
generated-image quality.

### 6.1 Analyzer boundary

1. `species`, `body_plan`, and `face_or_interface` are required, trimmed, non-placeholder, and
   single-line; both morphology fields reject values over 120 Unicode code points.
2. The extraction prompt says names, speech, actions, and emotions are not appearance evidence.
3. A mocked robot result folds body plan and interface into `body_features` in declared order.
4. Exact duplicate folded/additional body features appear once, preserving first-seen order.
5. The existing three-discriminator/two-axis and humanoid-clothing validation still fires.
6. Persisted `CharacterDescription` contains no new field and serializes under schema version 1.
7. Only one successful structured-text call occurs.
8. The extraction prompt contains the neutral-kind rule for stories that do not explicitly state
   physical kind and forbids using a name/pronoun alone as evidence.
9. Mocked `is_humanoid=False` ordinary-animal/non-human-machine results may omit clothing, while a
   mocked `is_humanoid=True` human/anthropomorphic result still fails without clothing.
10. Both folded morphology phrases survive the active Gouache projection in the robot fixture.
11. The log-only extraction prompt version is `1` and reaches the completion log.

### 6.2 Canonical-reference projection

1. A fresh robot named `Leo` does not directly supply `Leo` to the normal Fal prompt.
2. The same prompt contains species, body plan, face/interface, other axes, and style.
3. The reference judge subject contains the same persisted morphology and no character name.
4. A targeted redraw excludes the name and appends the explicit emphasis clause once. The selected
   value may also remain in the base identity axes, as ADR-039 requires.
5. A human reference remains fully described by species/axes/clothing without its name.
6. Narrative notes and placeholder values remain absent.
7. Existing framing, negative prompt, three-draw cap, best-of order, cost counting, Storage path,
   moderation status reset, and skip-existing behavior remain unchanged.
8. `JUDGE_PROMPT_VERSION == 6` and is persisted on new verdicts.
9. Legacy fallback covers a fully empty projection, while species-only and partially populated
   legacy descriptions remain name-free; an already-minted legacy reference still skips.
10. When every fresh reveal chip is style-filtered away, the fixed `overall physical appearance`
    chip reaches targeted redraw and the name does not.
11. A targeted legacy redraw follows the same projection predicate and neutral chip rule.
12. Folded body/face phrases are offered as concise, standalone reveal chips and survive targeted
    restatement without being concatenated into one unreadable chip.
13. Legacy fallback logging contains `char_id`/boolean only, never name, story, or prompt.

### 6.3 Integration regression

A pipeline fixture injects the known redacted Andres/Leo story and proves:

- analyzer input and `Character.name` contain `Leo`;
- the robot's persisted description contains explicit mechanical body and interface facts;
- both normal reference model calls omit the identifier and contain no `Leo`;
- character ID, reference path, reveal display name, captions, and scene binding remain unchanged;
- no new provider call, graph node, edge, or image attempt occurs;
- a separate scene-prompt assertion documents that `Leo` still appears there under D-P's non-goal.

Existing Presidio tests continue owning recognizer behavior. This feature does not pin
`Bolt → Leo` as a new deterministic contract because pseudonym assignment depends on exact story
bytes and recognizer output; it tests the downstream behavior once `Leo` is the redacted name.

Full backend verification remains `uv run ruff check . && uv run pytest` from `backend/`.

---

## 7. Tier-B quality check

Run after deterministic tests, never in CI. Use Gouache explicitly so the check does not mix this
feature with ADR-042's style-policy implementation. Review all reference attempts and the completed scene pages, not
only selected winners.

### 7.1 Fixtures

1. The exact Jamie/Bolt story supplied with the production report.
2. An ordinary talking animal with a human- or animal-coded pseudonym but no anthropomorphic anatomy.
3. An explicitly anthropomorphic nonhuman with stated anatomical/clothing evidence such as an
   upright humanoid torso, hands, clothing, or a human-like face. Expression alone does not qualify.

### 7.2 Record

For each character, record the redacted display name, persisted physical axes, exact prompt version,
three reference attempts where applicable, every reference verdict, selected reference, moderation
result, reveal choice, and visible identity across final scene attempts. Do not publish raw child PII.

### 7.3 Hard retention gates

Retain the change only if:

1. fresh canonical-reference assembly does not directly inject `Character.name`, and the exact
   Jamie/Bolt reproduction contains no `Leo` in its draw or judge prompt;
2. the persisted canon explicitly states a body plan and face/interface for every fixture;
3. the selected Jamie/Bolt reference has a mechanical, non-human face/interface consistent with
   the persisted canon;
4. an ordinary animal is not given unstated human anatomy;
5. explicitly stated anthropomorphic traits are preserved rather than stripped;
6. every morphology mismatch observed by the human reviewer is listed as a judge contradiction. A
   recorded judge miss is honest reporting but fails this retention gate;
7. the book completes inside existing call, image, and recursion bounds;
8. captions, reveal names, character binding, moderation order, and reference-conditioned scene
   generation remain functional.

### 7.4 Escalation by failing layer

| Observed failure | Next decision; do not substitute a prompt-writing LLM |
|---|---|
| Analyzer returns weak/contradictory morphology despite required fields | Consider a structured canon critic/repair call in a new ADR and matched evaluation. |
| Canon is correct but Fal ignores it | Revisit generator/style/reference acceptance, not text prompt ownership. |
| Judge observes mismatch but returns no contradiction | Fix/evaluate the judge under ADR-004 and Objective-4 constraints. |
| Reference is correct but scene prompts reintroduce name-driven drift | Resolve D-P: deterministic neutral aliases across all model-facing scene surfaces. |
| All draws fail or judge is unavailable | Resolve D-Q: fail-open, reveal-hold, or fail-closed reference policy. |

A second LLM is justified only when the first row is repeatedly observed. If introduced, it must
return structured canon at the existing analyzer seam, define replay persistence and failure policy,
use an open-weight model, and beat this design in a matched quality/cost/latency comparison. A
free-form prompt writer is not an accepted escalation.

---

## 8. Linked decisions, documentation, and implementation gate

### 8.1 Decisions

- **ADR-011:** Presidio remains mandatory before downstream processing.
- **ADR-023:** Story Memory remains the sole persisted inter-module contract.
- **ADR-028 / ADR-034:** contradiction-list reference acceptance and three-draw best-of remain.
- **ADR-035:** style filtering remains.
- **ADR-039 / ADR-040:** typed axes, not narrative notes, own character appearance.
- **Proposed ADR-041:** names are text identifiers, not canonical visual identity; explicit
  morphology is created at the existing analyzer boundary.
- **D-P:** broader scene-model aliasing, deferred pending scene-drift evidence.
- **D-Q:** reference failure posture, deferred because it changes completion behavior.
- **ADR-042:** selectable-style policy, independently accepted; implementation pending.

ADR-041 changes canonical-reference generation and reference-acceptance inputs before Objective-4
pair creation. Pre- and post-ADR-041 reference distributions must not be silently pooled. If any
pairs already exist, preserve and version the split or regenerate them before labelling, and disclose
the distribution change under the frozen pre-registration. The pre-registered scene-judge model,
schema, endpoint, and held-out evaluation rules remain unchanged.

### 8.2 Implementation documentation blast radius

When ADR-041 is accepted and implementation is authorized, the same behavior change must update:

- `docs/specs/story-analyzer.md` — transient schema, morphology rules, folding, edge cases, tests;
- `docs/specs/character-bible.md` — name-free projection, targeted path, legacy fallback, prompt
  version, tests, and Tier-B result;
- `docs/specs/kid-flow-pause-lifecycle.md` — folded morphology chips, fixed empty-chip fallback, and
  targeted-redraw tests;
- `docs/specs/visual-prompt-reliability.md` — replace the pseudonymized-nonhuman gap with a link to
  this spec while retaining scene-name and fail-open residuals;
- any capstone/design document claiming that names are part of canonical visual identity.

Frozen historical ADRs are not edited. Executed plans remain historical.

### 8.3 Definition of done

This feature is done only when:

1. ADR-041 is explicitly accepted by the owner;
2. this spec is owner-approved;
3. a disposable implementation plan is written under `docs/specs/plans/`;
4. implementation follows TDD and all §6 assertions pass;
5. backend lint and full deterministic tests pass;
6. the §7 Tier-B check is run and every hard gate passes, or the change is revised without a quality
   claim;
7. all affected live specs and status surfaces are reconciled;
8. the disposable plan is deleted after implementation, verification, and documentation complete.

**Not done** if Presidio is bypassed; `Character.name` is directly injected into a fresh canonical
draw or reference judge; the Jamie/Bolt reproduction sends `Leo` to either; body
or face morphology is invented in `char_bible`; a second prompt-writing LLM is added; Story Memory,
the graph, model/provider, retry budget, style policy, or failure posture changes inside this feature;
tests assert generated quality; or the three-fixture check is described as population-level evidence.

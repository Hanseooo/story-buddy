# Scene-judge investigation — October 2026

Dated investigation for GitHub #121, recorded 2026-10-13. Source snapshot: `origin/main`
`c0390bee`. This is a bounded development investigation, not a new product/research status source
or an Objective-4 result. Canonical status remains in [PHASE_05_RESULTS](../product/PHASE_05_RESULTS.md),
[PREREGISTRATION_OBJ4](../product/PREREGISTRATION_OBJ4.md), and the [research runbook](research_runbook.md).

## Scope and evidence

The question is whether retry feedback preserves the intended scene, and whether camera, setting,
and Paper Cutout criticisms identify stated violations rather than unstated preferences.
No production prompt, judge, gate, ranking, schema, model, provider, or behavior is changed here.
Generation prompt version is 7 after merged PR126. Both scene identity and scene-constraint judge
versions remain 4. PR124 scoped legacy identity corrections to the visible scene cast; PR125
retained per-reference attribution; PR126 distinguished named cast from requested background groups.
The merged changes are [PR124](https://github.com/Hanseooo/story-buddy/pull/124),
[PR125](https://github.com/Hanseooo/story-buddy/pull/125), and
[PR126](https://github.com/Hanseooo/story-buddy/pull/126).
These changes are engineering protections, not proof of image-quality improvement. See
[prompt optimizer](../../backend/pipeline/prompt_optimizer.py),
[regenerate](../../backend/pipeline/regenerate.py), and [checker](../../backend/pipeline/consistency_check.py).

This source snapshot does not establish the live worker revision or its deployed configuration.
The owner-supplied examples use Paper Cutout (`cut_paper`), not Cartoon (`cel`). Broad visual
coherence does not establish compliance with explicit camera or rendering requirements.

Evidence types are kept separate:

- Source/spec traces establish what inputs, gates, corrections, and selection rules do.
- Selected synthetic train/validation bundles establish recorded requirements, verdicts, and attempts.
- Hash-verified local images support explicitly **AI-assisted visual review**, not human labels.
  Three Sol subagents assisted separate reviews; the lead agent checked the reported source,
  images and replay results. This is not independent human agreement.
- Local deterministic replays can establish mechanical consequences of removing an entry, not
  whether that entry is correct or what a different generated image would look like.
- Private screenshots supply symptom context only. The owner confirmed the original job trace is
  unavailable. They are not public attachments or research examples. Gallery position is not a
  scene ID, and a displayed retry is not necessarily the selected final. Original-job resolution
  and the correctness of its visible corrections cannot be established without its prior asset.

Only synthetic `train`/`val` material was opened, with `run.json` metadata checked before memory.
No donated or held-out material, secret files, provider calls, paid draws, or human labels were used.
The locally retained bundle paths are `data/judge/corpus/runs/<run>/{run,memory,assets}.json`.
Assets resolve relative to `data/judge/corpus`, not relative to the run directory. Their availability
on this machine is not a committed-artifact dependency or a promise of public redistribution.

## Six investigation axes

### Named cast and background groups

Current generation version 7 (PR126) permits explicitly requested background groups alongside the
named cast. Pigeons in `syn-003/s3` are requested scene content, not an extra named protagonist.
Its old version-4 exact-character clause is not the current rule. Source checks establish the
distinction, not image realization or resolution of the unavailable private job.

### Off-scene attributes

The historical `syn-003` train bundle has generation version 4 and both judges at version 4.
In `s3`, attempt 1 records `wrong_body_feature` and no scene contradictions. Attempt 2 appends a
whole-roster body correction that includes the off-scene gardener's hat and gloves; those accessories
are visibly acquired. This is compatible with roster contamination, but an uncontrolled draw does
not establish its causal contribution. PR124 prevents that correction source in current code.
PR125 keeps referenced-subject failure reasons associated with caller-owned character IDs, including
clean checks, rather than applying a folded reason to every referenced character. Legacy checkpoints
retain a scene-scoped fallback. These protections do not rewrite old bundles.
They also do not semantically validate the scene judge's free-text contradiction subjects or
claims; a structured identity correction and a scene contradiction are different inputs.

### Orientation, elevation, and framing

Selected traces expose cross-axis comparisons: `syn-003/s3` attempt 3 contrasts a higher camera angle
with required `three-quarter`; `syn-024/s4` attempt 1 contrasts front/medium framing with a low angle.
Orientation, elevation, and framing can coexist, so those descriptions alone need not conflict.
The former arrives at the three-attempt cap and buys no further draw. Removing its one camera entry
changes contradiction count 10 to 9 but leaves attempt 1 selected. The latter feeds two clauses into
attempt 2; three other contradictions still trigger retry, and removing the two changes recorded
counts 5/7/7 to 3/7/7 without changing the selected attempt 1. These are selection consequences,
not corrected-image predictions. `syn-003/s1` attempt 1, profile versus facing the viewer, supplies a
plausible AI-reviewed orientation-conflict control among four recorded contradictions. A reviewed control explicitly
combining orientation and elevation is missing. See [pose/viewpoint spec](../specs/pose-viewpoint-composition.md).

### Correct subject and requested action

`syn-003/s3` fixes counting pigeons with stone fingers, concentrated expression, and slightly raised
wings. Attempt 2 shows pigeons and hand interaction alongside acquired accessories. Attempt 3 loses
the pigeons/counting interaction despite the preserved Visual direction clause. Its prompt starts
from the immutable base and includes only the latest attempt's corrections; it does not accumulate
the old body complaint. Multiple corrections, reference defects, and sampling variance compete as
explanations. The chain shows a preservation failure, not the effect of a single style/camera clause.
See [visual-prompt reliability](../specs/visual-prompt-reliability.md).

### Permanent setting and temporary state

The location extractor asks for permanent features, but its boundary validates nonblank content rather
than independently classifying permanence. The scene checker asks to allow temporary differences
supported by a later excerpt, yet ADR-040's generation projection excludes the narrative excerpt and
ADR-047 supplies that immutable visual base to the checker. This leaves an information-channel gap.
In validation `syn-027/s0`, frozen classroom canon includes a broken radio even though the scene's
`objects_present` is empty. The Setting prose still supplies the requirement. Attempt 1 is criticized
for a functional radio; functionality is not established by the image alone. Attempt 2 receives that correction, preserves crossed arms/frown, passes,
and is selected. The radio first appears later in the narrative already broken. This demonstrates
the requirement channel and retry driver, but does **not** prove it was intact or absent earlier.
Narrative prematurity remains uncertain. Text-only, unviewed controls include train `syn-021`
(night/stars canon reaching a morning scene), validation `syn-028` (rain/sheltering/eating alone
versus later sharing), and train `syn-023` (shipwreck broken windows as plausible persistent damage).
These are candidates for review, not visual findings. See [setting spec](../specs/setting-consistency.md)
and [ADR-040](../product/adr/ADR-040-narrative-notes-do-not-enter-scene-image-prompts.md).

### Paper Cutout style

Two different style signals must remain distinct. The per-reference identity judge compares linework,
shading, and colouring technique while ignoring background, composition, pose, crop, and expression.
`wrong_style` is nongating and `style_match` ranks last. The scene-constraint judge checks the immutable
generation prompt, including its explicit style fragment; any contradiction gates, and clean/fewer
composition contradictions rank before identity. Matching the reference can therefore coexist with
violating the ideal fragment, especially when the reference itself departs from that fragment.

AI visual review of `syn-003/s3` found mixed support. Its grey canon within a warm environment is not
alone a palette violation. Attempt 2 has defensible dimensional-shadow concerns, but “digital” alone
is not a prohibited technique, and absence of *subtle* paper fibre at display scale is uncertain.
Attempt 3 visibly has cool blue architecture, dimensional rendering, and unintended lettering.
The reference itself has soft dimensional edge/drop shadows. In selected train control `syn-006`,
`s0` attempt 1 has flat colour blocks, visible grain, silver canon and warm cabinetry, with a logged
pass and empty contradictions. `s3` attempt 2 has enclosing contours and glossy watery marks, with
both style mismatch and fragment criticism. Its reference also has a dimensional cast shadow.
These selected examples support both legitimate technique deviations and possible overreach.

The filter derives prohibited lexemes only from `no ...` clauses. Cut-paper prohibits outlines,
gradients, glossy highlights, and dimensional shadows; grey, blue, and silver are not filtered out.
It does not erase grey canon to enforce “limited warm palette.” See [config](../../backend/app/config.py),
[prompt optimizer](../../backend/pipeline/prompt_optimizer.py), [style spec](../specs/style-presets.md),
[ADR-007](../product/adr/ADR-007-style-as-a-fixed-constant-carried-by-the-character.md),
[ADR-022](../product/adr/ADR-022-selectable-art-style-presets-three-prompt-fragment.md), and
[ADR-035](../product/adr/ADR-035-the-style-fragment-s-own-prohibitions-filter-the.md).

## Calibration and limits of the instrument

Structured `subject/required/observed` contradictions make checklist echoes harder to express, but
do not establish semantic correctness. No independent human calibration labels were obtained.
Agreement between AI reviewers is not a substitute. Neither logged pass counts nor selected
examples are outcome measures or corpus quality rates. Reference imperfections, generator drift,
overliteral canon/palette interpretation, visibility uncertainty, and unseeded variance remain
competing explanations. See [ADR-004](../product/adr/ADR-004-consistency-via-vlm-as-judge-control-loop-human-ratings.md),
[ADR-049](../product/adr/ADR-049-the-scene-constraint-judge-returns-structured-contradictions-not-free-text-labels.md),
[judge fine-tune spec](../specs/judge-finetune.md), and [annotation spec](../specs/annotation-surface.md).

## Verification and completion boundary

SHA-256 checks matched manifest digests before viewing `syn-003` reference `ref-c0-1` and scene
`s1-1`/`s3-1/2/3`, `syn-024/s4-1`, `syn-006` reference `ref-c0-2` and scenes `s0-1`/`s3-2`,
and validation `syn-027/s0-1/2`. All 11 reviewed assets match their recorded digests.
Commands used metadata-first PowerShell JSON reads, repository `rg` searches, `Get-FileHash -Algorithm
SHA256`, and read-only image inspection. This documentation-only investigation did not run provider
smokes or quality experiments. Parent-agent replays through current `_rank` confirmed the two
camera-removal selection results, exact suspect clauses in the next prompt where one exists,
and the clean-base/latest-attempt omission on the following retry. All recorded generation,
identity, and constraint versions for these four captures were asserted as 4/4/4, using the
captured `google/gemma-3-27b-it` judge. Current source generation version 7 is not pooled with them.

Capture code commits: `syn-003` `1ddf1ce`, `syn-024` `f2048a4`, `syn-006` `c1f0557`,
`syn-027` `56d7f4c`. Full commits and manifests remain in each local bundle's `run.json` and
`assets.json`; the files were neither altered nor uploaded.

`uv sync --frozen` checked 133 packages. Existing analyze, segment, prompt optimizer, consistency
check, and regeneration tests ran through `uv run python -` / `pytest.main`, with dotenv disabled,
placeholder credentials and provider mocks: **453 passed**. No new tests or test infrastructure
were added for this documentation change. An initial replay rejected a mismatched capitalization
assumption about a captured string; reading its exact text and rerunning passed. This was a
diagnostic-harness correction, not a pipeline fix. No replay establishes human correctness or a
prompt effect.

Fresh full backend verification: `uv run ruff check .` passed; pytest through the same guarded
`uv run python -` invocation reported **1,489 passed, 87 skipped, six smoke tests deselected**.
Skipped checks need live database/research artifacts. One existing Starlette deprecation warning
remains. Frontend source is untouched; PR CI supplies its lint/build/test verification.

## Alternatives, review criteria, and recommendation

The smallest option is bounded documentation resolution with remaining human calibration recorded.
A prospective judge-prompt clarification would need versioning, approval of its exact scope, and
matched-input evaluation; a gate/rank demotion changes accepted selection policy and needs its own
decision. String-filtering contradiction prose risks hiding legitimate faults and conflicts with
ADR-047/049's boundary rationale. Changing the style fragment or adding a style exemplar changes
the rendering target or adds provenance/cost concerns under ADR-022. Replacing the judge or using
held-out examples for development would violate the registered baseline/evaluation boundaries.

Proposed fixed human-review criteria: distinguish orientation, elevation, and framing; require a
visible conflict on the stated axis; separate persistent setting facts from narrative state; retain
canon colours while assessing palette as a composition; judge explicit technique prohibitions with
visible evidence; mark subtle texture/occluded details uncertain; compare reference style separately
from fragment compliance; and track whether corrections preserve action and visible cast.

Before any independent human labels, freeze the permitted sample and these criteria. Show the
requirements, canonical references and evaluated asset first, hiding the stored verdict and
correction; then reveal the trace for comparison. Record each claimed violation as supported,
unsupported or uncertain, with the responsible subject/axis and observed action. Keep this
development worksheet separate from frozen Objective-4 annotations. The AI review here was
exploratory and unblinded; these prospective criteria do not retrospectively make it a human or
blinded study.

Acceptance criteria for this investigation: trace each claim to its owning source or identified
synthetic attempt; distinguish AI review from independent labels; report correction/selection
consequences without causal image claims; keep private and held-out material out; and leave prompts,
versions, gates, ranking, and research status unchanged. Remaining work is independent human review
and prospective matched controls, including combined orientation/elevation and canon-neutral palette
cases. Any later prompt-effect claim follows [ADR-055](../product/adr/ADR-055-a-prompt-change-is-measured-by-rate-not-read-off-a-page.md).
Recommendation: resolve the present task as bounded documentation, with calibration still outstanding,
not as a judge fix or proof that the unavailable original job is fixed.

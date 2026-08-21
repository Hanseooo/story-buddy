# Lessons Log

> Updated after every correction. Reviewed at session start.

## Patterns
<!-- Format:
### [Date] [Short description of mistake/insight]
- **What happened**: ...
- **Root cause**: ...
- **Rule**: Never do X. Always do Y instead.
-->

### 2026-07-10 Ran `ruff format` on a repo that does not use it
- **What happened**: After editing `spikes/phase_05.py` I ran `ruff format`, which rewrapped the
  whole file to its default 88-column width. A ~60-line change became 176 insertions of unrelated
  reformatting. Caught it in `git diff --stat`, reverted, and reapplied the edits by hand.
- **Root cause**: I assumed a formatter was in use because a linter was. There is no `[tool.ruff]`
  block, no pre-commit config, and no CI reference to it anywhere in the repo. `ruff check` passing
  says nothing about `ruff format` being the project's style.
- **Rule**: Never run a formatter unless the repo configures one (`pyproject.toml`, `.pre-commit-config`,
  CI). Verify with a grep first. Match the file's existing line width instead — long lines that the
  linter accepts are a deliberate style, not an oversight. (Global guidelines §3, CLAUDE.md §6.)

### 2026-07-10 A probe that passes while the thing it probes is broken
- **What happened**: Phase 0.5's `structured` probe validated the VLM judge with a **text-only** call.
  The judge is only ever invoked with two images. OpenRouter's structured-output support is per
  `(model, provider)` *and* per modality, so the probe would have printed PASS while the judge was
  broken. Root cause was deeper: `providers.py` had no multimodal path at all.
- **Root cause**: The probe tested the *model id*, not the *call shape the system actually makes*.
- **Rule**: A probe must exercise the exact call shape production uses — same modality, same message
  parts, same schema. If writing the probe reveals the production function doesn't exist yet, that is
  the finding. Ask "what would this probe let me believe that is false?"

### 2026-08-14 Do not turn a product-quality goal into a research harness
- **What happened**: The user wanted to improve observed pipeline consistency, but the initial S1
  discussion centered on corpus size, statistical strength, and paid baseline runs.
- **Root cause**: I followed the docket's measurement posture before confirming whether its level of
  evidence matched the user's immediate goal.
- **Rule**: For quality work, first ask whether the user needs a research claim or targeted product
  improvement. Concrete observed failures can drive a repro-based design without a paid corpus run;
  record the weaker attribution honestly instead of imposing unused rigor.

### 2026-08-15 Separate pasted context from the actual reproduction input
- **What happened**: A second story was included in the bug report for context but was not part of
  the end-to-end run. Treating both stories as runtime input would have widened the diagnosis.
- **Root cause**: I had not yet distinguished the pasted material from the exact provider payload.
- **Rule**: Before attributing prompt contamination across stories, anchor the diagnosis to the
  exact logged prompt and confirm which source text actually entered the run.

### 2026-08-17 Distinguish retiring a preset from retiring its catalog slot
- **What happened**: I framed removing Comic as permanently shrinking the selectable catalog, while
  the user intended to test a more consistent replacement before making that replacement official.
- **Root cause**: I treated the named preset and the product's three-choice slot as the same decision.
- **Rule**: When a selectable option is removed for quality, ask whether the catalog should shrink or
  the slot should enter quarantine pending a replacement; do not silently make either permanent.

### 2026-08-21 Authenticated role defaults need an end-to-end trace
- **What happened**: Error-page logout recovery was added, but the researcher could still land on the
  student-only surface because the auth flow had separate role-blind fallbacks: an incompatible
  `next`, a silent profile-query failure, and the teacher resolver's non-teacher redirect.
- **Root cause**: The earlier verification covered clean unauthenticated routing and isolated role
  tests, but not an already-authenticated researcher traversing `/login` → `/classroom` → `/s/<id>`.
- **Rule**: For auth bugs, trace both the fresh-login and stale-session paths through middleware,
  server layouts, and role resolution; never use a student route as the unknown-profile fallback.

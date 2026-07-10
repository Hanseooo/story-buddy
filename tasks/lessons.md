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

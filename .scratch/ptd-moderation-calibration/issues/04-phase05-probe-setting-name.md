# 04 — The phase_05 text moderation probe reads the current setting

**Status:** ready-for-agent
**Type:** task
**Progress:** done
**Blocked by:** None
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §7](../../../docs/specs/moderation-stack.md)
**What to build:** `uv run python -m spikes.phase_05 moderation` reaches its classifier calls
instead of failing on a missing settings attribute.
**Source criteria:** §7 "`spikes/phase_05.py:434` also still reads `settings.moderation_model` …
separate fix"; §9.5 evidence bullet on the old probe.
**Scope:** `backend/spikes/phase_05.py` `moderation()` and its docstring.
**Out of scope:** An image arm, a labelled replay set or production-path replay harness — audit
[01](01-audit-moderation-false-alarms.md) owns those (OD-09). Running the probe against real
classifiers (paid; needs owner cost approval).
**Complexity:** Low — a renamed setting.
**Blast radius:** Local — a spike script; no production path imports it.
**Unblocks:** None

## Context

`moderation_model` was split into `moderation_primary_model` and `moderation_backstop_model`
(Issue #28). The probe still reads the old name, so the pre-Phase-2 text gate cannot run at all.
Verified 2026-10-26: `backend/spikes/phase_05.py:434` is `models = [settings.moderation_model]`.

## Read first

- `backend/spikes/phase_05.py` — `moderation()`: model list and the stale docstring at line ~432
  saying the backstop "stays unset until ADR-011's backstop is amended".
- `backend/app/config.py` — `Settings`: the four moderation model fields.

## Behavior this changes

None. No test covers the spike.

## Acceptance criteria

- [ ] `moderation()` builds its model list from `moderation_primary_model` and
      `moderation_backstop_model`; no reference to `moderation_model` remains in `backend/`
      outside `.venv` (grep).
- [ ] The docstring no longer claims the backstop is unset.

## Guidance

The probe uses a different call path from `input_gate` (§9.5); do not present its output as
production-path evidence.

## Verification

$0 check: `cd backend && uv run python -c "import spikes.phase_05 as p; from app.config import settings; print(settings.moderation_primary_model, settings.moderation_backstop_model)"`
plus the grep above. A real run is paid: report it as not run unless the owner approves its cost.
**Targeted:** `cd backend && uv run ruff check spikes/phase_05.py`
**Full suite:** at the batch gate.

## Blocked by

None.

## Comments

Implemented 2026-10-26. The zero-cost import/settings check passes, backend lint passes,
and the backend search finds no use of the removed `moderation_model` field. The paid
classifier probe was not run. Batch-suite results are recorded in `CHANGELOG.md`.

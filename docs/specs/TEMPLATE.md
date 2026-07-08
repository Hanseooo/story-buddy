# Feature Spec — <module name>

**Status:** draft | approved | built · **Phase:** <0–3> · **Owner node:** `backend/pipeline/<file>.py`
**Derived from:** MASTER_SPEC §2 (system map) · **Rationale:** ADR-XXX, PRD §X

> One spec = one module = one LangGraph node = one concern. Keep it short. Delete any section
> that genuinely doesn't apply — don't pad.

## 1. Purpose
One or two sentences: what this module does and why it exists.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)
- **Reads:** `<fields it consumes>`
- **Writes:** `<fields it produces>`
- **Invariants:** what must be true of its output (validated by Pydantic / tests).

## 3. Position in the system map
Which node feeds it, which it feeds, and any conditional edge it owns
(only moderation pass/fail or consistency pass/fail — ADR-003).

## 4. Behavior & edge cases
Happy path in a few steps, then the edge cases it must handle
(short/messy/over-length input, model refusal, empty result, etc.).

## 5. Cross-cutting checklist (MASTER_SPEC §5)
Tick the ones this module touches and say *how* it satisfies each:

- [ ] CC-1 Moderation ordering
- [ ] CC-2 PII redaction
- [ ] CC-3 Cost control
- [ ] CC-4 Security (RLS + signed URLs)
- [ ] CC-5 Observability
- [ ] CC-6 Accessibility
- [ ] CC-7 Reproducibility (seed)
- [ ] CC-8 Kid vs parent design
- [ ] CC-9 Failure states = success states
- [ ] CC-10 Checkpointing / resumability

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)
List the assertions with **models mocked**. Never assert on generated content here.

## 7. Eval / quality checks (if fuzzy — MASTER_SPEC §6 Tier B)
Only if the module produces content whose quality is subjective (scene choice, consistency,
caption fidelity). Say which RQ/metric it feeds and how it's measured on the corpus. Otherwise: "N/A".

## 8. Linked decisions & open questions
- ADRs / PRD sections this depends on.
- Anything unresolved — flag it, don't guess (CLAUDE.md §1, §7).

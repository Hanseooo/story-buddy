# StoryBuddy — AI Operating Contract

Read this every session before touching code. These are **hard rules**, not suggestions.
This file complements the global `~/.claude/CLAUDE.md` behavioral guidelines — it does not restate them.

For *how the system connects* and *why* decisions were made, read `docs/MASTER_SPEC.md`
(the reference) and `docs/product/` (PRD, ADRs, ROADMAP — the source of truth). This file
only holds the guardrails you must never cross.

---

## 1. The architecture is locked

Every decision in `docs/product/ADRs.md` is **frozen**. Do not refactor around a decision,
swap a library, or change the pipeline shape because a different approach seems cleaner.

- To change a locked decision: **write a new ADR** (append to `docs/product/ADRs.md`) stating
  context / decision / consequences / alternatives, and **flag it to the human**. Do not
  implement the change until the ADR is accepted.
- If a task seems to *require* violating an ADR, stop and surface the conflict. Don't guess.

## 2. Contract-first

The **Story Memory schema** (`backend/contracts/`) is the contract between every pipeline
module. It is Pydantic and it is authoritative.

- Validate against it at **every LLM boundary** (Gemini structured output → Pydantic, always).
- A module reads its inputs and writes its outputs **through the schema**, never via ad-hoc dicts.
- Changing the schema is a contract change: update the schema, the affected specs, and every
  consumer in the same change.

## 3. Testing bright line

Two kinds of tests. Never mix them (see MASTER_SPEC §6).

- **Deterministic tests** (vitest / pytest / Playwright): **mock Gemini and Nano Banana.**
  Never assert on generated content ("is the character consistent?" is not a unit test).
  These run in CI and **must stay green** — a change that reddens CI is not done.
- **Eval harness** (offline, real models, story corpus): the only place fuzzy quality is
  measured. Never put it in CI. It doubles as research instrumentation (LangSmith/Langfuse).

## 4. The feature spec is the unit of work

Before writing code for a module, read its spec in `docs/specs/` **and** the cross-cutting
concerns registry (MASTER_SPEC §5). If a spec doesn't exist yet, write it from
`docs/specs/TEMPLATE.md` and get it approved before implementing.

- Behavior change → update the spec **in the same change**. Specs that lie are worse than none.

**Artifact hygiene (one home per type — avoid noise):**
- Superpowers `brainstorming` writes feature specs into **`docs/specs/`** — never a parallel
  `docs/superpowers/` tree. `writing-plans` writes into **`docs/specs/plans/`**.
- **Specs are durable, plans are disposable.** Keep and update specs (they're the contract).
  **Delete a plan once its module is built + tests green + spec updated** — git keeps the history.
  `docs/specs/plans/` should only ever contain *in-flight* work.
- To build a module, load only **`CLAUDE.md` + that module's spec + the CC registry** — not the
  whole docs tree. Lean context = better output.

## 5. Safety non-negotiables (child-facing product)

- **No unmoderated generated image ever reaches a child** — including the canonical character
  reference before the reveal. Moderation order: input text → char-ref → output image.
- **PII is redacted (Presidio) before** storage, captioning, or export. A child narrating real
  life is the expected case, not the exception.
- **RLS on every table**; signed URLs for every asset; no public buckets.
- Failure and moderation screens get the **same** design care as success screens.

## 6. Maintainability

- **Deterministic LangGraph nodes.** No autonomous-agent routing; conditional edges only at
  moderation pass/fail and consistency pass/fail (ADR-003).
- **One module = one concern**, one file per pipeline node. A node that sprawls across
  responsibilities is doing too much — split it. Rough ceiling: if a file passes ~300 lines or
  mixes concerns, that's the signal to split, not a hard limit to game.
- **No parallel structures.** One canonical location per artifact type (specs, plans, ADRs, code).
  Don't create a second folder that does the same job — the agent then has to reconcile two truths.
- **Follow the map.** New pipeline module → a file in `backend/pipeline/`; anything crossing a
  module boundary → through `backend/contracts/`. Don't invent new top-level folders without a reason.
- Match existing style. Touch only what the task requires. Don't "improve" adjacent code.
- No speculative abstraction — no interface with one implementation, no config for a value that
  never changes. (Global guidelines §2, §3 apply.)

## 7. When in doubt

Stop and ask one focused question. Surfacing a confusion is cheaper than a wrong build.
